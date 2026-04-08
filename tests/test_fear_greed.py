"""Tests for Fear & Greed Index integration and MRS modifier."""

from unittest.mock import MagicMock, patch

import pytest

from cryptoscholar.market.context import (
    compute_fear_greed_modifier,
    compute_mrs,
)


class TestComputeFearGreedModifier:
    def test_extreme_fear_returns_positive(self) -> None:
        assert compute_fear_greed_modifier(10) == 5.0
        assert compute_fear_greed_modifier(0) == 5.0
        assert compute_fear_greed_modifier(19) == 5.0

    def test_extreme_greed_returns_negative(self) -> None:
        assert compute_fear_greed_modifier(90) == -5.0
        assert compute_fear_greed_modifier(100) == -5.0
        assert compute_fear_greed_modifier(81) == -5.0

    def test_neutral_zone_returns_zero(self) -> None:
        for val in (20, 50, 75, 80):
            assert compute_fear_greed_modifier(val) == 0.0

    def test_boundary_20_is_neutral(self) -> None:
        assert compute_fear_greed_modifier(20) == 0.0

    def test_boundary_80_is_neutral(self) -> None:
        assert compute_fear_greed_modifier(80) == 0.0

    def test_none_returns_zero(self) -> None:
        assert compute_fear_greed_modifier(None) == 0.0


class TestComputeMRSWithFearGreed:
    def test_default_modifier_zero_unchanged(self) -> None:
        """compute_mrs without modifier should match old behaviour."""
        mrs_old = round(0.4 * 75.0 + 0.3 * 60.0 + 0.3 * 50.0, 1)
        mrs_new = compute_mrs(75.0, 60.0, 50.0)
        assert mrs_new == mrs_old

    def test_extreme_fear_raises_mrs(self) -> None:
        base = compute_mrs(50.0, 50.0, 50.0)
        with_fear = compute_mrs(50.0, 50.0, 50.0, fear_greed_modifier=5.0)
        assert with_fear == pytest.approx(base + 5.0, abs=0.1)

    def test_extreme_greed_lowers_mrs(self) -> None:
        base = compute_mrs(50.0, 50.0, 50.0)
        with_greed = compute_mrs(50.0, 50.0, 50.0, fear_greed_modifier=-5.0)
        assert with_greed == pytest.approx(base - 5.0, abs=0.1)

    def test_mrs_clamped_at_100(self) -> None:
        assert compute_mrs(100.0, 100.0, 100.0, fear_greed_modifier=5.0) == 100.0

    def test_mrs_clamped_at_zero(self) -> None:
        assert compute_mrs(0.0, 0.0, 0.0, fear_greed_modifier=-5.0) == 0.0


class TestFetchFearGreed:
    def test_returns_expected_keys_on_success(self) -> None:
        from cryptoscholar.data.alternative_me import fetch_fear_greed, _CACHE

        _CACHE.clear()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {"value": "25", "value_classification": "Fear", "timestamp": "1700000000"}
            ]
        }
        with patch("cryptoscholar.data.alternative_me.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            result = fetch_fear_greed()

        assert result is not None
        assert result["value"] == 25
        assert result["label"] == "Fear"
        assert isinstance(result["timestamp"], int)

    def test_returns_none_on_http_failure(self) -> None:
        from cryptoscholar.data.alternative_me import fetch_fear_greed, _CACHE

        _CACHE.clear()
        with patch("cryptoscholar.data.alternative_me.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = Exception("timeout")
            result = fetch_fear_greed()

        assert result is None

    def test_returns_none_on_empty_data(self) -> None:
        from cryptoscholar.data.alternative_me import fetch_fear_greed, _CACHE

        _CACHE.clear()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"data": []}
        with patch("cryptoscholar.data.alternative_me.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            result = fetch_fear_greed()

        assert result is None

    def test_uses_cache_on_second_call(self) -> None:
        from cryptoscholar.data.alternative_me import fetch_fear_greed, _CACHE

        _CACHE.clear()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "data": [{"value": "50", "value_classification": "Neutral", "timestamp": "1700000000"}]
        }
        with patch("cryptoscholar.data.alternative_me.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            fetch_fear_greed()
            fetch_fear_greed()
            # HTTP should only be called once — second call hits cache
            assert mock_client.return_value.__enter__.return_value.get.call_count == 1
