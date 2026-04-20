"""Watchlist and alert tool implementations."""

import logging
from typing import Optional

from cryptoscholar.data.watchlist_db import (
    add_symbols as _db_add,
    get_alerts as _db_get_alerts,
    get_watchlist as _db_get,
    list_all_watchlists as _db_list_all,
    remove_symbols as _db_remove,
    set_alert as _db_set_alert,
    update_alert_state as _db_update_alert,
)
from cryptoscholar.tools.rank import rank_coins

logger = logging.getLogger(__name__)


def watchlist_add(symbols: list[str], list_name: str = "default") -> dict:
    """
    Add one or more symbols to a named watchlist.

    Creates the watchlist if it doesn't exist. Returns which symbols were
    added vs already present.
    """
    if not symbols:
        raise ValueError("symbols list cannot be empty")
    return _db_add(list_name, symbols)


def watchlist_remove(symbols: list[str], list_name: str = "default") -> dict:
    """
    Remove symbols from a watchlist. Also removes any alerts for those symbols.
    """
    if not symbols:
        raise ValueError("symbols list cannot be empty")
    return _db_remove(list_name, symbols)


def watchlist_show(list_name: str = "default") -> dict:
    """
    Return all symbols and configured alerts for a named watchlist.

    Returns exists=False if the watchlist has not been created yet.
    """
    return _db_get(list_name)


def watchlist_lists() -> list[dict]:
    """
    List all named watchlists with their symbol counts and creation timestamps.
    """
    return _db_list_all()


def watchlist_scan(list_name: str = "default") -> list[dict]:
    """
    Run a full TSS analysis on all symbols in a watchlist and return them
    ranked by Trend Strength Score.

    This is the 'digest' — a snapshot of every coin in the list right now.
    Runs in parallel (up to 8 workers). Returns the same fields as rank_coins.
    """
    wl = _db_get(list_name)
    if not wl["exists"] or not wl["symbols"]:
        return []
    return rank_coins(wl["symbols"])


def alert_set(
    symbol: str,
    condition: str,
    threshold: Optional[float] = None,
    list_name: str = "default",
) -> dict:
    """
    Set a TSS threshold or regime-change alert on a symbol.

    Parameters
    ----------
    symbol    : Ticker symbol e.g. "BTC"
    condition : One of:
                  'tss_above'     — fires when TSS >= threshold
                  'tss_below'     — fires when TSS <= threshold
                  'regime_change' — fires when regime changes from last known value
    threshold : Required for tss_above / tss_below. Ignored for regime_change.
    list_name : Watchlist to attach the alert to (default: "default").
                Symbol is auto-added to the list if not already present.
    """
    return _db_set_alert(list_name, symbol, condition, threshold)


def alert_check(list_name: str = "default") -> dict:
    """
    Fetch current TA data for all alerted symbols and report which alerts
    have triggered.

    Uses rank_coins for parallel analysis across all alerted symbols.
    Updates the stored last_tss / last_regime after each check so subsequent
    calls track drift correctly.

    Returns
    -------
    Dict with:
        triggered  : list of alerts that fired (with reason + current values)
        checked    : total number of alert conditions evaluated
        symbols    : list of symbols analyzed
    """
    alerts = _db_get_alerts(list_name)
    if not alerts:
        return {"triggered": [], "checked": 0, "symbols": []}

    # Unique symbols across all alerts
    symbols = list({a["symbol"] for a in alerts})

    # Parallel analysis via rank_coins
    try:
        rankings = rank_coins(symbols)
    except Exception as exc:
        logger.error("rank_coins failed during alert_check: %s", exc)
        return {"triggered": [], "checked": 0, "symbols": symbols, "error": str(exc)}

    current: dict[str, dict] = {r["symbol"]: r for r in rankings}

    triggered: list[dict] = []
    for alert in alerts:
        sym = alert["symbol"]
        analysis = current.get(sym)
        if not analysis:
            logger.warning("No analysis result for %s — skipping alert", sym)
            continue

        current_tss: float = analysis["tss"]
        current_regime: str = analysis["regime"]
        condition: str = alert["condition"]
        threshold: Optional[float] = alert["threshold"]
        last_regime: Optional[str] = alert["last_regime"]

        fired = False
        reason = ""

        if condition == "tss_above" and threshold is not None and current_tss >= threshold:
            fired = True
            reason = f"TSS {current_tss:.1f} ≥ threshold {threshold:.1f}"
        elif condition == "tss_below" and threshold is not None and current_tss <= threshold:
            fired = True
            reason = f"TSS {current_tss:.1f} ≤ threshold {threshold:.1f}"
        elif (
            condition == "regime_change"
            and last_regime is not None
            and current_regime != last_regime
        ):
            fired = True
            reason = f"Regime changed: {last_regime} → {current_regime}"

        # Persist latest observed state so next check tracks drift
        _db_update_alert(alert["id"], last_tss=current_tss, last_regime=current_regime)

        if fired:
            triggered.append({
                "symbol": sym,
                "condition": condition,
                "threshold": threshold,
                "current_tss": current_tss,
                "current_regime": current_regime,
                "reason": reason,
            })

    return {
        "triggered": triggered,
        "checked": len(alerts),
        "symbols": symbols,
    }
