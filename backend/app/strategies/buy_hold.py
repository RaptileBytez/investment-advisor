"""Buy & Hold — favours steady compounders.

Score blends long-term CAGR (higher = better) with annualised volatility
(lower = better). Drawdown is folded in as a penalty so that "high CAGR
but punishing drawdowns" doesn't get a free pass.

Suitable as a conservative default. Works on any price series; does not
need fundamentals."""

from __future__ import annotations

from typing import ClassVar

import pandas as pd

from app.data.provider import Fundamentals
from app.risk.metrics import (
    annualized_volatility,
    cagr,
    daily_simple_returns,
    max_drawdown,
)
from app.strategies.base import Strategy, StrategyResult, Verdict, clamp01


class BuyHoldStrategy(Strategy):
    name: ClassVar[str] = "buy_hold"
    requires_fundamentals: ClassVar[bool] = False

    # Tunable thresholds — exposed as class attributes so tests can override
    # without touching the algorithm.
    MIN_OBSERVATIONS: ClassVar[int] = 60        # ~3 months daily
    HIGH_CAGR: ClassVar[float] = 0.12           # 12% p.a. is "good"
    HIGH_VOL: ClassVar[float] = 0.40            # 40% p.a. is "high"
    DEEP_DRAWDOWN: ClassVar[float] = -0.30      # -30% triggers caution

    def score(
        self,
        ticker: str,
        history: pd.DataFrame,
        fundamentals: Fundamentals | None = None,
    ) -> StrategyResult:
        if "Close" not in history.columns or history.shape[0] < self.MIN_OBSERVATIONS:
            raise ValueError(
                f"{ticker}: need at least {self.MIN_OBSERVATIONS} observations to score buy_hold"
            )

        closes = history["Close"].dropna()
        returns = daily_simple_returns(closes)
        long_term_cagr = cagr(closes)
        vol = annualized_volatility(returns)
        dd = max_drawdown(closes)

        # Normalise each signal to [0, 1] so we can blend them.
        cagr_score = clamp01(long_term_cagr / self.HIGH_CAGR / 2 + 0.5)   # 0 around -HIGH_CAGR, 1 around +HIGH_CAGR
        vol_score = clamp01(1.0 - (vol / self.HIGH_VOL))                   # lower vol → higher score
        dd_score = clamp01(1.0 - (abs(dd) / abs(self.DEEP_DRAWDOWN)))      # shallow DD → higher score

        # Weighted blend — CAGR matters most for a buy-hold investor.
        composite = 0.55 * cagr_score + 0.30 * vol_score + 0.15 * dd_score

        if composite >= 0.65:
            verdict = Verdict.BUY
        elif composite >= 0.40:
            verdict = Verdict.HOLD
        else:
            verdict = Verdict.SELL

        rationale = _explain(long_term_cagr, vol, dd, composite)

        return StrategyResult(
            strategy=self.name,
            ticker=ticker.upper(),
            verdict=verdict,
            score=composite,
            rationale=rationale,
            key_inputs={
                "cagr": long_term_cagr,
                "annualized_volatility": vol,
                "max_drawdown": dd,
                "observations": float(closes.size),
            },
        )


def _explain(cagr_v: float, vol: float, dd: float, score: float) -> str:
    cagr_pct = f"{cagr_v * 100:.1f}%"
    vol_pct = f"{vol * 100:.1f}%"
    dd_pct = f"{dd * 100:.1f}%"
    if score >= 0.65:
        return (
            f"Steady long-term performer: CAGR {cagr_pct}, volatility {vol_pct} p.a., "
            f"max drawdown {dd_pct}. Suited for a buy-and-hold position."
        )
    if score >= 0.40:
        return (
            f"Mixed buy-and-hold profile: CAGR {cagr_pct}, volatility {vol_pct} p.a., "
            f"max drawdown {dd_pct}. Hold if you already own it; tighter screens "
            f"if you're considering a new entry."
        )
    return (
        f"Weak buy-and-hold profile: CAGR {cagr_pct}, volatility {vol_pct} p.a., "
        f"max drawdown {dd_pct}. Trim or avoid if your goal is steady compounding."
    )
