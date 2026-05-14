"""FastAPI dependency providers."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.data.provider import DataProvider
from app.data.registry import get_provider as _resolve_provider
from app.db.models import User
from app.db.session import get_db
from app.portfolio.service import PortfolioService

# Single-user MVP. Multi-user auth lands behind an unchanged endpoint surface.
DEFAULT_USER_EMAIL = "default@local"


def get_data_provider() -> DataProvider:
    return _resolve_provider()


def get_portfolio_service(db: Session = Depends(get_db)) -> PortfolioService:
    return PortfolioService(db)


def get_current_user(service: PortfolioService = Depends(get_portfolio_service)) -> User:
    settings = get_settings()
    return service.get_or_create_user(
        DEFAULT_USER_EMAIL,
        base_currency=settings.base_currency,
        locale=settings.locale,
    )
