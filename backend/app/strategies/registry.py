"""Strategy registry — name → class lookup used by the API layer."""

from __future__ import annotations

from app.strategies.base import Strategy
from app.strategies.buy_hold import BuyHoldStrategy
from app.strategies.dca import DCAStrategy
from app.strategies.momentum import MomentumStrategy
from app.strategies.value import ValueStrategy

_STRATEGIES: dict[str, type[Strategy]] = {
    BuyHoldStrategy.name: BuyHoldStrategy,
    DCAStrategy.name: DCAStrategy,
    ValueStrategy.name: ValueStrategy,
    MomentumStrategy.name: MomentumStrategy,
}


def available() -> list[str]:
    """Names of every registered strategy."""
    return sorted(_STRATEGIES.keys())


def get(name: str) -> Strategy:
    """Instantiate a strategy by name. Raises ValueError on unknown names."""
    key = name.lower()
    if key not in _STRATEGIES:
        raise ValueError(f"unknown strategy '{name}'. Available: {available()}")
    return _STRATEGIES[key]()
