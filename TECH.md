# CryptoScholar — Technical Reference

## Stack
- Python 3.11+
- MCP SDK: `mcp` (FastMCP)
- TA: `pandas`, `pandas-ta`, `numpy`
- HTTP: `httpx` (async-compatible, sync used)
- AI: `anthropic` SDK
- Config: `python-dotenv`

## Run Commands

```bash
# Install
make install

# Run MCP server (stdio mode)
python -m cryptoscholar

# Run tests
make test
make test-parallel
make coverage
make lint-security
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required for debate) | Claude API key |
| `CRYPTOSCHOLAR_MODEL` | `claude-haiku-4-5-20251001` | Claude model for debate |
| `CRYPTOSCHOLAR_LOG_DIR` | `/tmp` | Directory for log file |

## MCP Config (Claude Code)

Add to `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "cryptoscholar": {
      "command": "python",
      "args": ["-m", "cryptoscholar"],
      "env": {
        "ANTHROPIC_API_KEY": "your_key_here"
      }
    }
  }
}
```

## Architecture

```
Claude → MCP call
           ↓
        server.py (FastMCP)
           ↓
     tools/analyze.py
           ↓
     data/coingecko.py  →  CoinGecko free API
           ↓
     ta/indicators.py   (pandas-ta + custom)
           ↓
     ta/regime.py       (rule-based, v1)
           ↓
     ta/scoring.py      (TSS computation)
           ↑
     tools/debate.py    →  Anthropic API (Claude)
```

## Key Files

| File | Purpose |
|------|---------|
| `cryptoscholar/server.py` | MCP entry point, tool registration |
| `cryptoscholar/data/coingecko.py` | CoinGecko client, OHLCV reconstruction |
| `cryptoscholar/ta/indicators.py` | All TA calculations |
| `cryptoscholar/ta/scoring.py` | TSS scoring (trend + momentum + RS) |
| `cryptoscholar/ta/regime.py` | Regime classification |
| `cryptoscholar/tools/analyze.py` | analyze_coin orchestrator |
| `cryptoscholar/tools/rank.py` | rank_coins orchestrator |
| `cryptoscholar/tools/debate.py` | Claude API debate generation |
| `ROADMAP.md` | Future version plans |

## Data Flow: analyze_coin("BTC")

1. Map "BTC" → "bitcoin" via SYMBOL_TO_ID
2. GET `/coins/bitcoin/market_chart?days=90&interval=daily` → price + volume history
3. GET `/coins/markets?ids=bitcoin` → current price, market cap, 24h change
4. Reconstruct daily OHLCV DataFrame (open≈prev_close, high/low approximated)
5. Compute all indicators via pandas-ta + custom functions
6. Classify regime (rule-based ATR + BBW percentile)
7. Compute TSS (40% EMA trend + 30% RSI/MACD/ADX + 30% RS vs BTC)
8. Return structured dict

## CoinGecko Rate Limits
- Free tier: ~10-30 req/min
- TTL cache: 5 min per endpoint+params
- rank_coins: 0.5s sleep between coins
- Retry: 3 attempts with exponential backoff

## Scoring Formulas

**TSS (Trend Strength Score, 0-100)**
= 0.4 × trend_component + 0.3 × momentum_component + 0.3 × rs_score

**Trend component** (EMA alignment):
- EMA20 > EMA50: +30
- EMA50 > EMA200: +30
- EMA20 > EMA200: +20
- Weekly EMA slope > 3%: +20; > 0%: +10; < -3%: -10

**Momentum component** (base 50):
- RSI 50-70: +25; RSI ≥70: +10; RSI 40-50: -10; RSI <40: -25
- MACD line > signal: +15; else: -15
- ADX > 25: +10; ADX < 20: -10

**Regime:**
- high_vol: ATR and BBW both in top 30% of 90-day range
- low_vol: ATR and BBW both in bottom 30%
- mid_vol: everything else
