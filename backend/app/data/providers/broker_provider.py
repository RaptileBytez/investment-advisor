"""Stub for future broker-backed providers (Alpaca, Interactive Brokers …).

This file deliberately ships unimplemented: it documents the interface that
will be extended to support live execution. When we add a real broker, it
will subclass `DataProvider` *and* the additional `BrokerProvider` mixin so
the same instance can both quote and trade."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.data.provider import DataProvider


@dataclass(frozen=True)
class Order:
    ticker: str
    side: str            # "buy" | "sell"
    quantity: float
    type: str            # "market" | "limit"
    limit_price: float | None = None
    note: str | None = None


@dataclass(frozen=True)
class OrderResult:
    order_id: str
    status: str
    filled_quantity: float
    average_price: float
    submitted_at: datetime


class BrokerProvider(DataProvider):
    """Mixed market-data + execution. Implementations must support both."""

    @abstractmethod
    def place_order(self, order: Order) -> OrderResult: ...

    @abstractmethod
    def get_account_balance(self, currency: str) -> float: ...

    @abstractmethod
    def get_open_orders(self) -> list[OrderResult]: ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> None: ...
