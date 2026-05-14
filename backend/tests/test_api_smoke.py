"""End-to-end API smoke tests using FastAPI's TestClient with FakeProvider
and an in-memory DB injected via dependency overrides.

These don't exercise yfinance — provider integration tests live behind the
`integration` pytest marker."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_current_user, get_data_provider, get_portfolio_service
from app.db.models import Base, RiskTolerance, User
from app.db.session import get_db
from app.main import create_app
from app.portfolio.service import PortfolioService
from tests.conftest import FakeProvider, rising_ohlcv


@pytest.fixture()
def wired_client(fake_provider):
    """A TestClient with an in-memory DB and FakeProvider wired in."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    # Single shared session for the test so changes are visible across calls.
    session = SessionLocal()
    service = PortfolioService(session)
    user = service.get_or_create_user("test@local", base_currency="EUR", locale="en")

    def override_user():
        return user

    def override_service():
        return service

    def override_provider():
        return fake_provider

    app = create_app()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_portfolio_service] = override_service
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_data_provider] = override_provider

    with TestClient(app) as client:
        yield client, fake_provider, user

    session.close()
    engine.dispose()


# ── Health & strategies list ──────────────────────────────────
def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_list_strategies(wired_client):
    client, _, _ = wired_client
    resp = client.get("/api/strategies")
    assert resp.status_code == 200
    assert set(resp.json()) == {"buy_hold", "dca", "value", "momentum"}


# ── Stocks router ────────────────────────────────────────────
def test_quote_returns_404_for_unknown(wired_client):
    client, _, _ = wired_client
    resp = client.get("/api/stocks/quote/UNKNOWN")
    assert resp.status_code == 404


def test_quote_returns_fake(wired_client):
    client, fp, _ = wired_client
    fp.set_quote("AAPL", 200.0, "USD")
    resp = client.get("/api/stocks/quote/AAPL")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "AAPL"
    assert body["price"] == 200.0
    assert body["currency"] == "USD"


def test_history_returns_bars(wired_client):
    client, fp, _ = wired_client
    fp.set_history("AAPL", rising_ohlcv(n=100))
    resp = client.get("/api/stocks/history/AAPL?period=1y&interval=1d")
    assert resp.status_code == 200
    bars = resp.json()["bars"]
    assert len(bars) == 100
    assert {"date", "open", "high", "low", "close", "volume"} <= bars[0].keys()


# ── Portfolio router ─────────────────────────────────────────
def test_me_returns_default_user(wired_client):
    client, _, user = wired_client
    resp = client.get("/api/portfolio/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == user.email
    assert body["base_currency"] == "EUR"


def test_update_preferences(wired_client):
    client, _, _ = wired_client
    resp = client.put(
        "/api/portfolio/me",
        json={"base_currency": "USD", "risk_tolerance": "aggressive"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["base_currency"] == "USD"
    assert body["risk_tolerance"] == "aggressive"


def test_record_trade_and_list_holdings(wired_client):
    client, _, _ = wired_client
    trade = {
        "ticker": "AAPL",
        "side": "buy",
        "quantity": 10,
        "price": 150,
        "executed_at": datetime(2025, 1, 1, tzinfo=UTC).isoformat(),
        "fees": 1.0,
    }
    resp = client.post("/api/portfolio/trades", json=trade)
    assert resp.status_code == 201

    holdings = client.get("/api/portfolio/holdings").json()
    assert len(holdings) == 1
    assert holdings[0]["ticker"] == "AAPL"
    assert holdings[0]["quantity"] == 10


def test_oversell_returns_409(wired_client):
    client, _, _ = wired_client
    buy = {
        "ticker": "AAPL", "side": "buy", "quantity": 5, "price": 100,
        "executed_at": datetime(2025, 1, 1, tzinfo=UTC).isoformat(),
    }
    client.post("/api/portfolio/trades", json=buy)
    sell = {**buy, "side": "sell", "quantity": 10}
    resp = client.post("/api/portfolio/trades", json=sell)
    assert resp.status_code == 409


def test_watchlist_add_remove(wired_client):
    client, _, _ = wired_client
    resp = client.post("/api/portfolio/watchlist/SAP.DE")
    assert resp.status_code == 201
    items = client.get("/api/portfolio/watchlist").json()
    assert any(i["ticker"] == "SAP.DE" for i in items)
    resp = client.delete("/api/portfolio/watchlist/SAP.DE")
    assert resp.status_code == 204


def test_valuation_in_base_currency(wired_client):
    client, fp, _ = wired_client
    # Trade + quotes
    client.post(
        "/api/portfolio/trades",
        json={
            "ticker": "AAPL", "side": "buy", "quantity": 10, "price": 100,
            "executed_at": datetime(2025, 1, 1, tzinfo=UTC).isoformat(),
        },
    )
    fp.set_quote("AAPL", 200.0, "USD")
    fp.set_quote("USDEUR=X", 0.9, "EUR")
    val = client.get("/api/portfolio/valuation").json()
    assert val["base_currency"] == "EUR"
    # 10 * 200 USD * 0.9 = 1800 EUR
    assert val["total_value"] == pytest.approx(1800.0, rel=1e-6)


# ── Recommendation router ────────────────────────────────────
def test_evaluate_returns_verdict(wired_client):
    client, fp, _ = wired_client
    fp.set_history("ACME", rising_ohlcv())
    fp.set_quote("^IRX", 5.0, "USD")
    fp.set_history("^GSPC", rising_ohlcv())
    resp = client.post(
        "/api/strategies/evaluate",
        json={"ticker": "ACME", "strategies": ["buy_hold", "momentum"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ticker"] == "ACME"
    assert body["action"] in {"buy", "hold", "sell", "watch"}
    assert body["risk_summary"] is not None


def test_evaluate_missing_history_returns_404(wired_client):
    client, _, _ = wired_client
    resp = client.post(
        "/api/strategies/evaluate",
        json={"ticker": "GHOST"},
    )
    assert resp.status_code == 404


# ── Risk router ──────────────────────────────────────────────
def test_risk_endpoint(wired_client):
    client, fp, _ = wired_client
    fp.set_history("ACME", rising_ohlcv())
    fp.set_quote("^IRX", 5.0, "USD")
    fp.set_history("^GSPC", rising_ohlcv())
    resp = client.get("/api/risk/ACME")
    assert resp.status_code == 200
    body = resp.json()
    assert body["benchmark"] == "S&P 500"
    assert "volatility" in body


# ── Glossary router ──────────────────────────────────────────
def test_glossary_list_runs_empty_ok(wired_client):
    """Glossary returns an empty list when no entries are seeded yet."""
    client, _, _ = wired_client
    resp = client.get("/api/glossary?lang=en")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_glossary_unknown_term_returns_404(wired_client):
    client, _, _ = wired_client
    resp = client.get("/api/glossary/no-such-term?lang=en")
    assert resp.status_code == 404
