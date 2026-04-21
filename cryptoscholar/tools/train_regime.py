"""train_regime_model tool — manually trigger HMM retrain on BTC data."""

import logging

logger = logging.getLogger(__name__)


def train_regime_model(force: bool = False) -> dict:
    """
    Train (or retrain) the HMM volatility regime model on BTC price history.

    Uses 300 days of BTC OHLCV to derive hv_20, atr_pct, and bb_width feature
    sequences. The trained model is persisted and used by analyze_coin /
    rank_coins for regime classification.

    Parameters
    ----------
    force : bool
        If True, retrain even if the model is fresh (< 7 days old).

    Returns
    -------
    Dict with status, model info, and training outcome.
    """
    from cryptoscholar.ta.hmm_regime import (
        get_model_info,
        model_age_days,
        train_hmm_model,
    )
    from cryptoscholar.ta.indicators import compute_indicators
    from cryptoscholar.tools.analyze import _fetch_ohlcv_with_fallback

    age = model_age_days()
    if not force and age is not None and age < 7:
        return {
            "status": "skipped",
            "reason": f"Model is only {age:.1f} days old (threshold: 7 days). Use force=True to retrain.",
            "model_info": get_model_info(),
        }

    try:
        df, source = _fetch_ohlcv_with_fallback("BTC", days=300)
    except Exception as exc:
        return {
            "status": "error",
            "reason": f"Failed to fetch BTC training data: {exc}",
            "model_info": get_model_info(),
        }

    indicators = compute_indicators(df)

    hv_series = indicators.get("_hv_series", [])
    atr_pct_series = indicators.get("_atr_pct_series", [])
    bbw_series = indicators.get("_bbw_series", [])

    try:
        train_hmm_model(hv_series, atr_pct_series, bbw_series)
    except ValueError as exc:
        return {
            "status": "error",
            "reason": str(exc),
            "model_info": get_model_info(),
        }

    info = get_model_info()
    return {
        "status": "trained",
        "data_source": source,
        "training_samples": info.get("n_samples"),
        "model_info": info,
    }
