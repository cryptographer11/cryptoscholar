"""Rule-based volatility regime classification (v1)."""

import logging

logger = logging.getLogger(__name__)

VRS_MAP: dict[str, int] = {
    "low_vol": 25,
    "mid_vol": 55,
    "high_vol": 80,
}


def classify_regime(indicators: dict) -> str:
    """
    Classify the current volatility regime.

    Uses ATR-14 and BB width relative to their 90-day range.

    Returns
    -------
    One of: 'low_vol', 'mid_vol', 'high_vol'
    """
    atr_series: list[float] = indicators.get("_atr_series", [])
    bbw_series: list[float] = indicators.get("_bbw_series", [])

    if len(atr_series) < 3 or len(bbw_series) < 3:
        return "mid_vol"

    atr_min = min(atr_series)
    atr_max = max(atr_series)
    atr_current = atr_series[-1]

    bbw_min = min(bbw_series)
    bbw_max = max(bbw_series)
    bbw_current = bbw_series[-1]

    atr_range = atr_max - atr_min
    bbw_range = bbw_max - bbw_min

    if atr_range == 0 or bbw_range == 0:
        return "mid_vol"

    atr_pct = (atr_current - atr_min) / atr_range  # 0=bottom, 1=top
    bbw_pct = (bbw_current - bbw_min) / bbw_range

    if atr_pct >= 0.70 and bbw_pct >= 0.70:
        return "high_vol"
    if atr_pct <= 0.30 and bbw_pct <= 0.30:
        return "low_vol"
    return "mid_vol"


def compute_vrs(regime: str) -> int:
    """Map regime label to Volatility Regime Score (0-100)."""
    return VRS_MAP.get(regime, 55)
