# CryptoScholar

> **Crypto technical analysis, directly inside Claude.** CryptoScholar is a Model Context Protocol (MCP) server that gives Claude real-time TA capabilities — no chart-switching, no copy-pasting data, no context loss.

Ask Claude *"Is SOL set up for a swing trade?"* and it fetches live data from Binance, runs a full indicator suite, scores it, and delivers a grounded bull/bear debate — all in one response.

---

## What it does

CryptoScholar exposes 4 MCP tools that Claude can call natively:

### `analyze_coin`
Full technical analysis snapshot for any coin. Fetches 300 days of real OHLCV candles from Binance (with CoinGecko fallback) and computes:

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

### `market_context`
Macro market signals to frame individual coin analysis. Uses CoinGecko global data and DefiLlama stablecoin supply. Returns:

| Signal | Description |
|--------|-------------|
| **BTC dominance** | Current % and 30-day change — falling = capital rotating to alts |
| **ETH/BTC ratio** | 20-day trend — rising = broadening rally |
| **TOTAL3** | Altcoin market cap (ex-BTC, ex-ETH) 30-day change |
| **Stablecoin supply** | Total stablecoin market cap and 30-day trend (rising = more buying powder) |
| **ARS** | Altcoin Rotation Score 0–100 — how favourable macro is for alts |
| **MRS** | Market Readiness Score 0–100 — overall market readiness for upside moves |

### `debate`
Claude reads the live TA data and generates a structured bull/bear debate grounded in actual indicator values — not hallucinated opinion. Returns:
- **Bull case** — what the technicals say in favour
- **Bear case** — what could go wrong
- **Bottom line** — one-sentence synthesis

No API key required for market data. Only `ANTHROPIC_API_KEY` is needed for the `debate` tool.

---

## What's new in v0.3.0

- **Multi-timeframe analysis** — fetches 4H candles alongside daily. If 4H EMA-20 > EMA-50, TSS gets a +3 bonus; bearish 4H alignment subtracts 3. Gives a finer-grained entry signal.
- **RSI divergence detection** — `analyze_coin` and `rank_coins` now return a `rsi_divergence` field: `bullish`, `bearish`, or `none`. Bullish divergence (price lower low + RSI higher low) can signal a trend reversal before it appears in EMAs.
- **`top_coins` tool** — new fifth tool. Fetches the top 50 coins by market cap from CoinGecko, filters out stablecoins automatically, and returns them ranked by TSS. No symbol list needed.
- **Batch ranking optimisation** — `rank_coins` now analyses coins in parallel (up to 8 workers via `ThreadPoolExecutor`). A 50-coin ranking that previously ran sequentially now completes in a fraction of the time.
- **Expanded symbol map** — `SYMBOL_TO_ID` grows from 20 → 65 entries, covering the full top-50 market cap universe. Fewer fallback API search calls when using `top_coins`.

---

## What's new in v0.2.0

- **Real OHLCV candles** — price data now comes from Binance's public API (300 days, no API key required). CoinGecko is kept as automatic fallback for any symbol not on Binance. The `analyze_coin` output includes a `data_source` field so you can see which was used.
- **`market_context` tool** — a new fourth tool that gives Claude a macro picture before diving into individual coins. Returns BTC dominance trend, ETH/BTC ratio, TOTAL3 altcoin market cap, and stablecoin supply from DefiLlama.
- **ARS (Altcoin Rotation Score)** — 0–100 composite scoring whether the macro environment favours alts. Factors in BTC dominance direction, ETH/BTC trend, and TOTAL3 momentum.
- **MRS (Market Readiness Score)** — 0–100 overall market readiness for upside. Weighted: 40% BTC trend + 30% ARS + 30% stablecoin supply trend.

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

In `~/.claude/.mcp.json`:

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
- *"What does the macro market look like right now?"*
- *"Give me the bull and bear case for DOGE based on current TA"*

---

## Screenshots

<p align="center">
  <a href="docs/rank_coins_xrp_bear.png">
    <img src="docs/rank_coins_xrp_bear.png" width="800" style="max-width: 100%">
  </a>
  <br>
  <em>Ranking BTC, ETH, and XRP by Trend Strength Score — then drilling into the bear case for XRP</em>
</p>

`rank_coins` scores each coin across trend, momentum, and relative strength vs BTC and returns them sorted by TSS. Here BTC leads at 63.7, ETH at 53.0, and XRP trails at 47.8 — all in `low_vol` regime. Asking for the XRP bear case immediately after surfaces the specific technical reasons: a steepest weekly EMA slope, faltering MACD, and ETH underperformance vs BTC flagged as early institutional exit pressure.

---

<p align="center">
  <a href="docs/sol_analysis.png">
    <img src="docs/sol_analysis.png" width="800" style="max-width: 100%">
  </a>
  <br>
  <em>Full technical analysis snapshot for SOL — indicators, scoring, and bear case in one response</em>
</p>

`analyze_coin` returns a structured breakdown covering EMA stack alignment, RSI, MACD, ADX, ATR, Bollinger Band width, and relative strength vs BTC — all computed from 300 days of live Binance candles. Claude then reads the raw indicator values to generate a grounded bear case: EMA-200 resistance, weekly slope steepening, and MACD crossdown risk. No chart-switching, no copy-pasting — the full TA context is already in Claude's window.

---

## Example output

**`market_context()`**
```json
{
  "btc_price_30d_change_pct": -8.4,
  "btc_dominance_current": 54.2,
  "btc_dominance_30d_change_pct": 2.1,
  "eth_btc_20d_change_pct": -5.3,
  "total3_30d_change_pct": -14.6,
  "stablecoin_supply_usd": 196500000000,
  "stablecoin_30d_change_pct": 2.8,
  "btc_trend_score": 35.0,
  "ars": 28.5,
  "stablecoin_score": 60.0,
  "mrs": 42.3
}
```

**`analyze_coin("SOL")`**
```json
{
  "symbol": "SOL",
  "data_source": "binance",
  "price": 142.30,
  "tss": 74.2,
  "regime": "mid_vol",
  "vrs": 55,
  "ema_alignment": "full_bull",
  "indicators": {
    "rsi_14": 61.4,
    "macd_hist": 0.42,
    "adx_14": 28.1,
    "atr_14": 6.82,
    "hv_20": 68.4,
    "rs_btc": 4.2,
    "bb_width": 0.18
  }
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

CryptoScholar works with any coin listed on CoinGecko or Binance — just pass the ticker symbol. No configuration needed.

A built-in symbol map covers 20 major coins for instant resolution (BTC, ETH, SOL, BNB, XRP, ADA, AVAX, LINK, DOGE, DOT, MATIC, UNI, ATOM, LTC, BCH, NEAR, APT, ARB, OP, INJ). For anything outside that list, CryptoScholar automatically queries CoinGecko's search API to resolve the symbol and falls back to CoinGecko OHLCV if the coin isn't available on Binance.

In practice: if it trades somewhere and has a CoinGecko listing, it will work.

---

## Architecture

Stateless by design — no database, no scheduler. Every tool call fetches fresh data.

```
Claude (MCP call)
    └── server.py              FastMCP entry point
         ├── tools/
         │    ├── analyze.py        Orchestrates fetch → indicators → regime → score
         │    ├── rank.py           Runs analyze_coin per symbol, sorts by TSS
         │    ├── debate.py         Builds prompt from TA data, calls Claude API
         │    └── market_context.py ARS + MRS + macro signals
         ├── ta/
         │    ├── indicators.py     pandas-ta + custom HV / RS functions
         │    ├── scoring.py        TSS: trend + momentum + relative strength
         │    └── regime.py         Rule-based vol regime (ATR + BBW percentile)
         ├── market/
         │    └── context.py        BTC dominance, ETH/BTC, TOTAL3, ARS, MRS
         └── data/
              ├── binance.py        Binance klines client (1,200 req/min, no auth)
              ├── coingecko.py      CoinGecko client, 5-min TTL cache, OHLCV builder
              └── defillama.py      DefiLlama stablecoin supply history
```

**Data flow for `analyze_coin("SOL")`:**
1. Map symbol → CoinGecko ID (`SOL` → `solana`)
2. Fetch 300-day OHLCV from Binance (`SOLUSDT` klines); fall back to CoinGecko if unavailable
3. Compute all indicators via pandas-ta and custom functions
4. Classify regime (ATR + BB width percentile position vs historical range)
5. Compute TSS (weighted composite of trend, momentum, RS vs BTC)
6. Fetch current market data (price, market cap, 24h change) from CoinGecko
7. Return structured dict to Claude

**Data flow for `market_context()`:**
1. Fetch total market cap history (30d) from CoinGecko `/global/market_cap_chart`
2. Fetch BTC and ETH market chart history (30d) from CoinGecko
3. Fetch stablecoin supply history from DefiLlama
4. Compute BTC dominance trend, ETH/BTC ratio trend, TOTAL3 change
5. Score into ARS (altcoin rotation) and MRS (market readiness)

---

## Development

```bash
make test            # run test suite
make test-parallel   # run tests in parallel (pytest-xdist)
make coverage        # coverage report
make lint-security   # bandit security scan
```

**71 tests, 0 failures.**

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned versions. Highlights:

- **v0.3** ✅ — Multi-timeframe (4H), RSI divergence, `top_coins` tool, parallel batch ranking
- **v0.4** — Persistent watchlist + Claude-triggered regime-change and TSS threshold alerts
- **v0.5** — HMM volatility regime (3-state GaussianHMM replacing rule-based classifier)
- **v0.6** — `generate_report` tool: cluster → write → assemble pipeline for formatted markdown reports
- **v0.7** — `research_coin` tool: web search + Jina reader for news and narrative context

---

## License

MIT
