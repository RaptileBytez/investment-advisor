"""YFinance-backed implementation of `DataProvider`.

Wraps the `yfinance` library — free, no API key, supports US + European +
Asian markets via ticker suffixes (`SAP.DE`, `BP.L`, `7203.T` …).

Caveats handled here:
- yfinance is unofficial and prone to transient errors. We surface them as
  `ProviderError` so callers can react uniformly.
- `info` dict shape varies between releases; every getter is defensive.
- Quote responses are cached for `Settings.quote_cache_ttl_seconds` to keep
  the UI snappy and avoid rate-limit pressure.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, ClassVar

import pandas as pd

from app.core.cache import TTLCache
from app.core.config import get_settings
from app.data.exchanges import info_for
from app.data.provider import DataProvider, Fundamentals, ProviderError, Quote, TickerInfo

log = logging.getLogger(__name__)

try:
    import yfinance as yf
except ImportError as exc:  # pragma: no cover - exercised only on broken installs
    raise ImportError(
        "yfinance is required for YFinanceProvider. Install via `pip install yfinance`."
    ) from exc


_settings = get_settings()
_quote_cache: TTLCache[Quote] = TTLCache(ttl_seconds=_settings.quote_cache_ttl_seconds)
_history_cache: TTLCache[pd.DataFrame] = TTLCache(
    ttl_seconds=_settings.history_cache_ttl_hours * 3600
)
_fundamentals_cache: TTLCache[Fundamentals] = TTLCache(
    ttl_seconds=_settings.history_cache_ttl_hours * 3600
)


def _safe_float(value: Any) -> float | None:
    """yfinance sometimes returns numpy NaN, '–', or weird sentinels for
    missing data. Normalise everything to None."""
    try:
        if value is None:
            return None
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN check
        return None
    return f


def _normalise_dividend_yield(value: Any) -> float | None:
    """yfinance ≥0.2.61 reports dividendYield as a percentage (e.g. 1.83 = 1.83 %)
    while older versions returned it as a decimal (0.0183). Downstream code
    expects a *decimal* throughout. Anything above 1.0 is almost certainly the
    percent form (real sustainable dividend yields top out around 12 %)."""
    f = _safe_float(value)
    if f is None:
        return None
    if f > 1.0:
        f /= 100.0
    return f


class YFinanceProvider(DataProvider):
    name: ClassVar[str] = "yfinance"

    # ── Search ────────────────────────────────────────────────
    def search(self, query: str, *, region: str | None = None, limit: int = 10) -> list[TickerInfo]:
        if not query.strip():
            return []
        try:
            results: list[TickerInfo] = []
            # yfinance.Search is available in 0.2.40+. Older installs fall back
            # to validating the literal ticker as a guess.
            search_cls = getattr(yf, "Search", None)
            if search_cls is not None:
                raw = search_cls(query, max_results=limit).quotes
                for item in raw[:limit]:
                    symbol = item.get("symbol")
                    if not symbol:
                        continue
                    ex = info_for(symbol)
                    if region and ex.region != region.upper():
                        continue
                    results.append(
                        TickerInfo(
                            ticker=symbol,
                            name=item.get("shortname") or item.get("longname") or symbol,
                            exchange=item.get("exchDisp") or ex.exchange,
                            region=ex.region,
                            currency=item.get("currency") or ex.currency,
                        )
                    )
                return results
            # Fallback: try query as an exact ticker.
            try:
                info = self._ticker_info(query.upper())
                ex = info_for(query.upper())
                return [
                    TickerInfo(
                        ticker=query.upper(),
                        name=info.get("shortName") or info.get("longName") or query.upper(),
                        exchange=info.get("exchange") or ex.exchange,
                        region=ex.region,
                        currency=info.get("currency") or ex.currency,
                    )
                ]
            except ProviderError:
                return []
        except Exception as exc:
            log.warning("yfinance search failed for %r: %s", query, exc)
            raise ProviderError(f"search failed: {exc}") from exc

    # ── Quote ─────────────────────────────────────────────────
    def get_quote(self, ticker: str) -> Quote:
        ticker = ticker.upper()
        cached = _quote_cache.get(ticker)
        if cached is not None:
            return cached
        try:
            tk = yf.Ticker(ticker)
            fi = tk.fast_info
            price = _safe_float(getattr(fi, "last_price", None))
            prev = _safe_float(getattr(fi, "previous_close", None))
            currency = getattr(fi, "currency", None) or info_for(ticker).currency
            if price is None:
                raise ProviderError(f"no price available for {ticker}")
            q = Quote(
                ticker=ticker,
                price=price,
                currency=currency,
                timestamp=datetime.now(UTC),
                previous_close=prev,
            )
            _quote_cache.set(ticker, q)
            return q
        except ProviderError:
            raise
        except Exception as exc:
            log.warning("yfinance quote failed for %s: %s", ticker, exc)
            raise ProviderError(f"quote failed for {ticker}: {exc}") from exc

    # ── History ───────────────────────────────────────────────
    def get_history(
        self,
        ticker: str,
        *,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        ticker = ticker.upper()
        cache_key = f"{ticker}|{period}|{interval}"
        cached = _history_cache.get(cache_key)
        if cached is not None:
            return cached.copy()
        try:
            df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
            if df is None or df.empty:
                raise ProviderError(f"no history for {ticker}")
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.index = pd.to_datetime(df.index)
            _history_cache.set(cache_key, df)
            return df.copy()
        except ProviderError:
            raise
        except Exception as exc:
            log.warning("yfinance history failed for %s: %s", ticker, exc)
            raise ProviderError(f"history failed for {ticker}: {exc}") from exc

    # ── Fundamentals ──────────────────────────────────────────
    def get_fundamentals(self, ticker: str) -> Fundamentals:
        ticker = ticker.upper()
        cached = _fundamentals_cache.get(ticker)
        if cached is not None:
            return cached
        info = self._ticker_info(ticker)
        ex = info_for(ticker)

        market_cap = _safe_float(info.get("marketCap"))
        op_cf = _safe_float(info.get("operatingCashflow"))
        capex = _safe_float(info.get("capitalExpenditures"))
        fcf_yield: float | None = None
        if market_cap and op_cf is not None and capex is not None:
            fcf = op_cf + capex  # capex is negative in yfinance
            fcf_yield = fcf / market_cap if market_cap else None

        result = Fundamentals(
            ticker=ticker,
            currency=info.get("currency") or ex.currency,
            market_cap=market_cap,
            trailing_pe=_safe_float(info.get("trailingPE")),
            forward_pe=_safe_float(info.get("forwardPE")),
            price_to_book=_safe_float(info.get("priceToBook")),
            debt_to_equity=_safe_float(info.get("debtToEquity")),
            dividend_yield=_normalise_dividend_yield(info.get("dividendYield")),
            free_cash_flow_yield=fcf_yield,
            eps=_safe_float(info.get("trailingEps")),
            sector=info.get("sector"),
            industry=info.get("industry"),
        )
        _fundamentals_cache.set(ticker, result)
        return result

    # ── Internals ─────────────────────────────────────────────
    def _ticker_info(self, ticker: str) -> dict[str, Any]:
        try:
            info = yf.Ticker(ticker).info or {}
            if not info:
                raise ProviderError(f"empty info for {ticker}")
            return info
        except ProviderError:
            raise
        except Exception as exc:
            log.warning("yfinance info failed for %s: %s", ticker, exc)
            raise ProviderError(f"info failed for {ticker}: {exc}") from exc
