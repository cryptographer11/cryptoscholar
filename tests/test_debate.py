"""Tests for the debate tool — OmniRoute-routed LLM bull/bear synthesis."""

import json
from unittest.mock import MagicMock, patch

import pytest

from cryptoscholar.tools.debate import debate

_MOCK_ANALYSIS = {
    "symbol": "BTC",
    "price": 65000.0,
    "price_change_24h_pct": 2.1,
    "tss": 72,
    "regime": "trending_bull",
    "vrs": 60,
    "ema_alignment": "bullish",
    "indicators": {"ema_20": 64000.0, "ema_50": 62000.0, "ema_200": 55000.0, "rsi_14": 58.0},
    "mtf_alignment_4h": "aligned",
}

_VALID_DEBATE_JSON = json.dumps(
    {
        "bull_case": "Momentum is strong with EMA alignment intact.",
        "bear_case": "RSI is approaching overbought territory.",
        "bottom_line": "Trend remains bullish while EMA structure holds.",
    }
)


def _mock_omniroute_response(content: str, status_ok: bool = True) -> MagicMock:
    resp = MagicMock()
    if status_ok:
        resp.raise_for_status = MagicMock()
    else:
        resp.raise_for_status = MagicMock(side_effect=Exception("HTTP 500"))
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    return resp


class TestDebateAuth:
    def test_missing_api_key_returns_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OMNIROUTE_API_KEY", raising=False)
        result = debate("BTC")
        assert result == {"error": "OMNIROUTE_API_KEY not configured"}


class TestDebateAnalysisFailure:
    def test_analyze_coin_exception_returns_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNIROUTE_API_KEY", "sk-test-key")
        with patch("cryptoscholar.tools.analyze.analyze_coin", side_effect=RuntimeError("no data")):
            result = debate("BTC")
        assert "error" in result
        assert "Failed to analyze BTC" in result["error"]


class TestDebateSuccess:
    def test_successful_debate_returns_parsed_fields(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNIROUTE_API_KEY", "sk-test-key")
        mock_resp = _mock_omniroute_response(_VALID_DEBATE_JSON)
        with patch("cryptoscholar.tools.analyze.analyze_coin", return_value=_MOCK_ANALYSIS), \
             patch("cryptoscholar.tools.debate.httpx.post", return_value=mock_resp) as mock_post:
            result = debate("BTC")

        assert result["symbol"] == "BTC"
        assert result["tss"] == 72
        assert result["regime"] == "trending_bull"
        assert "Momentum is strong" in result["bull_case"]
        assert "RSI is approaching" in result["bear_case"]
        assert "bullish" in result["bottom_line"]

        # Confirm it actually hit OmniRoute, not Anthropic directly
        call_args = mock_post.call_args
        assert call_args.args[0] == "http://localhost:20128/v1/chat/completions"
        assert call_args.kwargs["headers"]["Authorization"] == "Bearer sk-test-key"
        assert call_args.kwargs["json"]["model"] == "auto/smart"

    def test_custom_model_env_var_respected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNIROUTE_API_KEY", "sk-test-key")
        monkeypatch.setenv("CRYPTOSCHOLAR_MODEL", "auto/cheap")
        mock_resp = _mock_omniroute_response(_VALID_DEBATE_JSON)
        with patch("cryptoscholar.tools.analyze.analyze_coin", return_value=_MOCK_ANALYSIS), \
             patch("cryptoscholar.tools.debate.httpx.post", return_value=mock_resp) as mock_post:
            debate("BTC")
        assert mock_post.call_args.kwargs["json"]["model"] == "auto/cheap"

    def test_markdown_fenced_json_is_stripped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNIROUTE_API_KEY", "sk-test-key")
        fenced = f"```json\n{_VALID_DEBATE_JSON}\n```"
        mock_resp = _mock_omniroute_response(fenced)
        with patch("cryptoscholar.tools.analyze.analyze_coin", return_value=_MOCK_ANALYSIS), \
             patch("cryptoscholar.tools.debate.httpx.post", return_value=mock_resp):
            result = debate("BTC")
        assert "Momentum is strong" in result["bull_case"]


class TestDebateErrors:
    def test_invalid_json_returns_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNIROUTE_API_KEY", "sk-test-key")
        mock_resp = _mock_omniroute_response("not valid json at all")
        with patch("cryptoscholar.tools.analyze.analyze_coin", return_value=_MOCK_ANALYSIS), \
             patch("cryptoscholar.tools.debate.httpx.post", return_value=mock_resp):
            result = debate("BTC")
        assert "error" in result
        assert "invalid JSON" in result["error"]

    def test_http_failure_returns_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNIROUTE_API_KEY", "sk-test-key")
        mock_resp = _mock_omniroute_response(_VALID_DEBATE_JSON, status_ok=False)
        with patch("cryptoscholar.tools.analyze.analyze_coin", return_value=_MOCK_ANALYSIS), \
             patch("cryptoscholar.tools.debate.httpx.post", return_value=mock_resp):
            result = debate("BTC")
        assert "error" in result
        assert "Debate generation failed" in result["error"]

    def test_connection_error_returns_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OMNIROUTE_API_KEY", "sk-test-key")
        with patch("cryptoscholar.tools.analyze.analyze_coin", return_value=_MOCK_ANALYSIS), \
             patch("cryptoscholar.tools.debate.httpx.post", side_effect=ConnectionError("refused")):
            result = debate("BTC")
        assert "error" in result
        assert "Debate generation failed" in result["error"]
