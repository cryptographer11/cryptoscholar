# CryptoScholar

Crypto technical analysis MCP server powered by Claude AI. Exposes 3 tools to Claude via the Model Context Protocol:

- **analyze_coin** — full TA (EMA, RSI, MACD, ADX, ATR, Bollinger Bands, HV, RS vs BTC) + TSS score + regime
- **rank_coins** — TSS-ranked comparison of multiple coins
- **debate** — Claude AI bull/bear debate based on live TA data

Data source: CoinGecko free API (no key required for market data).

## Quick start

```bash
make install
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
cryptoscholar
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required for the `debate` tool |
| `CRYPTOSCHOLAR_MODEL` | `claude-haiku-4-5-20251001` | Claude model for debates |
| `CRYPTOSCHOLAR_LOG_DIR` | `/tmp` | Directory for rotating log files |

## Running tests

```bash
make test
make coverage
make lint-security
```

## Architecture

```
cryptoscholar/
  server.py        # MCP entry point (FastMCP)
  tools/
    analyze.py     # analyze_coin logic
    rank.py        # rank_coins logic
    debate.py      # Claude API debate generation
  ta/
    indicators.py  # pandas_ta wrapper + custom HV/RS
    scoring.py     # TSS components
    regime.py      # Rule-based vol regime (v1)
  data/
    coingecko.py   # HTTP client, TTL cache, OHLCV builder
```
