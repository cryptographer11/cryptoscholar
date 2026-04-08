"""Tests for the correlate_coins tool."""

from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest

from cryptoscholar.tools.correlate import correlate_coins


def _make_close_series(n: int, seed: int, trend: float = 0.001) -> pd.Series:
    """Generate a synthetic close price series."""
    rng = np.random.default_rng(seed)
    returns = rng.normal(trend, 0.02, n)
    closes = 100.0 * np.cumprod(1 + returns)
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    return pd.Series(closes, index=idx)


def _make_ohlcv_df(close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": close.shift(1).fillna(close.iloc[0]),
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "volume": 1e7,
        },
        index=close.index,
    )


def _make_fetch_mock(symbols: list[str], seeds: list[int]):
    """Build a mock for _fetch_ohlcv_with_fallback that returns synthetic data."""
    series_map = {
        sym: _make_ohlcv_df(_make_close_series(40, seed))
        for sym, seed in zip(symbols, seeds)
    }

    def _mock_fetch(symbol: str, days: int = 35):
        if symbol not in series_map:
            raise ValueError(f"Symbol {symbol} not found")
        return series_map[symbol], "binance"

    return _mock_fetch


class TestCorrelateCoins:
    def test_returns_expected_keys(self) -> None:
        symbols = ["BTC", "ETH", "SOL"]
        mock_fetch = _make_fetch_mock(symbols, [1, 2, 3])
        with patch("cryptoscholar.tools.correlate._fetch_ohlcv_with_fallback", side_effect=mock_fetch):
            result = correlate_coins(symbols)

        assert "symbols" in result
        assert "lookback_days" in result
        assert "matrix" in result
        assert "high_correlation_pairs" in result
        assert "uncorrelated_pairs" in result

    def test_matrix_is_square(self) -> None:
        symbols = ["BTC", "ETH", "SOL"]
        mock_fetch = _make_fetch_mock(symbols, [1, 2, 3])
        with patch("cryptoscholar.tools.correlate._fetch_ohlcv_with_fallback", side_effect=mock_fetch):
            result = correlate_coins(symbols)

        matrix = result["matrix"]
        assert set(matrix.keys()) == set(result["symbols"])
        for sym, row in matrix.items():
            assert set(row.keys()) == set(result["symbols"])

    def test_diagonal_is_one(self) -> None:
        symbols = ["BTC", "ETH"]
        mock_fetch = _make_fetch_mock(symbols, [1, 2])
        with patch("cryptoscholar.tools.correlate._fetch_ohlcv_with_fallback", side_effect=mock_fetch):
            result = correlate_coins(symbols)

        matrix = result["matrix"]
        for sym in result["symbols"]:
            assert matrix[sym][sym] == pytest.approx(1.0, abs=0.001)

    def test_matrix_symmetric(self) -> None:
        symbols = ["BTC", "ETH", "SOL"]
        mock_fetch = _make_fetch_mock(symbols, [1, 2, 3])
        with patch("cryptoscholar.tools.correlate._fetch_ohlcv_with_fallback", side_effect=mock_fetch):
            result = correlate_coins(symbols)

        matrix = result["matrix"]
        syms = result["symbols"]
        for i, a in enumerate(syms):
            for b in syms[i + 1:]:
                assert matrix[a][b] == pytest.approx(matrix[b][a], abs=0.001)

    def test_high_corr_pair_detected(self) -> None:
        """Two series with identical returns should show correlation ~1.0."""
        close = _make_close_series(40, seed=99)
        df = _make_ohlcv_df(close)

        def _mock_fetch(symbol: str, days: int = 35):
            return df, "binance"

        with patch("cryptoscholar.tools.correlate._fetch_ohlcv_with_fallback", side_effect=_mock_fetch):
            result = correlate_coins(["A", "B"])

        assert len(result["high_correlation_pairs"]) == 1
        pair = result["high_correlation_pairs"][0]
        assert pair["correlation"] == pytest.approx(1.0, abs=0.01)

    def test_raises_on_fewer_than_two_symbols(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            correlate_coins(["BTC"])

    def test_raises_on_more_than_twenty_symbols(self) -> None:
        symbols = [f"COIN{i}" for i in range(21)]
        with pytest.raises(ValueError, match="Maximum 20"):
            correlate_coins(symbols)

    def test_symbols_uppercased(self) -> None:
        symbols = ["btc", "eth"]
        mock_fetch = _make_fetch_mock(["BTC", "ETH"], [1, 2])
        with patch("cryptoscholar.tools.correlate._fetch_ohlcv_with_fallback", side_effect=mock_fetch):
            result = correlate_coins(symbols)
        assert "BTC" in result["symbols"]
        assert "ETH" in result["symbols"]

    def test_failed_symbol_skipped(self) -> None:
        def _mock_fetch(symbol: str, days: int = 35):
            if symbol == "FAIL":
                raise ValueError("not found")
            return _make_ohlcv_df(_make_close_series(40, seed=1)), "binance"

        with patch("cryptoscholar.tools.correlate._fetch_ohlcv_with_fallback", side_effect=_mock_fetch):
            result = correlate_coins(["BTC", "FAIL", "ETH"])

        assert "FAIL" not in result["symbols"]
        assert "BTC" in result["symbols"]
        assert "ETH" in result["symbols"]

    def test_raises_when_only_one_symbol_fetched(self) -> None:
        def _mock_fetch(symbol: str, days: int = 35):
            if symbol != "BTC":
                raise ValueError("not found")
            return _make_ohlcv_df(_make_close_series(40, seed=1)), "binance"

        with pytest.raises(ValueError, match="Insufficient data"):
            with patch("cryptoscholar.tools.correlate._fetch_ohlcv_with_fallback", side_effect=_mock_fetch):
                correlate_coins(["BTC", "FAIL"])
