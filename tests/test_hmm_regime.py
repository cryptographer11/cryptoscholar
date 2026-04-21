"""Tests for HMM volatility regime classification (v0.6.0)."""

import json
import pickle
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from cryptoscholar.ta.hmm_regime import (
    _build_feature_matrix,
    _data_dir,
    _meta_path,
    _model_path,
    classify_with_hmm,
    get_model_info,
    load_model,
    maybe_retrain,
    model_age_days,
    train_hmm_model,
)
from cryptoscholar.ta.regime import classify_regime, classify_regime_full, compute_vrs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_series(n: int = 100, seed: int = 42) -> list[float]:
    rng = np.random.default_rng(seed)
    return rng.uniform(5.0, 50.0, size=n).tolist()


def _make_indicators(n: int = 100) -> dict:
    rng = np.random.default_rng(0)
    hv = rng.uniform(10, 80, n).tolist()
    atr_pct = rng.uniform(0.5, 5.0, n).tolist()
    bbw = rng.uniform(5, 40, n).tolist()
    # rule-based series
    atr_abs = rng.uniform(100, 5000, n).tolist()
    return {
        "_hv_series": hv,
        "_atr_pct_series": atr_pct,
        "_bbw_series": bbw,
        "_atr_series": atr_abs,
    }


@pytest.fixture()
def tmp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CRYPTOSCHOLAR_DATA_DIR", str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# _build_feature_matrix
# ---------------------------------------------------------------------------

def test_build_feature_matrix_happy():
    hv = _make_series(100)
    atr = _make_series(100, seed=1)
    bbw = _make_series(100, seed=2)
    X = _build_feature_matrix(hv, atr, bbw)
    assert X is not None
    assert X.shape[1] == 3
    assert X.shape[0] <= 100


def test_build_feature_matrix_too_short():
    hv = [1.0] * 5
    atr = [1.0] * 5
    bbw = [1.0] * 5
    assert _build_feature_matrix(hv, atr, bbw) is None


def test_build_feature_matrix_drops_nan():
    hv = [float("nan")] * 10 + _make_series(90)
    atr = _make_series(100, seed=1)
    bbw = _make_series(100, seed=2)
    X = _build_feature_matrix(hv, atr, bbw)
    assert X is not None
    assert np.isfinite(X).all()


# ---------------------------------------------------------------------------
# train_hmm_model
# ---------------------------------------------------------------------------

def test_train_hmm_model_saves_files(tmp_data_dir):
    hv = _make_series(150)
    atr = _make_series(150, seed=1)
    bbw = _make_series(150, seed=2)
    model, sm = train_hmm_model(hv, atr, bbw)
    assert _model_path().exists()
    assert _meta_path().exists()
    assert set(sm.values()) == {"low_vol", "mid_vol", "high_vol"}


def test_train_hmm_model_insufficient_data(tmp_data_dir):
    with pytest.raises(ValueError, match="Insufficient"):
        train_hmm_model([1.0] * 5, [1.0] * 5, [1.0] * 5)


def test_train_hmm_model_state_map_covers_all_states(tmp_data_dir):
    hv = _make_series(200)
    atr = _make_series(200, seed=1)
    bbw = _make_series(200, seed=2)
    _, sm = train_hmm_model(hv, atr, bbw)
    assert len(sm) == 3
    assert set(sm.values()) == {"low_vol", "mid_vol", "high_vol"}


# ---------------------------------------------------------------------------
# load_model / model_age_days
# ---------------------------------------------------------------------------

def test_load_model_returns_none_when_missing(tmp_data_dir):
    assert load_model() is None


def test_load_model_returns_none_on_corrupt_file(tmp_data_dir):
    _model_path().write_bytes(b"not-a-pickle")
    assert load_model() is None


def test_model_age_days_none_when_missing(tmp_data_dir):
    assert model_age_days() is None


def test_model_age_days_after_train(tmp_data_dir):
    hv = _make_series(150)
    atr = _make_series(150, seed=1)
    bbw = _make_series(150, seed=2)
    train_hmm_model(hv, atr, bbw)
    age = model_age_days()
    assert age is not None
    assert 0 <= age < 1  # just trained


# ---------------------------------------------------------------------------
# classify_with_hmm
# ---------------------------------------------------------------------------

def test_classify_with_hmm_returns_none_without_model(tmp_data_dir):
    indicators = _make_indicators()
    assert classify_with_hmm(indicators) is None


def test_classify_with_hmm_returns_valid_label(tmp_data_dir):
    hv = _make_series(150)
    atr = _make_series(150, seed=1)
    bbw = _make_series(150, seed=2)
    train_hmm_model(hv, atr, bbw)
    indicators = _make_indicators(100)
    result = classify_with_hmm(indicators)
    assert result in {"low_vol", "mid_vol", "high_vol"}


def test_classify_with_hmm_returns_none_on_insufficient_indicators(tmp_data_dir):
    hv = _make_series(150)
    atr = _make_series(150, seed=1)
    bbw = _make_series(150, seed=2)
    train_hmm_model(hv, atr, bbw)
    # Provide too-short series
    indicators = {"_hv_series": [1.0], "_atr_pct_series": [1.0], "_bbw_series": [1.0]}
    assert classify_with_hmm(indicators) is None


# ---------------------------------------------------------------------------
# maybe_retrain
# ---------------------------------------------------------------------------

def test_maybe_retrain_trains_when_no_model(tmp_data_dir):
    hv = _make_series(150)
    atr = _make_series(150, seed=1)
    bbw = _make_series(150, seed=2)
    retrained = maybe_retrain(hv, atr, bbw)
    assert retrained is True
    assert _model_path().exists()


def test_maybe_retrain_skips_when_fresh(tmp_data_dir):
    hv = _make_series(150)
    atr = _make_series(150, seed=1)
    bbw = _make_series(150, seed=2)
    train_hmm_model(hv, atr, bbw)
    retrained = maybe_retrain(hv, atr, bbw)
    assert retrained is False


def test_maybe_retrain_retrains_when_stale(tmp_data_dir):
    hv = _make_series(150)
    atr = _make_series(150, seed=1)
    bbw = _make_series(150, seed=2)
    train_hmm_model(hv, atr, bbw)
    # Fake old metadata
    meta_path = _meta_path()
    meta = json.loads(meta_path.read_text())
    meta["trained_at"] = "2020-01-01T00:00:00+00:00"
    meta_path.write_text(json.dumps(meta))
    retrained = maybe_retrain(hv, atr, bbw)
    assert retrained is True


# ---------------------------------------------------------------------------
# get_model_info
# ---------------------------------------------------------------------------

def test_get_model_info_no_model(tmp_data_dir):
    info = get_model_info()
    assert info["trained"] is False


def test_get_model_info_after_train(tmp_data_dir):
    hv = _make_series(150)
    atr = _make_series(150, seed=1)
    bbw = _make_series(150, seed=2)
    train_hmm_model(hv, atr, bbw)
    info = get_model_info()
    assert info["trained"] is True
    assert info["n_states"] == 3
    assert info["age_days"] is not None


# ---------------------------------------------------------------------------
# classify_regime_full / classify_regime (integration)
# ---------------------------------------------------------------------------

def test_classify_regime_falls_back_to_rule_based_on_train_failure(tmp_data_dir):
    indicators = _make_indicators()
    # Force fallback by making maybe_retrain raise and load_model return None
    with patch("cryptoscholar.ta.hmm_regime.maybe_retrain", side_effect=Exception("forced")):
        with patch("cryptoscholar.ta.hmm_regime.load_model", return_value=None):
            regime, source = classify_regime_full(indicators)
    assert source == "rule_based"
    assert regime in {"low_vol", "mid_vol", "high_vol"}


def test_classify_regime_uses_hmm_when_model_exists(tmp_data_dir):
    hv = _make_series(150)
    atr = _make_series(150, seed=1)
    bbw = _make_series(150, seed=2)
    train_hmm_model(hv, atr, bbw)
    indicators = _make_indicators(100)
    regime, source = classify_regime_full(indicators)
    assert source == "hmm"
    assert regime in {"low_vol", "mid_vol", "high_vol"}


def test_classify_regime_string_interface_unchanged(tmp_data_dir):
    indicators = _make_indicators()
    result = classify_regime(indicators)
    assert result in {"low_vol", "mid_vol", "high_vol"}
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# compute_vrs (unchanged)
# ---------------------------------------------------------------------------

def test_compute_vrs_values():
    assert compute_vrs("low_vol") == 25
    assert compute_vrs("mid_vol") == 55
    assert compute_vrs("high_vol") == 80
    assert compute_vrs("unknown") == 55
