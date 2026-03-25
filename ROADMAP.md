# CryptoScholar Roadmap

## v0.1.0 (current)
- analyze_coin: full TA analysis via CoinGecko free API
- rank_coins: TSS-based ranking for multiple coins
- debate: Claude AI bull/bear synthesis
- Rule-based regime detection (low/mid/high vol)

## v0.2.0 — Smarter Regime + Market Context
- Replace rule-based regime with 3-state GaussianHMM (hv_20, atr_14, bb_width); auto-retrain every 7 days
- BTC dominance trend + velocity
- Altcoin Rotation Score (ARS) and Market Readiness Score (MRS)
- Stablecoin supply proxy via DefiLlama

## v0.3.0 — Multi-Timeframe + Scale
- 4H + weekly analysis alongside daily; MTF alignment bonus/penalty in TSS
- RSI divergence detection (bullish/bearish)
- `top_coins` tool — auto-fetch CoinGecko top 50 by market cap and rank them without a manual symbol list
- Batch ranking optimisation to handle 50+ coins without free-tier rate limit issues

## v0.4.0 — Watchlist + Alerts
- Persistent watchlist (SQLite) with named lists
- Claude-triggered alerts when regime changes or TSS crosses a user-defined threshold
- Scheduled background analysis with digest summary
