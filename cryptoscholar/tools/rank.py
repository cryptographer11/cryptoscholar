"""rank_coins tool implementation."""

import logging

from cryptoscholar.tools.analyze import _fetch_ohlcv_with_fallback, analyze_coin

logger = logging.getLogger(__name__)


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

    # Pre-fetch BTC OHLCV once (used for RS calculation of all non-BTC coins).
    # Tries Binance first, falls back to CoinGecko — same logic as analyze_coin.
    btc_df = None
    try:
        btc_df, src = _fetch_ohlcv_with_fallback("BTC", days=300)
        logger.info("Pre-fetched BTC OHLCV from %s for rank_coins RS baseline", src)
    except Exception as exc:
        logger.warning("Could not pre-fetch BTC data: %s", exc)

    results: list[dict] = []

    for symbol in symbols:
        try:
            analysis = analyze_coin(symbol, btc_df=btc_df)
            results.append({
                "symbol": analysis["symbol"],
                "tss": analysis["tss"],
                "regime": analysis["regime"],
                "vrs": analysis["vrs"],
                "data_source": analysis["data_source"],
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
