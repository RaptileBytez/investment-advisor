"""Value investing — fundamentals-based screen.

For the MVP we apply absolute thresholds on P/E, P/B, debt/equity,
dividend yield, and free-cash-flow yield. Each signal is a 0/0.5/1 vote;
the composite is their mean. Once we have sector-medians data we'll
switch to *relative* comparisons (cheap vs. sector) which is a stronger
value signal — that lands in a follow-up.

Requires fundamentals; the recommendation engine will skip this
strategy when fundamentals are unavailable."""

from __future__ import annotations

from typing import ClassVar

import pandas as pd

from app.data.provider import Fundamentals
from app.strategies.base import Strategy, StrategyResult, Verdict, clamp01


class ValueStrategy(Strategy):
    name: ClassVar[str] = "value"
    requires_fundamentals: ClassVar[bool] = True

    # Thresholds — exposed as class attrs for easy tuning / testing.
    PE_CHEAP: ClassVar[float] = 12.0
    PE_FAIR: ClassVar[float] = 22.0
    PB_CHEAP: ClassVar[float] = 1.5
    PB_FAIR: ClassVar[float] = 3.5
    DE_LOW: ClassVar[float] = 50.0          # yfinance reports D/E as a percentage
    DE_HIGH: ClassVar[float] = 200.0
    DIV_HIGH: ClassVar[float] = 0.03        # 3 % dividend yield
    DIV_LOW: ClassVar[float] = 0.005        # 0.5 %
    FCF_HIGH: ClassVar[float] = 0.06        # 6 % FCF yield

    def score(
        self,
        ticker: str,
        history: pd.DataFrame,
        fundamentals: Fundamentals | None = None,
        *,
        lang: str = "en",
    ) -> StrategyResult:
        if fundamentals is None:
            raise ValueError(f"{ticker}: value strategy requires fundamentals")

        signals: dict[str, float] = {}

        # P/E — prefer trailing; fall back to forward.
        pe = fundamentals.trailing_pe or fundamentals.forward_pe
        signals["pe"] = _bucket(pe, low=self.PE_CHEAP, high=self.PE_FAIR, prefer="low")

        # P/B
        signals["pb"] = _bucket(
            fundamentals.price_to_book, low=self.PB_CHEAP, high=self.PB_FAIR, prefer="low"
        )

        # Debt/Equity
        signals["debt_to_equity"] = _bucket(
            fundamentals.debt_to_equity, low=self.DE_LOW, high=self.DE_HIGH, prefer="low"
        )

        # Dividend yield — higher is better (within reason; >10% is a warning, not a treat)
        dy = fundamentals.dividend_yield
        if dy is None:
            signals["dividend_yield"] = 0.5
        elif dy >= self.DIV_HIGH and dy < 0.12:
            signals["dividend_yield"] = 1.0
        elif dy >= self.DIV_LOW:
            signals["dividend_yield"] = 0.5
        elif dy >= 0.12:
            signals["dividend_yield"] = 0.3     # implausibly high — likely a value trap
        else:
            signals["dividend_yield"] = 0.2

        # Free-cash-flow yield — higher is better
        fcfy = fundamentals.free_cash_flow_yield
        if fcfy is None:
            signals["fcf_yield"] = 0.5
        elif fcfy >= self.FCF_HIGH:
            signals["fcf_yield"] = 1.0
        elif fcfy >= 0.02:
            signals["fcf_yield"] = 0.6
        elif fcfy >= 0:
            signals["fcf_yield"] = 0.4
        else:
            signals["fcf_yield"] = 0.1

        composite = clamp01(sum(signals.values()) / len(signals))

        if composite >= 0.65:
            verdict = Verdict.BUY
        elif composite >= 0.45:
            verdict = Verdict.HOLD
        else:
            verdict = Verdict.SELL

        rationale = _explain(fundamentals, signals, composite, lang)

        return StrategyResult(
            strategy=self.name,
            ticker=ticker.upper(),
            verdict=verdict,
            score=composite,
            rationale=rationale,
            key_inputs={
                "trailing_pe": fundamentals.trailing_pe,
                "price_to_book": fundamentals.price_to_book,
                "debt_to_equity": fundamentals.debt_to_equity,
                "dividend_yield": fundamentals.dividend_yield,
                "fcf_yield": fundamentals.free_cash_flow_yield,
                **{f"signal_{k}": v for k, v in signals.items()},
            },
        )


def _bucket(value: float | None, *, low: float, high: float, prefer: str) -> float:
    """Score a single ratio. `prefer='low'` means below `low` is bullish."""
    if value is None or value <= 0:
        return 0.5     # unknown
    if prefer == "low":
        if value <= low:
            return 1.0
        if value <= high:
            return 0.6
        return 0.2
    if prefer == "high":
        if value >= high:
            return 1.0
        if value >= low:
            return 0.6
        return 0.2
    return 0.5


def _explain(
    fundamentals: Fundamentals, signals: dict[str, float], score: float, lang: str
) -> str:
    pe = fundamentals.trailing_pe or fundamentals.forward_pe
    pe_str = f"{pe:.1f}" if pe else "n/a"
    pb_str = f"{fundamentals.price_to_book:.1f}" if fundamentals.price_to_book else "n/a"
    dy_str = f"{fundamentals.dividend_yield * 100:.1f}%" if fundamentals.dividend_yield else "n/a"
    if lang == "de":
        if score >= 0.65:
            return (
                f"Günstig in mehreren Kennzahlen (KGV {pe_str}, KBV {pb_str}, "
                f"Dividende {dy_str}). Lohnt einen genaueren Blick für eine Value-Position."
            )
        if score >= 0.45:
            return (
                f"Fair bewertet: KGV {pe_str}, KBV {pb_str}, Dividende {dy_str}. "
                f"Weder offensichtlich günstig noch teuer."
            )
        return (
            f"Teuer im Value-Screen: KGV {pe_str}, KBV {pb_str}, Dividende {dy_str}. "
            f"Entweder wachstumsbewertet oder die Fundamentaldaten verschlechtern sich."
        )
    # English (default)
    if score >= 0.65:
        return (
            f"Cheap on multiple measures (P/E {pe_str}, P/B {pb_str}, dividend {dy_str}). "
            f"Worth a closer look for a value position."
        )
    if score >= 0.45:
        return (
            f"Fair-value zone: P/E {pe_str}, P/B {pb_str}, dividend {dy_str}. "
            f"Neither obviously cheap nor expensive."
        )
    return (
        f"Expensive on the value screen: P/E {pe_str}, P/B {pb_str}, dividend {dy_str}. "
        f"Either growth-priced or fundamentals are deteriorating."
    )
