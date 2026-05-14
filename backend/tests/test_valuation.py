"""Portfolio valuation in a chosen base currency."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.db.models import TradeSide
from app.portfolio.service import PortfolioService
from app.portfolio.valuation import value_portfolio


@pytest.fixture()
def populated_user(db_session, fake_provider):
    service = PortfolioService(db_session)
    user = service.get_or_create_user("multi@example.com", base_currency="EUR")
    service.record_trade(
        user_id=user.id, ticker="AAPL", side=TradeSide.BUY,
        quantity=10, price=150.0, executed_at=datetime(2025, 1, 1, tzinfo=UTC).replace(tzinfo=None),
    )
    service.record_trade(
        user_id=user.id, ticker="SAP.DE", side=TradeSide.BUY,
        quantity=20, price=120.0, executed_at=datetime(2025, 1, 1, tzinfo=UTC).replace(tzinfo=None),
    )
    fake_provider.set_quote("AAPL", 200.0, "USD")
    fake_provider.set_quote("SAP.DE", 150.0, "EUR")
    fake_provider.set_quote("USDEUR=X", 0.90, "EUR")
    fake_provider.set_quote("EUREUR=X", 1.0, "EUR")  # never used; same-currency short-circuits
    return user, service


def test_valuation_totals_in_base_currency(populated_user, fake_provider):
    user, service = populated_user
    val = value_portfolio(service.get_holdings(user.id), provider=fake_provider, base_currency="EUR")
    # AAPL: 10 * 200 USD * 0.90 EUR/USD = 1800 EUR
    # SAP.DE: 20 * 150 EUR = 3000 EUR
    # Total: 4800 EUR
    assert val.base_currency == "EUR"
    assert val.total_value == pytest.approx(4800.0, rel=1e-6)


def test_valuation_unrealized_pnl(populated_user, fake_provider):
    user, service = populated_user
    val = value_portfolio(service.get_holdings(user.id), provider=fake_provider, base_currency="EUR")
    # AAPL cost basis = 10 * 150 USD * 0.90 = 1350 EUR, market = 1800 → +450 EUR
    # SAP.DE cost = 20 * 120 = 2400, market = 3000 → +600 EUR
    # Total PL = 1050 EUR on 3750 cost basis
    assert val.total_unrealized_pl == pytest.approx(1050.0, rel=1e-6)
    assert val.total_cost_basis == pytest.approx(3750.0, rel=1e-6)


def test_valuation_position_weights_sum_to_one(populated_user, fake_provider):
    user, service = populated_user
    val = value_portfolio(service.get_holdings(user.id), provider=fake_provider, base_currency="EUR")
    assert sum(p.weight for p in val.positions) == pytest.approx(1.0, abs=1e-6)


def test_valuation_currency_exposure_split(populated_user, fake_provider):
    user, service = populated_user
    val = value_portfolio(service.get_holdings(user.id), provider=fake_provider, base_currency="EUR")
    assert set(val.currency_exposure.keys()) == {"USD", "EUR"}
    # USD share = 1800 / 4800 = 0.375
    assert val.currency_exposure["USD"] == pytest.approx(0.375, rel=1e-6)
    assert val.currency_exposure["EUR"] == pytest.approx(0.625, rel=1e-6)


def test_valuation_skips_unquotable_position(populated_user, fake_provider):
    user, service = populated_user
    service.record_trade(
        user_id=user.id, ticker="UNQ.OTC", side=TradeSide.BUY,
        quantity=5, price=10.0, executed_at=datetime(2025, 1, 1, tzinfo=UTC).replace(tzinfo=None),
    )
    val = value_portfolio(service.get_holdings(user.id), provider=fake_provider, base_currency="EUR")
    assert {p.ticker for p in val.positions} == {"AAPL", "SAP.DE"}


def test_valuation_empty_portfolio_returns_zero(db_session, fake_provider):
    service = PortfolioService(db_session)
    user = service.get_or_create_user("empty@example.com")
    val = value_portfolio(service.get_holdings(user.id), provider=fake_provider, base_currency="EUR")
    assert val.total_value == 0
    assert val.positions == []
