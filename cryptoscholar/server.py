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
from cryptoscholar.tools.rank import rank_coins as _rank_coins

mcp = FastMCP("CryptoScholar")


@mcp.tool()
def analyze_coin(symbol: str) -> dict:
    """Perform full technical analysis on a cryptocurrency.

    Fetches 90 days of daily OHLCV from CoinGecko, computes EMA, RSI,
    MACD, ADX, ATR, Bollinger Bands, historical volatility, and relative
    strength vs BTC. Returns indicators, TSS score, and regime label.
    """
    return _analyze_coin(symbol)


@mcp.tool()
def rank_coins(symbols: list[str]) -> list[dict]:
    """Rank multiple cryptocurrencies by Trend Strength Score (TSS).

    Analyzes each symbol and returns a ranked list with TSS, regime,
    key signals, and price data. Failed symbols are skipped gracefully.
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


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting CryptoScholar MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
