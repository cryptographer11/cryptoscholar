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

## v0.3.0 (released)
- 4H candles from Binance; MTF alignment bonus/penalty in TSS (±3 pts from 4H EMA-20 vs EMA-50)
- RSI divergence detection (bullish/bearish/none) added to `analyze_coin` and `rank_coins`
- `top_coins` tool — auto-fetch top 50 by market cap, filter stablecoins, rank by TSS
- Parallel batch ranking via `ThreadPoolExecutor` (8 workers) — handles 50+ coins efficiently
- `SYMBOL_TO_ID` map expanded from 20 → 65 entries covering the full top-50 universe

## v0.4.0 (released) — Signal Depth & Breadth
- **Volume / OBV confirmation** — On-Balance Volume added to `analyze_coin`; OBV trend incorporated as a TSS sub-component (rising OBV on uptrend = confirmation bonus; divergence = penalty)
- **Funding rates** — Binance perpetual funding rate fetched for `analyze_coin`; positive extreme = over-leveraged longs (bearish signal), negative extreme = over-leveraged shorts (contrarian bullish)
- **Fear & Greed Index** — Alternative.me daily F&G score added to `market_context`; extreme fear / greed modifier applied to MRS (same logic as AltFlow)
- **Smart `top_coins` filtering** — Beyond stablecoin exclusion: filter wrapped tokens (WBTC, WETH, stETH, cbBTC), low-liquidity coins (24h volume < threshold), and coins with <30 days of OHLCV history (insufficient for TSS)
- **Correlation tool** — `correlate_coins` tool: given a list of symbols, returns a pairwise Pearson correlation matrix of 30-day daily returns; highlights high-correlation clusters (>0.85) and uncorrelated pairs (<0.3)

## v0.5.0 (current) — Watchlist + Alerts
- Persistent watchlist (SQLite) with named lists — `watchlist_add`, `watchlist_remove`, `watchlist_show`, `watchlist_lists`
- `watchlist_scan` — digest view: ranks all coins in a watchlist by TSS on-demand (parallel, up to 8 workers)
- `alert_set` — set TSS threshold (`tss_above` / `tss_below`) or `regime_change` alerts per symbol
- `alert_check` — checks all alerts against live TA data, reports which triggered, updates stored baseline for drift tracking
- DB at `~/.cryptoscholar/watchlist.db`; override with `CRYPTOSCHOLAR_DATA_DIR` env var

## v0.6.0 (released) — HMM Volatility Regime
- 3-state GaussianHMM trained on hv_20, normalised ATR-14, and BB width — replaces percentile rule-based classifier
- Auto-retrains every 7 days on first `analyze_coin` / `rank_coins` call after threshold
- Model persisted to `~/.cryptoscholar/hmm_model.pkl`; survives server restarts
- Rule-based classifier retained as silent fallback (no model or prediction failure)
- `regime_source` field added to `analyze_coin` output (`"hmm"` or `"rule_based"`)
- `train_regime_model` tool (14th tool) for manual retrain with optional `force` flag

## v0.7.0 — Analysis Report Generation
- `generate_report` tool: 3-stage Cluster → Write → Assemble pipeline
- Stage 1: cluster related signals/indicators into thematic groups per coin
- Stage 2: write structured sections (trend, momentum, on-chain context, risks)
- Stage 3: assemble into a formatted markdown report with key stats table
- Support for multi-coin comparison reports (e.g. "compare BTC, ETH, SOL")
- Optional: output as JSON for downstream consumption

## v0.8.0 — Research & News Context
- `research_coin` tool: web search (DuckDuckGo + Jina reader) for news and narratives
- Jina AI reader (`r.jina.ai`) converts URLs to clean markdown for LLM ingestion
- Smart search cache: skip redundant searches when recent results are still relevant
- Integrate research context into `analyze_coin` and `debate` outputs
- Local result store (SQLite) for deduplication and re-use within session

## v0.9.0 — Market Structure Classification
One new field in `analyze_coin`. No new tools, no UI.

- **Swing point detection** — identify pivot highs/lows from daily OHLCV (configurable lookback, default 5-bar each side)
- **Market structure** — classify as `"uptrend"` (HH+HL), `"downtrend"` (LH+LL), or `"ranging"`; added as `market_structure` field alongside `ema_alignment`
- Swing-based classification is less lag-sensitive than EMAs; provides independent structural confirmation

## v1.0.0 — Support & Resistance Zones
Depends on v0.9.0 swing points.

- **S/R zone clustering** — group swing pivots within ATR proximity into named zones; output `support_zones` and `resistance_zones` lists (each: `{"price": float, "strength": int}`) in `analyze_coin`
- `strength` = number of touches; zones with 3+ touches flagged as key levels

## v1.1.0 — Setup Confluence Score
One new integer field. Depends on v0.9.0 + v1.0.0 output being present.

- **`setup_score`** (1–5) — counts how many signals align: EMA alignment, MTF, OBV trend, RSI divergence, market structure, S/R proximity; added to `analyze_coin` and `rank_coins` output
- Complements TSS (trend strength) — setup_score measures trade *readiness*, TSS measures trend *quality*
- Also surfaced in `watchlist_scan` digest

## v1.2.0 — Trade Plan Block
Depends on v1.0.0 S/R zones + ATR already being computed.

- **`trade_plan`** dict added to `analyze_coin` output: `entry_zone`, `take_profit`, `stop_loss`, `risk_reward_ratio`
- Entry = nearest S/R zone on the trend side; TP = next S/R zone beyond; SL = ATR-1.5× beyond entry zone
- Returns `null` when market structure is `"ranging"` or S/R data is insufficient

## v1.3.0 — Pi Cycle & LLM Brief
Two independent additions; small enough to ship together.

- **Pi Cycle indicator** — 111-day EMA vs 2×350-day EMA; historically signals BTC macro tops; added to `market_context` as `pi_cycle_signal` (`"neutral"` / `"approaching"` / `"crossed"`)
- **`brief` tool** — single-call Claude Haiku summary of a coin's setup (one paragraph, trade-plan focused); lighter than `debate`; uses `analyze_coin` data as input; no extra API calls

## v1.4.0 — EV Filter
Depends on v1.2.0 trade plan block.

- **Expected value gate** — `ev = setup_score × estimated_R / risk_R`; added as `ev_score` float to `analyze_coin` output
- Negative EV flagged as `ev_signal: "avoid"`; positive EV as `"valid"`
- Requires `trade_plan` block to be non-null; otherwise `ev_score: null`

## v1.5.0 — Walk-Forward Backtesting
Most complex feature. Standalone new tool.

- **`backtest_strategy` tool** — walk-forward simulation on historical OHLCV; entry signal = TSS > threshold + setup_score ≥ N; resolves TP/SL on subsequent candles
- Fee model: configurable round-trip (default 0.1%)
- Returns: per-trade log, win rate, avg fee-adjusted R, max drawdown; no UI — structured dict output only
- Accepts any symbol with ≥180 days of history
