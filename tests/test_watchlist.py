"""Tests for watchlist DB layer and watchlist tool functions."""

import os
import tempfile
from unittest.mock import patch

import pytest

from cryptoscholar.data.watchlist_db import (
    VALID_CONDITIONS,
    add_symbols,
    get_alerts,
    get_watchlist,
    list_all_watchlists,
    remove_symbols,
    set_alert,
    update_alert_state,
)
from cryptoscholar.tools.watchlist import (
    alert_check,
    alert_set,
    watchlist_add,
    watchlist_lists,
    watchlist_remove,
    watchlist_scan,
    watchlist_show,
)


@pytest.fixture()
def db(tmp_path):
    """Per-test SQLite DB path in a temp directory."""
    return str(tmp_path / "wl.db")


# ===========================================================================
# DB layer — watchlist CRUD
# ===========================================================================

class TestAddSymbols:
    def test_creates_list_and_adds_symbols(self, db):
        result = add_symbols("main", ["BTC", "ETH"], db_path=db)
        assert set(result["added"]) == {"BTC", "ETH"}
        assert result["already_present"] == []
        assert result["list_name"] == "main"

    def test_uppercases_symbols(self, db):
        result = add_symbols("main", ["btc", "sol"], db_path=db)
        assert "BTC" in result["added"]
        assert "SOL" in result["added"]

    def test_duplicate_reported_on_second_add(self, db):
        add_symbols("main", ["BTC"], db_path=db)
        result = add_symbols("main", ["BTC"], db_path=db)
        assert "BTC" in result["already_present"]
        assert result["added"] == []

    def test_empty_symbols_raises(self):
        with pytest.raises(ValueError):
            watchlist_add([], "main")


class TestGetWatchlist:
    def test_nonexistent_list_returns_exists_false(self, db):
        result = get_watchlist("ghost", db_path=db)
        assert result["exists"] is False
        assert result["symbols"] == []

    def test_returns_added_symbols(self, db):
        add_symbols("test", ["BTC", "SOL"], db_path=db)
        result = get_watchlist("test", db_path=db)
        assert result["exists"] is True
        assert set(result["symbols"]) == {"BTC", "SOL"}

    def test_symbol_count_correct(self, db):
        add_symbols("mylist", ["BTC", "ETH", "SOL"], db_path=db)
        result = get_watchlist("mylist", db_path=db)
        assert result["symbol_count"] == 3


class TestRemoveSymbols:
    def test_removes_existing_symbol(self, db):
        add_symbols("main", ["BTC", "ETH"], db_path=db)
        result = remove_symbols("main", ["BTC"], db_path=db)
        assert "BTC" in result["removed"]
        remaining = get_watchlist("main", db_path=db)
        assert "BTC" not in remaining["symbols"]
        assert "ETH" in remaining["symbols"]

    def test_nonexistent_symbol_in_not_found(self, db):
        add_symbols("main", ["BTC"], db_path=db)
        result = remove_symbols("main", ["XYZ"], db_path=db)
        assert "XYZ" in result["not_found"]

    def test_nonexistent_list_returns_gracefully(self, db):
        result = remove_symbols("ghost", ["BTC"], db_path=db)
        assert result["removed"] == []
        assert "BTC" in result["not_found"]


class TestListAllWatchlists:
    def test_empty_db_returns_empty_list(self, db):
        result = list_all_watchlists(db_path=db)
        assert result == []

    def test_returns_all_lists(self, db):
        add_symbols("alpha", ["BTC"], db_path=db)
        add_symbols("beta", ["ETH", "SOL"], db_path=db)
        result = list_all_watchlists(db_path=db)
        names = {r["name"] for r in result}
        assert names == {"alpha", "beta"}

    def test_symbol_count_accurate(self, db):
        add_symbols("mylist", ["BTC", "ETH", "SOL"], db_path=db)
        result = list_all_watchlists(db_path=db)
        assert result[0]["symbol_count"] == 3


# ===========================================================================
# DB layer — alerts CRUD
# ===========================================================================

class TestSetAlert:
    def test_valid_tss_above_alert(self, db):
        result = set_alert("main", "BTC", "tss_above", threshold=70.0, db_path=db)
        assert result["symbol"] == "BTC"
        assert result["condition"] == "tss_above"
        assert result["threshold"] == 70.0
        assert result["status"] == "set"

    def test_valid_tss_below_alert(self, db):
        result = set_alert("main", "ETH", "tss_below", threshold=30.0, db_path=db)
        assert result["condition"] == "tss_below"

    def test_valid_regime_change_alert(self, db):
        result = set_alert("main", "SOL", "regime_change", db_path=db)
        assert result["condition"] == "regime_change"
        assert result["threshold"] is None

    def test_invalid_condition_raises(self, db):
        with pytest.raises(ValueError, match="condition must be"):
            set_alert("main", "BTC", "bad_condition", threshold=50.0, db_path=db)

    def test_tss_above_without_threshold_raises(self, db):
        with pytest.raises(ValueError, match="threshold is required"):
            set_alert("main", "BTC", "tss_above", threshold=None, db_path=db)

    def test_symbol_auto_added_to_watchlist(self, db):
        set_alert("main", "BTC", "tss_above", threshold=60.0, db_path=db)
        wl = get_watchlist("main", db_path=db)
        assert "BTC" in wl["symbols"]

    def test_upsert_updates_threshold(self, db):
        set_alert("main", "BTC", "tss_above", threshold=60.0, db_path=db)
        set_alert("main", "BTC", "tss_above", threshold=75.0, db_path=db)
        alerts = get_alerts("main", db_path=db)
        tss_above = next(a for a in alerts if a["condition"] == "tss_above")
        assert tss_above["threshold"] == 75.0


class TestGetAlerts:
    def test_no_alerts_returns_empty(self, db):
        result = get_alerts("ghost", db_path=db)
        assert result == []

    def test_returns_set_alerts(self, db):
        set_alert("main", "BTC", "tss_above", threshold=70.0, db_path=db)
        set_alert("main", "ETH", "regime_change", db_path=db)
        alerts = get_alerts("main", db_path=db)
        assert len(alerts) == 2
        conditions = {a["condition"] for a in alerts}
        assert conditions == {"tss_above", "regime_change"}


class TestUpdateAlertState:
    def test_updates_last_tss_and_regime(self, db):
        set_alert("main", "BTC", "tss_above", threshold=70.0, db_path=db)
        alerts = get_alerts("main", db_path=db)
        alert_id = alerts[0]["id"]
        update_alert_state(alert_id, last_tss=65.3, last_regime="mid_vol", db_path=db)
        updated = get_alerts("main", db_path=db)
        a = updated[0]
        assert a["last_tss"] == pytest.approx(65.3)
        assert a["last_regime"] == "mid_vol"


# ===========================================================================
# Tool layer — watchlist tools (using mocked DB via temp files)
# ===========================================================================

def _make_mock_rankings(symbols: list[str]) -> list[dict]:
    return [
        {
            "symbol": sym,
            "tss": 50.0 + i * 5,
            "regime": "mid_vol",
            "vrs": 50,
            "rank": i + 1,
            "data_source": "binance",
            "price": 100.0,
            "price_change_24h_pct": 1.0,
            "ema_alignment": "full_bull",
            "mtf_alignment_4h": "bullish",
            "rsi_divergence": "none",
            "obv_trend": "rising",
            "funding_rate": 0.0001,
            "rsi_14": 60.0,
            "adx_14": 25.0,
            "rs_btc": 2.0,
        }
        for i, sym in enumerate(symbols)
    ]


class TestWatchlistToolLayer:
    def test_add_raises_on_empty_symbols(self):
        with pytest.raises(ValueError):
            watchlist_add([])

    def test_remove_raises_on_empty_symbols(self):
        with pytest.raises(ValueError):
            watchlist_remove([])

    def test_show_delegates_to_db_get(self):
        with patch("cryptoscholar.tools.watchlist._db_get") as mock_get:
            mock_get.return_value = {"list_name": "main", "exists": True, "symbols": ["BTC"]}
            result = watchlist_show("main")
        mock_get.assert_called_once_with("main")
        assert result["exists"] is True

    def test_lists_delegates_to_db_list_all(self):
        with patch("cryptoscholar.tools.watchlist._db_list_all") as mock_list:
            mock_list.return_value = [{"name": "main", "symbol_count": 3}]
            result = watchlist_lists()
        mock_list.assert_called_once()
        assert result[0]["name"] == "main"

    def test_scan_returns_empty_for_nonexistent_list(self):
        with patch("cryptoscholar.tools.watchlist._db_get") as mock_get:
            mock_get.return_value = {"exists": False, "symbols": []}
            result = watchlist_scan("ghost")
        assert result == []

    def test_scan_returns_empty_for_empty_list(self):
        with patch("cryptoscholar.tools.watchlist._db_get") as mock_get:
            mock_get.return_value = {"exists": True, "symbols": []}
            result = watchlist_scan("empty")
        assert result == []

    def test_scan_delegates_to_rank_coins(self):
        symbols = ["BTC", "ETH", "SOL"]
        mock_ranked = _make_mock_rankings(symbols)
        with patch("cryptoscholar.tools.watchlist._db_get") as mock_get, \
             patch("cryptoscholar.tools.watchlist.rank_coins", return_value=mock_ranked) as mock_rank:
            mock_get.return_value = {"exists": True, "symbols": symbols}
            result = watchlist_scan("main")
        mock_rank.assert_called_once_with(symbols)
        assert result == mock_ranked

    def test_alert_set_delegates_to_db(self):
        with patch("cryptoscholar.tools.watchlist._db_set_alert") as mock_set:
            mock_set.return_value = {"status": "set"}
            alert_set("BTC", "tss_above", threshold=70.0, list_name="main")
        mock_set.assert_called_once_with("main", "BTC", "tss_above", 70.0)


class TestAlertCheck:
    def _make_alerts(self) -> list[dict]:
        return [
            {"id": 1, "symbol": "BTC", "condition": "tss_above",
             "threshold": 70.0, "last_regime": None, "last_tss": None},
            {"id": 2, "symbol": "ETH", "condition": "tss_below",
             "threshold": 40.0, "last_regime": None, "last_tss": None},
            {"id": 3, "symbol": "SOL", "condition": "regime_change",
             "threshold": None, "last_regime": "low_vol", "last_tss": None},
        ]

    def test_no_alerts_returns_empty(self):
        with patch("cryptoscholar.tools.watchlist._db_get_alerts", return_value=[]):
            result = alert_check("empty")
        assert result["triggered"] == []
        assert result["checked"] == 0

    def test_tss_above_fires_when_current_gte_threshold(self):
        alerts = [self._make_alerts()[0]]  # BTC tss_above 70
        rankings = [{"symbol": "BTC", "tss": 75.0, "regime": "mid_vol"}]
        with patch("cryptoscholar.tools.watchlist._db_get_alerts", return_value=alerts), \
             patch("cryptoscholar.tools.watchlist.rank_coins", return_value=rankings), \
             patch("cryptoscholar.tools.watchlist._db_update_alert"):
            result = alert_check("main")
        assert len(result["triggered"]) == 1
        assert result["triggered"][0]["symbol"] == "BTC"
        assert "≥" in result["triggered"][0]["reason"]

    def test_tss_above_does_not_fire_below_threshold(self):
        alerts = [self._make_alerts()[0]]  # BTC tss_above 70
        rankings = [{"symbol": "BTC", "tss": 65.0, "regime": "low_vol"}]
        with patch("cryptoscholar.tools.watchlist._db_get_alerts", return_value=alerts), \
             patch("cryptoscholar.tools.watchlist.rank_coins", return_value=rankings), \
             patch("cryptoscholar.tools.watchlist._db_update_alert"):
            result = alert_check("main")
        assert result["triggered"] == []

    def test_tss_below_fires_when_current_lte_threshold(self):
        alerts = [self._make_alerts()[1]]  # ETH tss_below 40
        rankings = [{"symbol": "ETH", "tss": 35.0, "regime": "high_vol"}]
        with patch("cryptoscholar.tools.watchlist._db_get_alerts", return_value=alerts), \
             patch("cryptoscholar.tools.watchlist.rank_coins", return_value=rankings), \
             patch("cryptoscholar.tools.watchlist._db_update_alert"):
            result = alert_check("main")
        assert len(result["triggered"]) == 1
        assert result["triggered"][0]["symbol"] == "ETH"

    def test_regime_change_fires_on_different_regime(self):
        alerts = [self._make_alerts()[2]]  # SOL regime_change, last=low_vol
        rankings = [{"symbol": "SOL", "tss": 55.0, "regime": "high_vol"}]
        with patch("cryptoscholar.tools.watchlist._db_get_alerts", return_value=alerts), \
             patch("cryptoscholar.tools.watchlist.rank_coins", return_value=rankings), \
             patch("cryptoscholar.tools.watchlist._db_update_alert"):
            result = alert_check("main")
        assert len(result["triggered"]) == 1
        assert "low_vol" in result["triggered"][0]["reason"]
        assert "high_vol" in result["triggered"][0]["reason"]

    def test_regime_change_does_not_fire_on_same_regime(self):
        alerts = [self._make_alerts()[2]]  # SOL regime_change, last=low_vol
        rankings = [{"symbol": "SOL", "tss": 50.0, "regime": "low_vol"}]  # same
        with patch("cryptoscholar.tools.watchlist._db_get_alerts", return_value=alerts), \
             patch("cryptoscholar.tools.watchlist.rank_coins", return_value=rankings), \
             patch("cryptoscholar.tools.watchlist._db_update_alert"):
            result = alert_check("main")
        assert result["triggered"] == []

    def test_regime_change_does_not_fire_on_first_check(self):
        """If last_regime is None (never checked), regime_change should not fire."""
        alert = {**self._make_alerts()[2], "last_regime": None}
        rankings = [{"symbol": "SOL", "tss": 50.0, "regime": "mid_vol"}]
        with patch("cryptoscholar.tools.watchlist._db_get_alerts", return_value=[alert]), \
             patch("cryptoscholar.tools.watchlist.rank_coins", return_value=rankings), \
             patch("cryptoscholar.tools.watchlist._db_update_alert"):
            result = alert_check("main")
        assert result["triggered"] == []

    def test_update_state_called_for_each_alert(self):
        alerts = self._make_alerts()[:2]  # BTC + ETH
        rankings = [
            {"symbol": "BTC", "tss": 65.0, "regime": "mid_vol"},
            {"symbol": "ETH", "tss": 55.0, "regime": "low_vol"},
        ]
        with patch("cryptoscholar.tools.watchlist._db_get_alerts", return_value=alerts), \
             patch("cryptoscholar.tools.watchlist.rank_coins", return_value=rankings), \
             patch("cryptoscholar.tools.watchlist._db_update_alert") as mock_update:
            alert_check("main")
        assert mock_update.call_count == 2

    def test_checked_count_matches_alert_count(self):
        alerts = self._make_alerts()
        rankings = [
            {"symbol": "BTC", "tss": 65.0, "regime": "mid_vol"},
            {"symbol": "ETH", "tss": 55.0, "regime": "low_vol"},
            {"symbol": "SOL", "tss": 50.0, "regime": "low_vol"},
        ]
        with patch("cryptoscholar.tools.watchlist._db_get_alerts", return_value=alerts), \
             patch("cryptoscholar.tools.watchlist.rank_coins", return_value=rankings), \
             patch("cryptoscholar.tools.watchlist._db_update_alert"):
            result = alert_check("main")
        assert result["checked"] == 3
