"""rank_coins tool implementation."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from cryptoscholar.tools.analyze import _fetch_ohlcv_with_fallback, analyze_coin

logger = logging.getLogger(__name__)

_MAX_WORKERS = 8


def rank_coins(symbols: list[str]) -> list[dict]:
    """
    Rank multiple cryptocurrencies by Trend Strength Score.

    For lists larger than 5 coins, analysis runs in parallel using a thread pool
    (up to 8 workers). Binance fetches are effectively unlimited; CoinGecko
    fallbacks are serialised by the module-level rate limiter automatically.

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
    btc_df = None
    try:
        btc_df, src = _fetch_ohlcv_with_fallback("BTC", days=300)
        logger.info("Pre-fetched BTC OHLCV from %s for rank_coins RS baseline", src)
    except Exception as exc:
        logger.warning("Could not pre-fetch BTC data: %s", exc)

    results: list[dict] = []

    def _analyse(symbol: str) -> dict:
        analysis = analyze_coin(symbol, btc_df=btc_df)
        return {
            "symbol": analysis["symbol"],
            "tss": analysis["tss"],
            "regime": analysis["regime"],
            "vrs": analysis["vrs"],
            "data_source": analysis["data_source"],
            "price": analysis["price"],
            "price_change_24h_pct": analysis["price_change_24h_pct"],
            "ema_alignment": analysis["ema_alignment"],
            "mtf_alignment_4h": analysis.get("mtf_alignment_4h", "unavailable"),
            "rsi_divergence": analysis.get("rsi_divergence", "none"),
            "obv_trend": analysis.get("obv_trend", "flat"),
            "funding_rate": analysis.get("funding_rate"),
            "rsi_14": analysis["indicators"].get("rsi_14"),
            "adx_14": analysis["indicators"].get("adx_14"),
            "rs_btc": analysis["indicators"].get("rs_btc"),
        }

    workers = min(_MAX_WORKERS, len(symbols))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_analyse, sym): sym for sym in symbols}
        for future in as_completed(futures):
            sym = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                logger.warning("Failed to analyze %s — skipping: %s", sym, exc)

    results.sort(key=lambda x: x["tss"], reverse=True)
    for rank, item in enumerate(results, start=1):
        item["rank"] = rank

    return results
