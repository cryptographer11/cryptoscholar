"""Tests for TA indicator calculations."""

import numpy as np
import pandas as pd
import pytest

from cryptoscholar.ta.indicators import (
    calc_historical_volatility,
    calc_relative_strength,
    compute_indicators,
)


def _make_ohlcv(n: int = 100, start_price: float = 100.0, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic daily OHLCV data."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.001, 0.02, n)
    closes = start_price * np.cumprod(1 + returns)
    opens = np.roll(closes, 1)
    opens[0] = start_price
    highs = np.maximum(opens, closes) * (1 + rng.uniform(0, 0.005, n))
    lows = np.minimum(opens, closes) * (1 - rng.uniform(0, 0.005, n))
    volumes = rng.uniform(1e6, 1e8, n)

    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    }, index=idx)


class TestCalcHistoricalVolatility:
    def test_annualisation_math(self) -> None:
        """Verify HV is annualised: std of log returns * sqrt(365) * 100."""
        close = pd.Series([100.0, 102.0, 101.0, 103.0, 105.0,
                           104.0, 106.0, 108.0, 107.0, 109.0,
                           110.0, 108.0, 111.0, 113.0, 112.0,
                           114.0, 116.0, 115.0, 117.0, 119.0,
                           120.0])
        hv = calc_historical_volatility(close, period=20)
        # Manually compute expected value for last bar
        log_rets = np.log(close / close.shift(1))
        expected = float(log_rets.rolling(20).std().iloc[-1] * np.sqrt(365) * 100)
        assert abs(float(hv.iloc[-1]) - expected) < 1e-10

    def test_returns_series_same_length(self) -> None:
        close = pd.Series(range(50, 100, 1), dtype=float)
        hv = calc_historical_volatility(close, period=20)
        assert len(hv) == len(close)

    def test_nan_at_start(self) -> None:
        """First `period` values should be NaN."""
        close = pd.Series([float(i) for i in range(1, 31)])
        hv = calc_historical_volatility(close, period=10)
        assert hv.iloc[:10].isna().all()
        assert pd.notna(hv.iloc[-1])

    def test_positive_values(self) -> None:
        close = pd.Series([100.0 * (1 + 0.01 * i) for i in range(50)])
        hv = calc_historical_volatility(close, period=20)
        valid = hv.dropna()
        assert (valid >= 0).all()


class TestCalcRelativeStrength:
    def test_known_ratio_pct_change(self) -> None:
        """RS = (target[-1]/base[-1]) / (target[-21]/base[-21]) - 1, scaled to %."""
        n = 25
        # target doubles over n bars, base is flat
        target = pd.Series([100.0 + i * 4 for i in range(n)])
        base = pd.Series([100.0] * n)
        rs = calc_relative_strength(target, base, period=20)
        # ratio = target/base = target (since base=100); pct_change(20)
        ratio = target / base
        expected = ratio.pct_change(20) * 100
        pd.testing.assert_series_equal(rs, expected)

    def test_returns_series_same_length(self) -> None:
        target = pd.Series([float(i) for i in range(1, 51)])
        base = pd.Series([float(i) for i in range(1, 51)])
        rs = calc_relative_strength(target, base, period=20)
        assert len(rs) == len(target)

    def test_zero_base_handled(self) -> None:
        """Zero base values should produce NaN, not raise."""
        target = pd.Series([1.0, 2.0, 3.0])
        base = pd.Series([0.0, 0.0, 0.0])
        rs = calc_relative_strength(target, base, period=1)
        assert rs.isna().all()


class TestComputeIndicators:
    def test_all_expected_keys_present(self) -> None:
        df = _make_ohlcv(100)
        result = compute_indicators(df)
        expected_keys = [
            "ema_20", "ema_50", "ema_200",
            "weekly_ema_slope",
            "rsi_14",
            "macd_line", "macd_signal", "macd_hist",
            "adx_14",
            "atr_14",
            "bb_upper", "bb_lower", "bb_mid", "bb_width",
            "hv_20",
            "rs_btc",
            "price",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_values_are_float_or_none(self) -> None:
        df = _make_ohlcv(100)
        result = compute_indicators(df)
        _STRING_KEYS = {"rsi_divergence"}
        for key, val in result.items():
            if key.startswith("_"):
                continue  # internal series, skip
            if key in _STRING_KEYS:
                assert isinstance(val, str), f"Key {key!r} should be str, got {type(val).__name__}"
                continue
            assert val is None or isinstance(val, float), (
                f"Key {key!r} has unexpected type {type(val).__name__}: {val!r}"
            )

    def test_rs_btc_computed_when_btc_provided(self) -> None:
        df = _make_ohlcv(100, start_price=50.0, seed=1)
        btc_df = _make_ohlcv(100, start_price=60000.0, seed=2)
        result = compute_indicators(df, btc_close=btc_df["close"])
        assert result["rs_btc"] is not None
        assert isinstance(result["rs_btc"], float)

    def test_rs_btc_none_when_no_btc(self) -> None:
        df = _make_ohlcv(100)
        result = compute_indicators(df, btc_close=None)
        assert result["rs_btc"] is None

    def test_price_equals_last_close(self) -> None:
        df = _make_ohlcv(100)
        result = compute_indicators(df)
        assert result["price"] == pytest.approx(float(df["close"].iloc[-1]))

    def test_ema_200_none_with_insufficient_data(self) -> None:
        """EMA-200 requires 200 bars; with 100 bars it should be None."""
        df = _make_ohlcv(100)
        result = compute_indicators(df)
        assert result["ema_200"] is None

    def test_ema_200_computed_with_sufficient_data(self) -> None:
        df = _make_ohlcv(210)
        result = compute_indicators(df)
        assert result["ema_200"] is not None
        assert isinstance(result["ema_200"], float)
