"""Tests for the generate_report tool."""

import json
from unittest.mock import MagicMock, patch

import pytest

from cryptoscholar.tools.report import (
    _assemble_markdown,
    _build_stats_table,
    _cluster_signals,
    _format_clusters_for_prompt,
    _format_multi_coin_prompt,
    generate_report,
)

_SAMPLE_ANALYSIS = {
    "symbol": "BTC",
    "price": 65000.0,
    "price_change_24h_pct": 1.5,
    "tss": 72,
    "regime": "mid_vol",
    "regime_source": "hmm",
    "ema_alignment": "bullish",
    "mtf_alignment_4h": "aligned",
    "obv_trend": "rising",
    "data_source": "binance",
    "indicators": {
        "ema_20": 64000.0,
        "ema_50": 62000.0,
        "ema_200": 55000.0,
        "rsi_14": 58.5,
        "rsi_divergence": "none",
        "macd_hist": 120.5,
        "adx_14": 28.3,
        "atr_14": 1500.0,
        "bb_width": 0.08,
        "hv_20": 45.2,
        "rs_btc": 0.0,
        "weekly_ema_slope": 0.5,
        "funding_rate": 0.0001,
    },
}

_SAMPLE_SECTIONS_RESPONSE = json.dumps({
    "trend": "Price is above all EMAs, signalling a strong uptrend.",
    "momentum": "RSI at 58.5 is healthy; ADX 28 confirms trend strength.",
    "volume_onchain": "OBV is rising with price, confirming accumulation.",
    "risks": "Funding rate slightly positive; watch for long squeeze.",
    "summary": "BTC is in a healthy uptrend with broad signal confirmation.",
})

_SAMPLE_COMPARISON_RESPONSE = json.dumps({
    "comparison_table_notes": "BTC leads on trend; ETH lags on momentum.",
    "strongest_setup": "BTC — broadest confirmation across all signal groups.",
    "weakest_setup": "ETH — RSI divergence and weaker OBV trend.",
    "summary": "BTC is the stronger setup; ETH needs confirmation before entry.",
})


def _make_mock_client(single_response: str, comparison_response: str | None = None):
    """Build a mock anthropic.Anthropic client."""
    call_count = {"n": 0}

    def _create(**kwargs):
        msg = MagicMock()
        msg.content = [MagicMock(text=single_response)]
        if comparison_response and call_count["n"] >= 1:
            msg.content = [MagicMock(text=comparison_response)]
        call_count["n"] += 1
        return msg

    client = MagicMock()
    client.messages.create.side_effect = _create
    return client


class TestClusterSignals:
    def test_returns_expected_groups(self) -> None:
        clusters = _cluster_signals(_SAMPLE_ANALYSIS)
        assert set(clusters.keys()) == {
            "trend", "momentum", "volume_onchain", "volatility_regime", "relative_strength"
        }

    def test_trend_group_has_ema_alignment(self) -> None:
        clusters = _cluster_signals(_SAMPLE_ANALYSIS)
        assert clusters["trend"]["ema_alignment"] == "bullish"

    def test_missing_indicators_default_to_na(self) -> None:
        clusters = _cluster_signals({"symbol": "X", "indicators": {}})
        assert clusters["trend"]["ema_alignment"] == "N/A"
        assert clusters["momentum"]["rsi_14"] == "N/A"


class TestFormatPrompts:
    def test_format_clusters_includes_symbol(self) -> None:
        clusters = _cluster_signals(_SAMPLE_ANALYSIS)
        text = _format_clusters_for_prompt("BTC", clusters)
        assert "Symbol: BTC" in text
        assert "[TREND]" in text
        assert "[MOMENTUM]" in text

    def test_format_multi_coin_includes_all_symbols(self) -> None:
        eth = {**_SAMPLE_ANALYSIS, "symbol": "ETH", "tss": 55}
        text = _format_multi_coin_prompt([_SAMPLE_ANALYSIS, eth])
        assert "BTC" in text
        assert "ETH" in text
        assert "TSS=" in text


class TestBuildStatsTable:
    def test_returns_one_row_per_analysis(self) -> None:
        eth = {**_SAMPLE_ANALYSIS, "symbol": "ETH"}
        rows = _build_stats_table([_SAMPLE_ANALYSIS, eth])
        assert len(rows) == 2
        assert rows[0]["symbol"] == "BTC"
        assert rows[1]["symbol"] == "ETH"

    def test_row_has_required_keys(self) -> None:
        rows = _build_stats_table([_SAMPLE_ANALYSIS])
        assert "symbol" in rows[0]
        assert "tss" in rows[0]
        assert "regime" in rows[0]
        assert "rsi_14" in rows[0]


class TestAssembleMarkdown:
    def test_single_coin_contains_sections(self) -> None:
        sections = {
            "BTC": {
                "trend": "Uptrend confirmed.",
                "momentum": "Healthy RSI.",
                "volume_onchain": "OBV rising.",
                "risks": "Watch funding.",
                "summary": "Strong setup.",
            }
        }
        stats = _build_stats_table([_SAMPLE_ANALYSIS])
        md = _assemble_markdown(["BTC"], stats, sections)
        assert "# CryptoScholar Analysis Report" in md
        assert "## Key Statistics" in md
        assert "## BTC — Trend" in md
        assert "## BTC — Risks" in md
        assert "## BTC — Summary" in md

    def test_multi_coin_contains_comparison(self) -> None:
        sections = {
            "BTC": {"summary": "BTC is strong."},
            "ETH": {"summary": "ETH is moderate."},
        }
        stats = _build_stats_table([_SAMPLE_ANALYSIS, {**_SAMPLE_ANALYSIS, "symbol": "ETH"}])
        comparison = {
            "comparison_table_notes": "BTC leads.",
            "strongest_setup": "BTC",
            "weakest_setup": "ETH",
            "summary": "BTC wins.",
        }
        md = _assemble_markdown(["BTC", "ETH"], stats, sections, comparison)
        assert "## Comparative Analysis" in md
        assert "**Strongest setup:**" in md
        assert "## Overall Summary" in md


def _patch_generate_report(symbols, output_format="markdown"):
    """Helper: run generate_report with all external calls mocked."""
    mock_client = _make_mock_client(_SAMPLE_SECTIONS_RESPONSE, _SAMPLE_COMPARISON_RESPONSE)
    mock_future = MagicMock()
    mock_future.result.return_value = (symbols[0].upper(), _SAMPLE_ANALYSIS)

    with (
        patch("anthropic.Anthropic", return_value=mock_client),
        patch("cryptoscholar.tools.report.analyze_coin", return_value=_SAMPLE_ANALYSIS),
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
        patch("cryptoscholar.tools.report.ThreadPoolExecutor") as mock_executor,
        patch("cryptoscholar.tools.report.as_completed", return_value=[mock_future]),
    ):
        mock_executor.return_value.__enter__.return_value.submit.return_value = mock_future
        return generate_report(symbols, output_format=output_format)


class TestGenerateReport:
    def test_returns_error_on_empty_symbols(self) -> None:
        result = generate_report([])
        assert "error" in result

    def test_returns_error_on_too_many_symbols(self) -> None:
        result = generate_report([f"COIN{i}" for i in range(11)])
        assert "error" in result

    def test_returns_error_without_api_key(self) -> None:
        import os
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict("os.environ", env, clear=True):
            result = generate_report(["BTC"])
        assert "error" in result
        assert "ANTHROPIC_API_KEY" in result["error"]

    def test_single_coin_markdown_report(self) -> None:
        result = _patch_generate_report(["BTC"])
        assert result.get("errors") is None or result.get("errors") == []
        assert result["format"] == "markdown"
        assert "report" in result
        assert "stats_table" in result

    def test_markdown_report_contains_header(self) -> None:
        result = _patch_generate_report(["BTC"])
        assert "# CryptoScholar Analysis Report" in result["report"]

    def test_json_output_format(self) -> None:
        result = _patch_generate_report(["BTC"], output_format="json")
        assert result["format"] == "json"
        assert isinstance(result["report"], dict)
        assert "sections" in result["report"]
        assert "stats_table" in result["report"]

    def test_symbols_uppercased(self) -> None:
        result = _patch_generate_report(["btc"])
        assert result.get("symbols") == ["BTC"]

    def test_failed_symbol_excluded_gracefully(self) -> None:
        mock_client = _make_mock_client(_SAMPLE_SECTIONS_RESPONSE)
        fail_future = MagicMock()
        fail_future.result.side_effect = ValueError("not found")
        btc_future = MagicMock()
        btc_future.result.return_value = ("BTC", _SAMPLE_ANALYSIS)

        futures_map = {"FAIL": fail_future, "BTC": btc_future}

        def _submit(fn, sym):
            return futures_map.get(sym, fail_future)

        with (
            patch("anthropic.Anthropic", return_value=mock_client),
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch("cryptoscholar.tools.report.ThreadPoolExecutor") as mock_executor,
            patch("cryptoscholar.tools.report.as_completed", return_value=[fail_future, btc_future]),
        ):
            mock_executor.return_value.__enter__.return_value.submit.side_effect = _submit
            result = generate_report(["FAIL", "BTC"])

        assert "FAIL" not in (result.get("symbols") or [])
        assert "BTC" in (result.get("symbols") or [result.get("error", "")])
