"""rank_coins tool implementation."""

import logging
import time

from cryptoscholar.data.coingecko import build_ohlcv_dataframe, fetch_market_chart
from cryptoscholar.tools.analyze import analyze_coin

logger = logging.getLogger(__name__)

_RATE_LIMIT_SLEEP = 0.5  # seconds between coins to respect CoinGecko free tier


def rank_coins(symbols: list[str]) -> list[dict]:
    """
    Rank multiple cryptocurrencies by Trend Strength Score.

    Parameters
    ----------
    symbols:
        List of ticker symbols e.g. ["BTC", "ETH", "SOL"].

    Returns
    -------
    List of dicts sorted by TSS descending. Failed symbols are skipped.
    """
    if not symbols:
        return []

    # Pre-fetch BTC data once (used for RS calculation of all non-BTC coins)
    btc_df = None
    try:
        btc_chart = fetch_market_chart("bitcoin", days=90)
        btc_df = build_ohlcv_dataframe(btc_chart)
    except Exception as exc:
        logger.warning("Could not pre-fetch BTC data: %s", exc)

    results: list[dict] = []

    for i, symbol in enumerate(symbols):
        if i > 0:
            time.sleep(_RATE_LIMIT_SLEEP)

        try:
            analysis = analyze_coin(symbol, btc_df=btc_df)
            results.append({
                "symbol": analysis["symbol"],
                "tss": analysis["tss"],
                "regime": analysis["regime"],
                "vrs": analysis["vrs"],
                "price": analysis["price"],
                "price_change_24h_pct": analysis["price_change_24h_pct"],
                "ema_alignment": analysis["ema_alignment"],
                "rsi_14": analysis["indicators"].get("rsi_14"),
                "adx_14": analysis["indicators"].get("adx_14"),
                "rs_btc": analysis["indicators"].get("rs_btc"),
            })
        except Exception as exc:
            logger.warning("Failed to analyze %s — skipping: %s", symbol, exc)

    results.sort(key=lambda x: x["tss"], reverse=True)
    for rank, item in enumerate(results, start=1):
        item["rank"] = rank

    return results
