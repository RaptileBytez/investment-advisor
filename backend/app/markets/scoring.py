"""Lightweight ranking pass for the Markets discovery feature.

Why this exists: `RecommendationEngine.evaluate()` takes ~3-8 s per ticker
(5-year history + 4 strategies). Running it across the full universe on a
cold cache would take 30+ minutes. We don't need that level of detail
just to rank — we only need to identify the ~30 best candidates the full
engine should then evaluate.

This module:
- Pulls 1y of daily prices for the whole universe in one batched call.
- Computes cheap momentum / trend / volatility signals from price alone
  (no fundamentals).
- Returns a composite `light_score ∈ [0, 1]` per ticker so the caller can
  rank, take top N, and only then invoke the expensive engine.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.data.provider import DataProvider

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class LightSignals:
    ticker: str
    last_close: float
    return_1m: float          # 1-month total return (decimal)
    return_12_1: float        # 12-1 momentum (12m return excluding most recent month)
    sma_50: float
    sma_200: float
    above_200: bool           # close > SMA-200
    golden_cross: bool        # SMA-50 > SMA-200
    volatility_20d: float     # annualised stdev of 20-day daily log returns
    light_score: float        # composite [0, 1]


def _safe_pct_change(series: pd.Series, periods: int) -> float:
    """Return total return over `periods` trailing observations, or NaN."""
    s = series.dropna()
    if len(s) <= periods:
        return float("nan")
    return float(s.iloc[-1] / s.iloc[-1 - periods] - 1.0)


def _annualised_vol_20d(closes: pd.Series) -> float:
    s = closes.dropna()
    if len(s) < 21:
        return float("nan")
    log_returns = np.log(s.iloc[-21:].values[1:] / s.iloc[-21:].values[:-1])
    if log_returns.size == 0:
        return float("nan")
    return float(np.std(log_returns, ddof=1) * math.sqrt(252))


def _sma(closes: pd.Series, window: int) -> float:
    s = closes.dropna()
    if len(s) < window:
        return float("nan")
    return float(s.iloc[-window:].mean())


def _normalise(value: float, lo: float, hi: float) -> float:
    """Linear-clip `value` from [lo, hi] to [0, 1]."""
    if math.isnan(value):
        return 0.5
    if value <= lo:
        return 0.0
    if value >= hi:
        return 1.0
    return (value - lo) / (hi - lo)


def compute_signals(ticker: str, history: pd.DataFrame) -> LightSignals | None:
    """Compute light signals from a daily-OHLCV DataFrame. Returns None if
    insufficient data (fewer than 200 trading days)."""
    if "Close" not in history.columns:
        return None
    closes = history["Close"].dropna()
    if len(closes) < 200:
        return None

    last = float(closes.iloc[-1])
    ret_1m = _safe_pct_change(closes, periods=21)
    # 12-1 momentum: 12-month return excluding the most recent month.
    if len(closes) >= 252:
        ret_12_1 = float(closes.iloc[-21] / closes.iloc[-252] - 1.0)
    else:
        ret_12_1 = float("nan")
    sma50 = _sma(closes, 50)
    sma200 = _sma(closes, 200)
    above_200 = not math.isnan(sma200) and last > sma200
    golden = not math.isnan(sma50) and not math.isnan(sma200) and sma50 > sma200
    vol_20 = _annualised_vol_20d(closes)

    # Composite score: reward strong 12-1 momentum and recent positive return,
    # bonus for trend confirmation (above SMA-200, golden cross), penalty for
    # high recent volatility. Each component is clipped to [0,1] and
    # combined with fixed weights.
    score_mom_12_1 = _normalise(ret_12_1, -0.30, 0.50)
    score_mom_1m   = _normalise(ret_1m,   -0.10, 0.15)
    score_trend    = (0.5 if above_200 else 0.0) + (0.5 if golden else 0.0)
    score_vol_inv  = 1.0 - _normalise(vol_20, 0.15, 0.60)
    light_score = (
        0.40 * score_mom_12_1
        + 0.20 * score_mom_1m
        + 0.25 * score_trend
        + 0.15 * score_vol_inv
    )
    light_score = max(0.0, min(1.0, light_score))

    return LightSignals(
        ticker=ticker,
        last_close=last,
        return_1m=ret_1m if not math.isnan(ret_1m) else 0.0,
        return_12_1=ret_12_1 if not math.isnan(ret_12_1) else 0.0,
        sma_50=sma50 if not math.isnan(sma50) else 0.0,
        sma_200=sma200 if not math.isnan(sma200) else 0.0,
        above_200=above_200,
        golden_cross=golden,
        volatility_20d=vol_20 if not math.isnan(vol_20) else 0.0,
        light_score=light_score,
    )


def scan_universe(
    provider: DataProvider,
    tickers: list[str],
    *,
    period: str = "1y",
) -> list[LightSignals]:
    """Batch-fetch 1y histories and compute light signals across `tickers`.

    Returns one `LightSignals` per ticker that had enough data; missing or
    too-short series are silently skipped (the universe is large enough
    that a handful of misses is fine)."""
    if not tickers:
        return []
    histories = provider.get_histories_batch(tickers, period=period, interval="1d")
    out: list[LightSignals] = []
    for t in tickers:
        df = histories.get(t.upper())
        if df is None:
            continue
        sig = compute_signals(t.upper(), df)
        if sig is not None:
            out.append(sig)
    return out


def top_by_score(signals: list[LightSignals], limit: int) -> list[LightSignals]:
    """Sort descending by composite score and take the first `limit`."""
    return sorted(signals, key=lambda s: s.light_score, reverse=True)[:limit]
