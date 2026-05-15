"""Markets service — orchestrates indices, movers, and Top Picks.

This is the only module the API layer talks to. It hides:
- the universe loading,
- the two-pass scoring (cheap signals → top N → full engine),
- the 1-hour TTL caches that keep cold-start cost off the user-visible path.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass

from app.core.cache import TTLCache
from app.data.provider import DataProvider, ProviderError, Quote
from app.db.models import RiskTolerance
from app.markets.scoring import LightSignals, scan_universe, top_by_score
from app.markets.universe import UniverseEntry, load_universe
from app.recommendation.engine import FinalVerdict, RecommendationEngine
from app.strategies.base import Verdict

log = logging.getLogger(__name__)

# Heavy passes are cached for 1 hour. Quote-level batches lean on the
# YFinanceProvider's existing 60s quote cache, so we don't double-cache them.
_HOUR = 3600
_signal_cache: TTLCache[list[LightSignals]] = TTLCache(ttl_seconds=_HOUR)
_pick_cache: TTLCache = TTLCache(ttl_seconds=_HOUR)


# Fixed indices snapshot — one per major region in the universe. We keep
# this list explicit (rather than deriving from the universe regions) so
# the ribbon order is deterministic regardless of which region files are
# present.
INDICES: tuple[tuple[str, str, str], ...] = (
    # (yfinance ticker, display name, ISO region)
    ("^GSPC",  "S&P 500",     "US"),
    ("^GDAXI", "DAX",         "DE"),
    ("^FTSE",  "FTSE 100",    "GB"),
    ("^FCHI",  "CAC 40",      "FR"),
    ("^N225",  "Nikkei 225",  "JP"),
)


@dataclass(frozen=True)
class IndexSnapshot:
    ticker: str
    name: str
    region: str
    price: float
    previous_close: float | None
    change: float | None
    change_pct: float | None
    currency: str


@dataclass(frozen=True)
class Mover:
    ticker: str
    name: str
    exchange: str
    region: str
    currency: str
    price: float
    previous_close: float | None
    change: float | None
    change_pct: float | None


@dataclass(frozen=True)
class TopPick:
    ticker: str
    name: str
    exchange: str
    region: str
    currency: str
    price: float
    change_pct: float | None
    action: str
    confidence: float
    rationale: str
    score: float


# ──────────────────────────────────────────────────────────────
# Indices snapshot
# ──────────────────────────────────────────────────────────────
def indices_snapshot(provider: DataProvider) -> list[IndexSnapshot]:
    """Fetch one quote per major index. Uses the batch path so all five
    fire in a single yfinance call when uncached."""
    tickers = [t for t, _name, _region in INDICES]
    quotes = provider.get_quotes_batch(tickers)
    out: list[IndexSnapshot] = []
    for ticker, name, region in INDICES:
        q: Quote | None = quotes.get(ticker)
        if q is None:
            # Index missed the batch; try a single fetch so one stale or
            # rate-limited symbol doesn't blank the whole ribbon.
            try:
                q = provider.get_quote(ticker)
            except ProviderError:
                log.info("indices ribbon: dropping %s (no data)", ticker)
                continue
        out.append(
            IndexSnapshot(
                ticker=ticker,
                name=name,
                region=region,
                price=q.price,
                previous_close=q.previous_close,
                change=q.change,
                change_pct=q.change_pct,
                currency=q.currency,
            )
        )
    return out


# ──────────────────────────────────────────────────────────────
# Top movers
# ──────────────────────────────────────────────────────────────
def top_movers(
    provider: DataProvider,
    *,
    region: str | None = None,
    kind: str = "gainers",
    limit: int = 10,
) -> list[Mover]:
    """Today's biggest gainers or losers from the universe.

    Computed from the change between the latest two daily closes (so
    cheap: one batched download + arithmetic). Result is *not* cached
    here — the underlying provider quote cache (60s) already keeps this
    inexpensive and the freshness expectation for "today's movers" is
    minutes, not hours."""
    if kind not in {"gainers", "losers"}:
        raise ValueError(f"unsupported kind: {kind!r}")
    universe = load_universe(region)
    if not universe:
        return []
    tickers = [e.ticker for e in universe]
    quotes = provider.get_quotes_batch(tickers)
    movers: list[Mover] = []
    by_ticker: dict[str, UniverseEntry] = {e.ticker: e for e in universe}
    for ticker, q in quotes.items():
        if q.change_pct is None:
            continue
        meta = by_ticker.get(ticker)
        if meta is None:
            continue
        movers.append(
            Mover(
                ticker=ticker,
                name=meta.name,
                exchange=meta.exchange,
                region=meta.region,
                currency=q.currency or meta.currency,
                price=q.price,
                previous_close=q.previous_close,
                change=q.change,
                change_pct=q.change_pct,
            )
        )
    reverse = kind == "gainers"
    movers.sort(key=lambda m: m.change_pct or 0.0, reverse=reverse)
    return movers[:limit]


# ──────────────────────────────────────────────────────────────
# Top picks (cached, two-pass)
# ──────────────────────────────────────────────────────────────
def top_picks(
    provider: DataProvider,
    *,
    region: str | None,
    risk_tolerance: RiskTolerance,
    lang: str,
    limit: int = 10,
    candidate_pool: int = 30,
) -> list[TopPick]:
    """Surface the universe's strongest BUY-rated candidates.

    Two-pass design (see scoring.py):
    1. Cheap signal scan across the whole region's universe.
    2. Full engine on the top `candidate_pool` by light score.

    Both passes are cached for 1 hour; pass-2 results are keyed by
    `(ticker, risk_tolerance, lang)` so language flips re-run the
    engine but pass-1 stays warm."""
    region_key = (region or "all").upper()
    cache_key = f"{region_key}|{risk_tolerance.value}|{lang}|{limit}|{candidate_pool}"
    cached = _pick_cache.get(cache_key)
    if cached is not None:
        return cached

    universe = load_universe(region)
    if not universe:
        _pick_cache.set(cache_key, [])
        return []

    # Pass 1 — cheap signals, cached per region only (independent of lang/tol).
    signal_key = f"signals|{region_key}"
    signals = _signal_cache.get(signal_key)
    if signals is None:
        tickers = [e.ticker for e in universe]
        signals = scan_universe(provider, tickers, period="1y")
        _signal_cache.set(signal_key, signals)

    candidates = top_by_score(signals, candidate_pool)
    if not candidates:
        _pick_cache.set(cache_key, [])
        return []

    # Pass 2 — full engine on the candidate pool, keep only BUYs.
    engine = RecommendationEngine(provider)
    by_ticker: dict[str, UniverseEntry] = {e.ticker: e for e in universe}
    picks: list[TopPick] = []
    for sig in candidates:
        meta = by_ticker.get(sig.ticker)
        if meta is None:
            continue
        try:
            verdict: FinalVerdict = engine.evaluate(
                sig.ticker,
                risk_tolerance=risk_tolerance,
                lang=lang,
                history_period="5y",
            )
        except (ProviderError, ValueError) as exc:
            log.info("top-picks: skipping %s (%s)", sig.ticker, exc)
            continue
        if verdict.action != Verdict.BUY:
            continue
        # Quote for the displayed price + today's change.
        quote = None
        with contextlib.suppress(ProviderError):
            quote = provider.get_quote(sig.ticker)
        picks.append(
            TopPick(
                ticker=sig.ticker,
                name=meta.name,
                exchange=meta.exchange,
                region=meta.region,
                currency=meta.currency,
                price=quote.price if quote else sig.last_close,
                change_pct=quote.change_pct if quote else None,
                action=verdict.action.value,
                confidence=verdict.confidence,
                rationale=verdict.rationale,
                score=sig.light_score,
            )
        )
        if len(picks) >= limit:
            break

    picks.sort(key=lambda p: p.confidence, reverse=True)
    _pick_cache.set(cache_key, picks)
    return picks


def invalidate_caches() -> None:
    """Test-only — clears both 1h caches."""
    _signal_cache.invalidate()
    _pick_cache.invalidate()
