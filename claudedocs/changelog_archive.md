# Recent Changes — Archive

Entries aged out of `CLAUDE.md` by `/root/scripts/doc_health_check.py`.
Appended, never pruned — this file is not scanned by that script.

### 2026-07-29 MYT — debate tool migrated to OmniRoute
- `cryptoscholar/tools/debate.py`: replaced direct `anthropic.Anthropic()` SDK call with `httpx.post()` to the self-hosted OmniRoute gateway (`http://localhost:20128/v1/chat/completions`, OpenAI-compatible). This tool was completely non-functional before — no `ANTHROPIC_API_KEY` had ever been configured for this project.
- New env var `OMNIROUTE_API_KEY` (was `ANTHROPIC_API_KEY`); new `/root/secrets/cryptoscholar.env` + `.env` symlink (first secret this project has).
- Default model `auto/smart` (was `claude-haiku-4-5-20251001` hardcoded); `max_tokens` 512 → 2048 after live testing showed a reasoning model's hidden reasoning tokens were exhausting the budget before the JSON finished (`finish_reason: "length"`, JSON truncated mid-string).
- Added markdown-code-fence stripping before `json.loads` — live testing showed `auto/smart` wraps its JSON answer in ` ```json ` despite the system prompt saying not to.
- 8 new tests in `tests/test_debate.py` (no test existed for this tool before). Full suite 230/230 passing.
- Verified live end-to-end for BTC and ETH.
