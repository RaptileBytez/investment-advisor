"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_data_provider, get_portfolio_service
from app.data.provider import Fundamentals, ProviderError, Quote, TickerInfo
from app.db.models import Base
from app.db.session import get_db
from app.main import create_app
from app.portfolio.service import PortfolioService


@pytest.fixture(scope="session")
def app():
    return create_app()


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db_session() -> Iterator[Session]:
    """An ephemeral SQLite-in-memory session with the schema created."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# ──────────────────────────────────────────────────────────────
# FakeProvider — deterministic in-process DataProvider stand-in
# ──────────────────────────────────────────────────────────────
class FakeProvider:
    """In-process DataProvider stub used by unit tests.

    Quotes and FX rates are keyed by ticker; history is a function returning
    a synthetic OHLCV DataFrame. The FakeProvider raises ProviderError for
    any ticker not registered, which keeps tests honest about coverage."""

    def __init__(self):
        self.quotes: dict[str, Quote] = {}
        self.histories: dict[str, pd.DataFrame] = {}
        self.fundamentals: dict[str, Fundamentals] = {}

    # ── Setters used in test setup ────────────────────────────
    def set_quote(self, ticker: str, price: float, currency: str = "USD") -> None:
        self.quotes[ticker.upper()] = Quote(
            ticker=ticker.upper(),
            price=price,
            currency=currency,
            timestamp=datetime.now(UTC),
            previous_close=price * 0.99,
        )

    def set_history(self, ticker: str, df: pd.DataFrame) -> None:
        self.histories[ticker.upper()] = df

    def set_fundamentals(self, ticker: str, fundamentals: Fundamentals) -> None:
        self.fundamentals[ticker.upper()] = fundamentals

    # ── DataProvider interface ────────────────────────────────
    def search(self, query, *, region=None, limit=10):
        upper = query.upper()
        return [
            TickerInfo(ticker=upper, name=upper, exchange="FAKE", region="US", currency="USD")
        ] if upper in self.quotes else []

    def get_quote(self, ticker: str) -> Quote:
        upper = ticker.upper()
        if upper not in self.quotes:
            raise ProviderError(f"no fake quote for {upper}")
        return self.quotes[upper]

    def get_history(self, ticker: str, *, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        upper = ticker.upper()
        if upper not in self.histories:
            raise ProviderError(f"no fake history for {upper}")
        return self.histories[upper]

    def get_fundamentals(self, ticker: str) -> Fundamentals:
        upper = ticker.upper()
        if upper not in self.fundamentals:
            raise ProviderError(f"no fake fundamentals for {upper}")
        return self.fundamentals[upper]


@pytest.fixture()
def fake_provider() -> FakeProvider:
    return FakeProvider()


# ──────────────────────────────────────────────────────────────
# Synthetic price helpers reused across strategy / engine tests
# ──────────────────────────────────────────────────────────────
@pytest.fixture()
def wired_client(fake_provider):
    """A TestClient with an in-memory DB and FakeProvider wired in via
    FastAPI dependency overrides. Shared across API + glossary tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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


def rising_ohlcv(n: int = 500, start: float = 100.0, end: float = 200.0) -> pd.DataFrame:
    closes = np.linspace(start, end, n)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {"Open": closes, "High": closes, "Low": closes, "Close": closes,
         "Volume": np.ones(n) * 1_000_000},
        index=idx,
    )


def falling_ohlcv(n: int = 500, start: float = 200.0, end: float = 100.0) -> pd.DataFrame:
    closes = np.linspace(start, end, n)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {"Open": closes, "High": closes, "Low": closes, "Close": closes,
         "Volume": np.ones(n) * 1_000_000},
        index=idx,
    )
