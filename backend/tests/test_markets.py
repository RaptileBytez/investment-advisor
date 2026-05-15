"""Market-discovery tests — universe loader, scoring, service, and API."""

from __future__ import annotations

import pytest

from app.db.models import RiskTolerance
from app.markets import scoring, service, universe
from tests.conftest import falling_ohlcv, rising_ohlcv


# ──────────────────────────────────────────────────────────────
# Universe loader
# ──────────────────────────────────────────────────────────────
def test_universe_loads_each_index_file():
    """All six bundled JSONs must parse and contribute entries."""
    entries = universe.load_universe()
    # Should include US + DE + GB + FR + JP at minimum.
    regions = {e.region for e in entries}
    assert {"US", "DE", "GB", "FR", "JP"}.issubset(regions)
    # Sanity floor: the curated lists ship hundreds of tickers; if one of
    # the JSON files breaks, this test should fail loudly.
    assert len(entries) > 200


def test_universe_filters_by_region():
    de = universe.load_universe("DE")
    assert len(de) > 30
    assert all(e.region == "DE" for e in de)
    # SAP is the load-bearing canary for the German section.
    assert any(e.ticker == "SAP.DE" for e in de)


def test_universe_deduplicates_overlapping_indices():
    """Tickers that appear in both Dow 30 and S&P 500 should appear once."""
    entries = universe.load_universe("US")
    tickers = [e.ticker for e in entries]
    assert len(tickers) == len(set(tickers))


def test_available_regions_sorted():
    regions = universe.available_regions()
    assert regions == sorted(regions)


# ──────────────────────────────────────────────────────────────
# Lightweight scoring
# ──────────────────────────────────────────────────────────────
def test_scoring_ranks_rising_above_falling():
    rising = scoring.compute_signals("RISE", rising_ohlcv())
    falling = scoring.compute_signals("FALL", falling_ohlcv())
    assert rising is not None and falling is not None
    assert rising.light_score > falling.light_score
    assert rising.above_200 is True
    assert falling.above_200 is False


def test_scoring_requires_minimum_history():
    short_df = rising_ohlcv(n=50)
    assert scoring.compute_signals("SHORT", short_df) is None


def test_top_by_score_orders_descending():
    sigs = [
        scoring.LightSignals(
            ticker=f"T{i}", last_close=100.0, return_1m=0.0, return_12_1=0.0,
            sma_50=0.0, sma_200=0.0, above_200=False, golden_cross=False,
            volatility_20d=0.0, light_score=score,
        )
        for i, score in enumerate([0.4, 0.9, 0.1, 0.7])
    ]
    top = scoring.top_by_score(sigs, limit=3)
    assert [s.light_score for s in top] == [0.9, 0.7, 0.4]


# ──────────────────────────────────────────────────────────────
# Service — movers + picks (mocked provider)
# ──────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _clear_caches():
    """Each test runs with a clean cache so 1-hour TTLs don't leak across
    cases that exercise the same region."""
    service.invalidate_caches()
    yield
    service.invalidate_caches()


def _quote(ticker: str, price: float, prev: float):
    from datetime import UTC, datetime

    from app.data.provider import Quote
    return Quote(
        ticker=ticker.upper(),
        price=price,
        currency="USD",
        timestamp=datetime.now(UTC),
        previous_close=prev,
    )


def test_indices_snapshot_returns_per_region_quotes(fake_provider):
    # Seed all five indices so the snapshot can populate.
    for t in ("^GSPC", "^GDAXI", "^FTSE", "^FCHI", "^N225"):
        fake_provider.quotes[t] = _quote(t, 5000.0, 4900.0)
    snaps = service.indices_snapshot(fake_provider)
    assert {s.ticker for s in snaps} == {"^GSPC", "^GDAXI", "^FTSE", "^FCHI", "^N225"}
    for s in snaps:
        assert s.change_pct is not None
        assert s.change_pct == pytest.approx((5000 - 4900) / 4900)


def test_indices_snapshot_drops_missing_indices(fake_provider):
    """Rate-limited or stale indices should be skipped, not 500 the request."""
    fake_provider.quotes["^GSPC"] = _quote("^GSPC", 5000.0, 4900.0)
    # No other indices seeded.
    snaps = service.indices_snapshot(fake_provider)
    assert [s.ticker for s in snaps] == ["^GSPC"]


def test_top_movers_sorts_gainers_descending(fake_provider):
    # SAP.DE is in the curated DE universe.
    fake_provider.quotes["SAP.DE"] = _quote("SAP.DE", 200.0, 100.0)    # +100%
    fake_provider.quotes["BMW.DE"] = _quote("BMW.DE", 105.0, 100.0)    # +5%
    fake_provider.quotes["BAS.DE"] = _quote("BAS.DE", 90.0, 100.0)     # -10%
    gainers = service.top_movers(fake_provider, region="DE", kind="gainers", limit=5)
    tickers_in_order = [g.ticker for g in gainers]
    assert tickers_in_order[0] == "SAP.DE"
    # BMW should rank above BAS for gainers.
    assert tickers_in_order.index("BMW.DE") < tickers_in_order.index("BAS.DE")


def test_top_movers_losers_sorts_ascending(fake_provider):
    fake_provider.quotes["SAP.DE"] = _quote("SAP.DE", 200.0, 100.0)    # +100%
    fake_provider.quotes["BMW.DE"] = _quote("BMW.DE", 90.0, 100.0)     # -10%
    fake_provider.quotes["BAS.DE"] = _quote("BAS.DE", 80.0, 100.0)     # -20%
    losers = service.top_movers(fake_provider, region="DE", kind="losers", limit=5)
    assert losers[0].ticker == "BAS.DE"
    assert losers[0].change_pct < losers[1].change_pct


def test_top_movers_rejects_unknown_kind(fake_provider):
    with pytest.raises(ValueError):
        service.top_movers(fake_provider, region="DE", kind="weirdest")


def test_top_picks_returns_only_buy_verdicts(fake_provider, monkeypatch):
    """The engine is invoked across pre-filtered candidates; only BUY actions
    survive into the final list, sorted by confidence."""
    # Pretend the cheap signal pass returned three candidates.
    fake_signals = [
        scoring.LightSignals(
            ticker=t, last_close=100.0, return_1m=0.05, return_12_1=0.25,
            sma_50=100.0, sma_200=90.0, above_200=True, golden_cross=True,
            volatility_20d=0.20, light_score=0.8,
        )
        for t in ("SAP.DE", "BMW.DE", "BAS.DE")
    ]
    monkeypatch.setattr(service, "scan_universe", lambda *a, **kw: fake_signals)

    # Engine stub: SAP=BUY high conf, BMW=HOLD, BAS=BUY low conf.
    from app.recommendation.engine import FinalVerdict, RiskSummary
    from app.strategies.base import Verdict

    def fake_evaluate(self, ticker, *, risk_tolerance, lang, history_period="5y"):
        if ticker == "SAP.DE":
            action, conf = Verdict.BUY, 0.85
        elif ticker == "BAS.DE":
            action, conf = Verdict.BUY, 0.66
        else:
            action, conf = Verdict.HOLD, 0.55
        return FinalVerdict(
            ticker=ticker,
            action=action,
            confidence=conf,
            rationale=f"{ticker} mocked rationale.",
            risk_summary=RiskSummary(
                volatility=0.2, sharpe=1.0, beta=1.0, max_drawdown=-0.1,
                value_at_risk_95=-0.02, benchmark="DAX", risk_free_rate=0.03,
            ),
            strategy_results=[],
        )

    monkeypatch.setattr(
        "app.markets.service.RecommendationEngine.evaluate", fake_evaluate
    )
    # Seed quotes so the post-evaluate quote lookup doesn't blank prices.
    for t in ("SAP.DE", "BMW.DE", "BAS.DE"):
        fake_provider.quotes[t] = _quote(t, 100.0, 99.0)

    picks = service.top_picks(
        fake_provider,
        region="DE",
        risk_tolerance=RiskTolerance.BALANCED,
        lang="en",
        limit=10,
    )
    tickers = [p.ticker for p in picks]
    assert "BMW.DE" not in tickers       # HOLD filtered out
    assert tickers == ["SAP.DE", "BAS.DE"]  # sorted by confidence desc


def test_top_picks_cached_across_calls(fake_provider, monkeypatch):
    """Pass 1 (cheap signals) must only run once per (region) within the TTL."""
    call_count = {"n": 0}

    def counting_scan(*args, **kwargs):
        call_count["n"] += 1
        return []

    monkeypatch.setattr(service, "scan_universe", counting_scan)
    service.top_picks(
        fake_provider, region="DE",
        risk_tolerance=RiskTolerance.BALANCED, lang="en", limit=5,
    )
    service.top_picks(
        fake_provider, region="DE",
        risk_tolerance=RiskTolerance.BALANCED, lang="en", limit=5,
    )
    # Two service calls, but only one underlying scan_universe call thanks
    # to the per-(region) signal cache + pick cache.
    assert call_count["n"] <= 1


# ──────────────────────────────────────────────────────────────
# API endpoints
# ──────────────────────────────────────────────────────────────
def test_api_indices_returns_quotes(wired_client):
    client, fp, _ = wired_client
    fp.quotes["^GSPC"] = _quote("^GSPC", 5000.0, 4900.0)
    resp = client.get("/api/markets/indices")
    assert resp.status_code == 200
    body = resp.json()
    assert any(s["ticker"] == "^GSPC" for s in body)


def test_api_movers_endpoint(wired_client):
    client, fp, _ = wired_client
    fp.quotes["SAP.DE"] = _quote("SAP.DE", 110.0, 100.0)  # +10%
    fp.quotes["BMW.DE"] = _quote("BMW.DE", 95.0, 100.0)   # -5%
    resp = client.get("/api/markets/movers?region=DE&kind=gainers&limit=5")
    assert resp.status_code == 200
    body = resp.json()
    tickers = [m["ticker"] for m in body]
    assert "SAP.DE" in tickers
    # SAP should outrank BMW for gainers.
    if "BMW.DE" in tickers:
        assert tickers.index("SAP.DE") < tickers.index("BMW.DE")


def test_api_movers_rejects_bad_kind(wired_client):
    client, _, _ = wired_client
    resp = client.get("/api/markets/movers?kind=weirdest")
    assert resp.status_code == 422


def test_api_top_picks_threads_lang(wired_client, monkeypatch):
    """The Top Picks endpoint must forward the requested lang to the engine
    so the rationale comes back in the right language."""
    client, fp, _ = wired_client
    captured = {}

    fake_signals = [
        scoring.LightSignals(
            ticker="SAP.DE", last_close=100.0, return_1m=0.05, return_12_1=0.25,
            sma_50=100.0, sma_200=90.0, above_200=True, golden_cross=True,
            volatility_20d=0.20, light_score=0.8,
        ),
    ]
    monkeypatch.setattr(service, "scan_universe", lambda *a, **kw: fake_signals)

    from app.recommendation.engine import FinalVerdict
    from app.strategies.base import Verdict

    def fake_evaluate(self, ticker, *, risk_tolerance, lang, history_period="5y"):
        captured["lang"] = lang
        return FinalVerdict(
            ticker=ticker, action=Verdict.BUY, confidence=0.9,
            rationale=f"rationale-{lang}", risk_summary=None, strategy_results=[],
        )

    monkeypatch.setattr(
        "app.markets.service.RecommendationEngine.evaluate", fake_evaluate
    )
    fp.quotes["SAP.DE"] = _quote("SAP.DE", 200.0, 199.0)

    resp = client.get("/api/markets/top-picks?region=DE&lang=de&limit=3")
    assert resp.status_code == 200
    assert captured["lang"] == "de"
    body = resp.json()
    assert body[0]["rationale"] == "rationale-de"
    assert body[0]["action"] == "buy"
