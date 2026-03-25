# CryptoScholar Roadmap

## v0.1.0 (current)
- analyze_coin: full TA analysis via CoinGecko free API
- rank_coins: TSS-based ranking for multiple coins
- debate: Claude AI bull/bear synthesis
- Rule-based regime detection (low/mid/high vol)

## v0.2.0 — HMM Volatility Regime
- Replace rule-based regime with 3-state GaussianHMM (hv_20, atr_14, bb_width)
- Auto-retrain every 7 days on accumulated price history
- Persist trained model to ~/.cryptoscholar/hmm_model.pkl

## v0.3.0 — Market Context
- BTC dominance trend + velocity
- Altcoin Rotation Score (ARS)
- Stablecoin supply proxy
- Market Readiness Score (MRS)

## v0.4.0 — Multi-timeframe
- 4H + weekly analysis alongside daily
- MTF alignment bonus/penalty in TSS
- Divergence detection (RSI divergence)

## v0.5.0 — Watchlist & Alerts
- Persistent watchlist (SQLite or JSON)
- Claude-triggered alerts when regime changes or TSS crosses threshold
- Scheduled background analysis
