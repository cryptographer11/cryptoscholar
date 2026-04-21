"""GaussianHMM-based volatility regime classification."""

import json
import logging
import os
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_RETRAIN_DAYS = 7
_N_STATES = 3
_INFERENCE_WINDOW = 30
_MIN_TRAIN_SAMPLES = _N_STATES * 10


def _data_dir() -> Path:
    base = os.environ.get("CRYPTOSCHOLAR_DATA_DIR", str(Path.home() / ".cryptoscholar"))
    return Path(base)


def _model_path() -> Path:
    return _data_dir() / "hmm_model.pkl"


def _meta_path() -> Path:
    return _data_dir() / "hmm_model_meta.json"


def load_model() -> Optional[tuple]:
    """Return (model, state_map) or None if unavailable/corrupt."""
    path = _model_path()
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
        return data["model"], data["state_map"]
    except Exception as exc:
        logger.warning("Failed to load HMM model: %s", exc)
        return None


def _save_model(model, state_map: dict[int, str], n_samples: int) -> None:
    _data_dir().mkdir(parents=True, exist_ok=True)
    with open(_model_path(), "wb") as f:
        pickle.dump({"model": model, "state_map": state_map}, f)
    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": n_samples,
        "n_states": _N_STATES,
    }
    with open(_meta_path(), "w") as f:
        json.dump(meta, f)


def model_age_days() -> Optional[float]:
    """Return model age in days, or None if no model exists."""
    path = _meta_path()
    if not path.exists():
        return None
    try:
        with open(path) as f:
            meta = json.load(f)
        trained_at = datetime.fromisoformat(meta["trained_at"])
        return (datetime.now(timezone.utc) - trained_at).total_seconds() / 86400
    except Exception:
        return None


def _build_feature_matrix(
    hv_series: list[float],
    atr_pct_series: list[float],
    bbw_series: list[float],
) -> Optional[np.ndarray]:
    """Stack 3 feature series into (n_samples, 3), drop NaN/inf rows."""
    min_len = min(len(hv_series), len(atr_pct_series), len(bbw_series))
    if min_len < _MIN_TRAIN_SAMPLES:
        return None
    X = np.column_stack([
        hv_series[-min_len:],
        atr_pct_series[-min_len:],
        bbw_series[-min_len:],
    ]).astype(float)
    mask = np.isfinite(X).all(axis=1)
    X = X[mask]
    return X if len(X) >= _MIN_TRAIN_SAMPLES else None


def _state_map(model, X: np.ndarray) -> dict[int, str]:
    """Map HMM states → regime labels by ascending mean hv_20."""
    sorted_states = np.argsort(model.means_[:, 0])
    labels = ["low_vol", "mid_vol", "high_vol"]
    return {int(sorted_states[i]): labels[i] for i in range(_N_STATES)}


def train_hmm_model(
    hv_series: list[float],
    atr_pct_series: list[float],
    bbw_series: list[float],
) -> tuple:
    """
    Train GaussianHMM on feature sequences and persist to disk.

    Returns (model, state_map).
    Raises ValueError if data is insufficient.
    """
    from hmmlearn.hmm import GaussianHMM

    X = _build_feature_matrix(hv_series, atr_pct_series, bbw_series)
    if X is None:
        raise ValueError(
            f"Insufficient data to train HMM (need {_MIN_TRAIN_SAMPLES} clean samples)"
        )

    model = GaussianHMM(
        n_components=_N_STATES,
        covariance_type="full",
        n_iter=200,
        random_state=42,
        tol=1e-4,
    )
    model.fit(X)
    sm = _state_map(model, X)
    _save_model(model, sm, n_samples=len(X))
    logger.info("HMM model trained on %d samples, state_map=%s", len(X), sm)
    return model, sm


def classify_with_hmm(indicators: dict) -> Optional[str]:
    """
    Predict regime using the persisted HMM model.

    Uses the last _INFERENCE_WINDOW observations from indicators.
    Returns regime label or None if model unavailable or data insufficient.
    """
    result = load_model()
    if result is None:
        return None
    model, sm = result

    hv_series = indicators.get("_hv_series", [])
    atr_pct_series = indicators.get("_atr_pct_series", [])
    bbw_series = indicators.get("_bbw_series", [])

    X = _build_feature_matrix(hv_series, atr_pct_series, bbw_series)
    if X is None:
        return None

    X_inf = X[-_INFERENCE_WINDOW:]
    try:
        states = model.predict(X_inf)
        return sm.get(int(states[-1]), "mid_vol")
    except Exception as exc:
        logger.warning("HMM prediction failed: %s", exc)
        return None


def maybe_retrain(
    hv_series: list[float],
    atr_pct_series: list[float],
    bbw_series: list[float],
) -> bool:
    """Retrain if model is missing or older than _RETRAIN_DAYS. Returns True if retrained."""
    age = model_age_days()
    if age is not None and age < _RETRAIN_DAYS:
        return False
    try:
        train_hmm_model(hv_series, atr_pct_series, bbw_series)
        logger.info("HMM model retrained (previous age: %s days)", age)
        return True
    except Exception as exc:
        logger.warning("HMM retrain failed: %s", exc)
        return False


def get_model_info() -> dict:
    """Return model metadata dict for MCP tool output."""
    path = _meta_path()
    if not path.exists():
        return {"trained": False, "model_path": str(_model_path())}
    try:
        with open(path) as f:
            meta = json.load(f)
        age = model_age_days()
        return {
            "trained": True,
            "trained_at": meta.get("trained_at"),
            "age_days": round(age, 1) if age is not None else None,
            "n_samples": meta.get("n_samples"),
            "n_states": meta.get("n_states"),
            "model_path": str(_model_path()),
        }
    except Exception:
        return {"trained": False, "model_path": str(_model_path())}
