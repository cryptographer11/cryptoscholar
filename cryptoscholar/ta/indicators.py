"""Technical analysis indicator computations."""

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calc_historical_volatility(close: pd.Series, period: int = 20) -> pd.Series:
    """Annualised historical volatility as percentage (log returns std × √365 × 100)."""
    log_ret = np.log(close / close.shift(1))
    return log_ret.rolling(period).std() * np.sqrt(365) * 100


def calc_relative_strength(
    target_close: pd.Series,
    base_close: pd.Series,
    period: int = 20,
) -> pd.Series:
    """Percentage change of target/base ratio over `period` bars."""
    ratio = target_close / base_close.replace(0, np.nan)
    return ratio.pct_change(period) * 100


def _resample_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV to weekly (week ending Friday)."""
    weekly = df.resample("W-FRI").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna()
    return weekly


def compute_4h_indicators(df_4h: pd.DataFrame) -> dict:
    """
    Compute minimal indicators from 4H OHLCV for multi-timeframe alignment.

    Parameters
    ----------
    df_4h : 4H OHLCV DataFrame with DatetimeIndex.

    Returns
    -------
    Dict with ema_20_4h, ema_50_4h, rsi_14_4h.
    """
    try:
        import pandas_ta as ta
    except ImportError as exc:
        raise ImportError("pandas_ta is required: pip install pandas-ta") from exc

    result: dict = {}
    close = df_4h["close"]

    def _last(series: pd.Series) -> Optional[float]:
        if series is None or series.empty:
            return None
        val = series.iloc[-1]
        return float(val) if pd.notna(val) else None

    result["ema_20_4h"] = _last(ta.ema(close, length=20))
    result["ema_50_4h"] = _last(ta.ema(close, length=50))
    result["rsi_14_4h"] = _last(ta.rsi(close, length=14))
    return result


def detect_rsi_divergence(df: pd.DataFrame, window: int = 30) -> str:
    """
    Detect RSI divergence over the last `window` bars.

    Splits the window into two halves and compares price extremes vs RSI extremes:
    - Bullish: price lower low + RSI higher low  → trend may be bottoming
    - Bearish: price higher high + RSI lower high → trend may be topping

    Parameters
    ----------
    df     : Daily OHLCV DataFrame with DatetimeIndex.
    window : Number of bars to examine (default 30).

    Returns
    -------
    One of: 'bullish', 'bearish', 'none'
    """
    try:
        import pandas_ta as ta
    except ImportError as exc:
        raise ImportError("pandas_ta is required: pip install pandas-ta") from exc

    if len(df) < window + 14:
        return "none"

    close = df["close"].iloc[-(window + 14):]
    rsi = ta.rsi(close, length=14)
    if rsi is None or rsi.dropna().empty:
        return "none"

    price_window = df["close"].iloc[-window:]
    rsi_window = rsi.iloc[-window:]

    if len(price_window) < window or rsi_window.isna().any():
        return "none"

    half = window // 2
    price_first = price_window.iloc[:half]
    price_second = price_window.iloc[half:]
    rsi_first = rsi_window.iloc[:half]
    rsi_second = rsi_window.iloc[half:]

    # Bullish divergence: price lower low but RSI higher low
    if price_second.min() < price_first.min() and rsi_second.min() > rsi_first.min():
        return "bullish"
    # Bearish divergence: price higher high but RSI lower high
    if price_second.max() > price_first.max() and rsi_second.max() < rsi_first.max():
        return "bearish"
    return "none"


def calc_obv_trend(df: pd.DataFrame, ema_length: int = 10, window: int = 5) -> str:
    """
    Compute OBV trend direction using EMA of On-Balance Volume.

    Computes OBV → smooths with EMA-10 → checks slope over last `window` bars.

    Returns
    -------
    'rising'  — OBV EMA sloped up > 2% over window
    'falling' — OBV EMA sloped down > 2% over window
    'flat'    — otherwise or insufficient data
    """
    try:
        import pandas_ta as ta
    except ImportError as exc:
        raise ImportError("pandas_ta is required: pip install pandas-ta") from exc

    close = df["close"]
    volume = df["volume"]

    obv = ta.obv(close, volume)
    if obv is None or len(obv.dropna()) < ema_length + window:
        return "flat"

    obv_ema = ta.ema(obv, length=ema_length)
    if obv_ema is None or len(obv_ema.dropna()) < window:
        return "flat"

    tail = obv_ema.dropna().iloc[-window:]
    if len(tail) < 2:
        return "flat"

    start_val = float(tail.iloc[0])
    end_val = float(tail.iloc[-1])
    if start_val == 0:
        return "flat"

    slope_pct = (end_val - start_val) / abs(start_val) * 100
    if slope_pct > 2.0:
        return "rising"
    if slope_pct < -2.0:
        return "falling"
    return "flat"


def compute_indicators(
    df: pd.DataFrame,
    btc_close: Optional[pd.Series] = None,
) -> dict:
    """
    Compute all TA indicators from a daily OHLCV DataFrame.

    Parameters
    ----------
    df:
        DataFrame with columns: open, high, low, close, volume.
        Index must be DatetimeIndex.
    btc_close:
        Optional BTC daily close series for relative strength calculation.
        Only used when the input coin is not BTC.

    Returns
    -------
    Flat dict of indicator values (latest bar only).
    """
    try:
        import pandas_ta as ta
    except ImportError as exc:
        raise ImportError("pandas_ta is required: pip install pandas-ta") from exc

    result: dict = {}
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    def _last(series: pd.Series) -> Optional[float]:
        if series is None or series.empty:
            return None
        val = series.iloc[-1]
        return float(val) if pd.notna(val) else None

    # --- EMAs ---
    result["ema_20"] = _last(ta.ema(close, length=20))
    result["ema_50"] = _last(ta.ema(close, length=50))
    result["ema_200"] = _last(ta.ema(close, length=200))

    # --- Weekly EMA slope (3-bar % change of EMA-10 on weekly candles) ---
    weekly_df = _resample_weekly(df)
    if len(weekly_df) >= 13:
        weekly_ema10 = ta.ema(weekly_df["close"], length=10)
        if weekly_ema10 is not None and len(weekly_ema10.dropna()) >= 4:
            vals = weekly_ema10.dropna()
            slope = float((vals.iloc[-1] - vals.iloc[-4]) / vals.iloc[-4] * 100) if vals.iloc[-4] != 0 else None
            result["weekly_ema_slope"] = slope
        else:
            result["weekly_ema_slope"] = None
    else:
        result["weekly_ema_slope"] = None

    # --- RSI-14 ---
    rsi = ta.rsi(close, length=14)
    result["rsi_14"] = _last(rsi)

    # --- MACD ---
    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    if macd_df is not None and not macd_df.empty:
        macd_cols = macd_df.columns.tolist()
        # pandas_ta names cols like MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
        line_col = next((c for c in macd_cols if c.startswith("MACD_")), None)
        signal_col = next((c for c in macd_cols if c.startswith("MACDs_")), None)
        hist_col = next((c for c in macd_cols if c.startswith("MACDh_")), None)
        result["macd_line"] = _last(macd_df[line_col]) if line_col else None
        result["macd_signal"] = _last(macd_df[signal_col]) if signal_col else None
        result["macd_hist"] = _last(macd_df[hist_col]) if hist_col else None
    else:
        result["macd_line"] = None
        result["macd_signal"] = None
        result["macd_hist"] = None

    # --- ADX-14 ---
    adx_df = ta.adx(high, low, close, length=14)
    if adx_df is not None and not adx_df.empty:
        adx_col = next((c for c in adx_df.columns if c.startswith("ADX_")), None)
        result["adx_14"] = _last(adx_df[adx_col]) if adx_col else None
    else:
        result["adx_14"] = None

    # --- ATR-14 ---
    atr = ta.atr(high, low, close, length=14)
    result["atr_14"] = _last(atr)

    # Store full ATR series for regime detection (last 90 values)
    if atr is not None:
        result["_atr_series"] = atr.dropna().tolist()
    else:
        result["_atr_series"] = []

    # --- Bollinger Bands ---
    bbands = ta.bbands(close, length=20, std=2)
    if bbands is not None and not bbands.empty:
        bb_cols = bbands.columns.tolist()
        bbu_col = next((c for c in bb_cols if c.startswith("BBU_")), None)
        bbl_col = next((c for c in bb_cols if c.startswith("BBL_")), None)
        bbm_col = next((c for c in bb_cols if c.startswith("BBM_")), None)
        bbb_col = next((c for c in bb_cols if c.startswith("BBB_")), None)
        result["bb_upper"] = _last(bbands[bbu_col]) if bbu_col else None
        result["bb_lower"] = _last(bbands[bbl_col]) if bbl_col else None
        result["bb_mid"] = _last(bbands[bbm_col]) if bbm_col else None
        result["bb_width"] = _last(bbands[bbb_col]) if bbb_col else None
        # Store full BBW series for regime detection
        if bbb_col:
            result["_bbw_series"] = bbands[bbb_col].dropna().tolist()
        else:
            result["_bbw_series"] = []
    else:
        result["bb_upper"] = None
        result["bb_lower"] = None
        result["bb_mid"] = None
        result["bb_width"] = None
        result["_bbw_series"] = []

    # --- Historical Volatility 20-day ---
    hv = calc_historical_volatility(close, period=20)
    result["hv_20"] = _last(hv)

    # --- Relative strength vs BTC ---
    if btc_close is not None:
        # Align indices before computing
        aligned_target, aligned_base = close.align(btc_close, join="inner")
        if len(aligned_target) >= 21:
            rs = calc_relative_strength(aligned_target, aligned_base, period=20)
            result["rs_btc"] = _last(rs)
        else:
            result["rs_btc"] = None
    else:
        result["rs_btc"] = None

    # --- Current price ---
    result["price"] = _last(close)

    # --- RSI divergence ---
    result["rsi_divergence"] = detect_rsi_divergence(df)

    # --- OBV trend ---
    result["obv_trend"] = calc_obv_trend(df)

    return result
