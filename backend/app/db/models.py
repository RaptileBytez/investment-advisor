"""SQLAlchemy models for users, portfolio, watchlist, snapshots, cache."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RiskTolerance(str, enum.Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class TradeSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    base_currency: Mapped[str] = mapped_column(String(3), default="EUR")
    locale: Mapped[str] = mapped_column(String(8), default="en")
    risk_tolerance: Mapped[RiskTolerance] = mapped_column(
        Enum(RiskTolerance), default=RiskTolerance.BALANCED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    holdings: Mapped[list["Holding"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    watchlist: Mapped[list["WatchlistItem"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    snapshots: Mapped[list["Snapshot"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Holding(Base):
    """Denormalised current position. Kept in sync by the portfolio service
    when transactions are added. The source of truth for history is the
    `transactions` table; `holdings` is a convenience cache for fast reads."""

    __tablename__ = "holdings"
    __table_args__ = (UniqueConstraint("user_id", "ticker", name="uq_holding_user_ticker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    avg_cost: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    opened_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="holdings")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    side: Mapped[TradeSide] = mapped_column(Enum(TradeSide))
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    executed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="transactions")


class WatchlistItem(Base):
    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("user_id", "ticker", name="uq_watch_user_ticker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="watchlist")


class Snapshot(Base):
    """Daily portfolio valuation history. Populated by a scheduled job."""

    __tablename__ = "snapshots"
    __table_args__ = (UniqueConstraint("user_id", "taken_at", name="uq_snapshot_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    taken_at: Mapped[date] = mapped_column(Date, index=True)
    total_value: Mapped[float] = mapped_column(Float)
    base_currency: Mapped[str] = mapped_column(String(3), default="EUR")
    by_position: Mapped[dict] = mapped_column(JSON, default=dict)

    user: Mapped[User] = relationship(back_populates="snapshots")


class CachePrice(Base):
    """OHLCV daily cache for any (ticker, date). Refreshed by the data layer."""

    __tablename__ = "cache_prices"
    __table_args__ = (UniqueConstraint("ticker", "date", name="uq_cache_ticker_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
