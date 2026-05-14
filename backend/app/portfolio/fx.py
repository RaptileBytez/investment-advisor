"""Currency conversion helpers.

For MVP we read FX rates from the same DataProvider that serves equity
quotes (yfinance exposes `EURUSD=X`, `GBPEUR=X` etc.). The conversion is
cached by the provider's quote cache so repeated lookups are cheap."""

from __future__ import annotations

import logging

from app.data.provider import DataProvider, ProviderError

log = logging.getLogger(__name__)


def fx_rate(provider: DataProvider, from_ccy: str, to_ccy: str) -> float:
    """Return units of `to_ccy` per unit of `from_ccy`.

    Raises `ProviderError` if no rate is available."""
    from_ccy = from_ccy.upper()
    to_ccy = to_ccy.upper()
    if from_ccy == to_ccy:
        return 1.0
    pair = f"{from_ccy}{to_ccy}=X"
    try:
        return provider.get_quote(pair).price
    except ProviderError:
        # Fall back via USD if a direct cross isn't quoted.
        if from_ccy != "USD" and to_ccy != "USD":
            try:
                via_usd_from = provider.get_quote(f"{from_ccy}USD=X").price
                via_usd_to = provider.get_quote(f"USD{to_ccy}=X").price
                return via_usd_from * via_usd_to
            except ProviderError as exc:
                raise ProviderError(f"no FX path {from_ccy}->{to_ccy}: {exc}") from exc
        raise


def convert(provider: DataProvider, amount: float, from_ccy: str, to_ccy: str) -> float:
    return amount * fx_rate(provider, from_ccy, to_ccy)
