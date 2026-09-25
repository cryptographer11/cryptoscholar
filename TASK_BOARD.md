# CryptoScholar — Task Board

## In Progress
### v0.7.0 — Analysis Report Generation
- [~]  tool: 3-stage Cluster → Write → Assemble pipeline

## Backlog

- [ ] Upgrade `mcp` SDK 1.26.0 → 2.x. Claude Code (2.1.282+, gradual rollout) opens with the 2026 `server/discover` probe; 1.x logs a harmless "Failed to validate request" stderr WARNING and falls back to `initialize`. Done for lumenar-mcp 2026-09-25 — its `CHANGELOG.md` entry lists what 2.x breaks (`FastMCP` → `MCPServer`, transport params to `run()`, sync tools on worker threads, `python-dotenv`/`httpx` no longer transitive). Open-source package: bumping `mcp>=2` changes the floor for every user, so release-note it. Found 2026-09-25.

### v0.7.0 — Analysis Report Generation
- [ ] `generate_report` tool: 3-stage Cluster → Write → Assemble pipeline
- [ ] Stage 1: cluster related signals/indicators into thematic groups per coin
- [ ] Stage 2: write structured sections (trend, momentum, on-chain context, risks)
- [ ] Stage 3: assemble into formatted markdown report with key stats table
- [ ] Multi-coin comparison reports (e.g. "compare BTC, ETH, SOL")

### v0.8.0 — Research & News Context
- [ ] `research_coin` tool: web search (DuckDuckGo + Jina reader)
- [ ] Jina AI reader (`r.jina.ai`) converts URLs to clean markdown
- [ ] Smart search cache: skip redundant searches when recent results still relevant
- [ ] Integrate research context into `analyze_coin` and `debate` outputs
- [ ] Local result store (SQLite) for deduplication and re-use within session

### Polish (any version)
- [ ] Smoke-test against live APIs (integration test, skipped by default)
- [ ] Publish to PyPI as `cryptoscholar`

## Done

### debate tool — migrated to OmniRoute (2026-07-29)
- [x] `debate` no longer calls Anthropic directly — routes through the self-hosted OmniRoute gateway (`http://localhost:20128`), which was completely broken before (no `ANTHROPIC_API_KEY` was ever configured for this project)
- [x] New `/root/secrets/cryptoscholar.env` (first secret this project has) + `.env` symlink, scoped `OMNIROUTE_API_KEY`
- [x] Default model `auto/smart`; `max_tokens` raised 512 → 2048 after live testing showed reasoning-model overhead was truncating the JSON output (`finish_reason: "length"`)
- [x] Markdown-code-fence stripping added — the live model wraps JSON in ` ```json ` despite instructions not to
- [x] 8 new tests in `tests/test_debate.py` (none existed before) — 230/230 passing full suite
- [x] Verified live end-to-end for BTC and ETH — real bull/bear JSON returned

### v0.6.0 — HMM Volatility Regime (2026-04-21)
- [x] 3-state GaussianHMM trained on hv_20, normalised ATR-14, and BB width features
- [x] Auto-retrain every 7 days on first `analyze_coin` / `rank_coins` call after threshold
- [x] Model persisted to `~/.cryptoscholar/hmm_model.pkl` + metadata JSON
- [x] Rule-based classifier retained as fallback (no model or prediction failure)
- [x] `regime_source` field added to `analyze_coin` output ('hmm' or 'rule_based')
- [x] `train_regime_model` MCP tool for manual retrain (with `force` flag)
- [x] `_hv_series` and `_atr_pct_series` added to indicators for HMM feature extraction
- [x] 22 new tests → 205 total passing

### v0.5.0 — Watchlist + Alerts (2026-04-20)
- [x] Persistent watchlist (SQLite) with named lists
- [x] `watchlist_add`, `watchlist_remove`, `watchlist_show`, `watchlist_lists` tools
- [x] `watchlist_scan` — digest view, ranks all coins in a watchlist by TSS (parallel, 8 workers)
- [x] `alert_set` — TSS threshold (`tss_above` / `tss_below`) or `regime_change` alerts per symbol
- [x] `alert_check` — checks all alerts against live TA, reports triggers, updates stored baseline
- [x] DB at `~/.cryptoscholar/watchlist.db`; override with `CRYPTOSCHOLAR_DATA_DIR` env var
- [x] 40 new tests → 183 total passing

### v0.4.0 — Signal Depth & Breadth (2026-04-20)
- [x] OBV trend added to `analyze_coin`; incorporated as TSS sub-component (±2 pts)
- [x] Binance perpetual funding rate fetched for `analyze_coin`
- [x] Fear & Greed Index (Alternative.me) added to `market_context`; modifies MRS
- [x] Smart `top_coins` filtering: wrapped tokens, low-volume, insufficient history
- [x] `correlate_coins` tool: Pearson matrix, high-corr clusters (>0.85), uncorrelated pairs (<0.30)

### v0.3.0 — Multi-Timeframe + Scale (2026-04-20)
- [x] 4H candles from Binance; MTF alignment bonus/penalty in TSS (±3 pts)
- [x] RSI divergence detection (bullish/bearish/none)
- [x] `top_coins` tool — auto-fetch top 50 by market cap, filter stablecoins, rank by TSS
- [x] Parallel batch ranking via `ThreadPoolExecutor` (8 workers)
- [x] `SYMBOL_TO_ID` map expanded 20 → 65 entries

### v0.2.0 — Binance + Market Context (2026-03-26)
- [x] Binance public API for real OHLCV; CoinGecko retained as fallback
- [x] `market_context` tool: BTC dom, ETH/BTC, TOTAL3, ARS, MRS
- [x] Stablecoin supply trend via DefiLlama
- [x] 71/71 tests passing

### v0.1.0 — Foundation (2026-03-26)
- [x] Project scaffold: pyproject.toml, Makefile, .env.example, ROADMAP.md
- [x] CoinGecko data layer: SYMBOL_TO_ID map, /search fallback, TTL cache, retry
- [x] TA indicators: EMA-20/50/200, RSI, MACD, ADX, ATR, BB, HV-20, RS vs BTC
- [x] Regime detection: rule-based (low/mid/high vol) based on ATR + BBW percentile
- [x] Scoring: TSS = 40% trend + 30% momentum + 30% RS ± MTF ± OBV, clamped 0–100
- [x] MCP tools: `analyze_coin`, `rank_coins`, `debate`
- [x] 36/36 tests passing
- [x] Pushed to GitHub (github.com/cryptographer11/cryptoscholar)
- [x] Registered as MCP server in `~/.claude.json`
- [x] Submitted to appcypher/awesome-mcp-servers (PR #737), mcpservers.org, mcp.so, Glama, Cline
