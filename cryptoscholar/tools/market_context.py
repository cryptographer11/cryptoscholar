"""market_context tool — macro market signals, ARS, and MRS."""

import logging

logger = logging.getLogger(__name__)


def market_context() -> dict:
    """
    Fetch macro market context signals for the overall crypto market.

    Makes 3 CoinGecko API calls (rate-limited, cached 5 min) and 1 DefiLlama call.
    Returns raw signals alongside composite scores so Claude can reason about
    macro conditions before individual coin analysis.

    Returns
    -------
    Dict with:
        btc_price_30d_change_pct     : BTC price % change over 30 days
        btc_dominance_current        : Current BTC market cap dominance (%)
        btc_dominance_30d_change_pct : Change in BTC dominance over 30 days
                                       (negative = capital rotating to alts)
        eth_btc_20d_change_pct       : ETH/BTC ratio % change over 20 days
                                       (positive = ETH outperforming, broad rally)
        total3_30d_change_pct        : % change in TOTAL3 market cap over 30 days
                                       (TOTAL3 = total crypto minus BTC minus ETH)
        stablecoin_supply_usd        : Current total stablecoin supply in USD
        stablecoin_30d_change_pct    : % change in stablecoin supply over 30 days
        btc_trend_score              : BTC macro trend score (0-100)
        ars                          : Altcoin Rotation Score (0-100)
        stablecoin_score             : Stablecoin supply trend score (0-100)
        mrs                          : Market Readiness Score (0-100)
    On error, affected keys will be None; scores default to 50.
    """
    from cryptoscholar.market.context import fetch_market_context

    try:
        return fetch_market_context()
    except Exception as exc:
        logger.error("market_context failed: %s", exc)
        return {"error": str(exc)}
