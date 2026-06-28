"""CoinGecko market data fetch + ticker→id resolution."""

import logging

import httpx

from app.config import get_settings
from app.models.schemas import MarketData

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Seed map for common / ambiguous tickers (CoinGecko needs the id, not the ticker).
SEED_MAP: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "XRP": "ripple",
    "SOL": "solana",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "BNB": "binancecoin",
    "USDT": "tether",
    "USDC": "usd-coin",
    "TRX": "tron",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "LTC": "litecoin",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "ATOM": "cosmos",
    "XLM": "stellar",
    "BCH": "bitcoin-cash",
    "SHIB": "shiba-inu",
    "UNI": "uniswap",
}

# Lazily populated cache of CoinGecko's full coin list (ticker -> [ids]).
_coins_list_cache: dict[str, list[str]] | None = None


def _headers() -> dict[str, str]:
    settings = get_settings()
    if settings.coingecko_api_key:
        return {"x-cg-demo-api-key": settings.coingecko_api_key}
    return {}


def _load_coins_list() -> dict[str, list[str]]:
    """Fetch /coins/list once and index by upper-case ticker symbol."""
    global _coins_list_cache
    if _coins_list_cache is not None:
        return _coins_list_cache

    index: dict[str, list[str]] = {}
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{COINGECKO_BASE}/coins/list", headers=_headers())
            resp.raise_for_status()
            for entry in resp.json():
                sym = (entry.get("symbol") or "").upper()
                cid = entry.get("id")
                if sym and cid:
                    index.setdefault(sym, []).append(cid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("coins/list yüklenemedi: %s", exc)

    _coins_list_cache = index
    return index


def resolve_coin_id(ticker: str) -> str | None:
    """Resolve a ticker (e.g. 'XRP') to a CoinGecko id (e.g. 'ripple')."""
    t = ticker.strip().upper()
    if not t:
        return None

    if t in SEED_MAP:
        return SEED_MAP[t]

    candidates = _load_coins_list().get(t, [])
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    # Collision: pick the one with the highest market cap.
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{COINGECKO_BASE}/coins/markets",
                params={
                    "vs_currency": "usd",
                    "ids": ",".join(candidates),
                    "order": "market_cap_desc",
                    "per_page": len(candidates),
                    "page": 1,
                },
                headers=_headers(),
            )
            resp.raise_for_status()
            rows = resp.json()
            if rows:
                return rows[0]["id"]
    except Exception as exc:  # noqa: BLE001
        logger.warning("ticker collision çözülemedi (%s): %s", t, exc)

    # Fallback: first candidate.
    return candidates[0]


def get_market_data(coin_id: str) -> MarketData:
    """Fetch current market data for a CoinGecko coin id."""
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{COINGECKO_BASE}/coins/markets",
            params={
                "vs_currency": "usd",
                "ids": coin_id,
                "price_change_percentage": "24h,7d,30d",
            },
            headers=_headers(),
        )
        resp.raise_for_status()
        rows = resp.json()

    if not rows:
        # Unknown id / no data — return empty MarketData rather than crashing.
        return MarketData()

    row = rows[0]
    return MarketData(
        price_usd=row.get("current_price"),
        change_24h=row.get("price_change_percentage_24h_in_currency")
        or row.get("price_change_percentage_24h"),
        change_7d=row.get("price_change_percentage_7d_in_currency"),
        change_30d=row.get("price_change_percentage_30d_in_currency"),
        volume_24h=row.get("total_volume"),
        market_cap=row.get("market_cap"),
    )
