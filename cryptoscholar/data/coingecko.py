"""CoinGecko free API client with TTL cache and retry logic."""

import time
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.coingecko.com/api/v3"

SYMBOL_TO_ID: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "NEAR": "near",
    "APT": "aptos",
    "ARB": "arbitrum",
    "OP": "optimism",
    "INJ": "injective-protocol",
}

_CACHE: dict[str, tuple[float, object]] = {}
_TTL_SECONDS = 300  # 5 minutes


def _cache_get(key: str) -> Optional[object]:
    entry = _CACHE.get(key)
    if entry is None:
        return None
    ts, value = entry
    if time.time() - ts > _TTL_SECONDS:
        del _CACHE[key]
        return None
    return value


def _cache_set(key: str, value: object) -> None:
    _CACHE[key] = (time.time(), value)


def _get(url: str, params: dict | None = None, retries: int = 3) -> dict:
    """GET with retry + exponential backoff."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            last_exc = exc
            if attempt < retries - 1:
                sleep_time = 2 ** attempt
                logger.warning("Request failed (attempt %d/%d): %s — retrying in %ds",
                               attempt + 1, retries, exc, sleep_time)
                time.sleep(sleep_time)
    raise RuntimeError(f"CoinGecko request failed after {retries} attempts: {last_exc}") from last_exc


def resolve_symbol(symbol: str) -> str:
    """Resolve a ticker symbol to a CoinGecko coin ID."""
    upper = symbol.upper()
    if upper in SYMBOL_TO_ID:
        return SYMBOL_TO_ID[upper]

    cache_key = f"search:{upper}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return str(cached)

    logger.info("Symbol %s not in static map — searching CoinGecko", upper)
    data = _get(f"{BASE_URL}/search", params={"query": upper})
    coins = data.get("coins", [])
    if not coins:
        raise ValueError(f"Symbol '{symbol}' not found on CoinGecko")

    # Prefer exact symbol match
    for coin in coins:
        if coin.get("symbol", "").upper() == upper:
            coin_id = coin["id"]
            _cache_set(cache_key, coin_id)
            return coin_id

    # Fall back to first result
    coin_id = coins[0]["id"]
    _cache_set(cache_key, coin_id)
    return coin_id


def fetch_market_chart(coin_id: str, days: int = 90) -> dict:
    """
    Fetch daily OHLCV data from CoinGecko market_chart endpoint.

    Returns dict with keys: prices, market_caps, total_volumes
    Each value is a list of [timestamp_ms, value] pairs.
    """
    cache_key = f"market_chart:{coin_id}:{days}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    url = f"{BASE_URL}/coins/{coin_id}/market_chart"
    data = _get(url, params={"vs_currency": "usd", "days": days, "interval": "daily"})
    _cache_set(cache_key, data)
    return data


def fetch_market_data(coin_id: str) -> dict:
    """
    Fetch current market data for a coin.

    Returns the first item from /coins/markets.
    """
    cache_key = f"market_data:{coin_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    url = f"{BASE_URL}/coins/markets"
    data = _get(url, params={"vs_currency": "usd", "ids": coin_id})
    if not data:
        raise ValueError(f"No market data found for coin ID '{coin_id}'")
    result = data[0]
    _cache_set(cache_key, result)
    return result


def fetch_global() -> dict:
    """Fetch global market data (BTC dominance, total market cap)."""
    cache_key = "global"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    data = _get(f"{BASE_URL}/global")
    result = data.get("data", data)
    _cache_set(cache_key, result)
    return result


def build_ohlcv_dataframe(chart_data: dict) -> "pandas.DataFrame":  # type: ignore[name-defined]
    """
    Build a daily OHLCV DataFrame from CoinGecko market_chart response.

    Since the free API only provides daily close prices and volumes,
    OHLCV is approximated:
      open  = prev_close
      high  = max(open, close) * 1.005
      low   = min(open, close) * 0.995
      close = close
      volume = volume
    """
    import pandas as pd

    prices = chart_data.get("prices", [])
    volumes = chart_data.get("total_volumes", [])

    if not prices:
        raise ValueError("No price data in chart response")

    closes = [p[1] for p in prices]
    timestamps = [p[0] for p in prices]
    vol_map = {v[0]: v[1] for v in volumes}

    rows = []
    for i, (ts, close) in enumerate(zip(timestamps, closes)):
        open_ = closes[i - 1] if i > 0 else close
        high = max(open_, close) * 1.005
        low = min(open_, close) * 0.995
        volume = vol_map.get(ts, 0.0)
        rows.append({
            "timestamp": pd.Timestamp(ts, unit="ms", tz="UTC"),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        })

    df = pd.DataFrame(rows)
    df = df.set_index("timestamp")
    return df
