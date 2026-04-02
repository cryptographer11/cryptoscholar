"""Binance public API client — real OHLCV candles, no authentication required.

Free tier: 1,200 request-weight per minute. Klines endpoint has weight=2,
giving ~600 calls/min effective. No rate limiter needed at normal usage.
"""

import logging
from typing import Optional

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com/api/v3"

# Override map for symbols that don't follow the simple SYMBOL+USDT convention
_BINANCE_SYMBOL_OVERRIDES: dict[str, str] = {
    # None needed yet — all 20 coins in our map use standard USDT pairs
}


def _to_binance_pair(symbol: str) -> str:
    """Convert a ticker symbol to a Binance USDT trading pair."""
    upper = symbol.upper()
    return _BINANCE_SYMBOL_OVERRIDES.get(upper, upper + "USDT")


def fetch_klines(
    binance_pair: str,
    interval: str = "1d",
    limit: int = 300,
) -> list[list]:
    """
    Fetch raw klines from Binance.

    Parameters
    ----------
    binance_pair : e.g. "BTCUSDT"
    interval     : Binance interval string, e.g. "1d", "4h"
    limit        : Number of candles (max 1000)

    Returns
    -------
    List of kline arrays: [open_time, open, high, low, close, volume, ...]
    Raises httpx.HTTPStatusError on non-2xx response (incl. invalid symbol).
    """
    url = f"{BASE_URL}/klines"
    params = {"symbol": binance_pair, "interval": interval, "limit": min(limit, 1000)}
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
    return resp.json()


def build_ohlcv_dataframe(klines: list[list]) -> pd.DataFrame:
    """
    Convert Binance kline arrays to a daily OHLCV DataFrame.

    Binance kline format:
    [open_time, open, high, low, close, volume, close_time, ...]
    All price/volume fields are strings — we cast to float.
    """
    rows = []
    for entry in klines:
        rows.append({
            "timestamp": pd.Timestamp(entry[0], unit="ms", tz="UTC"),
            "open": float(entry[1]),
            "high": float(entry[2]),
            "low": float(entry[3]),
            "close": float(entry[4]),
            "volume": float(entry[5]),
        })
    df = pd.DataFrame(rows)
    df = df.set_index("timestamp")
    return df


def fetch_ohlcv_4h(symbol: str, bars: int = 200) -> pd.DataFrame:
    """
    Fetch 4H OHLCV candles for multi-timeframe analysis.

    Parameters
    ----------
    symbol : Ticker symbol e.g. "BTC", "SOL"
    bars   : Number of 4H candles (200 bars ≈ 33 days)

    Returns
    -------
    OHLCV DataFrame with DatetimeIndex.
    """
    pair = _to_binance_pair(symbol)
    try:
        klines = fetch_klines(pair, interval="4h", limit=min(bars, 1000))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 400:
            raise ValueError(
                f"Symbol '{symbol}' (pair '{pair}') not found on Binance"
            ) from exc
        raise RuntimeError(f"Binance 4H request failed for {pair}: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Binance 4H request failed for {pair}: {exc}") from exc

    if not klines:
        raise ValueError(f"Binance returned empty 4H klines for '{pair}'")

    df = build_ohlcv_dataframe(klines)
    logger.debug("Binance 4H: fetched %d candles for %s", len(df), pair)
    return df


def fetch_ohlcv(symbol: str, days: int = 300) -> pd.DataFrame:
    """
    Fetch real OHLCV candles for a symbol from Binance.

    Parameters
    ----------
    symbol : Ticker symbol e.g. "BTC", "SOL"
    days   : Number of daily candles to fetch (max 1000)

    Returns
    -------
    OHLCV DataFrame with DatetimeIndex.

    Raises
    ------
    ValueError  : Symbol not found on Binance (HTTP 400 from exchange).
    RuntimeError: Network or unexpected error.
    """
    pair = _to_binance_pair(symbol)
    try:
        klines = fetch_klines(pair, interval="1d", limit=days)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 400:
            raise ValueError(
                f"Symbol '{symbol}' (pair '{pair}') not found on Binance"
            ) from exc
        raise RuntimeError(f"Binance request failed for {pair}: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Binance request failed for {pair}: {exc}") from exc

    if not klines:
        raise ValueError(f"Binance returned empty klines for '{pair}'")

    df = build_ohlcv_dataframe(klines)
    logger.debug("Binance: fetched %d candles for %s", len(df), pair)
    return df
