"""generate_report tool — 3-stage analysis report generation."""

import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import anthropic

from cryptoscholar.tools.analyze import analyze_coin

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"

_SINGLE_COIN_SYSTEM = """\
You are a professional crypto market analyst. Given clustered technical analysis signals for a cryptocurrency, write a structured analysis report.

Respond ONLY with valid JSON in this exact format:
{
  "trend": "2-3 sentences on trend direction, EMA alignment, MTF confirmation",
  "momentum": "2-3 sentences on RSI, MACD, ADX momentum signals",
  "volume_onchain": "2-3 sentences on OBV trend, funding rate, volume context",
  "risks": "2-3 sentences on key risks, bearish signals, or caution flags",
  "summary": "1-2 sentence overall setup summary"
}"""

_MULTI_COIN_SYSTEM = """\
You are a professional crypto market analyst. Given technical analysis data for multiple cryptocurrencies, write a comparative analysis.

Respond ONLY with valid JSON in this exact format:
{
  "comparison_table_notes": "2-3 sentences highlighting key differences across coins",
  "strongest_setup": "symbol and 1-sentence reason why it has the best setup",
  "weakest_setup": "symbol and 1-sentence reason why it has the worst setup",
  "summary": "2-3 sentence overall comparative summary"
}"""


def _fmt(val: Optional[float], decimals: int = 2) -> str:
    if val is None:
        return "N/A"
    return f"{val:.{decimals}f}"


def _cluster_signals(analysis: dict) -> dict:
    """Stage 1: Group TA signals into thematic clusters."""
    ind = analysis.get("indicators", {})
    return {
        "trend": {
            "ema_alignment": analysis.get("ema_alignment", "N/A"),
            "mtf_alignment_4h": analysis.get("mtf_alignment_4h", "unavailable"),
            "weekly_ema_slope": _fmt(ind.get("weekly_ema_slope")),
            "ema_20": _fmt(ind.get("ema_20")),
            "ema_50": _fmt(ind.get("ema_50")),
            "ema_200": _fmt(ind.get("ema_200")),
            "price": _fmt(analysis.get("price")),
        },
        "momentum": {
            "rsi_14": _fmt(ind.get("rsi_14")),
            "rsi_divergence": ind.get("rsi_divergence", "none"),
            "macd_hist": _fmt(ind.get("macd_hist")),
            "adx_14": _fmt(ind.get("adx_14")),
        },
        "volume_onchain": {
            "obv_trend": analysis.get("obv_trend", "N/A"),
            "funding_rate": _fmt(ind.get("funding_rate"), 4),
        },
        "volatility_regime": {
            "regime": analysis.get("regime", "N/A"),
            "regime_source": analysis.get("regime_source", "rule_based"),
            "hv_20": _fmt(ind.get("hv_20")),
            "atr_14": _fmt(ind.get("atr_14")),
            "bb_width": _fmt(ind.get("bb_width")),
        },
        "relative_strength": {
            "rs_btc": _fmt(ind.get("rs_btc")),
            "price_change_24h_pct": _fmt(analysis.get("price_change_24h_pct")),
            "tss": analysis.get("tss"),
        },
    }


def _format_clusters_for_prompt(symbol: str, clusters: dict) -> str:
    """Format clustered signals as readable text for the Claude prompt."""
    lines = [f"Symbol: {symbol}", ""]
    for group, signals in clusters.items():
        lines.append(f"[{group.upper()}]")
        for k, v in signals.items():
            lines.append(f"  {k}: {v}")
        lines.append("")
    return "\n".join(lines)


def _format_multi_coin_prompt(analyses: list[dict]) -> str:
    """Format multiple coin analyses for the comparison prompt."""
    lines = []
    for a in analyses:
        sym = a.get("symbol", "?")
        ind = a.get("indicators", {})
        rsi = ind.get("rsi_14")
        rsi_str = f"{rsi:.1f}" if isinstance(rsi, float) else "N/A"
        lines.append(
            f"{sym}: TSS={a.get('tss', 'N/A')} | regime={a.get('regime', 'N/A')} | "
            f"EMA={a.get('ema_alignment', 'N/A')} | RSI={rsi_str} | "
            f"OBV={a.get('obv_trend', 'N/A')} | MTF={a.get('mtf_alignment_4h', 'N/A')}"
        )
    return "\n".join(lines)


def _build_stats_table(analyses: list[dict]) -> list[dict]:
    """Build key stats table rows."""
    rows = []
    for a in analyses:
        ind = a.get("indicators", {})
        rows.append({
            "symbol": a.get("symbol", "?"),
            "price": a.get("price"),
            "tss": a.get("tss"),
            "regime": a.get("regime"),
            "ema_alignment": a.get("ema_alignment"),
            "rsi_14": _fmt(ind.get("rsi_14")),
            "adx_14": _fmt(ind.get("adx_14")),
            "obv_trend": a.get("obv_trend"),
            "mtf_alignment_4h": a.get("mtf_alignment_4h"),
            "rs_btc": _fmt(ind.get("rs_btc")),
            "data_source": a.get("data_source"),
        })
    return rows


def _assemble_markdown(
    symbols: list[str],
    stats_table: list[dict],
    sections: dict[str, dict],
    comparison: Optional[dict] = None,
) -> str:
    """Stage 3: Assemble final markdown report."""
    lines = ["# CryptoScholar Analysis Report", ""]

    lines.append("## Key Statistics")
    lines.append("")
    lines.append("| Symbol | Price | TSS | Regime | EMA | RSI | ADX | OBV | MTF 4H | RS BTC |")
    lines.append("|--------|-------|-----|--------|-----|-----|-----|-----|--------|--------|")
    for row in stats_table:
        lines.append(
            f"| {row['symbol']} | {row['price'] or 'N/A'} | {row['tss'] or 'N/A'} | "
            f"{row['regime'] or 'N/A'} | {row['ema_alignment'] or 'N/A'} | "
            f"{row['rsi_14']} | {row['adx_14']} | {row['obv_trend'] or 'N/A'} | "
            f"{row['mtf_alignment_4h'] or 'N/A'} | {row['rs_btc']} |"
        )
    lines.append("")

    if len(symbols) == 1:
        sym = symbols[0]
        s = sections.get(sym, {})
        for section_key, heading in [
            ("trend", "Trend"),
            ("momentum", "Momentum"),
            ("volume_onchain", "Volume & On-Chain"),
            ("risks", "Risks"),
            ("summary", "Summary"),
        ]:
            lines.append(f"## {sym} — {heading}")
            lines.append(s.get(section_key, ""))
            lines.append("")
    else:
        for sym in symbols:
            s = sections.get(sym, {})
            lines.append(f"## {sym}")
            lines.append(s.get("summary", ""))
            lines.append("")

        if comparison:
            lines.append("## Comparative Analysis")
            lines.append(comparison.get("comparison_table_notes", ""))
            lines.append("")
            lines.append(f"**Strongest setup:** {comparison.get('strongest_setup', 'N/A')}")
            lines.append(f"**Weakest setup:** {comparison.get('weakest_setup', 'N/A')}")
            lines.append("")
            lines.append("## Overall Summary")
            lines.append(comparison.get("summary", ""))

    return "\n".join(lines)


def generate_report(symbols: list[str], output_format: str = "markdown") -> dict:
    """
    Generate a structured analysis report for one or more cryptocurrencies.

    3-stage pipeline: Cluster → Write → Assemble.
      Stage 1: cluster TA signals into thematic groups (trend, momentum, volume, etc.)
      Stage 2: use Claude to write narrative sections per group
      Stage 3: assemble into a formatted markdown report with key stats table

    Parameters
    ----------
    symbols      : list of ticker symbols e.g. ["BTC"] or ["BTC", "ETH", "SOL"]
    output_format: "markdown" (default) or "json"

    Returns dict with "report", "stats_table", "symbols", and optional "errors".
    On fatal error returns dict with "error" key.
    """
    if not symbols:
        return {"error": "At least one symbol required"}
    if len(symbols) > 10:
        return {"error": "Maximum 10 symbols for report generation"}

    symbols = [s.upper().strip() for s in symbols]

    api_key: Optional[str] = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not configured"}

    model = os.environ.get("CRYPTOSCHOLAR_MODEL", _DEFAULT_MODEL)

    # Fetch analyses in parallel
    errors: list[str] = []
    results_map: dict[str, dict] = {}

    def _fetch(sym: str) -> tuple[str, dict]:
        return sym, analyze_coin(sym)

    with ThreadPoolExecutor(max_workers=min(len(symbols), 8)) as executor:
        futures = {executor.submit(_fetch, sym): sym for sym in symbols}
        for future in as_completed(futures):
            sym = futures[future]
            try:
                _, result = future.result()
                results_map[sym] = result
            except Exception as exc:
                errors.append(f"{sym}: {exc}")
                logger.warning("Failed to analyze %s for report: %s", sym, exc)

    analyses = [results_map[sym] for sym in symbols if sym in results_map]

    if not analyses:
        return {"error": f"All symbols failed: {'; '.join(errors)}"}

    successful_symbols = [a["symbol"] for a in analyses]

    # Stage 1: Cluster signals
    clusters_map = {a["symbol"]: _cluster_signals(a) for a in analyses}

    # Stage 2: Write sections via Claude
    client = anthropic.Anthropic(api_key=api_key)
    sections: dict[str, dict] = {}

    for analysis in analyses:
        sym = analysis["symbol"]
        prompt_text = _format_clusters_for_prompt(sym, clusters_map[sym])
        try:
            response = client.messages.create(
                model=model,
                max_tokens=600,
                system=_SINGLE_COIN_SYSTEM,
                messages=[{"role": "user", "content": prompt_text}],
            )
            sections[sym] = json.loads(response.content[0].text.strip())
        except json.JSONDecodeError as exc:
            logger.error("Claude returned invalid JSON for report on %s: %s", sym, exc)
            sections[sym] = {
                "trend": "", "momentum": "", "volume_onchain": "",
                "risks": "", "summary": "Analysis unavailable (JSON parse error)",
            }
        except Exception as exc:
            logger.error("Claude call failed for report on %s: %s", sym, exc)
            sections[sym] = {
                "trend": "", "momentum": "", "volume_onchain": "",
                "risks": "", "summary": f"Analysis unavailable: {exc}",
            }

    # Multi-coin comparison (Stage 2b)
    comparison: Optional[dict] = None
    if len(analyses) > 1:
        multi_prompt = _format_multi_coin_prompt(analyses)
        try:
            response = client.messages.create(
                model=model,
                max_tokens=400,
                system=_MULTI_COIN_SYSTEM,
                messages=[{"role": "user", "content": multi_prompt}],
            )
            comparison = json.loads(response.content[0].text.strip())
        except Exception as exc:
            logger.warning("Multi-coin comparison failed: %s", exc)
            comparison = {
                "comparison_table_notes": "",
                "strongest_setup": "N/A",
                "weakest_setup": "N/A",
                "summary": "",
            }

    # Stage 3: Assemble
    stats_table = _build_stats_table(analyses)

    if output_format == "json":
        report_data: dict = {
            "symbols": successful_symbols,
            "stats_table": stats_table,
            "sections": sections,
        }
        if comparison:
            report_data["comparison"] = comparison
        return {
            "report": report_data,
            "stats_table": stats_table,
            "format": "json",
            "symbols": successful_symbols,
            "errors": errors or None,
        }

    markdown = _assemble_markdown(successful_symbols, stats_table, sections, comparison)
    return {
        "report": markdown,
        "stats_table": stats_table,
        "format": "markdown",
        "symbols": successful_symbols,
        "errors": errors or None,
    }
