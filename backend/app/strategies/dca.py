"""Dollar-Cost Averaging strategy.

DCA isn't really a per-ticker BUY/SELL signal — it's a *scheduling* answer
to timing risk. The output is therefore a recommendation about how to DCA
into a given ticker plus a simulated outcome over the historical window.

Key result fields:
- verdict.BUY when historical DCA produced positive returns with lower
  drawdown than a lump-sum entry on day 1.
- verdict.HOLD/WATCH if results are mixed.
- verdict.SELL is rare for DCA on a single name and is reserved for cases
  where the asset has consistently destroyed value (no schedule fixes that).

`key_inputs` includes the simulated final value, total invested, average
purchase price, and a comparison vs. lump-sum so the UI can show side-by-side
numbers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import pandas as pd

from app.data.provider import Fundamentals
from app.risk.metrics import max_drawdown
from app.strategies.base import Strategy, StrategyResult, Verdict, clamp01


@dataclass(frozen=True)
class DCASimulation:
    total_invested: float
    units_held: float
    final_value: float
    avg_purchase_price: float
    total_return: float           # decimal, e.g. 0.32 = +32%
    lump_sum_return: float        # buying it all on day 1
    max_drawdown: float           # on the rolling DCA equity curve


def simulate_dca(
    close: pd.Series,
    *,
    per_period_amount: float = 100.0,
    cadence_days: int = 30,
) -> DCASimulation:
    """Simulate buying `per_period_amount` every `cadence_days` days.

    Pure function — fed a price series, returns a `DCASimulation`. Used by
    the strategy *and* by API endpoints that want to show the simulation
    independently of the verdict."""
    if close.size < cadence_days + 1:
        raise ValueError("price series too short for the given cadence")
    schedule = close.iloc[::cadence_days]
    total_invested = 0.0
    units = 0.0
    equity = []
    for _date, price in schedule.items():
        units += per_period_amount / float(price)
        total_invested += per_period_amount
        equity.append(units * float(price))
    final_price = float(close.iloc[-1])
    final_value = units * final_price
    avg_price = total_invested / units if units else float("nan")
    total_return = (final_value / total_invested) - 1 if total_invested else float("nan")
    lump_sum_units = (per_period_amount * len(schedule)) / float(close.iloc[0])
    lump_sum_final = lump_sum_units * final_price
    lump_sum_return = (lump_sum_final / (per_period_amount * len(schedule))) - 1
    dd = max_drawdown(pd.Series(equity)) if len(equity) > 1 else 0.0
    return DCASimulation(
        total_invested=total_invested,
        units_held=units,
        final_value=final_value,
        avg_purchase_price=avg_price,
        total_return=total_return,
        lump_sum_return=lump_sum_return,
        max_drawdown=dd,
    )


class DCAStrategy(Strategy):
    name: ClassVar[str] = "dca"
    requires_fundamentals: ClassVar[bool] = False
    MIN_OBSERVATIONS: ClassVar[int] = 252  # need ~1y to be meaningful
    DEFAULT_AMOUNT: ClassVar[float] = 100.0
    DEFAULT_CADENCE_DAYS: ClassVar[int] = 30

    def score(
        self,
        ticker: str,
        history: pd.DataFrame,
        fundamentals: Fundamentals | None = None,
        *,
        lang: str = "en",
    ) -> StrategyResult:
        if "Close" not in history.columns or history.shape[0] < self.MIN_OBSERVATIONS:
            raise ValueError(
                f"{ticker}: need at least {self.MIN_OBSERVATIONS} observations to score dca"
            )
        close = history["Close"].dropna()
        sim = simulate_dca(
            close,
            per_period_amount=self.DEFAULT_AMOUNT,
            cadence_days=self.DEFAULT_CADENCE_DAYS,
        )

        return_score = clamp01(sim.total_return / 0.30 / 2 + 0.5)     # ±30% → [0, 1]
        dd_score = clamp01(1.0 - abs(sim.max_drawdown) / 0.50)        # -50% DD → 0
        # DCA wins when it tames a volatile but trending-up asset. If
        # lump-sum smoked it (e.g. relentless bull), score is similar; if
        # DCA beat lump-sum on drawdown, give a small bonus.
        beat_lump_sum = sim.total_return - sim.lump_sum_return
        composite = clamp01(0.6 * return_score + 0.3 * dd_score + 0.1 * (0.5 + beat_lump_sum))

        if composite >= 0.60 and sim.total_return > 0:
            verdict = Verdict.BUY
        elif sim.total_return <= -0.20:
            verdict = Verdict.SELL
        else:
            verdict = Verdict.HOLD

        rationale = _explain(sim, verdict, ticker, lang)

        return StrategyResult(
            strategy=self.name,
            ticker=ticker.upper(),
            verdict=verdict,
            score=composite,
            rationale=rationale,
            key_inputs={
                "per_period_amount": self.DEFAULT_AMOUNT,
                "cadence_days": float(self.DEFAULT_CADENCE_DAYS),
                "total_invested": sim.total_invested,
                "final_value": sim.final_value,
                "avg_purchase_price": sim.avg_purchase_price,
                "total_return": sim.total_return,
                "lump_sum_return": sim.lump_sum_return,
                "max_drawdown": sim.max_drawdown,
            },
        )


def _explain(sim: DCASimulation, verdict: Verdict, ticker: str, lang: str) -> str:
    ret_pct = f"{sim.total_return * 100:+.1f}%"
    lump_pct = f"{sim.lump_sum_return * 100:+.1f}%"
    dd_pct = f"{sim.max_drawdown * 100:.1f}%"
    beat = sim.total_return - sim.lump_sum_return
    if lang == "de":
        beat_phrase = (
            "besser als ein Einmalkauf"
            if beat > 0.02
            else "schlechter als ein Einmalkauf"
            if beat < -0.02
            else "vergleichbar mit einem Einmalkauf"
        )
        if verdict == Verdict.BUY:
            return (
                f"Historischer DCA in {ticker} ergab {ret_pct} (Einmalkauf {lump_pct}) — "
                f"{beat_phrase} — mit max. Equity-Drawdown von {dd_pct}. "
                f"Geeignet für regelmäßiges Ansparen."
            )
        if verdict == Verdict.SELL:
            return (
                f"DCA in {ticker} ergab historisch {ret_pct}. Ein Zeitplan rettet kein "
                f"dauerhaft schwaches Asset; eine Alternative prüfen."
            )
        return (
            f"DCA in {ticker} ergab {ret_pct} (Einmalkauf {lump_pct}) mit "
            f"{dd_pct} max. Equity-Drawdown. Gemischt — für kleine Positionen geeignet."
        )
    # English (default)
    beat_phrase = (
        "outperformed a lump-sum entry"
        if beat > 0.02
        else "underperformed a lump-sum entry"
        if beat < -0.02
        else "matched a lump-sum entry"
    )
    if verdict == Verdict.BUY:
        return (
            f"Historical DCA into {ticker} returned {ret_pct} (lump-sum {lump_pct}) — "
            f"{beat_phrase} — with a worst-case equity drawdown of {dd_pct}. "
            f"Suitable for periodic accumulation."
        )
    if verdict == Verdict.SELL:
        return (
            f"DCA into {ticker} returned {ret_pct} historically. Scheduling doesn't "
            f"rescue a persistently weak asset; consider an alternative."
        )
    return (
        f"DCA into {ticker} produced {ret_pct} (lump-sum {lump_pct}) with "
        f"{dd_pct} max equity drawdown. Mixed — fine for small allocations."
    )
