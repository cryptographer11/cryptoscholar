"""analyze_coin tool implementation."""

import logging
from typing import Optional

from cryptoscholar.data.coingecko import (
    build_ohlcv_dataframe,
    fetch_market_chart,
    fetch_market_data,
    resolve_symbol,
)
from cryptoscholar.ta.indicators import compute_indicators
from cryptoscholar.ta.regime import classify_regime, compute_vrs
from cryptoscholar.ta.scoring import compute_tss

logger = logging.getLogger(__name__)


def analyze_coin(symbol: str, btc_df=None) -> dict:
    """
    Perform full technical analysis on a cryptocurrency.

    Parameters
    ----------
    symbol:
        Ticker symbol e.g. "BTC", "SOL".
    btc_df:
        Optional pre-fetched BTC OHLCV DataFrame (avoids extra API call
        when called from rank_coins).

    Returns
    -------
    Structured dict with all indicators, scores, regime, and market data.
    """
    symbol = symbol.upper().strip()
    coin_id = resolve_symbol(symbol)

    # Fetch price history — 250 days needed for EMA-200 to have enough data
    chart_data = fetch_market_chart(coin_id, days=250)
    df = build_ohlcv_dataframe(chart_data)

    if len(df) < 30:
        raise ValueError(f"Insufficient price history for {symbol} (got {len(df)} days, need 30)")

    # Get BTC close for relative strength (only for non-BTC coins)
    btc_close = None
    if symbol != "BTC":
        if btc_df is not None:
            btc_close = btc_df["close"]
        else:
            try:
                btc_chart = fetch_market_chart("bitcoin", days=250)
                btc_ohlcv = build_ohlcv_dataframe(btc_chart)
                btc_close = btc_ohlcv["close"]
            except Exception as exc:
                logger.warning("Could not fetch BTC data for RS calculation: %s", exc)

    # Compute indicators
    indicators = compute_indicators(df, btc_close=btc_close)

    # Regime
    regime = classify_regime(indicators)
    vrs = compute_vrs(regime)

    # TSS
    tss = compute_tss(indicators)

    # Current market data
    try:
        market = fetch_market_data(coin_id)
        price = market.get("current_price")
        market_cap = market.get("market_cap")
        price_change_24h = market.get("price_change_percentage_24h")
    except Exception as exc:
        logger.warning("Could not fetch market data for %s: %s", symbol, exc)
        price = indicators.get("price")
        market_cap = None
        price_change_24h = None

    # Build EMA alignment summary
    ema20 = indicators.get("ema_20")
    ema50 = indicators.get("ema_50")
    ema200 = indicators.get("ema_200")
    ema_alignment = _describe_ema_alignment(ema20, ema50, ema200)

    # Strip internal series keys from output
    public_indicators = {k: v for k, v in indicators.items() if not k.startswith("_")}

    return {
        "symbol": symbol,
        "coin_id": coin_id,
        "price": price,
        "market_cap": market_cap,
        "price_change_24h_pct": price_change_24h,
        "tss": tss,
        "regime": regime,
        "vrs": vrs,
        "ema_alignment": ema_alignment,
        "indicators": public_indicators,
    }


def _describe_ema_alignment(
    ema20: Optional[float],
    ema50: Optional[float],
    ema200: Optional[float],
) -> str:
    if any(v is None for v in (ema20, ema50, ema200)):
        return "unknown"
    if ema20 > ema50 > ema200:  # type: ignore[operator]
        return "full_bull"
    if ema20 < ema50 < ema200:  # type: ignore[operator]
        return "full_bear"
    if ema50 > ema200:  # type: ignore[operator]
        return "partial_bull"
    return "partial_bear"
