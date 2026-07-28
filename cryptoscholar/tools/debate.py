"""debate tool — LLM bull/bear synthesis for a cryptocurrency, via OmniRoute."""

import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "auto/smart"
_OMNIROUTE_URL = "http://localhost:20128/v1/chat/completions"

_SYSTEM_PROMPT = """\
You are a professional crypto market analyst. Given technical analysis data for a cryptocurrency, generate a concise structured bull/bear debate.

Respond ONLY with valid JSON in this exact format:
{
  "bull_case": "2-3 sentence bullish argument based on the TA data",
  "bear_case": "2-3 sentence bearish argument based on the TA data",
  "bottom_line": "1 sentence synthesis — what the TA suggests overall"
}"""


def _format_ta_message(analysis: dict) -> str:
    """Format TA analysis dict as a human-readable string for the prompt."""
    ind = analysis.get("indicators", {})
    ema20 = ind.get("ema_20")
    ema50 = ind.get("ema_50")
    ema200 = ind.get("ema_200")
    lines = [
        f"Symbol: {analysis.get('symbol')}",
        f"Price: ${analysis.get('price', 'N/A')}",
        f"24h Change: {analysis.get('price_change_24h_pct', 'N/A')}%",
        f"TSS (Trend Strength Score): {analysis.get('tss')}",
        f"Regime: {analysis.get('regime')} (VRS: {analysis.get('vrs')})",
        f"EMA Alignment: {analysis.get('ema_alignment')}",
        f"  EMA-20: {_fmt(ema20)}  EMA-50: {_fmt(ema50)}  EMA-200: {_fmt(ema200)}",
        f"RSI-14: {_fmt(ind.get('rsi_14'))}",
        f"MACD Line: {_fmt(ind.get('macd_line'))}  Signal: {_fmt(ind.get('macd_signal'))}  Hist: {_fmt(ind.get('macd_hist'))}",
        f"ADX-14: {_fmt(ind.get('adx_14'))}",
        f"ATR-14: {_fmt(ind.get('atr_14'))}",
        f"BB Width: {_fmt(ind.get('bb_width'))}",
        f"HV-20: {_fmt(ind.get('hv_20'))}%",
        f"RS vs BTC (20d): {_fmt(ind.get('rs_btc'))}%",
        f"Weekly EMA Slope: {_fmt(ind.get('weekly_ema_slope'))}%",
        f"4H MTF Alignment: {analysis.get('mtf_alignment_4h', 'unavailable')}",
        f"RSI Divergence: {ind.get('rsi_divergence', 'none')}",
    ]
    return "\n".join(lines)


def _fmt(val: Optional[float], decimals: int = 2) -> str:
    if val is None:
        return "N/A"
    return f"{val:.{decimals}f}"


def debate(symbol: str) -> dict:
    """
    Generate an LLM bull/bear debate for a cryptocurrency, routed through OmniRoute.

    Parameters
    ----------
    symbol:
        Ticker symbol e.g. "BTC", "SOL".

    Returns
    -------
    Dict with keys: symbol, bull_case, bear_case, bottom_line, tss, regime.
    On error returns dict with "error" key.
    """
    api_key: Optional[str] = os.environ.get("OMNIROUTE_API_KEY")
    if not api_key:
        return {"error": "OMNIROUTE_API_KEY not configured"}

    model = os.environ.get("CRYPTOSCHOLAR_MODEL", _DEFAULT_MODEL)

    from cryptoscholar.tools.analyze import analyze_coin

    try:
        analysis = analyze_coin(symbol)
    except Exception as exc:
        return {"error": f"Failed to analyze {symbol}: {exc}"}

    user_message = _format_ta_message(analysis)

    try:
        response = httpx.post(
            _OMNIROUTE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                # Some auto-routed models spend a large share of the budget on hidden
                # reasoning before emitting the actual JSON — 512 wasn't enough in
                # live testing (finish_reason="length" with the JSON truncated mid-string).
                "max_tokens": 2048,
                "stream": False,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            },
            timeout=30.0,
        )
        response.raise_for_status()
        raw_text = response.json()["choices"][0]["message"]["content"].strip()

        # Some models wrap JSON in a markdown code fence despite instructions — strip it
        if raw_text.startswith("```"):
            raw_text = raw_text.strip("`")
            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()

        debate_result = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("OmniRoute returned invalid JSON for debate on %s: %s", symbol, exc)
        return {"error": f"OmniRoute returned invalid JSON: {exc}"}
    except Exception as exc:
        logger.error("Debate generation failed for %s: %s", symbol, exc)
        return {"error": f"Debate generation failed: {exc}"}

    return {
        "symbol": analysis["symbol"],
        "tss": analysis["tss"],
        "regime": analysis["regime"],
        "bull_case": debate_result.get("bull_case", ""),
        "bear_case": debate_result.get("bear_case", ""),
        "bottom_line": debate_result.get("bottom_line", ""),
    }
