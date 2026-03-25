# CryptoScholar

> **Crypto technical analysis, directly inside Claude.** CryptoScholar is a Model Context Protocol (MCP) server that gives Claude real-time TA capabilities — no chart-switching, no copy-pasting data, no context loss.

Ask Claude *"Is SOL set up for a swing trade?"* and it fetches live data, runs a full indicator suite, scores it, and delivers a grounded bull/bear debate — all in one response.

---

## What it does

CryptoScholar exposes 3 MCP tools that Claude can call natively:

### `analyze_coin`
Full technical analysis snapshot for any coin. Fetches 250 days of OHLCV from CoinGecko and computes:

| Indicator | Details |
|-----------|---------|
| **Trend** | EMA-20, EMA-50, EMA-200 alignment + weekly EMA slope |
| **Momentum** | RSI-14, MACD (line / signal / histogram), ADX-14 |
| **Volatility** | ATR-14, Bollinger Band width, Historical Volatility (20-day annualised) |
| **Relative Strength** | Coin vs BTC (20-day ratio change) |
| **Regime** | Low / mid / high volatility classification |
| **TSS** | Trend Strength Score — 0–100 composite (40% trend + 30% momentum + 30% RS) |

### `rank_coins`
Pass a list of symbols and get them back ranked by TSS. Useful for quickly identifying the strongest setups across your watchlist.

### `debate`
Claude reads the live TA data and generates a structured bull/bear debate grounded in actual indicator values — not hallucinated opinion. Returns:
- **Bull case** — what the technicals say in favour
- **Bear case** — what could go wrong
- **Bottom line** — one-sentence synthesis

No API key required for market data. Only `ANTHROPIC_API_KEY` is needed for the `debate` tool.

---

## Quick start

**Requirements:** Python 3.11+

```bash
git clone https://github.com/cryptographer11/cryptoscholar.git
cd cryptoscholar
make install
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env (only needed for debate tool)
cryptoscholar
```

### Add to Claude Code

In `~/.claude/settings.json`:

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

Restart Claude Code. You can now ask:
- *"Analyze BTC for me"*
- *"Rank ETH, SOL, AVAX, and LINK by trend strength"*
- *"Give me the bull and bear case for DOGE based on current TA"*

---

## Example output

**`analyze_coin("SOL")`**
```json
{
  "symbol": "SOL",
  "price": 142.30,
  "tss": 74.2,
  "regime": "mid_vol",
  "vrs": 55,
  "ema_alignment": "EMA20 > EMA50 > EMA200 (bullish stack)",
  "rsi_14": 61.4,
  "macd_signal": "bullish crossover",
  "adx_14": 28.1,
  "atr_14": 6.82,
  "hv_20": 68.4,
  "rs_btc": 4.2,
  "bb_width": 0.18,
  "market_cap": 65800000000,
  "change_24h": 2.3
}
```

**`debate("SOL")`**
```json
{
  "bull_case": "SOL is in a full bullish EMA stack with RSI at 61 — healthy momentum without overbought conditions. ADX at 28 confirms trending structure, and relative strength vs BTC is positive at +4.2%, signalling capital rotation into SOL.",
  "bear_case": "Historical volatility at 68% is elevated, and Bollinger Band width is widening — conditions that often precede sharp reversals. A break below EMA-20 would invalidate the current trend structure.",
  "bottom_line": "Technicals are constructive for continuation but volatility is high; position sizing should reflect the risk."
}
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required for the `debate` tool |
| `CRYPTOSCHOLAR_MODEL` | `claude-haiku-4-5-20251001` | Claude model used for debates (swap for Sonnet/Opus for deeper analysis) |
| `CRYPTOSCHOLAR_LOG_DIR` | `/tmp` | Directory for rotating log files |

---

## Supported coins

CryptoScholar ships with a built-in symbol map for 20 major coins (BTC, ETH, SOL, BNB, XRP, ADA, AVAX, LINK, DOGE, DOT, MATIC, UNI, ATOM, LTC, BCH, NEAR, APT, ARB, OP, INJ) and falls back to a CoinGecko search for any other symbol.

---

## Architecture

Stateless by design — no database, no scheduler. Every tool call fetches fresh data.

```
Claude (MCP call)
    └── server.py          FastMCP entry point
         ├── tools/
         │    ├── analyze.py    Orchestrates fetch → indicators → regime → score
         │    ├── rank.py       Runs analyze_coin per symbol, sorts by TSS
         │    └── debate.py     Builds prompt from TA data, calls Claude API
         ├── ta/
         │    ├── indicators.py pandas-ta + custom HV / RS functions
         │    ├── scoring.py    TSS: trend + momentum + relative strength
         │    └── regime.py     Rule-based vol regime (ATR + BBW percentile)
         └── data/
              └── coingecko.py  HTTP client, 5-min TTL cache, OHLCV builder
```

**Data flow for `analyze_coin("BTC")`:**
1. Map symbol → CoinGecko ID (`BTC` → `bitcoin`)
2. Fetch 90-day daily price/volume history + current market data
3. Reconstruct OHLCV DataFrame
4. Compute all indicators via pandas-ta and custom functions
5. Classify regime (ATR + BB width percentile position vs 90-day range)
6. Compute TSS (weighted composite of trend, momentum, RS)
7. Return structured dict to Claude

---

## Development

```bash
make test            # run test suite
make test-parallel   # run tests in parallel (pytest-xdist)
make coverage        # coverage report
make lint-security   # bandit security scan
```

**36 tests, 0 failures.**

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned versions. Highlights:

- **v0.2** — Binance API for real OHLCV + market context (BTC dominance, ARS, MRS, stablecoin supply)
- **v0.3** — Multi-timeframe (4H + weekly), RSI divergence, `top_coins` tool, 50+ coin batch ranking
- **v0.4** — Persistent watchlist + Claude-triggered regime-change and TSS threshold alerts
- **v0.5** — HMM volatility regime (3-state GaussianHMM replacing rule-based classifier)

---

## License

MIT
