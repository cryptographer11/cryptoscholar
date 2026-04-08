"""TSS (Trend Strength Score) computation."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def compute_4h_alignment_bonus(ind_4h: dict) -> float:
    """
    Return MTF alignment bonus based on 4H EMA-20 vs EMA-50.

    +3 if 4H EMA-20 > EMA-50 (bullish alignment)
    -3 if 4H EMA-20 < EMA-50 (bearish alignment)
     0 if data unavailable
    """
    ema20 = ind_4h.get("ema_20_4h")
    ema50 = ind_4h.get("ema_50_4h")
    if ema20 is None or ema50 is None:
        return 0.0
    if ema20 > ema50:
        return 3.0
    if ema20 < ema50:
        return -3.0
    return 0.0


def score_trend_component(ind: dict) -> float:
    """EMA alignment score 0-100."""
    score = 0.0
    ema20: Optional[float] = ind.get("ema_20")
    ema50: Optional[float] = ind.get("ema_50")
    ema200: Optional[float] = ind.get("ema_200")
    if all(v is not None for v in (ema20, ema50, ema200)):
        if ema20 > ema50:  # type: ignore[operator]
            score += 30
        if ema50 > ema200:  # type: ignore[operator]
            score += 30
        if ema20 > ema200:  # type: ignore[operator]
            score += 20
    slope: Optional[float] = ind.get("weekly_ema_slope")
    if slope is not None:
        if slope > 3:
            score += 20
        elif slope > 0:
            score += 10
        elif slope < -3:
            score -= 10
    return min(max(score, 0.0), 100.0)


def score_momentum_component(ind: dict) -> float:
    """RSI + MACD + ADX momentum score 0-100."""
    score = 50.0
    rsi: Optional[float] = ind.get("rsi_14")
    macd_line: Optional[float] = ind.get("macd_line")
    macd_signal: Optional[float] = ind.get("macd_signal")
    adx: Optional[float] = ind.get("adx_14")

    if rsi is not None:
        if 50 < rsi < 70:
            score += 25
        elif rsi >= 70:
            score += 10
        elif 40 <= rsi <= 50:
            score -= 10
        elif rsi < 40:
            score -= 25

    if macd_line is not None and macd_signal is not None:
        if macd_line > macd_signal:
            score += 15
        else:
            score -= 15

    if adx is not None:
        if adx > 25:
            score += 10
        elif adx < 20:
            score -= 10

    return min(max(score, 0.0), 100.0)


def compute_obv_bonus(ind: dict) -> float:
    """
    OBV volume confirmation bonus for TSS.

    +2 if OBV trend is rising  (volume confirms the move)
    -2 if OBV trend is falling (volume diverges — weakness signal)
     0 if flat or data unavailable
    """
    obv_trend = ind.get("obv_trend")
    if obv_trend == "rising":
        return 2.0
    if obv_trend == "falling":
        return -2.0
    return 0.0


def compute_tss(ind: dict, ind_4h: Optional[dict] = None) -> float:
    """
    Trend Strength Score: 40% trend + 30% momentum + 30% RS.

    RS vs BTC is normalised to 0-100 scale.
    Optional ind_4h applies a ±3 MTF alignment bonus from 4H EMA alignment.
    """
    trend = score_trend_component(ind)
    momentum = score_momentum_component(ind)
    rs: Optional[float] = ind.get("rs_btc")
    rs_raw = rs if rs is not None else 0.0
    rs_score = min(max(50.0 + rs_raw * 2, 0.0), 100.0)
    base = 0.4 * trend + 0.3 * momentum + 0.3 * rs_score
    mtf_bonus = compute_4h_alignment_bonus(ind_4h) if ind_4h is not None else 0.0
    obv_bonus = compute_obv_bonus(ind)
    return round(min(max(base + mtf_bonus + obv_bonus, 0.0), 100.0), 1)
