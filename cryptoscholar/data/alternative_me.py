"""Alternative.me Fear & Greed Index client."""

import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.alternative.me/fng/"
_CACHE: dict = {}
_TTL = 3600  # 1 hour — index updates once per day


def fetch_fear_greed() -> Optional[dict]:
    """
    Fetch the current Fear & Greed Index from Alternative.me.

    No API key required. Updated daily.

    Returns
    -------
    Dict with keys:
        value (int 0-100)   — raw score
        label (str)         — classification e.g. "Extreme Fear", "Greed"
        timestamp (int)     — unix timestamp of the reading
    Returns None on failure.
    """
    cache_key = "fear_greed"
    cached = _CACHE.get(cache_key)
    if cached is not None:
        ts, val = cached
        if time.time() - ts < _TTL:
            return val

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(_BASE_URL, params={"limit": 1})
            resp.raise_for_status()
        data = resp.json()
        items = data.get("data", [])
        if not items:
            return None
        item = items[0]
        result = {
            "value": int(item["value"]),
            "label": item["value_classification"],
            "timestamp": int(item["timestamp"]),
        }
        _CACHE[cache_key] = (time.time(), result)
        return result
    except Exception as exc:
        logger.warning("Could not fetch Fear & Greed Index: %s", exc)
        return None
