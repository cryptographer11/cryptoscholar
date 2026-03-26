"""Market context computation — ARS, MRS, macro signals.

ARS (Altcoin Rotation Score, 0-100):
  Measures how favourable the macro environment is for altcoin gains.
  Inputs: BTC dominance trend, ETH/BTC ratio trend, TOTAL3 market cap trend.

MRS (Market Readiness Score, 0-100):
  Composite readiness of the overall market for upside moves.
  = 40% BTC trend score + 30% ARS + 30% stablecoin supply score.
"""

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure scoring functions (fully testable, no I/O)
# ---------------------------------------------------------------------------


def compute_ars(
    btc_dom_30d_change_pct: Optional[float],
    eth_btc_20d_change_pct: Optional[float],
    total3_30d_change_pct: Optional[float],
) -> float:
    """
    Altcoin Rotation Score (0-100).

    Parameters
    ----------
    btc_dom_30d_change_pct  : % change in BTC dominance over 30 days.
                              Negative = capital rotating to alts (bullish for alts).
    eth_btc_20d_change_pct  : % change in ETH/BTC price ratio over 20 days.
                              Positive = ETH outperforming BTC (broadening rally).
    total3_30d_change_pct   : % change in TOTAL3 market cap over 30 days.
                              TOTAL3 = total crypto market cap minus BTC minus ETH.

    Returns
    -------
    Float score 0-100. 50 = neutral.
    """
    score = 50.0

    # BTC dominance direction — falling = alts gaining
    if btc_dom_30d_change_pct is not None:
        if btc_dom_30d_change_pct < -5:
            score += 20
        elif btc_dom_30d_change_pct < -1:
            score += 10
        elif btc_dom_30d_change_pct > 5:
            score -= 20
        elif btc_dom_30d_change_pct > 1:
            score -= 10

    # ETH/BTC trend — rising = broader rally signal
    if eth_btc_20d_change_pct is not None:
        if eth_btc_20d_change_pct > 5:
            score += 15
        elif eth_btc_20d_change_pct > 0:
            score += 8
        elif eth_btc_20d_change_pct < -5:
            score -= 15
        else:
            score -= 8

    # TOTAL3 (altcoin market cap) momentum
    if total3_30d_change_pct is not None:
        if total3_30d_change_pct > 10:
            score += 15
        elif total3_30d_change_pct > 0:
            score += 8
        elif total3_30d_change_pct < -10:
            score -= 15
        else:
            score -= 8

    return round(min(max(score, 0.0), 100.0), 1)


def compute_btc_trend_score(btc_price_30d_change_pct: Optional[float]) -> float:
    """
    BTC macro trend score (0-100) based on 30-day price change.

    50 = flat, 100 = strongly up, 0 = strongly down.
    """
    if btc_price_30d_change_pct is None:
        return 50.0
    p = btc_price_30d_change_pct
    if p > 30:
        return 90.0
    if p > 15:
        return 75.0
    if p > 5:
        return 62.0
    if p > -5:
        return 50.0
    if p > -15:
        return 35.0
    if p > -30:
        return 22.0
    return 10.0


def compute_stablecoin_score(stablecoin_30d_change_pct: Optional[float]) -> float:
    """
    Stablecoin supply trend score (0-100).

    Rising stablecoin supply = more capital on sidelines, ready to deploy.
    50 = neutral / data unavailable.
    """
    if stablecoin_30d_change_pct is None:
        return 50.0
    p = stablecoin_30d_change_pct
    if p > 10:
        return 80.0
    if p > 5:
        return 70.0
    if p > 1:
        return 60.0
    if p > -1:
        return 50.0
    if p > -5:
        return 38.0
    return 25.0


def compute_mrs(
    btc_trend_score: float,
    ars: float,
    stablecoin_score: float,
) -> float:
    """
    Market Readiness Score (0-100).

    Weights: 40% BTC trend + 30% ARS + 30% stablecoin supply.
    """
    return round(0.4 * btc_trend_score + 0.3 * ars + 0.3 * stablecoin_score, 1)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def _pct_change(series_values: list[float]) -> Optional[float]:
    """Percentage change from first to last value. Returns None if < 2 values."""
    if len(series_values) < 2 or series_values[0] == 0:
        return None
    return (series_values[-1] - series_values[0]) / series_values[0] * 100


def _align_and_pct_change(
    a_pairs: list[list],
    b_pairs: list[list],
    lookback: int,
) -> Optional[float]:
    """
    Given two [[ts_ms, value], ...] series, align by date and compute
    % change of (a / b) ratio over the last `lookback` bars.
    Returns None if insufficient data.
    """
    if not a_pairs or not b_pairs:
        return None

    a_series = pd.Series(
        {pd.Timestamp(p[0], unit="ms", tz="UTC").date(): p[1] for p in a_pairs}
    )
    b_series = pd.Series(
        {pd.Timestamp(p[0], unit="ms", tz="UTC").date(): p[1] for p in b_pairs}
    )

    common = a_series.index.intersection(b_series.index)
    if len(common) < 2:
        return None

    a_aligned = a_series[common]
    b_aligned = b_series[common]
    ratio = a_aligned / b_aligned.replace(0, float("nan"))

    tail = ratio.dropna().tail(lookback)
    if len(tail) < 2:
        return None
    return round((float(tail.iloc[-1]) - float(tail.iloc[0])) / float(tail.iloc[0]) * 100, 2)


# ---------------------------------------------------------------------------
# Main fetch function
# ---------------------------------------------------------------------------


def fetch_market_context() -> dict:
    """
    Fetch and compute all market context signals.

    Makes 3 CoinGecko calls (rate-limited) + 1 DefiLlama call.
    Results are cached for 5 minutes by each underlying client.

    Returns
    -------
    Dict with keys:
        btc_price_30d_change_pct, btc_dominance_current, btc_dominance_30d_change_pct,
        eth_btc_20d_change_pct, total3_30d_change_pct,
        stablecoin_supply_usd, stablecoin_30d_change_pct,
        btc_trend_score, ars, stablecoin_score, mrs
    """
    from cryptoscholar.data.coingecko import (
        fetch_global,
        fetch_global_market_chart,
        fetch_market_chart,
    )
    from cryptoscholar.data.defillama import extract_total_mcap_usd, fetch_stablecoin_chart

    result: dict = {}

    # --- CoinGecko: current global data ---
    try:
        global_data = fetch_global()
        result["btc_dominance_current"] = round(
            float(global_data.get("market_cap_percentage", {}).get("btc", 0)), 2
        )
    except Exception as exc:
        logger.warning("fetch_global failed: %s", exc)
        result["btc_dominance_current"] = None

    # --- CoinGecko: historical total market cap (30d) ---
    total_mcap_pairs: list[list] = []
    try:
        global_chart = fetch_global_market_chart(days=30)
        total_mcap_pairs = global_chart.get("market_cap", [])
    except Exception as exc:
        logger.warning("fetch_global_market_chart failed: %s", exc)

    # --- CoinGecko: BTC historical (30d) — prices + market caps ---
    btc_price_pairs: list[list] = []
    btc_mcap_pairs: list[list] = []
    try:
        btc_chart = fetch_market_chart("bitcoin", days=30)
        btc_price_pairs = btc_chart.get("prices", [])
        btc_mcap_pairs = btc_chart.get("market_caps", [])
    except Exception as exc:
        logger.warning("fetch_market_chart(bitcoin) failed: %s", exc)

    # --- CoinGecko: ETH historical (30d) — prices + market caps ---
    eth_price_pairs: list[list] = []
    eth_mcap_pairs: list[list] = []
    try:
        eth_chart = fetch_market_chart("ethereum", days=30)
        eth_price_pairs = eth_chart.get("prices", [])
        eth_mcap_pairs = eth_chart.get("market_caps", [])
    except Exception as exc:
        logger.warning("fetch_market_chart(ethereum) failed: %s", exc)

    # --- DefiLlama: stablecoin supply history ---
    stablecoin_history = fetch_stablecoin_chart(days=31)

    # --- Compute BTC 30d price change ---
    btc_prices = [p[1] for p in btc_price_pairs]
    result["btc_price_30d_change_pct"] = (
        round(_pct_change(btc_prices), 2) if btc_prices else None
    )

    # --- Compute BTC dominance 30d change ---
    if total_mcap_pairs and btc_mcap_pairs:
        btc_dom_series: list[float] = []
        total_by_date: dict = {
            pd.Timestamp(p[0], unit="ms", tz="UTC").date(): p[1]
            for p in total_mcap_pairs
        }
        for p in btc_mcap_pairs:
            date = pd.Timestamp(p[0], unit="ms", tz="UTC").date()
            total = total_by_date.get(date)
            if total and total > 0:
                btc_dom_series.append(p[1] / total * 100)
        result["btc_dominance_30d_change_pct"] = (
            round(_pct_change(btc_dom_series), 2) if btc_dom_series else None
        )
    else:
        result["btc_dominance_30d_change_pct"] = None

    # --- ETH/BTC price ratio 20d change ---
    result["eth_btc_20d_change_pct"] = _align_and_pct_change(
        eth_price_pairs, btc_price_pairs, lookback=20
    )

    # --- TOTAL3: total - BTC mcap - ETH mcap (30d % change) ---
    if total_mcap_pairs and btc_mcap_pairs and eth_mcap_pairs:
        total_by_date = {
            pd.Timestamp(p[0], unit="ms", tz="UTC").date(): p[1]
            for p in total_mcap_pairs
        }
        btc_by_date: dict = {
            pd.Timestamp(p[0], unit="ms", tz="UTC").date(): p[1]
            for p in btc_mcap_pairs
        }
        eth_by_date: dict = {
            pd.Timestamp(p[0], unit="ms", tz="UTC").date(): p[1]
            for p in eth_mcap_pairs
        }
        common_dates = sorted(
            set(total_by_date) & set(btc_by_date) & set(eth_by_date)
        )
        total3_vals = [
            total_by_date[d] - btc_by_date[d] - eth_by_date[d]
            for d in common_dates
            if total_by_date[d] - btc_by_date[d] - eth_by_date[d] > 0
        ]
        result["total3_30d_change_pct"] = (
            round(_pct_change(total3_vals), 2) if len(total3_vals) >= 2 else None
        )
    else:
        result["total3_30d_change_pct"] = None

    # --- Stablecoin supply trend ---
    if stablecoin_history:
        supply_vals = [
            v
            for entry in stablecoin_history
            if (v := extract_total_mcap_usd(entry)) is not None
        ]
        result["stablecoin_supply_usd"] = int(supply_vals[-1]) if supply_vals else None
        result["stablecoin_30d_change_pct"] = (
            round(_pct_change(supply_vals), 2) if len(supply_vals) >= 2 else None
        )
    else:
        result["stablecoin_supply_usd"] = None
        result["stablecoin_30d_change_pct"] = None

    # --- Composite scores ---
    btc_trend_score = compute_btc_trend_score(result.get("btc_price_30d_change_pct"))
    ars = compute_ars(
        result.get("btc_dominance_30d_change_pct"),
        result.get("eth_btc_20d_change_pct"),
        result.get("total3_30d_change_pct"),
    )
    stablecoin_score = compute_stablecoin_score(result.get("stablecoin_30d_change_pct"))
    mrs = compute_mrs(btc_trend_score, ars, stablecoin_score)

    result["btc_trend_score"] = btc_trend_score
    result["ars"] = ars
    result["stablecoin_score"] = stablecoin_score
    result["mrs"] = mrs

    return result
