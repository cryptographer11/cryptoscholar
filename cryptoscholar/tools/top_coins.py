"""top_coins tool — fetch top N coins by market cap and rank by TSS."""

import logging

from cryptoscholar.data.coingecko import fetch_top_coins_by_market_cap
from cryptoscholar.tools.rank import rank_coins

logger = logging.getLogger(__name__)


def top_coins(limit: int = 50) -> list[dict]:
    """
    Fetch the top N cryptocurrencies by market cap and rank them by TSS.

    Stablecoins are excluded automatically. Coins that fail analysis are skipped.

    Parameters
    ----------
    limit : Number of top-market-cap coins to analyse (default 50, max 250).

    Returns
    -------
    List of dicts sorted by TSS descending, each with rank, symbol, TSS,
    regime, EMA alignment, MTF alignment, RSI divergence, and price data.
    """
    limit = max(1, min(limit, 250))
    logger.info("top_coins: fetching top %d symbols by market cap", limit)

    symbols = fetch_top_coins_by_market_cap(limit=limit)
    if not symbols:
        logger.warning("top_coins: no symbols returned from CoinGecko")
        return []

    logger.info("top_coins: ranking %d symbols", len(symbols))
    return rank_coins(symbols)
