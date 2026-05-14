"""Momentum / trend-following strategy.

Signals (all computed locally — no pandas-ta dependency so we work on
Python 3.14):
- 12-1 momentum: total return over the last 12 months *excluding* the
  most recent month (well-established academic factor).
- RSI(14): Wilder's relative strength index; 50 is neutral, > 70 is
  often overbought, < 30 oversold.
- SMA50 vs SMA200: golden cross (50 above 200) = uptrend; death cross
  = downtrend.

Verdict combines them: a name with positive 12-1, price above SMA200,
and RSI in (50, 70) is a high-conviction BUY. Any major signal flipping
negative drops the verdict toward HOLD or SELL."""

from __future__ import annotations

import math
from typing import ClassVar

import numpy as np
import pandas as pd

from app.data.provider import Fundamentals
from app.strategies.base import Strategy, StrategyResult, Verdict, clamp01


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's RSI computed from daily closes."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Wilder smoothing — exponential moving avg with alpha = 1/n.
    avg_gain = gain.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _twelve_one_momentum(close: pd.Series) -> float:
    """Return over the last ~12 months excluding the most recent ~1 month."""
    if close.size < 252:
        return float("nan")
    t_minus_12 = close.iloc[-252]
    t_minus_1 = close.iloc[-21]
    if t_minus_12 == 0:
        return float("nan")
    return float(t_minus_1 / t_minus_12 - 1)


class MomentumStrategy(Strategy):
    name: ClassVar[str] = "momentum"
    requires_fundamentals: ClassVar[bool] = False
    MIN_OBSERVATIONS: ClassVar[int] = 220  # need SMA200 + a bit

    def score(
        self,
        ticker: str,
        history: pd.DataFrame,
        fundamentals: Fundamentals | None = None,
    ) -> StrategyResult:
        if "Close" not in history.columns or history.shape[0] < self.MIN_OBSERVATIONS:
            raise ValueError(
                f"{ticker}: need at least {self.MIN_OBSERVATIONS} observations to score momentum"
            )

        close = history["Close"].dropna()
        sma50 = close.rolling(50).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1]
        last = float(close.iloc[-1])
        rsi_now = float(_rsi(close).iloc[-1])
        momentum = _twelve_one_momentum(close)

        # Per-signal scoring.
        momentum_score = clamp01(momentum / 0.40 / 2 + 0.5)         # ±40% → [0, 1]
        trend_score = clamp01(((last - sma200) / sma200) / 0.20 + 0.5) if not math.isnan(sma200) else 0.5
        if math.isnan(rsi_now):
            rsi_score = 0.5
        elif rsi_now < 30 or rsi_now > 80:
            rsi_score = 0.2     # oversold or overbought = weak
        elif 50 <= rsi_now <= 70:
            rsi_score = 0.9     # strong but not exhausted
        else:
            rsi_score = 0.6
        cross_bonus = 0.0
        if not math.isnan(sma50) and not math.isnan(sma200):
            cross_bonus = 0.1 if sma50 > sma200 else -0.1

        composite = clamp01(0.4 * momentum_score + 0.3 * trend_score + 0.3 * rsi_score + cross_bonus)

        if composite >= 0.65 and (momentum or 0) > 0 and last > sma200:
            verdict = Verdict.BUY
        elif composite <= 0.35 or (momentum is not None and not math.isnan(momentum) and momentum < -0.10):
            verdict = Verdict.SELL
        else:
            verdict = Verdict.HOLD

        rationale = _explain(momentum, last, sma50, sma200, rsi_now, verdict)

        return StrategyResult(
            strategy=self.name,
            ticker=ticker.upper(),
            verdict=verdict,
            score=composite,
            rationale=rationale,
            key_inputs={
                "twelve_one_momentum": momentum,
                "rsi_14": rsi_now,
                "sma_50": float(sma50) if not math.isnan(sma50) else None,
                "sma_200": float(sma200) if not math.isnan(sma200) else None,
                "last_close": last,
            },
        )


def _explain(
    momentum: float,
    last: float,
    sma50: float,
    sma200: float,
    rsi: float,
    verdict: Verdict,
) -> str:
    mom_pct = f"{momentum * 100:+.1f}%" if not math.isnan(momentum) else "n/a"
    trend = "above its 200-day SMA" if last > sma200 else "below its 200-day SMA"
    cross = "golden cross (SMA50 > SMA200)" if sma50 > sma200 else "death cross (SMA50 < SMA200)"
    rsi_state = (
        "neutral" if 40 <= rsi <= 60
        else "strong" if 60 < rsi <= 70
        else "overbought" if rsi > 70
        else "weak" if 30 <= rsi < 40
        else "oversold"
    )
    if verdict == Verdict.BUY:
        return (
            f"Positive momentum ({mom_pct} over 12-1), price {trend} with a {cross}, "
            f"and RSI {rsi:.0f} ({rsi_state}). Trend is intact."
        )
    if verdict == Verdict.SELL:
        return (
            f"Negative momentum ({mom_pct} over 12-1), price {trend}; RSI {rsi:.0f} "
            f"({rsi_state}). Trend has rolled over."
        )
    return (
        f"Mixed momentum signals: 12-1 {mom_pct}, price {trend}, {cross}, "
        f"RSI {rsi:.0f} ({rsi_state}). Wait for confirmation."
    )
