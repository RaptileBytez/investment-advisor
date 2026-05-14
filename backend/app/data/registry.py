"""Provider factory — selects and caches a single `DataProvider` instance
based on the `DATA_PROVIDER` setting."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.data.provider import DataProvider
from app.data.providers.yfinance_provider import YFinanceProvider

# Add new providers here as they're implemented.
_PROVIDERS: dict[str, type[DataProvider]] = {
    "yfinance": YFinanceProvider,
}


@lru_cache(maxsize=1)
def get_provider() -> DataProvider:
    name = get_settings().data_provider.lower()
    if name not in _PROVIDERS:
        raise ValueError(
            f"Unknown DATA_PROVIDER '{name}'. Available: {sorted(_PROVIDERS)}"
        )
    return _PROVIDERS[name]()
