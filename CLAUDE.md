# CryptoScholar — Project Guide

## What it is
Open-source MCP server — 14 crypto TA + watchlist tools for Claude.
Path: `/root/projects/cryptoscholar` | GitHub: `github.com/cryptographer11/cryptoscholar` | v0.6.0
Registered in `~/.claude.json` mcpServers.

## Stack
Python 3.11 · FastMCP · pandas-ta · httpx · SQLite (watchlist) · pytest (230 tests)

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
- `debate` routes through the self-hosted OmniRoute gateway (`OMNIROUTE_API_KEY`), not a direct provider SDK — see Recent Changes 2026-07-29
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

