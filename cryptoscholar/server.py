"""CryptoScholar MCP server entry point."""

import logging
import logging.handlers
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Configure rotating log handler
_log_dir = Path(os.environ.get("CRYPTOSCHOLAR_LOG_DIR", "/tmp"))
_log_path = _log_dir / "cryptoscholar.log"

_handler = logging.handlers.RotatingFileHandler(
    _log_path, maxBytes=5 * 1024 * 1024, backupCount=3
)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[_handler, logging.StreamHandler()],
)

logger = logging.getLogger(__name__)

from mcp.server.fastmcp import FastMCP

from cryptoscholar.tools.analyze import analyze_coin as _analyze_coin
from cryptoscholar.tools.correlate import correlate_coins as _correlate_coins
from cryptoscholar.tools.debate import debate as _debate
from cryptoscholar.tools.market_context import market_context as _market_context
from cryptoscholar.tools.rank import rank_coins as _rank_coins
from cryptoscholar.tools.top_coins import top_coins as _top_coins
from cryptoscholar.tools.train_regime import train_regime_model as _train_regime_model
from cryptoscholar.tools.watchlist import (
    alert_check as _alert_check,
    alert_set as _alert_set,
    watchlist_add as _watchlist_add,
    watchlist_lists as _watchlist_lists,
    watchlist_remove as _watchlist_remove,
    watchlist_scan as _watchlist_scan,
    watchlist_show as _watchlist_show,
)

mcp = FastMCP("CryptoScholar")


@mcp.tool()
def analyze_coin(symbol: str) -> dict:
    """Perform full technical analysis on a cryptocurrency.

    Fetches 300 days of daily OHLCV from Binance (or CoinGecko as fallback),
    computes EMA, RSI, MACD, ADX, ATR, Bollinger Bands, OBV trend,
    historical volatility, and relative strength vs BTC.
    Also fetches 4H candles for multi-timeframe alignment, detects RSI
    divergence, and fetches the USDT-M perpetual funding rate.

    Returns indicators, TSS score (base ± MTF bonus ± OBV bonus), regime label,
    mtf_alignment_4h, rsi_divergence, obv_trend, funding_rate, and data source.
    """
    return _analyze_coin(symbol)


@mcp.tool()
def rank_coins(symbols: list[str]) -> list[dict]:
    """Rank multiple cryptocurrencies by Trend Strength Score (TSS).

    Analyzes each symbol using Binance OHLCV (CoinGecko fallback) and returns
    a ranked list with TSS, regime, key signals, and price data. Analysis runs
    in parallel (up to 8 workers) for fast results on large lists.

    Each result includes: tss, regime, ema_alignment, mtf_alignment_4h,
    rsi_divergence, obv_trend, funding_rate, rsi_14, adx_14, rs_btc,
    price, price_change_24h_pct. Failed symbols are skipped gracefully.
    """
    return _rank_coins(symbols)


@mcp.tool()
def debate(symbol: str) -> dict:
    """Generate a Claude AI bull/bear debate for a cryptocurrency.

    Fetches fresh TA data for the symbol then calls Claude to produce
    a structured bull case, bear case, and bottom-line synthesis.
    Requires ANTHROPIC_API_KEY to be set.
    """
    return _debate(symbol)


@mcp.tool()
def market_context() -> dict:
    """Fetch macro market context signals for the overall crypto market.

    Returns BTC dominance trend, ETH/BTC ratio trend, TOTAL3 market cap trend,
    stablecoin supply trend, Fear & Greed Index, and composite scores:
      - ARS (Altcoin Rotation Score): how favourable macro is for alts (0-100)
      - MRS (Market Readiness Score): overall market readiness for upside (0-100)
        MRS includes a ±5 Fear & Greed modifier (extreme fear/greed readings).

    No API key required. Data from CoinGecko, DefiLlama, and Alternative.me.
    Results are cached for 5 minutes.
    """
    return _market_context()


@mcp.tool()
def correlate_coins(symbols: list[str]) -> dict:
    """Compute pairwise Pearson correlation of 30-day daily returns.

    Fetches price history for each symbol and builds a full correlation matrix.
    Highlights high-correlation clusters (>0.85) and uncorrelated pairs (<0.30)
    for portfolio diversification analysis.

    Parameters
    ----------
    symbols : 2–20 ticker symbols e.g. ["BTC", "ETH", "SOL", "BNB"]

    Returns matrix, high_correlation_pairs, and uncorrelated_pairs.
    """
    return _correlate_coins(symbols)


@mcp.tool()
def top_coins(limit: int = 50) -> list[dict]:
    """Fetch the top N cryptocurrencies by market cap and rank them by TSS.

    Stablecoins are excluded automatically. Uses parallel analysis (up to 8
    workers) for fast results across 50+ coins. Returns the same fields as
    rank_coins, plus mtf_alignment_4h and rsi_divergence for each coin.
    """
    return _top_coins(limit)


@mcp.tool()
def watchlist_add(symbols: list[str], list_name: str = "default") -> dict:
    """Add symbols to a named watchlist (creates the list if it doesn't exist).

    Returns which symbols were added vs already present.
    """
    return _watchlist_add(symbols, list_name)


@mcp.tool()
def watchlist_remove(symbols: list[str], list_name: str = "default") -> dict:
    """Remove symbols from a watchlist. Also removes any alerts for those symbols."""
    return _watchlist_remove(symbols, list_name)


@mcp.tool()
def watchlist_show(list_name: str = "default") -> dict:
    """Show all symbols and configured alerts for a named watchlist.

    Returns exists=False if the list hasn't been created yet.
    """
    return _watchlist_show(list_name)


@mcp.tool()
def watchlist_lists() -> list[dict]:
    """List all named watchlists with symbol counts and creation timestamps."""
    return _watchlist_lists()


@mcp.tool()
def watchlist_scan(list_name: str = "default") -> list[dict]:
    """Run a full TSS analysis on every symbol in a watchlist and rank by TSS.

    This is the digest view — a live snapshot of the entire watchlist right now.
    Runs in parallel (up to 8 workers). Returns the same fields as rank_coins.
    """
    return _watchlist_scan(list_name)


@mcp.tool()
def alert_set(
    symbol: str,
    condition: str,
    threshold: float | None = None,
    list_name: str = "default",
) -> dict:
    """Set a TSS threshold or regime-change alert on a symbol.

    Parameters
    ----------
    symbol    : Ticker e.g. "BTC"
    condition : 'tss_above'     — fires when TSS >= threshold
                'tss_below'     — fires when TSS <= threshold
                'regime_change' — fires when regime changes from last known value
    threshold : Required for tss_above / tss_below (0–100). Ignored for regime_change.
    list_name : Watchlist to attach to. Symbol is auto-added if not already present.
    """
    return _alert_set(symbol, condition, threshold, list_name)


@mcp.tool()
def alert_check(list_name: str = "default") -> dict:
    """Check all alerts in a watchlist against live TA data.

    Fetches current TSS and regime for every alerted symbol (parallel),
    reports which alerts have fired, and updates the stored baseline so
    subsequent checks track drift correctly.

    Returns triggered alerts with reason, current_tss, and current_regime.
    """
    return _alert_check(list_name)


@mcp.tool()
def train_regime_model(force: bool = False) -> dict:
    """Train (or retrain) the HMM volatility regime model on BTC price history.

    The model classifies market volatility into 3 states (low_vol / mid_vol /
    high_vol) using GaussianHMM trained on three features: historical volatility
    (hv_20), normalised ATR-14, and Bollinger Band width.

    The model is persisted to ~/.cryptoscholar/hmm_model.pkl and auto-retrains
    every 7 days when analyze_coin or rank_coins is called. Use this tool to
    trigger a manual retrain (e.g. after a major market structure shift).

    Parameters
    ----------
    force : bool
        If True, retrain even if the model was trained less than 7 days ago.
    """
    return _train_regime_model(force)


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting CryptoScholar MCP server v0.6.0")
    mcp.run()


if __name__ == "__main__":
    main()
