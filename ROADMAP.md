# CryptoScholar Roadmap

## v0.1.0 (released)
- analyze_coin: full TA analysis via CoinGecko free API
- rank_coins: TSS-based ranking for multiple coins
- debate: Claude AI bull/bear synthesis
- Rule-based regime detection (low/mid/high vol)

## v0.2.0 (released)
- Binance public API for real OHLCV candles (1,200 req/min, no auth required); CoinGecko retained as fallback
- `market_context` tool: BTC dominance trend + velocity, ETH/BTC ratio trend, TOTAL3 market cap
- ARS (Altcoin Rotation Score) — composite of BTC dominance direction, ETH/BTC trend, TOTAL3
- MRS (Market Readiness Score) — 40% BTC trend + 30% ARS + 30% stablecoin supply trend
- Stablecoin supply trend via DefiLlama public API
- `data_source` field in analyze_coin output (`binance` or `coingecko`)

## v0.3.0 (current)
- 4H candles from Binance; MTF alignment bonus/penalty in TSS (±3 pts from 4H EMA-20 vs EMA-50)
- RSI divergence detection (bullish/bearish/none) added to `analyze_coin` and `rank_coins`
- `top_coins` tool — auto-fetch top 50 by market cap, filter stablecoins, rank by TSS
- Parallel batch ranking via `ThreadPoolExecutor` (8 workers) — handles 50+ coins efficiently
- `SYMBOL_TO_ID` map expanded from 20 → 65 entries covering the full top-50 universe

## v0.4.0 — Watchlist + Alerts
- Persistent watchlist (SQLite) with named lists
- Claude-triggered alerts when regime changes or TSS crosses a user-defined threshold
- Scheduled background analysis with digest summary

## v0.5.0 — HMM Volatility Regime
- Replace rule-based regime with 3-state GaussianHMM (hv_20, atr_14, bb_width)
- Auto-retrain every 7 days on accumulated price history
- Persist trained model to ~/.cryptoscholar/hmm_model.pkl
- `train_regime_model` tool for manual retrain

## v0.6.0 — Analysis Report Generation
- `generate_report` tool: 3-stage Cluster → Write → Assemble pipeline
- Stage 1: cluster related signals/indicators into thematic groups per coin
- Stage 2: write structured sections (trend, momentum, on-chain context, risks)
- Stage 3: assemble into a formatted markdown report with key stats table
- Support for multi-coin comparison reports (e.g. "compare BTC, ETH, SOL")
- Optional: output as JSON for downstream consumption

## v0.7.0 — Research & News Context
- `research_coin` tool: web search (DuckDuckGo + Jina reader) for news and narratives
- Jina AI reader (`r.jina.ai`) converts URLs to clean markdown for LLM ingestion
- Smart search cache: skip redundant searches when recent results are still relevant
- Integrate research context into `analyze_coin` and `debate` outputs
- Local result store (SQLite) for deduplication and re-use within session
