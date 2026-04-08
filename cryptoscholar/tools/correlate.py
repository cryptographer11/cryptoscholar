"""correlate_coins tool — pairwise Pearson correlation of 30-day daily returns."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import pandas as pd

from cryptoscholar.tools.analyze import _fetch_ohlcv_with_fallback

logger = logging.getLogger(__name__)

_MAX_WORKERS = 8
_LOOKBACK_DAYS = 35  # fetch 35 to get 30 clean returns after pct_change dropna
_TARGET_RETURNS = 30


def correlate_coins(symbols: list[str]) -> dict:
    """
    Compute pairwise Pearson correlation of 30-day daily returns.

    Parameters
    ----------
    symbols : List of ticker symbols e.g. ["BTC", "ETH", "SOL", "BNB"]
              Minimum 2, maximum 20.

    Returns
    -------
    Dict with:
        symbols              : list of symbols successfully fetched
        lookback_days        : actual number of return bars used
        matrix               : dict-of-dicts, correlation rounded to 3 dp
        high_correlation_pairs  : pairs with correlation > 0.85 (sorted desc)
        uncorrelated_pairs      : pairs with |correlation| < 0.30 (sorted asc)
    """
    if len(symbols) < 2:
        raise ValueError("Need at least 2 symbols for correlation")
    if len(symbols) > 20:
        raise ValueError("Maximum 20 symbols per correlation request")

    symbols = [s.upper().strip() for s in symbols]

    # Fetch OHLCV for each symbol in parallel
    closes: dict[str, pd.Series] = {}

    def _fetch(sym: str) -> tuple[str, pd.Series]:
        df, _ = _fetch_ohlcv_with_fallback(sym, days=_LOOKBACK_DAYS)
        return sym, df["close"]

    workers = min(_MAX_WORKERS, len(symbols))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_fetch, sym): sym for sym in symbols}
        for future in as_completed(futures):
            sym = futures[future]
            try:
                s, close = future.result()
                closes[s] = close
            except Exception as exc:
                logger.warning("Could not fetch data for %s — skipping: %s", sym, exc)

    if len(closes) < 2:
        raise ValueError(
            f"Insufficient data — only {len(closes)} symbol(s) fetched successfully"
        )

    # Align by date index, take last 31 rows → 30 return bars
    closes_df = pd.DataFrame(closes)
    closes_df = closes_df.tail(_TARGET_RETURNS + 1)
    returns_df = closes_df.pct_change().dropna()

    if len(returns_df) < 5:
        raise ValueError("Too few overlapping return bars after alignment")

    corr_matrix = returns_df.corr(method="pearson")
    available = list(corr_matrix.columns)

    # Build output matrix
    matrix: dict[str, dict[str, Optional[float]]] = {}
    for sym_a in available:
        matrix[sym_a] = {}
        for sym_b in available:
            val = corr_matrix.loc[sym_a, sym_b]
            matrix[sym_a][sym_b] = round(float(val), 3) if pd.notna(val) else None

    # Identify notable pairs (upper triangle only)
    high_corr: list[dict] = []
    uncorr: list[dict] = []

    for i, sym_a in enumerate(available):
        for sym_b in available[i + 1:]:
            val = matrix[sym_a].get(sym_b)
            if val is None:
                continue
            entry = {"symbol_a": sym_a, "symbol_b": sym_b, "correlation": val}
            if val > 0.85:
                high_corr.append(entry)
            elif abs(val) < 0.30:
                uncorr.append(entry)

    high_corr.sort(key=lambda x: x["correlation"], reverse=True)
    uncorr.sort(key=lambda x: abs(x["correlation"]))

    return {
        "symbols": available,
        "lookback_days": len(returns_df),
        "matrix": matrix,
        "high_correlation_pairs": high_corr,
        "uncorrelated_pairs": uncorr,
    }
