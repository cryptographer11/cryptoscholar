"""Tests for top_coins tool and fetch_top_coins_by_market_cap."""

from unittest.mock import MagicMock, patch

import pytest

from cryptoscholar.data.coingecko import (
    _STABLECOINS,
    _WRAPPED_TOKENS,
    fetch_top_coins_by_market_cap,
)
from cryptoscholar.tools.top_coins import top_coins


# ---------------------------------------------------------------------------
# fetch_top_coins_by_market_cap
# ---------------------------------------------------------------------------

_HIGH_VOLUME = 50_000_000  # $50M — safely above the $10M threshold


def _make_market_response(symbols: list[str], volume: float = _HIGH_VOLUME) -> list[dict]:
    return [
        {"symbol": s.lower(), "id": s.lower(), "market_cap": 1_000_000_000, "total_volume": volume}
        for s in symbols
    ]


class TestFetchTopCoinsByMarketCap:
    def test_filters_stablecoins(self):
        raw = _make_market_response(["BTC", "ETH", "USDT", "SOL", "USDC", "BNB"])
        with patch("cryptoscholar.data.coingecko._get", return_value=raw), \
             patch("cryptoscholar.data.coingecko._cache_get", return_value=None), \
             patch("cryptoscholar.data.coingecko._cache_set"):
            result = fetch_top_coins_by_market_cap(limit=10)
        assert "USDT" not in result
        assert "USDC" not in result
        assert "BTC" in result
        assert "ETH" in result

    def test_filters_wrapped_tokens(self):
        raw = _make_market_response(["BTC", "WBTC", "ETH", "WETH", "SOL"])
        with patch("cryptoscholar.data.coingecko._get", return_value=raw), \
             patch("cryptoscholar.data.coingecko._cache_get", return_value=None), \
             patch("cryptoscholar.data.coingecko._cache_set"):
            result = fetch_top_coins_by_market_cap(limit=10)
        assert "WBTC" not in result
        assert "WETH" not in result
        assert "BTC" in result
        assert "ETH" in result

    def test_filters_low_volume_coins(self):
        raw = _make_market_response(["BTC", "LOWVOL"], volume=_HIGH_VOLUME)
        # Override LOWVOL to have tiny volume
        raw[1]["total_volume"] = 1_000_000  # $1M — below threshold
        with patch("cryptoscholar.data.coingecko._get", return_value=raw), \
             patch("cryptoscholar.data.coingecko._cache_get", return_value=None), \
             patch("cryptoscholar.data.coingecko._cache_set"):
            result = fetch_top_coins_by_market_cap(limit=10)
        assert "LOWVOL" not in result
        assert "BTC" in result

    def test_respects_limit(self):
        raw = _make_market_response([f"COIN{i}" for i in range(100)])
        with patch("cryptoscholar.data.coingecko._get", return_value=raw), \
             patch("cryptoscholar.data.coingecko._cache_get", return_value=None), \
             patch("cryptoscholar.data.coingecko._cache_set"):
            result = fetch_top_coins_by_market_cap(limit=5)
        assert len(result) == 5

    def test_returns_uppercase_symbols(self):
        raw = _make_market_response(["btc", "eth", "sol"])
        with patch("cryptoscholar.data.coingecko._get", return_value=raw), \
             patch("cryptoscholar.data.coingecko._cache_get", return_value=None), \
             patch("cryptoscholar.data.coingecko._cache_set"):
            result = fetch_top_coins_by_market_cap(limit=5)
        assert all(s == s.upper() for s in result)

    def test_uses_cache_when_available(self):
        cached = ["BTC", "ETH", "SOL"]
        with patch("cryptoscholar.data.coingecko._cache_get", return_value=cached), \
             patch("cryptoscholar.data.coingecko._get") as mock_get:
            result = fetch_top_coins_by_market_cap(limit=3)
        mock_get.assert_not_called()
        assert result == cached

    def test_all_known_stablecoins_filtered(self):
        raw = _make_market_response(list(_STABLECOINS) + ["BTC"])
        with patch("cryptoscholar.data.coingecko._get", return_value=raw), \
             patch("cryptoscholar.data.coingecko._cache_get", return_value=None), \
             patch("cryptoscholar.data.coingecko._cache_set"):
            result = fetch_top_coins_by_market_cap(limit=50)
        for stable in _STABLECOINS:
            assert stable not in result
        assert "BTC" in result

    def test_all_known_wrapped_tokens_filtered(self):
        raw = _make_market_response(list(_WRAPPED_TOKENS) + ["BTC"])
        with patch("cryptoscholar.data.coingecko._get", return_value=raw), \
             patch("cryptoscholar.data.coingecko._cache_get", return_value=None), \
             patch("cryptoscholar.data.coingecko._cache_set"):
            result = fetch_top_coins_by_market_cap(limit=50)
        for wrapped in _WRAPPED_TOKENS:
            assert wrapped not in result
        assert "BTC" in result

    def test_empty_response_returns_empty_list(self):
        with patch("cryptoscholar.data.coingecko._get", return_value=[]), \
             patch("cryptoscholar.data.coingecko._cache_get", return_value=None), \
             patch("cryptoscholar.data.coingecko._cache_set"):
            result = fetch_top_coins_by_market_cap(limit=10)
        assert result == []


# ---------------------------------------------------------------------------
# top_coins
# ---------------------------------------------------------------------------

class TestTopCoins:
    def test_delegates_to_rank_coins(self):
        mock_symbols = ["BTC", "ETH", "SOL"]
        mock_ranked = [
            {"symbol": "BTC", "tss": 80.0, "rank": 1},
            {"symbol": "ETH", "tss": 70.0, "rank": 2},
            {"symbol": "SOL", "tss": 60.0, "rank": 3},
        ]
        with patch("cryptoscholar.tools.top_coins.fetch_top_coins_by_market_cap", return_value=mock_symbols), \
             patch("cryptoscholar.tools.top_coins.rank_coins", return_value=mock_ranked) as mock_rank:
            result = top_coins(limit=3)
        mock_rank.assert_called_once_with(mock_symbols)
        assert result == mock_ranked

    def test_empty_symbols_returns_empty(self):
        with patch("cryptoscholar.tools.top_coins.fetch_top_coins_by_market_cap", return_value=[]):
            result = top_coins(limit=10)
        assert result == []

    def test_limit_clamped_to_250(self):
        with patch("cryptoscholar.tools.top_coins.fetch_top_coins_by_market_cap", return_value=[]) as mock_fetch, \
             patch("cryptoscholar.tools.top_coins.rank_coins", return_value=[]):
            top_coins(limit=9999)
        mock_fetch.assert_called_once_with(limit=250)

    def test_limit_clamped_to_1(self):
        with patch("cryptoscholar.tools.top_coins.fetch_top_coins_by_market_cap", return_value=[]) as mock_fetch, \
             patch("cryptoscholar.tools.top_coins.rank_coins", return_value=[]):
            top_coins(limit=0)
        mock_fetch.assert_called_once_with(limit=1)

    def test_default_limit_is_50(self):
        with patch("cryptoscholar.tools.top_coins.fetch_top_coins_by_market_cap", return_value=[]) as mock_fetch, \
             patch("cryptoscholar.tools.top_coins.rank_coins", return_value=[]):
            top_coins()
        mock_fetch.assert_called_once_with(limit=50)
