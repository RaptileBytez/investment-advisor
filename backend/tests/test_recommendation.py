"""Recommendation engine wiring — combines strategy outputs into a verdict."""

from __future__ import annotations

import pytest

from app.data.provider import Fundamentals
from app.db.models import RiskTolerance
from app.recommendation.engine import RecommendationEngine
from app.strategies.base import Verdict
from tests.conftest import falling_ohlcv, rising_ohlcv


@pytest.fixture()
def engine(fake_provider):
    return RecommendationEngine(fake_provider)


def _seed_rising_acme(fp):
    fp.set_quote("ACME", 200.0, "USD")
    fp.set_history("ACME", rising_ohlcv())
    fp.set_fundamentals(
        "ACME",
        Fundamentals(
            ticker="ACME", currency="USD", market_cap=1e10,
            trailing_pe=10.0, price_to_book=1.2,
            debt_to_equity=40.0, dividend_yield=0.04, free_cash_flow_yield=0.08,
        ),
    )
    # Benchmark + risk-free
    fp.set_quote("^IRX", 5.0, "USD")
    fp.set_history("^GSPC", rising_ohlcv())


def _seed_falling_acme(fp):
    fp.set_quote("ACME", 100.0, "USD")
    fp.set_history("ACME", falling_ohlcv())
    fp.set_fundamentals(
        "ACME",
        Fundamentals(
            ticker="ACME", currency="USD", market_cap=1e10,
            trailing_pe=80.0, price_to_book=15.0,
            debt_to_equity=400.0, dividend_yield=0.0, free_cash_flow_yield=-0.05,
        ),
    )
    fp.set_quote("^IRX", 5.0, "USD")
    fp.set_history("^GSPC", falling_ohlcv())


def test_engine_recommends_buy_on_strong_uptrend(engine, fake_provider):
    _seed_rising_acme(fake_provider)
    verdict = engine.evaluate("ACME", risk_tolerance=RiskTolerance.BALANCED)
    assert verdict.action == Verdict.BUY
    assert verdict.confidence >= 0.65
    assert verdict.risk_summary is not None
    assert verdict.risk_summary.benchmark == "S&P 500"


def test_engine_recommends_sell_on_downtrend_with_bad_fundamentals(engine, fake_provider):
    _seed_falling_acme(fake_provider)
    verdict = engine.evaluate("ACME", risk_tolerance=RiskTolerance.BALANCED)
    assert verdict.action == Verdict.SELL


def test_engine_respects_explicit_strategies(engine, fake_provider):
    _seed_rising_acme(fake_provider)
    verdict = engine.evaluate("ACME", strategies=["momentum"])
    names = {r.strategy for r in verdict.strategy_results}
    assert names == {"momentum"}


def test_engine_handles_custom_weights(engine, fake_provider):
    _seed_rising_acme(fake_provider)
    weights = {"buy_hold": 0.8, "momentum": 0.2}
    verdict = engine.evaluate("ACME", strategy_weights=weights)
    names = {r.strategy for r in verdict.strategy_results}
    assert names == {"buy_hold", "momentum"}


def test_engine_thresholds_are_tolerance_aware(engine, fake_provider):
    _seed_rising_acme(fake_provider)
    conservative = engine.evaluate("ACME", risk_tolerance=RiskTolerance.CONSERVATIVE)
    aggressive = engine.evaluate("ACME", risk_tolerance=RiskTolerance.AGGRESSIVE)
    # Same data, different thresholds → aggressive is at least as bullish.
    rank = {Verdict.SELL: 0, Verdict.HOLD: 1, Verdict.WATCH: 1, Verdict.BUY: 2}
    assert rank[aggressive.action] >= rank[conservative.action]


def test_engine_rationale_includes_risk_summary(engine, fake_provider):
    _seed_rising_acme(fake_provider)
    verdict = engine.evaluate("ACME")
    assert "Composite score" in verdict.rationale
    assert "Risk profile" in verdict.rationale
