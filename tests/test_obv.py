"""Tests for OBV trend and funding rate components."""

import numpy as np
import pandas as pd
import pytest

from cryptoscholar.ta.indicators import calc_obv_trend
from cryptoscholar.ta.scoring import compute_obv_bonus, compute_tss


def _make_ohlcv(
    n: int = 60,
    start_price: float = 100.0,
    volume_multiplier: float = 1.0,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.001, 0.02, n)
    closes = start_price * np.cumprod(1 + returns)
    opens = np.roll(closes, 1)
    opens[0] = start_price
    highs = np.maximum(opens, closes) * (1 + rng.uniform(0, 0.005, n))
    lows = np.minimum(opens, closes) * (1 - rng.uniform(0, 0.005, n))
    volumes = rng.uniform(1e6, 1e8, n) * volume_multiplier
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=idx,
    )


def _make_rising_obv_df(n: int = 60) -> pd.DataFrame:
    """Construct DataFrame where OBV will trend upward: rising prices + high volume."""
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    closes = np.linspace(100, 150, n)
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    highs = closes * 1.005
    lows = closes * 0.995
    # Volume increases alongside price — classic rising OBV pattern
    volumes = np.linspace(1e7, 5e7, n)
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=idx,
    )


def _make_falling_obv_df(n: int = 60) -> pd.DataFrame:
    """Construct DataFrame where OBV will trend downward: falling prices + high volume."""
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    closes = np.linspace(150, 100, n)
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    highs = closes * 1.005
    lows = closes * 0.995
    volumes = np.linspace(1e7, 5e7, n)
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=idx,
    )


class TestCalcObvTrend:
    def test_returns_valid_string(self) -> None:
        df = _make_ohlcv(60)
        result = calc_obv_trend(df)
        assert result in ("rising", "falling", "flat")

    def test_insufficient_data_returns_flat(self) -> None:
        df = _make_ohlcv(5)
        assert calc_obv_trend(df) == "flat"

    def test_rising_obv_detected(self) -> None:
        df = _make_rising_obv_df(60)
        result = calc_obv_trend(df)
        assert result == "rising"

    def test_falling_obv_detected(self) -> None:
        df = _make_falling_obv_df(60)
        result = calc_obv_trend(df)
        assert result == "falling"

    def test_flat_volume_neutral(self) -> None:
        """Flat prices should produce OBV near zero, resulting in flat trend."""
        idx = pd.date_range("2024-01-01", periods=60, freq="D", tz="UTC")
        closes = np.full(60, 100.0)
        df = pd.DataFrame(
            {
                "open": closes,
                "high": closes * 1.001,
                "low": closes * 0.999,
                "close": closes,
                "volume": np.full(60, 1e7),
            },
            index=idx,
        )
        result = calc_obv_trend(df)
        assert result == "flat"


class TestComputeObvBonus:
    def test_rising_returns_positive(self) -> None:
        assert compute_obv_bonus({"obv_trend": "rising"}) == 2.0

    def test_falling_returns_negative(self) -> None:
        assert compute_obv_bonus({"obv_trend": "falling"}) == -2.0

    def test_flat_returns_zero(self) -> None:
        assert compute_obv_bonus({"obv_trend": "flat"}) == 0.0

    def test_missing_key_returns_zero(self) -> None:
        assert compute_obv_bonus({}) == 0.0

    def test_none_value_returns_zero(self) -> None:
        assert compute_obv_bonus({"obv_trend": None}) == 0.0


class TestTSSWithOBV:
    def _base_ind(self) -> dict:
        return {
            "ema_20": 105.0,
            "ema_50": 100.0,
            "ema_200": 90.0,
            "weekly_ema_slope": 5.0,
            "rsi_14": 60.0,
            "macd_line": 1.0,
            "macd_signal": 0.5,
            "adx_14": 30.0,
            "rs_btc": 5.0,
            "rsi_divergence": "none",
        }

    def test_rising_obv_raises_tss(self) -> None:
        ind_no_obv = self._base_ind()
        ind_rising = {**self._base_ind(), "obv_trend": "rising"}
        tss_no = compute_tss(ind_no_obv)
        tss_up = compute_tss(ind_rising)
        assert tss_up == pytest.approx(tss_no + 2.0, abs=0.1)

    def test_falling_obv_lowers_tss(self) -> None:
        ind_no_obv = self._base_ind()
        ind_falling = {**self._base_ind(), "obv_trend": "falling"}
        tss_no = compute_tss(ind_no_obv)
        tss_down = compute_tss(ind_falling)
        assert tss_down == pytest.approx(tss_no - 2.0, abs=0.1)

    def test_tss_clamped_at_100(self) -> None:
        ind = {
            "ema_20": 110.0, "ema_50": 100.0, "ema_200": 90.0,
            "weekly_ema_slope": 20.0,
            "rsi_14": 65.0, "macd_line": 2.0, "macd_signal": 0.5,
            "adx_14": 35.0, "rs_btc": 50.0,
            "rsi_divergence": "none", "obv_trend": "rising",
        }
        assert compute_tss(ind) <= 100.0

    def test_tss_clamped_at_zero(self) -> None:
        ind = {
            "ema_20": 80.0, "ema_50": 100.0, "ema_200": 120.0,
            "weekly_ema_slope": -20.0,
            "rsi_14": 20.0, "macd_line": -2.0, "macd_signal": 0.5,
            "adx_14": 5.0, "rs_btc": -50.0,
            "rsi_divergence": "none", "obv_trend": "falling",
        }
        assert compute_tss(ind) >= 0.0
