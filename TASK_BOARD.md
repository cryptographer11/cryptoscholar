# CryptoScholar — Task Board

## In Progress
<!-- nothing -->

## Backlog

### v0.2.0 — HMM Volatility Regime
- [ ] Replace rule-based regime with 3-state GaussianHMM (see ROADMAP.md)
- [ ] Auto-retrain every 7 days, persist to ~/.cryptoscholar/hmm_model.pkl
- [ ] Add `train_regime_model` MCP tool for manual retrain

### v0.2.0 — Polish
- [ ] Add `conftest.py` filterwarnings for pandas_ta Pandas4Warning
- [ ] Smoke-test against live CoinGecko API (integration test, skipped by default)
- [ ] Publish to PyPI as `cryptoscholar`

### v0.3.0 — Market Context
- [ ] BTC dominance trend + velocity from CoinGecko /global history
- [ ] Altcoin Rotation Score (ARS)
- [ ] Market Readiness Score (MRS)

## Done (2026-03-26)
- [x] Project scaffold: pyproject.toml, Makefile, .env.example, ROADMAP.md
- [x] CoinGecko data layer: SYMBOL_TO_ID map, /search fallback, TTL cache, retry
- [x] TA indicators: EMA-20/50/200, RSI, MACD, ADX, ATR, BB, HV-20, RS vs BTC
- [x] Regime detection: rule-based (low/mid/high vol) based on ATR + BBW percentile
- [x] Scoring: score_trend_component, score_momentum_component, compute_tss (40/30/30)
- [x] MCP tools: analyze_coin, rank_coins, debate (Claude API)
- [x] Tests: 36/36 passing (test_indicators.py, test_scoring.py)
- [x] README.md, ROADMAP.md
