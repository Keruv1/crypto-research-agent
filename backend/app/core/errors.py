"""Shared domain exceptions."""


class CoinNotFoundError(Exception):
    """Raised when a ticker cannot be resolved to a CoinGecko id."""
