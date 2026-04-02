"""CoinGecko free API client with TTL cache and retry logic."""

import threading
import time
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.coingecko.com/api/v3"

# Global rate limiter: minimum 2s between any HTTP request to CoinGecko.
# Free tier is ~10 req/min; 2s interval keeps us safely under that.
_RATE_LOCK = threading.Lock()
_LAST_REQUEST_TS: float = 0.0
_MIN_INTERVAL = 2.0  # seconds


def _rate_limit() -> None:
    """Block until the minimum interval since the last request has elapsed."""
    global _LAST_REQUEST_TS
    with _RATE_LOCK:
        elapsed = time.time() - _LAST_REQUEST_TS
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
        _LAST_REQUEST_TS = time.time()

SYMBOL_TO_ID: dict[str, str] = {
    # Tier 1 — top 10 by market cap
    "BTC":   "bitcoin",
    "ETH":   "ethereum",
    "BNB":   "binancecoin",
    "SOL":   "solana",
    "XRP":   "ripple",
    "USDC":  "usd-coin",
    "ADA":   "cardano",
    "AVAX":  "avalanche-2",
    "DOGE":  "dogecoin",
    "TRX":   "tron",
    # Tier 2 — 11–30
    "LINK":  "chainlink",
    "DOT":   "polkadot",
    "MATIC": "matic-network",
    "SHIB":  "shiba-inu",
    "LTC":   "litecoin",
    "BCH":   "bitcoin-cash",
    "UNI":   "uniswap",
    "ATOM":  "cosmos",
    "NEAR":  "near",
    "XLM":   "stellar",
    "ETC":   "ethereum-classic",
    "APT":   "aptos",
    "ARB":   "arbitrum",
    "OP":    "optimism",
    "INJ":   "injective-protocol",
    "ICP":   "internet-computer",
    "FIL":   "filecoin",
    "HBAR":  "hedera-hashgraph",
    "VET":   "vechain",
    "MKR":   "maker",
    # Tier 3 — 31–65
    "AAVE":  "aave",
    "GRT":   "the-graph",
    "ALGO":  "algorand",
    "EGLD":  "elrond-erd-2",
    "SAND":  "the-sandbox",
    "MANA":  "decentraland",
    "AXS":   "axie-infinity",
    "THETA": "theta-token",
    "XTZ":   "tezos",
    "EOS":   "eos",
    "CAKE":  "pancakeswap-token",
    "KAVA":  "kava",
    "ZEC":   "zcash",
    "XMR":   "monero",
    "RUNE":  "thorchain",
    "LDO":   "lido-dao",
    "CRV":   "curve-dao-token",
    "SNX":   "synthetix-network-token",
    "COMP":  "compound-governance-token",
    "1INCH": "1inch",
    "ENS":   "ethereum-name-service",
    "IMX":   "immutable-x",
    "BLUR":  "blur",
    "PENDLE":"pendle",
    "JTO":   "jito-governance-token",
    "PYTH":  "pyth-network",
    "W":     "wormhole",
    "STX":   "blockstack",
    "CFX":   "conflux-token",
    "FTM":   "fantom",
    "ONDO":  "ondo-finance",
    "SEI":   "sei-network",
    "SUI":   "sui",
    "TIA":   "celestia",
    "WIF":   "dogwifcoin",
    "BONK":  "bonk",
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
    """GET with rate limiting, retry, and exponential backoff. Handles 429 with a longer wait."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        _rate_limit()
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 429:
                    wait = 60
                    logger.warning("CoinGecko rate limited (429) — waiting %ds before retry", wait)
                    time.sleep(wait)
                    continue
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


def fetch_global_market_chart(days: int = 30) -> dict:
    """
    Fetch historical total crypto market cap from CoinGecko.

    Returns dict with keys:
      market_cap : [[timestamp_ms, total_mcap_usd], ...]
      volume     : [[timestamp_ms, total_vol_usd], ...]
    """
    cache_key = f"global_market_chart:{days}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    data = _get(
        f"{BASE_URL}/global/market_cap_chart",
        params={"days": days, "vs_currency": "usd"},
    )
    _cache_set(cache_key, data)
    return data


_STABLECOINS: frozenset[str] = frozenset({
    "USDT", "USDC", "BUSD", "DAI", "TUSD", "USDP", "USDD", "FRAX", "LUSD",
    "FDUSD", "PYUSD", "USDE", "USDS",
})


def fetch_top_coins_by_market_cap(limit: int = 50) -> list[str]:
    """
    Fetch top N cryptocurrency symbols by market cap from CoinGecko.

    Stablecoins are filtered out automatically.

    Parameters
    ----------
    limit : Maximum number of symbols to return (default 50, max 250).

    Returns
    -------
    List of uppercase ticker symbols e.g. ["BTC", "ETH", "SOL", ...]
    """
    per_page = min(limit + len(_STABLECOINS) + 5, 250)  # fetch extra to cover filtered ones
    cache_key = f"top_coins:{per_page}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached[:limit]  # type: ignore[index]

    data = _get(
        f"{BASE_URL}/coins/markets",
        params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": 1,
            "sparkline": False,
        },
    )

    symbols: list[str] = []
    for coin in data:
        sym = coin.get("symbol", "").upper()
        if sym and sym not in _STABLECOINS:
            symbols.append(sym)
        if len(symbols) >= limit:
            break

    _cache_set(cache_key, symbols)
    return symbols


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
