# CryptoScholar Roadmap

## v0.1.0 (current)
- analyze_coin: full TA analysis via CoinGecko free API
- rank_coins: TSS-based ranking for multiple coins
- debate: Claude AI bull/bear synthesis
- Rule-based regime detection (low/mid/high vol)

## v0.2.0 — Better Data + Market Context
- Switch OHLCV data source from CoinGecko to Binance public API (real candles, 1,200 req/min, no auth)
- BTC dominance trend + velocity (CoinGecko /global, kept for macro context)
- Altcoin Rotation Score (ARS) — BTC dominance trend, ETH/BTC ratio, TOTAL3 proxy
- Market Readiness Score (MRS) — composite of trend signal, ARS, and VRS
- Stablecoin supply proxy via DefiLlama

## v0.3.0 — Multi-Timeframe + Scale
- 4H + weekly analysis alongside daily; MTF alignment bonus/penalty in TSS
- RSI divergence detection (bullish/bearish)
- `top_coins` tool — auto-fetch top 50 by market cap and rank without a manual symbol list
- Batch ranking optimisation to handle 50+ coins efficiently

## v0.4.0 — Watchlist + Alerts
- Persistent watchlist (SQLite) with named lists
- Claude-triggered alerts when regime changes or TSS crosses a user-defined threshold
- Scheduled background analysis with digest summary

## v0.5.0 — HMM Volatility Regime
- Replace rule-based regime with 3-state GaussianHMM (hv_20, atr_14, bb_width)
- Auto-retrain every 7 days on accumulated price history
- Persist trained model to ~/.cryptoscholar/hmm_model.pkl
- `train_regime_model` tool for manual retrain
