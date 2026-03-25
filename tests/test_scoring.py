"""Tests for TSS scoring and regime classification."""

import pytest

from cryptoscholar.ta.regime import classify_regime, compute_vrs
from cryptoscholar.ta.scoring import (
    compute_tss,
    score_momentum_component,
    score_trend_component,
)


class TestScoreTrendComponent:
    def test_full_bull_alignment(self) -> None:
        """EMA20 > EMA50 > EMA200 + positive slope → high score."""
        ind = {
            "ema_20": 120.0,
            "ema_50": 110.0,
            "ema_200": 100.0,
            "weekly_ema_slope": 5.0,  # > 3
        }
        score = score_trend_component(ind)
        # 30 + 30 + 20 + 20 = 100
        assert score == pytest.approx(100.0)

    def test_all_none_returns_zero(self) -> None:
        ind: dict = {"ema_20": None, "ema_50": None, "ema_200": None, "weekly_ema_slope": None}
        assert score_trend_component(ind) == pytest.approx(0.0)

    def test_full_bear_alignment(self) -> None:
        """EMA20 < EMA50 < EMA200 + steep negative slope → 0 (clamped)."""
        ind = {
            "ema_20": 80.0,
            "ema_50": 90.0,
            "ema_200": 100.0,
            "weekly_ema_slope": -5.0,  # < -3 → -10
        }
        score = score_trend_component(ind)
        # 0 EMAs score + (-10) slope, clamped to 0
        assert score == pytest.approx(0.0)

    def test_partial_bull(self) -> None:
        """EMA50 > EMA200 but EMA20 < EMA50 → partial score."""
        ind = {
            "ema_20": 105.0,
            "ema_50": 110.0,
            "ema_200": 100.0,
            "weekly_ema_slope": 1.0,  # 0 < slope < 3 → +10
        }
        score = score_trend_component(ind)
        # EMA50>EMA200: +30, EMA20>EMA200: +20, slope: +10 = 60
        assert score == pytest.approx(60.0)

    def test_score_clamped_to_0_100(self) -> None:
        ind = {"ema_20": None, "ema_50": None, "ema_200": None, "weekly_ema_slope": -100.0}
        score = score_trend_component(ind)
        assert 0.0 <= score <= 100.0


class TestScoreMomentumComponent:
    def test_rsi_60_macd_bullish_adx_30(self) -> None:
        """RSI in 50-70 + bullish MACD + ADX > 25 → score > 50."""
        ind = {
            "rsi_14": 60.0,
            "macd_line": 1.5,
            "macd_signal": 1.0,
            "adx_14": 30.0,
        }
        score = score_momentum_component(ind)
        # 50 + 25 + 15 + 10 = 100
        assert score == pytest.approx(100.0)

    def test_all_none_returns_50(self) -> None:
        ind: dict = {"rsi_14": None, "macd_line": None, "macd_signal": None, "adx_14": None}
        assert score_momentum_component(ind) == pytest.approx(50.0)

    def test_weak_momentum(self) -> None:
        """RSI < 40 + bearish MACD + weak ADX → score < 50."""
        ind = {
            "rsi_14": 35.0,
            "macd_line": 0.5,
            "macd_signal": 1.0,
            "adx_14": 15.0,
        }
        score = score_momentum_component(ind)
        # 50 - 25 - 15 - 10 = 0
        assert score == pytest.approx(0.0)

    def test_overbought_rsi(self) -> None:
        """RSI >= 70 → only +10, not +25."""
        ind = {
            "rsi_14": 75.0,
            "macd_line": None,
            "macd_signal": None,
            "adx_14": None,
        }
        score = score_momentum_component(ind)
        assert score == pytest.approx(60.0)  # 50 + 10

    def test_score_clamped_to_0_100(self) -> None:
        ind = {"rsi_14": 5.0, "macd_line": 0.0, "macd_signal": 10.0, "adx_14": 10.0}
        score = score_momentum_component(ind)
        assert 0.0 <= score <= 100.0


class TestComputeTSS:
    def test_weighted_combination(self) -> None:
        """Verify TSS = 0.4*trend + 0.3*momentum + 0.3*rs_score."""
        ind = {
            "ema_20": 120.0,
            "ema_50": 110.0,
            "ema_200": 100.0,
            "weekly_ema_slope": 5.0,
            "rsi_14": 60.0,
            "macd_line": 1.5,
            "macd_signal": 1.0,
            "adx_14": 30.0,
            "rs_btc": 0.0,  # neutral RS → rs_score = 50
        }
        tss = compute_tss(ind)
        # trend=100, momentum=100, rs_score=50
        expected = round(0.4 * 100 + 0.3 * 100 + 0.3 * 50, 1)
        assert tss == pytest.approx(expected)

    def test_rs_btc_none_treated_as_zero(self) -> None:
        ind = {
            "ema_20": None, "ema_50": None, "ema_200": None,
            "weekly_ema_slope": None,
            "rsi_14": None, "macd_line": None, "macd_signal": None, "adx_14": None,
            "rs_btc": None,
        }
        tss = compute_tss(ind)
        # trend=0, momentum=50, rs_score=50
        expected = round(0.4 * 0 + 0.3 * 50 + 0.3 * 50, 1)
        assert tss == pytest.approx(expected)

    def test_positive_rs_increases_score(self) -> None:
        base_ind: dict = {
            "ema_20": None, "ema_50": None, "ema_200": None,
            "weekly_ema_slope": None,
            "rsi_14": None, "macd_line": None, "macd_signal": None, "adx_14": None,
        }
        ind_neutral = {**base_ind, "rs_btc": 0.0}
        ind_positive = {**base_ind, "rs_btc": 10.0}
        assert compute_tss(ind_positive) > compute_tss(ind_neutral)

    def test_tss_in_0_100_range(self) -> None:
        ind = {
            "ema_20": 120.0, "ema_50": 110.0, "ema_200": 100.0,
            "weekly_ema_slope": 10.0,
            "rsi_14": 65.0, "macd_line": 2.0, "macd_signal": 1.0, "adx_14": 35.0,
            "rs_btc": 50.0,
        }
        tss = compute_tss(ind)
        assert 0.0 <= tss <= 100.0


class TestClassifyRegime:
    def _make_series(self, n: int, value: float) -> list[float]:
        return [value] * n

    def test_high_vol_regime(self) -> None:
        """Current ATR and BBW in top 30% → high_vol."""
        # Range 1..10; top 30% threshold = 7. Current = 10 (100th percentile)
        atr_series = list(range(1, 11))   # current=10, max=10
        bbw_series = list(range(1, 11))
        ind = {"_atr_series": atr_series, "_bbw_series": bbw_series}
        assert classify_regime(ind) == "high_vol"

    def test_low_vol_regime(self) -> None:
        """Current ATR and BBW in bottom 30% → low_vol."""
        # Range 1..10; bottom 30% threshold = 3. Current = 1 (0th percentile)
        atr_series = list(range(1, 11))
        bbw_series = list(range(1, 11))
        ind = {
            "_atr_series": [10, 9, 8, 7, 6, 5, 4, 3, 2, 1],  # current=1
            "_bbw_series": [10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
        }
        assert classify_regime(ind) == "low_vol"

    def test_mid_vol_regime(self) -> None:
        """ATR/BBW in middle of range → mid_vol."""
        # Range 1..10; current = 5 (44th percentile — between 30% and 70%)
        atr_series = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        bbw_series = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        # Set last element to middle value
        mid_atr = [1, 2, 3, 4, 5, 6, 7, 8, 9, 5]
        mid_bbw = [1, 2, 3, 4, 5, 6, 7, 8, 9, 5]
        ind = {"_atr_series": mid_atr, "_bbw_series": mid_bbw}
        assert classify_regime(ind) == "mid_vol"

    def test_insufficient_data_defaults_mid(self) -> None:
        ind = {"_atr_series": [1.0, 2.0], "_bbw_series": [1.0]}
        assert classify_regime(ind) == "mid_vol"

    def test_empty_series_defaults_mid(self) -> None:
        ind: dict = {}
        assert classify_regime(ind) == "mid_vol"

    def test_vrs_low_vol(self) -> None:
        assert compute_vrs("low_vol") == 25

    def test_vrs_mid_vol(self) -> None:
        assert compute_vrs("mid_vol") == 55

    def test_vrs_high_vol(self) -> None:
        assert compute_vrs("high_vol") == 80
