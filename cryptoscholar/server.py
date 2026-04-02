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
from cryptoscholar.tools.debate import debate as _debate
from cryptoscholar.tools.market_context import market_context as _market_context
from cryptoscholar.tools.rank import rank_coins as _rank_coins
from cryptoscholar.tools.top_coins import top_coins as _top_coins

mcp = FastMCP("CryptoScholar")


@mcp.tool()
def analyze_coin(symbol: str) -> dict:
    """Perform full technical analysis on a cryptocurrency.

    Fetches 300 days of daily OHLCV from Binance (or CoinGecko as fallback),
    computes EMA, RSI, MACD, ADX, ATR, Bollinger Bands, historical volatility,
    and relative strength vs BTC. Also fetches 4H candles for multi-timeframe
    alignment and detects RSI divergence.

    Returns indicators, TSS score (with ±3 MTF bonus), regime label,
    mtf_alignment_4h (bullish/bearish/neutral/unavailable),
    rsi_divergence (bullish/bearish/none), and the data source used.
    """
    return _analyze_coin(symbol)


@mcp.tool()
def rank_coins(symbols: list[str]) -> list[dict]:
    """Rank multiple cryptocurrencies by Trend Strength Score (TSS).

    Analyzes each symbol using Binance OHLCV (CoinGecko fallback) and returns
    a ranked list with TSS, regime, key signals, and price data. Analysis runs
    in parallel (up to 8 workers) for fast results on large lists.

    Each result includes: tss, regime, ema_alignment, mtf_alignment_4h,
    rsi_divergence, rsi_14, adx_14, rs_btc, price, price_change_24h_pct.
    Failed symbols are skipped gracefully.
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
    stablecoin supply trend, and composite scores:
      - ARS (Altcoin Rotation Score): how favourable macro is for alts (0-100)
      - MRS (Market Readiness Score): overall market readiness for upside (0-100)

    No API key required. Data from CoinGecko (rate-limited) and DefiLlama.
    Results are cached for 5 minutes.
    """
    return _market_context()


@mcp.tool()
def top_coins(limit: int = 50) -> list[dict]:
    """Fetch the top N cryptocurrencies by market cap and rank them by TSS.

    Stablecoins are excluded automatically. Uses parallel analysis (up to 8
    workers) for fast results across 50+ coins. Returns the same fields as
    rank_coins, plus mtf_alignment_4h and rsi_divergence for each coin.
    """
    return _top_coins(limit)


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting CryptoScholar MCP server v0.3.0")
    mcp.run()


if __name__ == "__main__":
    main()
