"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import glossary, markets, portfolio, risk, stocks, strategies
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.models import Base
from app.db.session import engine

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    # Create any missing tables on first run. Alembic remains the canonical
    # tool for schema *changes*, but the initial bootstrap shouldn't require
    # the user to run `alembic upgrade head` before the app is usable.
    Base.metadata.create_all(engine)
    log.info(
        "Investment Advisor backend v%s starting (provider=%s, languages=%s)",
        __version__,
        settings.data_provider,
        ",".join(settings.supported_languages),
    )
    yield
    log.info("Shutting down.")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Investment Advisor",
        version=__version__,
        description="Risk-aware investment advisor backend.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    app.include_router(stocks.router,     prefix="/api/stocks",     tags=["stocks"])
    app.include_router(portfolio.router,  prefix="/api/portfolio",  tags=["portfolio"])
    app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
    app.include_router(risk.router,       prefix="/api/risk",       tags=["risk"])
    app.include_router(glossary.router,   prefix="/api/glossary",   tags=["glossary"])
    app.include_router(markets.router,    prefix="/api/markets",    tags=["markets"])

    return app


app = create_app()
