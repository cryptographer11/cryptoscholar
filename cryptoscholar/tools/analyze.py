"""analyze_coin tool implementation."""

import logging
from typing import Optional

from cryptoscholar.data.coingecko import (
    build_ohlcv_dataframe,
    fetch_market_chart,
    fetch_market_data,
    resolve_symbol,
)
from cryptoscholar.ta.indicators import compute_4h_indicators, compute_indicators
from cryptoscholar.ta.regime import classify_regime, compute_vrs
from cryptoscholar.ta.scoring import compute_4h_alignment_bonus, compute_tss

logger = logging.getLogger(__name__)


def _fetch_ohlcv_with_fallback(symbol: str, days: int = 300) -> tuple["pd.DataFrame", str]:  # type: ignore[name-defined]
    """
    Try Binance first for real OHLCV candles; fall back to CoinGecko approximation.

    Returns (DataFrame, data_source) where data_source is 'binance' or 'coingecko'.
    """
    import pandas as pd  # noqa: F401

    try:
        from cryptoscholar.data.binance import fetch_ohlcv as fetch_binance
        df = fetch_binance(symbol, days=days)
        logger.debug("OHLCV source: Binance (%d candles for %s)", len(df), symbol)
        return df, "binance"
    except Exception as exc:
        logger.info("Binance unavailable for %s (%s) — falling back to CoinGecko", symbol, exc)

    # CoinGecko fallback: needs 250 days for EMA-200
    coin_id = resolve_symbol(symbol)
    chart_data = fetch_market_chart(coin_id, days=250)
    df = build_ohlcv_dataframe(chart_data)
    logger.debug("OHLCV source: CoinGecko (%d candles for %s)", len(df), symbol)
    return df, "coingecko"


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
    Includes 'data_source' field: 'binance' or 'coingecko'.
    """
    symbol = symbol.upper().strip()
    coin_id = resolve_symbol(symbol)

    # Fetch OHLCV — Binance (real candles) first, CoinGecko fallback
    df, data_source = _fetch_ohlcv_with_fallback(symbol, days=300)

    if len(df) < 30:
        raise ValueError(f"Insufficient price history for {symbol} (got {len(df)} days, need 30)")

    # Get BTC close for relative strength (only for non-BTC coins)
    btc_close = None
    if symbol != "BTC":
        if btc_df is not None:
            btc_close = btc_df["close"]
        else:
            try:
                btc_df_fetched, _ = _fetch_ohlcv_with_fallback("BTC", days=300)
                btc_close = btc_df_fetched["close"]
            except Exception as exc:
                logger.warning("Could not fetch BTC data for RS calculation: %s", exc)

    # Compute indicators (includes rsi_divergence)
    indicators = compute_indicators(df, btc_close=btc_close)

    # Fetch 4H data for MTF alignment (Binance only — no CoinGecko fallback for 4H)
    ind_4h: Optional[dict] = None
    try:
        from cryptoscholar.data.binance import fetch_ohlcv_4h
        df_4h = fetch_ohlcv_4h(symbol, bars=200)
        ind_4h = compute_4h_indicators(df_4h)
        logger.debug("4H MTF indicators fetched for %s", symbol)
    except Exception as exc:
        logger.info("Could not fetch 4H data for %s (%s) — MTF bonus skipped", symbol, exc)

    # Regime
    regime = classify_regime(indicators)
    vrs = compute_vrs(regime)

    # TSS with optional MTF bonus
    tss = compute_tss(indicators, ind_4h=ind_4h)

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

    mtf_alignment_4h = (
        "bullish" if ind_4h and compute_4h_alignment_bonus(ind_4h) > 0
        else "bearish" if ind_4h and compute_4h_alignment_bonus(ind_4h) < 0
        else "neutral" if ind_4h
        else "unavailable"
    )

    return {
        "symbol": symbol,
        "coin_id": coin_id,
        "data_source": data_source,
        "price": price,
        "market_cap": market_cap,
        "price_change_24h_pct": price_change_24h,
        "tss": tss,
        "regime": regime,
        "vrs": vrs,
        "ema_alignment": ema_alignment,
        "mtf_alignment_4h": mtf_alignment_4h,
        "rsi_divergence": indicators.get("rsi_divergence", "none"),
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
