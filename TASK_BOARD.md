# CryptoScholar — Task Board

## In Progress
<!-- nothing -->

## Backlog

### v0.3.0 — Multi-Timeframe + Scale
- [ ] 4H + weekly OHLCV via Binance klines
- [ ] MTF alignment bonus/penalty in TSS (+3/-3)
- [ ] RSI divergence detection (bullish/bearish)
- [ ] `top_coins` tool — fetch top 50 by market cap, rank automatically
- [ ] Batch ranking optimisation (50+ coins)

### v0.4.0 — Watchlist + Alerts
- [ ] Persistent watchlist (SQLite)
- [ ] Claude-triggered alerts on regime change or TSS threshold cross
- [ ] Scheduled digest summary

### v0.5.0 — HMM Volatility Regime
- [ ] Replace rule-based regime with 3-state GaussianHMM
- [ ] Auto-retrain every 7 days, persist to ~/.cryptoscholar/hmm_model.pkl
- [ ] Add `train_regime_model` MCP tool for manual retrain

### Polish (any version)
- [ ] Smoke-test against live APIs (integration test, skipped by default)
- [ ] Publish to PyPI as `cryptoscholar`

## Done (2026-03-26)
- [x] Project scaffold: pyproject.toml, Makefile, .env.example, ROADMAP.md
- [x] CoinGecko data layer: SYMBOL_TO_ID map, /search fallback, TTL cache, retry
- [x] TA indicators: EMA-20/50/200, RSI, MACD, ADX, ATR, BB, HV-20, RS vs BTC
- [x] Regime detection: rule-based (low/mid/high vol) based on ATR + BBW percentile
- [x] Scoring: score_trend_component, score_momentum_component, compute_tss (40/30/30)
- [x] MCP tools: analyze_coin, rank_coins, debate (Claude API)
- [x] Tests: 36/36 passing (test_indicators.py, test_scoring.py)
- [x] README.md, ROADMAP.md
- [x] Thread-safe global rate limiter in coingecko.py (2s min interval, 60s on 429)
- [x] Increased price history fetch from 90→250 days to fix EMA-200 returning None
- [x] Pushed to GitHub (github.com/cryptographer11/cryptoscholar)
- [x] Registered as MCP server in ~/.claude/.mcp.json
- [x] Submitted to appcypher/awesome-mcp-servers (PR #737)
- [x] Submitted to mcpservers.org
- [x] Roadmap restructured: v0.2 Binance API, v0.3 MTF, v0.4 watchlist, v0.5 HMM
- [x] Screenshots section added to README (docs/rank_coins_xrp_bear.png, docs/sol_analysis.png)
- [x] v0.2.0: data/binance.py — Binance klines client, real OHLCV, no auth
- [x] v0.2.0: data/defillama.py — DefiLlama stablecoin supply history
- [x] v0.2.0: data/coingecko.py — fetch_global_market_chart() added
- [x] v0.2.0: market/context.py — ARS, MRS, btc_trend_score, stablecoin_score
- [x] v0.2.0: tools/market_context.py — new market_context MCP tool (4th tool)
- [x] v0.2.0: analyze.py — Binance first, CoinGecko fallback, data_source field
- [x] v0.2.0: rank.py — Binance BTC pre-fetch, removed stale sleep
- [x] v0.2.0: server.py — market_context registered, version bumped
- [x] v0.2.0: 71/71 tests passing (35 new in test_market_context.py)
