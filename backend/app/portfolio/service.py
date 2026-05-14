"""Portfolio service — records trades, keeps the denormalised `Holding` row
in sync, manages the watchlist.

Transactions are the source of truth; `Holding` is a cache for fast reads.
Avg-cost is updated only on BUY (weighted average); SELL reduces quantity
without touching avg_cost — realised P&L is computed at report time.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.data.exchanges import info_for
from app.db.models import Holding, Transaction, TradeSide, User, WatchlistItem

log = logging.getLogger(__name__)


class PortfolioError(RuntimeError):
    """Raised on invalid trade input (e.g. SELL more than held)."""


class PortfolioService:
    def __init__(self, db: Session):
        self.db = db

    # ── Users ────────────────────────────────────────────────
    def get_or_create_user(
        self,
        email: str,
        *,
        base_currency: str = "EUR",
        locale: str = "en",
    ) -> User:
        user = self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is not None:
            return user
        user = User(email=email, base_currency=base_currency, locale=locale)
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            user = self.db.execute(select(User).where(User.email == email)).scalar_one()
        self.db.refresh(user)
        return user

    # ── Transactions ─────────────────────────────────────────
    def record_trade(
        self,
        *,
        user_id: int,
        ticker: str,
        side: TradeSide,
        quantity: float,
        price: float,
        executed_at: datetime,
        fees: float = 0.0,
        currency: str | None = None,
        note: str | None = None,
    ) -> Transaction:
        if quantity <= 0:
            raise PortfolioError("quantity must be positive")
        if price < 0:
            raise PortfolioError("price cannot be negative")
        ticker = ticker.upper()
        currency = (currency or info_for(ticker).currency).upper()

        tx = Transaction(
            user_id=user_id,
            ticker=ticker,
            side=side,
            quantity=quantity,
            price=price,
            fees=fees,
            currency=currency,
            executed_at=executed_at,
            note=note,
        )
        self.db.add(tx)
        self._apply_to_holding(user_id=user_id, tx=tx)
        self.db.commit()
        self.db.refresh(tx)
        return tx

    # ── Holdings ─────────────────────────────────────────────
    def get_holdings(self, user_id: int) -> list[Holding]:
        rows = self.db.execute(
            select(Holding).where(Holding.user_id == user_id).order_by(Holding.ticker)
        ).scalars().all()
        return [h for h in rows if h.quantity > 0]

    def get_transactions(self, user_id: int, *, ticker: str | None = None) -> list[Transaction]:
        q = select(Transaction).where(Transaction.user_id == user_id)
        if ticker is not None:
            q = q.where(Transaction.ticker == ticker.upper())
        q = q.order_by(Transaction.executed_at.desc(), Transaction.id.desc())
        return list(self.db.execute(q).scalars().all())

    def _apply_to_holding(self, *, user_id: int, tx: Transaction) -> None:
        holding = self.db.execute(
            select(Holding).where(Holding.user_id == user_id, Holding.ticker == tx.ticker)
        ).scalar_one_or_none()

        if tx.side == TradeSide.BUY:
            if holding is None:
                holding = Holding(
                    user_id=user_id,
                    ticker=tx.ticker,
                    quantity=tx.quantity,
                    avg_cost=tx.price,
                    currency=tx.currency,
                )
                self.db.add(holding)
                return
            new_qty = holding.quantity + tx.quantity
            holding.avg_cost = (
                (holding.avg_cost * holding.quantity) + (tx.price * tx.quantity)
            ) / new_qty
            holding.quantity = new_qty
            return

        # SELL
        if holding is None or holding.quantity < tx.quantity - 1e-9:
            raise PortfolioError(
                f"cannot sell {tx.quantity} of {tx.ticker}: only "
                f"{holding.quantity if holding else 0} held"
            )
        holding.quantity = max(0.0, holding.quantity - tx.quantity)
        # avg_cost intentionally unchanged on sells.
        if holding.quantity <= 1e-9:
            holding.quantity = 0.0

    # ── Watchlist ────────────────────────────────────────────
    def add_to_watchlist(self, user_id: int, ticker: str) -> WatchlistItem:
        ticker = ticker.upper()
        existing = self.db.execute(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id, WatchlistItem.ticker == ticker
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        item = WatchlistItem(user_id=user_id, ticker=ticker)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def remove_from_watchlist(self, user_id: int, ticker: str) -> bool:
        ticker = ticker.upper()
        existing = self.db.execute(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id, WatchlistItem.ticker == ticker
            )
        ).scalar_one_or_none()
        if existing is None:
            return False
        self.db.delete(existing)
        self.db.commit()
        return True

    def get_watchlist(self, user_id: int) -> list[WatchlistItem]:
        return list(
            self.db.execute(
                select(WatchlistItem)
                .where(WatchlistItem.user_id == user_id)
                .order_by(WatchlistItem.added_at.desc())
            ).scalars().all()
        )
