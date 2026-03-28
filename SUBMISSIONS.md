# CryptoScholar — Directory Submissions

## Status

| Directory | Status | Notes |
|-----------|--------|-------|
| appcypher/awesome-mcp-servers | DONE | PR #737 |
| mcpservers.org | DONE | Submitted |
| Official MCP Registry | TODO — YOU | Needs `mcp-publisher` CLI + PyPI |
| PulseMCP | AUTO | Pulls from Official MCP Registry |
| Smithery | TODO — YOU | Needs account login |
| mcp.so | TODO — YOU | Needs account login |
| Glama | TODO — YOU | Needs GitHub OAuth |
| Cline Marketplace | TODO — YOU | Needs GitHub account to open issue |
| Claude Plugins Marketplace | TODO — YOU | Needs claude.ai login |

---

## 1. Official MCP Registry (highest priority — unlocks PulseMCP auto-listing)

```bash
# Install mcp-publisher
brew install mcp-publisher
# OR download from https://github.com/modelcontextprotocol/registry/releases

# Publish to PyPI first (if not already)
cd /root/projects/cryptoscholar
python -m build
twine upload dist/*

# Then register on Official MCP Registry
mcp-publisher init       # generates server.json
mcp-publisher login github  # browser OAuth — you complete this
mcp-publisher publish
```

**server.json** (run `mcp-publisher init` then fill in):
```json
{
  "name": "io.github.cryptographer11/cryptoscholar",
  "displayName": "CryptoScholar",
  "description": "Crypto technical analysis inside Claude. Live TA from Binance, TSS scoring, macro context (ARS/MRS), and grounded bull/bear debate.",
  "version": "0.2.0",
  "repository": "https://github.com/cryptographer11/cryptoscholar",
  "packages": [{ "registry": "pypi", "name": "cryptoscholar" }]
}
```

---

## 2. Smithery (smithery.ai)

1. Go to https://smithery.ai — sign up/login with GitHub
2. Click **+ New Server**
3. Enter GitHub URL: `https://github.com/cryptographer11/cryptoscholar`
4. Smithery will auto-scan tools from the repo

---

## 3. mcp.so

1. Go to https://mcp.so/submit — sign in with Google or GitHub
2. Fill in:
   - **Type:** MCP Server
   - **Name:** CryptoScholar
   - **URL:** `https://github.com/cryptographer11/cryptoscholar`
   - **Server Config:**
     ```json
     {"mcpServers": {"cryptoscholar": {"command": "cryptoscholar", "env": {"ANTHROPIC_API_KEY": "<YOUR_ANTHROPIC_API_KEY>"}}}}
     ```

---

## 4. Glama (glama.ai/mcp/servers)

1. Go to https://glama.ai/mcp/servers
2. Click **Add Server**
3. Enter: `https://github.com/cryptographer11/cryptoscholar`
4. After it's listed, click **Claim Ownership** → GitHub OAuth → confirms you own the repo
5. Add `glama.json` to repo root:
   ```json
   {"$schema": "https://glama.ai/mcp/schemas/server.json", "maintainers": ["cryptographer11"]}
   ```

---

## 5. Cline MCP Marketplace

Open a GitHub issue at: https://github.com/cline/mcp-marketplace/issues/new?template=mcp-server-submission.yml

Fill in:
- **GitHub Repository URL:** `https://github.com/cryptographer11/cryptoscholar`
- **Logo Image:** `https://raw.githubusercontent.com/cryptographer11/cryptoscholar/main/docs/logo_400x400.png`
- Check both testing checkboxes
- **Additional Information:**

```
CryptoScholar gives Cline real-time crypto TA with 4 tools:
- analyze_coin — EMA-20/50/200, RSI-14, MACD, ADX, ATR, Bollinger Bands, TSS score (Binance data, no key needed)
- rank_coins — rank a watchlist by Trend Strength Score
- market_context — BTC dominance, ETH/BTC ratio, TOTAL3, stablecoin supply, ARS + MRS macro scores
- debate — grounded bull/bear debate from live TA data (requires ANTHROPIC_API_KEY)

Install: pip install cryptoscholar
Only ANTHROPIC_API_KEY needed, and only for the debate tool.
```

---

## 6. Claude Plugins Marketplace

1. Go to https://claude.ai/settings/plugins/submit
2. Submit GitHub repo: `https://github.com/cryptographer11/cryptoscholar`
3. Plugin manifest is already at `.claude-plugin/marketplace.json`

---

## Logo

Public URL for all submissions:
```
https://raw.githubusercontent.com/cryptographer11/cryptoscholar/main/docs/logo_400x400.png
```
