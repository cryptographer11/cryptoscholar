"""Volatility regime classification — HMM-first, rule-based fallback."""

import logging

logger = logging.getLogger(__name__)

VRS_MAP: dict[str, int] = {
    "low_vol": 25,
    "mid_vol": 55,
    "high_vol": 80,
}


def _rule_based(indicators: dict) -> str:
    """Original ATR + BBW percentile rule-based classifier."""
    atr_series: list[float] = indicators.get("_atr_series", [])
    bbw_series: list[float] = indicators.get("_bbw_series", [])

    if len(atr_series) < 3 or len(bbw_series) < 3:
        return "mid_vol"

    atr_range = max(atr_series) - min(atr_series)
    bbw_range = max(bbw_series) - min(bbw_series)

    if atr_range == 0 or bbw_range == 0:
        return "mid_vol"

    atr_pct = (atr_series[-1] - min(atr_series)) / atr_range
    bbw_pct = (bbw_series[-1] - min(bbw_series)) / bbw_range

    if atr_pct >= 0.70 and bbw_pct >= 0.70:
        return "high_vol"
    if atr_pct <= 0.30 and bbw_pct <= 0.30:
        return "low_vol"
    return "mid_vol"


def classify_regime_full(indicators: dict) -> tuple[str, str]:
    """
    Classify volatility regime, returning (label, source).

    Tries HMM model first; falls back to rule-based if unavailable.
    Also triggers auto-retrain when model is missing or stale.

    Returns
    -------
    (regime, source) where regime is 'low_vol'/'mid_vol'/'high_vol'
    and source is 'hmm' or 'rule_based'.
    """
    try:
        from cryptoscholar.ta.hmm_regime import classify_with_hmm, maybe_retrain

        hv_series = indicators.get("_hv_series", [])
        atr_pct_series = indicators.get("_atr_pct_series", [])
        bbw_series = indicators.get("_bbw_series", [])

        maybe_retrain(hv_series, atr_pct_series, bbw_series)

        regime = classify_with_hmm(indicators)
        if regime is not None:
            return regime, "hmm"
    except Exception as exc:
        logger.warning("HMM classification error: %s", exc)

    return _rule_based(indicators), "rule_based"


def classify_regime(indicators: dict) -> str:
    """Classify volatility regime. Returns 'low_vol', 'mid_vol', or 'high_vol'."""
    regime, _ = classify_regime_full(indicators)
    return regime


def compute_vrs(regime: str) -> int:
    """Map regime label to Volatility Regime Score (0-100)."""
    return VRS_MAP.get(regime, 55)
