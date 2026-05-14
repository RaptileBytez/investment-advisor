"""Portfolio service — record trades, keep holdings in sync, watchlist."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.db.models import TradeSide
from app.portfolio.service import PortfolioError, PortfolioService


@pytest.fixture()
def service(db_session):
    return PortfolioService(db_session)


@pytest.fixture()
def user(service):
    return service.get_or_create_user("trader@example.com", base_currency="EUR", locale="en")


def _ts(year=2025, month=6, day=1):
    return datetime(year, month, day, tzinfo=UTC).replace(tzinfo=None)


# ── Trade recording / holding sync ─────────────────────────────
def test_first_buy_creates_holding(service, user):
    service.record_trade(
        user_id=user.id, ticker="AAPL", side=TradeSide.BUY,
        quantity=10, price=150.0, executed_at=_ts(),
    )
    holdings = service.get_holdings(user.id)
    assert len(holdings) == 1
    h = holdings[0]
    assert h.ticker == "AAPL"
    assert h.quantity == 10
    assert h.avg_cost == 150.0
    assert h.currency == "USD"  # inferred from ticker


def test_second_buy_updates_average_cost(service, user):
    service.record_trade(
        user_id=user.id, ticker="AAPL", side=TradeSide.BUY,
        quantity=10, price=100.0, executed_at=_ts(),
    )
    service.record_trade(
        user_id=user.id, ticker="AAPL", side=TradeSide.BUY,
        quantity=10, price=200.0, executed_at=_ts(month=7),
    )
    h = service.get_holdings(user.id)[0]
    assert h.quantity == 20
    assert h.avg_cost == 150.0   # (10*100 + 10*200) / 20


def test_partial_sell_reduces_quantity_keeps_avg_cost(service, user):
    service.record_trade(
        user_id=user.id, ticker="AAPL", side=TradeSide.BUY,
        quantity=10, price=100.0, executed_at=_ts(),
    )
    service.record_trade(
        user_id=user.id, ticker="AAPL", side=TradeSide.SELL,
        quantity=4, price=150.0, executed_at=_ts(month=7),
    )
    h = service.get_holdings(user.id)[0]
    assert h.quantity == 6
    assert h.avg_cost == 100.0   # cost basis unchanged on sell


def test_full_sell_zeros_holding(service, user):
    service.record_trade(
        user_id=user.id, ticker="AAPL", side=TradeSide.BUY,
        quantity=10, price=100.0, executed_at=_ts(),
    )
    service.record_trade(
        user_id=user.id, ticker="AAPL", side=TradeSide.SELL,
        quantity=10, price=150.0, executed_at=_ts(month=7),
    )
    assert service.get_holdings(user.id) == []  # zero qty → filtered out


def test_oversell_raises(service, user):
    service.record_trade(
        user_id=user.id, ticker="AAPL", side=TradeSide.BUY,
        quantity=5, price=100.0, executed_at=_ts(),
    )
    with pytest.raises(PortfolioError):
        service.record_trade(
            user_id=user.id, ticker="AAPL", side=TradeSide.SELL,
            quantity=10, price=150.0, executed_at=_ts(month=7),
        )


def test_negative_quantity_rejected(service, user):
    with pytest.raises(PortfolioError):
        service.record_trade(
            user_id=user.id, ticker="AAPL", side=TradeSide.BUY,
            quantity=-1, price=100.0, executed_at=_ts(),
        )


def test_european_ticker_resolves_eur_currency(service, user):
    service.record_trade(
        user_id=user.id, ticker="SAP.DE", side=TradeSide.BUY,
        quantity=5, price=120.0, executed_at=_ts(),
    )
    h = service.get_holdings(user.id)[0]
    assert h.currency == "EUR"


def test_transactions_returned_newest_first(service, user):
    service.record_trade(
        user_id=user.id, ticker="AAPL", side=TradeSide.BUY,
        quantity=5, price=100.0, executed_at=_ts(),
    )
    service.record_trade(
        user_id=user.id, ticker="AAPL", side=TradeSide.BUY,
        quantity=5, price=110.0, executed_at=_ts(month=8),
    )
    txs = service.get_transactions(user.id)
    assert txs[0].executed_at > txs[1].executed_at


# ── Watchlist ─────────────────────────────────────────────────
def test_watchlist_add_and_get(service, user):
    service.add_to_watchlist(user.id, "AAPL")
    service.add_to_watchlist(user.id, "SAP.DE")
    items = service.get_watchlist(user.id)
    assert {i.ticker for i in items} == {"AAPL", "SAP.DE"}


def test_watchlist_dedupes(service, user):
    service.add_to_watchlist(user.id, "AAPL")
    service.add_to_watchlist(user.id, "AAPL")
    assert len(service.get_watchlist(user.id)) == 1


def test_watchlist_remove(service, user):
    service.add_to_watchlist(user.id, "AAPL")
    assert service.remove_from_watchlist(user.id, "AAPL") is True
    assert service.get_watchlist(user.id) == []


def test_watchlist_remove_missing_returns_false(service, user):
    assert service.remove_from_watchlist(user.id, "NONE") is False
