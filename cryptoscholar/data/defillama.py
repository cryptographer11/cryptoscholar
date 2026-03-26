"""DefiLlama public API client — stablecoin supply history.

No API key or rate limiting required. Used for stablecoin supply trend
as a market context signal (rising supply = more buying powder = bullish).
"""

import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://stablecoins.llama.fi"

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


def fetch_stablecoin_chart(days: int = 30) -> list[dict]:
    """
    Fetch total stablecoin market cap history from DefiLlama.

    Parameters
    ----------
    days : Number of recent daily data points to return.

    Returns
    -------
    List of dicts with keys: 'date' (unix timestamp int), 'totalCirculatingUSD' (dict).
    The key 'totalCirculatingUSD.peggedUSD' holds the USD total.
    Returns empty list on network error (non-fatal — stablecoin signal is optional).
    """
    cache_key = f"stablecoin_chart:{days}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached  # type: ignore[return-value]

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(f"{BASE_URL}/stablecoincharts/all")
            resp.raise_for_status()
            data: list[dict] = resp.json()
    except Exception as exc:
        logger.warning("DefiLlama stablecoin chart fetch failed: %s", exc)
        return []

    result = data[-days:] if len(data) >= days else data
    _cache_set(cache_key, result)
    return result


def extract_total_mcap_usd(entry: dict) -> Optional[float]:
    """Extract total USD stablecoin supply from a DefiLlama chart entry."""
    circ = entry.get("totalCirculatingUSD", {})
    if isinstance(circ, dict):
        val = circ.get("peggedUSD")
        if val is not None:
            return float(val)
    # Some older entries store it directly as a number
    if isinstance(circ, (int, float)):
        return float(circ)
    return None
