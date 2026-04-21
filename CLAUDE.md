# CryptoScholar — Project Guide

## What it is
Open-source MCP server — 14 crypto TA + watchlist tools for Claude.
Path: `/root/projects/cryptoscholar` | GitHub: `github.com/cryptographer11/cryptoscholar` | v0.6.0
Registered in `~/.claude.json` mcpServers.

## Stack
Python 3.11 · FastMCP · pandas-ta · httpx · SQLite (watchlist) · pytest (183 tests)

## Key File Paths
| File | Purpose |
|------|---------|
| `cryptoscholar/server.py` | MCP entry — all 13 tools registered |
| `cryptoscholar/tools/analyze.py` | `analyze_coin` — full TA orchestration |
| `cryptoscholar/tools/rank.py` | `rank_coins` — parallel TSS ranking |
| `cryptoscholar/tools/top_coins.py` | `top_coins` — top N by market cap |
| `cryptoscholar/tools/correlate.py` | `correlate_coins` — Pearson correlation matrix |
| `cryptoscholar/tools/watchlist.py` | 7 watchlist/alert tools |
| `cryptoscholar/tools/debate.py` | `debate` — Claude API bull/bear synthesis |
| `cryptoscholar/tools/market_context.py` | `market_context` — ARS, MRS, F&G |
| `cryptoscholar/data/binance.py` | Primary OHLCV + 4H + funding rate |
| `cryptoscholar/data/coingecko.py` | Fallback OHLCV; 2s rate limiter; top_coins API |
| `cryptoscholar/data/alternative_me.py` | Fear & Greed Index (1-hr TTL cache) |
| `cryptoscholar/data/defillama.py` | Stablecoin supply history |
| `cryptoscholar/data/watchlist_db.py` | SQLite layer — `~/.cryptoscholar/watchlist.db` |
| `cryptoscholar/ta/indicators.py` | EMA, RSI, MACD, ADX, OBV trend, RSI divergence |
| `cryptoscholar/ta/scoring.py` | TSS = 40% trend + 30% momentum + 30% RS ± MTF ± OBV |
| `cryptoscholar/ta/regime.py` | HMM-first regime classifier with rule-based fallback |
| `cryptoscholar/ta/hmm_regime.py` | GaussianHMM train/persist/classify/auto-retrain logic |
| `cryptoscholar/tools/train_regime.py` | `train_regime_model` MCP tool |
| `cryptoscholar/market/context.py` | BTC dom, ETH/BTC, TOTAL3, F&G, ARS, MRS |

## Key Decisions
- Binance primary, CoinGecko fallback for OHLCV; CoinGecko for non-OHLCV market_context
- EMA-200 needs 250+ days — CoinGecko fetches 250, Binance fetches 300
- TSS bonuses are additive post-base (MTF ±3, OBV ±2), clamped 0–100
- `debate` calls Claude API only — no other providers
- `alert_check` uses `rank_coins` (parallel) not individual `analyze_coin` calls
- SQLite `:memory:` creates isolated DBs per connection — tests use `tmp_path` fixture
- GitHub fine-grained PAT can't open PRs on third-party repos — use classic PAT

## Tools (14 total)
`analyze_coin` · `rank_coins` · `top_coins` · `correlate_coins` · `debate` · `market_context`
`watchlist_add` · `watchlist_remove` · `watchlist_show` · `watchlist_lists` · `watchlist_scan`
`alert_set` · `alert_check` · `train_regime_model`

## Directory Submissions
| Directory | Status |
|-----------|--------|
| appcypher/awesome-mcp-servers | Done (PR #737) |
| mcpservers.org / mcp.so / Glama / Cline | Done |
| Claude Plugins Marketplace | Submitted |
| Official MCP Registry | Pending (needs PyPI + mcp-publisher OAuth) |
| PulseMCP | Auto (ingests from Official MCP Registry) |
| Smithery | Skip (requires hosted HTTP) |

## Key Decisions
- HMM trained on BTC data (market representative); classifies any coin's current features
- `classify_regime` string signature preserved — `classify_regime_full` returns `(label, source)` for callers that need provenance
- HMM auto-retrains on first `analyze_coin` / `rank_coins` call after 7-day stale threshold using current coin's data

## Recent Changes

### 2026-04-21 MYT — v0.6.0 HMM Regime
- `cryptoscholar/ta/hmm_regime.py` (new): GaussianHMM 3-state model, train/persist/classify/retrain
- `cryptoscholar/ta/regime.py`: HMM-first with rule-based fallback; `classify_regime_full()` added
- `cryptoscholar/ta/indicators.py`: `_hv_series` and `_atr_pct_series` added to indicators dict
- `cryptoscholar/tools/train_regime.py` (new): `train_regime_model` MCP tool
- `analyze_coin` output gains `regime_source` field ('hmm' or 'rule_based')
- `hmmlearn>=0.3.0` + `scikit-learn>=1.4.0` added to dependencies
- 205 tests passing (22 new)

### 2026-04-20 MYT
- v0.5.0: watchlist_db.py (SQLite CRUD), watchlist.py (7 tools), 40 new tests → 183 total
- `alert_check` runs rank_coins in parallel on alerted symbols, updates last_tss/last_regime baseline
- SQLite `:memory:` gotcha: each `_connect()` opens isolated DB — test fixture must use tmp_path file

### 2026-04-20 MYT (earlier)
- v0.4.0: OBV trend (±2 TSS), funding rate via Binance fapi, Fear & Greed (Alternative.me, ±5 MRS)
- Smart top_coins filtering: _WRAPPED_TOKENS frozenset + _MIN_VOLUME_USD=$10M
- correlate_coins tool: Pearson matrix, high-corr clusters (>0.85), uncorrelated pairs (<0.30)
- ROADMAP updated: v0.5→v0.8 shifted, v0.4 = Signal Depth & Breadth
