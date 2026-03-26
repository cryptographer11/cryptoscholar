"""Unit tests for market context scoring functions (pure, no I/O)."""

import pytest

from cryptoscholar.market.context import (
    _pct_change,
    compute_ars,
    compute_btc_trend_score,
    compute_mrs,
    compute_stablecoin_score,
)


# ---------------------------------------------------------------------------
# _pct_change
# ---------------------------------------------------------------------------


def test_pct_change_basic() -> None:
    assert _pct_change([100.0, 110.0]) == pytest.approx(10.0)


def test_pct_change_negative() -> None:
    assert _pct_change([200.0, 150.0]) == pytest.approx(-25.0)


def test_pct_change_single_element_returns_none() -> None:
    assert _pct_change([100.0]) is None


def test_pct_change_empty_returns_none() -> None:
    assert _pct_change([]) is None


def test_pct_change_zero_first_returns_none() -> None:
    assert _pct_change([0.0, 100.0]) is None


def test_pct_change_longer_series_uses_first_and_last() -> None:
    # first=10, last=20 → +100%
    result = _pct_change([10.0, 12.0, 15.0, 18.0, 20.0])
    assert result == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# compute_btc_trend_score
# ---------------------------------------------------------------------------


def test_btc_trend_score_strong_up() -> None:
    assert compute_btc_trend_score(35.0) == 90.0


def test_btc_trend_score_moderate_up() -> None:
    assert compute_btc_trend_score(20.0) == 75.0


def test_btc_trend_score_mild_up() -> None:
    assert compute_btc_trend_score(8.0) == 62.0


def test_btc_trend_score_flat() -> None:
    assert compute_btc_trend_score(0.0) == 50.0


def test_btc_trend_score_mild_down() -> None:
    assert compute_btc_trend_score(-8.0) == 35.0


def test_btc_trend_score_moderate_down() -> None:
    assert compute_btc_trend_score(-20.0) == 22.0


def test_btc_trend_score_strong_down() -> None:
    assert compute_btc_trend_score(-35.0) == 10.0


def test_btc_trend_score_none_returns_neutral() -> None:
    assert compute_btc_trend_score(None) == 50.0


# ---------------------------------------------------------------------------
# compute_stablecoin_score
# ---------------------------------------------------------------------------


def test_stablecoin_score_large_increase() -> None:
    assert compute_stablecoin_score(12.0) == 80.0


def test_stablecoin_score_moderate_increase() -> None:
    assert compute_stablecoin_score(6.0) == 70.0


def test_stablecoin_score_small_increase() -> None:
    assert compute_stablecoin_score(2.0) == 60.0


def test_stablecoin_score_flat() -> None:
    assert compute_stablecoin_score(0.0) == 50.0


def test_stablecoin_score_small_decrease() -> None:
    assert compute_stablecoin_score(-2.0) == 38.0


def test_stablecoin_score_large_decrease() -> None:
    assert compute_stablecoin_score(-8.0) == 25.0


def test_stablecoin_score_none_returns_neutral() -> None:
    assert compute_stablecoin_score(None) == 50.0


# ---------------------------------------------------------------------------
# compute_ars
# ---------------------------------------------------------------------------


def test_ars_strongly_bullish_alts() -> None:
    # BTC dom fell >5%, ETH/BTC up >5%, TOTAL3 up >10%
    score = compute_ars(-6.0, 7.0, 12.0)
    assert score == pytest.approx(100.0)  # 50+20+15+15=100


def test_ars_strongly_bearish_alts() -> None:
    # BTC dom rose >5%, ETH/BTC down >5%, TOTAL3 down >10%
    score = compute_ars(6.0, -6.0, -11.0)
    assert score == pytest.approx(0.0)  # 50-20-15-15=0


def test_ars_neutral_all_none() -> None:
    assert compute_ars(None, None, None) == 50.0


def test_ars_neutral_small_changes() -> None:
    # BTC dom ±1% (no score change), ETH/BTC 0.5% (+8), TOTAL3 1% (+8)
    score = compute_ars(0.5, 0.5, 1.0)
    assert score == pytest.approx(50.0 + 8 + 8)


def test_ars_mixed_signals() -> None:
    # BTC dom falling -2% (+10), ETH/BTC flat -2% (-8), TOTAL3 neutral (-8)
    score = compute_ars(-2.0, -2.0, -2.0)
    assert score == pytest.approx(50.0 + 10 - 8 - 8)


def test_ars_clamped_at_100() -> None:
    score = compute_ars(-10.0, 10.0, 20.0)
    assert score == 100.0


def test_ars_clamped_at_0() -> None:
    score = compute_ars(10.0, -10.0, -20.0)
    assert score == 0.0


# ---------------------------------------------------------------------------
# compute_mrs
# ---------------------------------------------------------------------------


def test_mrs_weights() -> None:
    # 40% * 60 + 30% * 80 + 30% * 40 = 24 + 24 + 12 = 60
    assert compute_mrs(60.0, 80.0, 40.0) == pytest.approx(60.0)


def test_mrs_all_neutral() -> None:
    assert compute_mrs(50.0, 50.0, 50.0) == pytest.approx(50.0)


def test_mrs_all_max() -> None:
    assert compute_mrs(100.0, 100.0, 100.0) == pytest.approx(100.0)


def test_mrs_all_min() -> None:
    assert compute_mrs(0.0, 0.0, 0.0) == pytest.approx(0.0)


def test_mrs_btc_dominant_weight() -> None:
    # BTC trend dominates at 40%; others zero
    assert compute_mrs(100.0, 0.0, 0.0) == pytest.approx(40.0)


def test_mrs_ars_weight() -> None:
    assert compute_mrs(0.0, 100.0, 0.0) == pytest.approx(30.0)


def test_mrs_stablecoin_weight() -> None:
    assert compute_mrs(0.0, 0.0, 100.0) == pytest.approx(30.0)
