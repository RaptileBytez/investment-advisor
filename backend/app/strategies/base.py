"""Strategy framework — the interface every strategy implements.

Each strategy reads a price history (and optionally fundamentals) and
returns a `StrategyResult`. The recommendation engine combines results
from one or more strategies into a final verdict; strategies themselves
stay narrowly focused on producing their own signal."""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

import pandas as pd

from app.data.provider import Fundamentals


class Verdict(str, enum.Enum):
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    WATCH = "watch"


@dataclass(frozen=True)
class StrategyResult:
    """One strategy's read on one ticker.

    Attributes:
        strategy: Strategy name (matches `Strategy.name`).
        ticker: Upper-cased ticker symbol.
        verdict: BUY / HOLD / SELL / WATCH.
        score: Standardised confidence in [0, 1]. 0.5 ~= neutral.
        rationale: One- to three-sentence plain-language explanation
            intended for direct display in the UI. Always in English
            here; the API layer translates if a non-English locale is
            requested.
        key_inputs: The raw signals used (e.g. {"rsi_14": 65.2, …}).
            UI surfaces these in tooltips so the user can drill in.
    """

    strategy: str
    ticker: str
    verdict: Verdict
    score: float
    rationale: str
    key_inputs: dict[str, float | str | None] = field(default_factory=dict)


class Strategy(ABC):
    """Abstract base for all investment strategies.

    Subclasses should:
    - set a unique `name` class variable;
    - set `requires_fundamentals = True` if `.score()` needs the
      fundamentals argument populated (callers can then skip fetching
      it for cheaper strategies);
    - keep `score()` pure — no I/O, no globals — so it stays unit-testable.
    """

    name: ClassVar[str] = "abstract"
    requires_fundamentals: ClassVar[bool] = False

    @abstractmethod
    def score(
        self,
        ticker: str,
        history: pd.DataFrame,
        fundamentals: Fundamentals | None = None,
    ) -> StrategyResult:
        """Return this strategy's read on `ticker`.

        Args:
            ticker: Upper-cased symbol.
            history: OHLCV daily DataFrame indexed by date. Must include
                at least a `Close` column.
            fundamentals: Latest fundamentals snapshot, required iff
                `requires_fundamentals` is True.

        Raises:
            ValueError: if inputs are insufficient for this strategy.
        """


def clamp01(x: float) -> float:
    """Clamp a real number to the [0, 1] interval used for scores."""
    if x != x:  # NaN
        return 0.5
    if x < 0:
        return 0.0
    if x > 1:
        return 1.0
    return float(x)
