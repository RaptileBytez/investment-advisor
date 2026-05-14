"""Recommendation engine — combines strategy results + risk into a verdict.

Strategies produce per-strategy reads. Here we:

1. Decide which strategies to run (or take an explicit list from the caller).
2. Run each strategy on the same price history + fundamentals.
3. Compute the risk metrics that the UI displays alongside the verdict.
4. Combine the strategy scores using weights derived from the user's
   risk tolerance (or explicit overrides).
5. Map the composite score to BUY / HOLD / SELL with tolerance-adjusted
   thresholds (a conservative user needs higher conviction to BUY than
   an aggressive one).

This is the single place where the final action is decided. Strategies
stay narrowly focused on producing their own signal.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

from app.data.provider import DataProvider, Fundamentals, ProviderError
from app.db.models import RiskTolerance
from app.risk.benchmarks import get_config_for_ticker, get_risk_free_rate
from app.risk.metrics import (
    annualized_volatility,
    beta,
    daily_simple_returns,
    max_drawdown,
    sharpe_ratio,
    value_at_risk,
)
from app.strategies import registry
from app.strategies.base import Strategy, StrategyResult, Verdict

log = logging.getLogger(__name__)

# Default strategy weights per risk-tolerance bucket. Weights must sum to 1.
DEFAULT_WEIGHTS: dict[RiskTolerance, dict[str, float]] = {
    RiskTolerance.CONSERVATIVE: {"buy_hold": 0.50, "value": 0.30, "dca": 0.15, "momentum": 0.05},
    RiskTolerance.BALANCED:     {"buy_hold": 0.30, "value": 0.25, "dca": 0.20, "momentum": 0.25},
    RiskTolerance.AGGRESSIVE:   {"buy_hold": 0.15, "value": 0.20, "dca": 0.20, "momentum": 0.45},
}

# Score thresholds for BUY / SELL — narrower for conservative users, wider
# for aggressive. The HOLD band falls between.
THRESHOLDS: dict[RiskTolerance, tuple[float, float]] = {
    RiskTolerance.CONSERVATIVE: (0.35, 0.75),
    RiskTolerance.BALANCED:     (0.40, 0.65),
    RiskTolerance.AGGRESSIVE:   (0.30, 0.55),
}


@dataclass
class RiskSummary:
    volatility: float
    sharpe: float
    beta: float
    max_drawdown: float
    value_at_risk_95: float
    benchmark: str
    risk_free_rate: float


@dataclass
class FinalVerdict:
    ticker: str
    action: Verdict
    confidence: float                  # weighted composite, [0, 1]
    rationale: str                     # human-readable, multi-sentence
    risk_summary: RiskSummary | None
    strategy_results: list[StrategyResult] = field(default_factory=list)


class RecommendationEngine:
    def __init__(self, provider: DataProvider):
        self.provider = provider

    # ── Public entry point ────────────────────────────────────
    def evaluate(
        self,
        ticker: str,
        *,
        strategies: list[str] | None = None,
        strategy_weights: dict[str, float] | None = None,
        risk_tolerance: RiskTolerance = RiskTolerance.BALANCED,
        history_period: str = "5y",
    ) -> FinalVerdict:
        ticker = ticker.upper()
        weights = self._resolve_weights(strategies, strategy_weights, risk_tolerance)
        strategies_to_run = [registry.get(name) for name in weights]

        history = self._fetch_history(ticker, period=history_period)
        fundamentals = self._maybe_fetch_fundamentals(ticker, strategies_to_run)

        results: list[StrategyResult] = []
        for strat in strategies_to_run:
            try:
                results.append(strat.score(ticker, history, fundamentals))
            except ValueError as exc:
                log.info("strategy %s skipped for %s: %s", strat.name, ticker, exc)

        composite = self._composite_score(results, weights)
        action = self._verdict_for(composite, risk_tolerance)
        risk = self._risk_summary(ticker, history)
        rationale = self._compose_rationale(action, composite, results, risk, risk_tolerance)

        return FinalVerdict(
            ticker=ticker,
            action=action,
            confidence=composite,
            rationale=rationale,
            risk_summary=risk,
            strategy_results=results,
        )

    # ── Weights / strategy selection ──────────────────────────
    def _resolve_weights(
        self,
        strategies: list[str] | None,
        weights: dict[str, float] | None,
        risk_tolerance: RiskTolerance,
    ) -> dict[str, float]:
        if weights:
            total = sum(weights.values())
            if total <= 0:
                raise ValueError("strategy_weights must sum to a positive number")
            return {k: v / total for k, v in weights.items()}
        if strategies:
            equal = 1 / len(strategies)
            return dict.fromkeys(strategies, equal)
        return dict(DEFAULT_WEIGHTS[risk_tolerance])

    # ── Composite ─────────────────────────────────────────────
    @staticmethod
    def _composite_score(results: list[StrategyResult], weights: dict[str, float]) -> float:
        if not results:
            return 0.5
        active_weight = sum(weights[r.strategy] for r in results if r.strategy in weights)
        if active_weight == 0:
            return sum(r.score for r in results) / len(results)
        return sum(r.score * weights[r.strategy] for r in results if r.strategy in weights) / active_weight

    @staticmethod
    def _verdict_for(score: float, tolerance: RiskTolerance) -> Verdict:
        sell_below, buy_above = THRESHOLDS[tolerance]
        if score >= buy_above:
            return Verdict.BUY
        if score <= sell_below:
            return Verdict.SELL
        return Verdict.HOLD

    # ── Data fetching ─────────────────────────────────────────
    def _fetch_history(self, ticker: str, *, period: str) -> pd.DataFrame:
        try:
            return self.provider.get_history(ticker, period=period, interval="1d")
        except ProviderError as exc:
            raise ProviderError(f"could not load history for {ticker}: {exc}") from exc

    def _maybe_fetch_fundamentals(
        self, ticker: str, strategies: list[Strategy]
    ) -> Fundamentals | None:
        if not any(s.requires_fundamentals for s in strategies):
            return None
        try:
            return self.provider.get_fundamentals(ticker)
        except ProviderError as exc:
            log.info("fundamentals unavailable for %s (%s) — value strategy will skip", ticker, exc)
            return None

    # ── Risk summary ──────────────────────────────────────────
    def _risk_summary(self, ticker: str, history: pd.DataFrame) -> RiskSummary | None:
        if "Close" not in history.columns or history.shape[0] < 40:
            return None
        cfg = get_config_for_ticker(ticker)
        rf_rate = get_risk_free_rate(cfg.region, self.provider)
        closes = history["Close"].dropna()
        asset_returns = daily_simple_returns(closes)
        try:
            bench_history = self.provider.get_history(
                cfg.benchmark_ticker, period="5y", interval="1d"
            )
            bench_returns = daily_simple_returns(bench_history["Close"].dropna())
            b = beta(asset_returns, bench_returns)
        except ProviderError:
            b = float("nan")
        return RiskSummary(
            volatility=annualized_volatility(asset_returns),
            sharpe=sharpe_ratio(asset_returns, rf_rate),
            beta=b,
            max_drawdown=max_drawdown(closes),
            value_at_risk_95=value_at_risk(asset_returns, confidence=0.95),
            benchmark=cfg.benchmark_name,
            risk_free_rate=rf_rate,
        )

    # ── Rationale ─────────────────────────────────────────────
    @staticmethod
    def _compose_rationale(
        action: Verdict,
        score: float,
        results: list[StrategyResult],
        risk: RiskSummary | None,
        tolerance: RiskTolerance,
    ) -> str:
        if not results:
            return (
                "Not enough strategy signal to form a recommendation. "
                "Showing risk metrics for context."
            )
        # Lead with the strongest strategy agreeing with the final action.
        agreeing = [r for r in results if r.verdict == action]
        anchor = max(agreeing or results, key=lambda r: r.score)
        bits = [anchor.rationale]
        if risk:
            bits.append(
                f"Risk profile: volatility {risk.volatility * 100:.1f}% p.a., "
                f"β {risk.beta:.2f} vs. {risk.benchmark}, max drawdown {risk.max_drawdown * 100:.1f}%."
            )
        bits.append(
            f"Composite score {score * 100:.0f}/100 against a {tolerance.value} profile."
        )
        return " ".join(bits)
