"""Persistent watchlist and alert storage using SQLite.

DB path: ~/.cryptoscholar/watchlist.db
Override with CRYPTOSCHOLAR_DATA_DIR env var.
Pass db_path=":memory:" in tests.
"""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlists (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    UNIQUE NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS watchlist_coins (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    watchlist_id INTEGER NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    symbol       TEXT    NOT NULL,
    added_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(watchlist_id, symbol)
);

CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    watchlist_id INTEGER NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    symbol       TEXT    NOT NULL,
    condition    TEXT    NOT NULL,  -- 'tss_above' | 'tss_below' | 'regime_change'
    threshold    REAL,              -- NULL for regime_change
    last_regime  TEXT,              -- last observed regime (for regime_change detection)
    last_tss     REAL,              -- last observed TSS (informational)
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(watchlist_id, symbol, condition)
);

PRAGMA foreign_keys = ON;
"""

VALID_CONDITIONS = {"tss_above", "tss_below", "regime_change"}


def _default_db_path() -> str:
    data_dir = os.environ.get("CRYPTOSCHOLAR_DATA_DIR")
    if data_dir:
        return str(Path(data_dir) / "watchlist.db")
    return str(Path.home() / ".cryptoscholar" / "watchlist.db")


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or _default_db_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Create tables if they don't exist. Idempotent."""
    conn = _connect(db_path)
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_or_create_watchlist(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute("SELECT id FROM watchlists WHERE name = ?", (name,)).fetchone()
    if row:
        return int(row["id"])
    cur = conn.execute("INSERT INTO watchlists (name) VALUES (?)", (name,))
    return cur.lastrowid  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Watchlist CRUD
# ---------------------------------------------------------------------------

def add_symbols(
    list_name: str,
    symbols: list[str],
    db_path: Optional[str] = None,
) -> dict:
    """Add symbols to a named watchlist. Creates the list if it doesn't exist."""
    init_db(db_path)
    symbols = [s.upper().strip() for s in symbols if s.strip()]
    added: list[str] = []
    already_present: list[str] = []

    conn = _connect(db_path)
    try:
        wl_id = _get_or_create_watchlist(conn, list_name)
        for sym in symbols:
            try:
                conn.execute(
                    "INSERT INTO watchlist_coins (watchlist_id, symbol) VALUES (?, ?)",
                    (wl_id, sym),
                )
                added.append(sym)
            except sqlite3.IntegrityError:
                already_present.append(sym)
        conn.commit()
    finally:
        conn.close()

    return {"list_name": list_name, "added": added, "already_present": already_present}


def remove_symbols(
    list_name: str,
    symbols: list[str],
    db_path: Optional[str] = None,
) -> dict:
    """Remove symbols from a watchlist. Also removes any alerts for those symbols."""
    init_db(db_path)
    symbols = [s.upper().strip() for s in symbols if s.strip()]
    removed: list[str] = []
    not_found: list[str] = []

    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM watchlists WHERE name = ?", (list_name,)
        ).fetchone()
        if not row:
            return {"list_name": list_name, "removed": [], "not_found": symbols}
        wl_id = int(row["id"])
        for sym in symbols:
            cur = conn.execute(
                "DELETE FROM watchlist_coins WHERE watchlist_id = ? AND symbol = ?",
                (wl_id, sym),
            )
            if cur.rowcount > 0:
                removed.append(sym)
                conn.execute(
                    "DELETE FROM alerts WHERE watchlist_id = ? AND symbol = ?",
                    (wl_id, sym),
                )
            else:
                not_found.append(sym)
        conn.commit()
    finally:
        conn.close()

    return {"list_name": list_name, "removed": removed, "not_found": not_found}


def get_watchlist(list_name: str, db_path: Optional[str] = None) -> dict:
    """Return all symbols and alert configs for a named watchlist."""
    init_db(db_path)
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, created_at FROM watchlists WHERE name = ?", (list_name,)
        ).fetchone()
        if not row:
            return {"list_name": list_name, "exists": False, "symbols": [], "alerts": []}
        wl_id = int(row["id"])
        symbols = [
            r["symbol"]
            for r in conn.execute(
                "SELECT symbol FROM watchlist_coins WHERE watchlist_id = ? ORDER BY added_at",
                (wl_id,),
            ).fetchall()
        ]
        alerts = [
            dict(r)
            for r in conn.execute(
                "SELECT symbol, condition, threshold, last_regime, last_tss "
                "FROM alerts WHERE watchlist_id = ? ORDER BY symbol, condition",
                (wl_id,),
            ).fetchall()
        ]
    finally:
        conn.close()

    return {
        "list_name": list_name,
        "exists": True,
        "symbol_count": len(symbols),
        "symbols": symbols,
        "alerts": alerts,
        "created_at": row["created_at"],
    }


def list_all_watchlists(db_path: Optional[str] = None) -> list[dict]:
    """Return all watchlist names with symbol counts."""
    init_db(db_path)
    conn = _connect(db_path)
    try:
        rows = conn.execute("""
            SELECT w.name, w.created_at, COUNT(wc.id) AS symbol_count
            FROM watchlists w
            LEFT JOIN watchlist_coins wc ON wc.watchlist_id = w.id
            GROUP BY w.id, w.name, w.created_at
            ORDER BY w.created_at
        """).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Alert CRUD
# ---------------------------------------------------------------------------

def set_alert(
    list_name: str,
    symbol: str,
    condition: str,
    threshold: Optional[float] = None,
    db_path: Optional[str] = None,
) -> dict:
    """
    Set (or update) an alert on a symbol.

    Conditions
    ----------
    tss_above     : fires when TSS >= threshold
    tss_below     : fires when TSS <= threshold
    regime_change : fires when regime differs from the last observed value

    The symbol is auto-added to the watchlist if not already present.
    """
    if condition not in VALID_CONDITIONS:
        raise ValueError(f"condition must be one of {sorted(VALID_CONDITIONS)}")
    if condition in ("tss_above", "tss_below") and threshold is None:
        raise ValueError(f"threshold is required for condition '{condition}'")

    init_db(db_path)
    symbol = symbol.upper().strip()

    conn = _connect(db_path)
    try:
        wl_id = _get_or_create_watchlist(conn, list_name)
        # Auto-add symbol to watchlist
        try:
            conn.execute(
                "INSERT INTO watchlist_coins (watchlist_id, symbol) VALUES (?, ?)",
                (wl_id, symbol),
            )
        except sqlite3.IntegrityError:
            pass  # already in list
        # Upsert alert
        conn.execute(
            """
            INSERT INTO alerts (watchlist_id, symbol, condition, threshold)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(watchlist_id, symbol, condition)
            DO UPDATE SET threshold = excluded.threshold
            """,
            (wl_id, symbol, condition, threshold),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "list_name": list_name,
        "symbol": symbol,
        "condition": condition,
        "threshold": threshold,
        "status": "set",
    }


def get_alerts(list_name: str, db_path: Optional[str] = None) -> list[dict]:
    """Return all alerts for a watchlist (for use by alert_check)."""
    init_db(db_path)
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM watchlists WHERE name = ?", (list_name,)
        ).fetchone()
        if not row:
            return []
        wl_id = int(row["id"])
        rows = conn.execute(
            "SELECT id, symbol, condition, threshold, last_regime, last_tss "
            "FROM alerts WHERE watchlist_id = ?",
            (wl_id,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def update_alert_state(
    alert_id: int,
    last_tss: Optional[float],
    last_regime: Optional[str],
    db_path: Optional[str] = None,
) -> None:
    """Persist the latest observed TSS and regime after an alert_check run."""
    conn = _connect(db_path)
    try:
        conn.execute(
            "UPDATE alerts SET last_tss = ?, last_regime = ? WHERE id = ?",
            (last_tss, last_regime, alert_id),
        )
        conn.commit()
    finally:
        conn.close()
