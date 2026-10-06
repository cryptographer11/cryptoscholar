"""Protocol-level tests: the server driven over real stdio by the mcp SDK's own client,
the way Claude Code talks to it.

Every other test file calls tool functions directly, so none of them would notice the MCP
layer breaking. Added with the mcp 1.x -> 2.x upgrade: Claude Code (2.1.282+) opens with the
2026 `server/discover` probe, which mcp 1.x rejected with a "Failed to validate request"
stderr warning before falling back to `initialize`.

Only side-effect-free tools are called: the subprocess talks to no network, and the
watchlist database lives in a temp dir.
"""
import asyncio
import os
import sys
from pathlib import Path

import pytest
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

from cryptoscholar import server

ROOT = Path(server.__file__).parent.parent

EXPECTED_TOOLS = {
    "alert_check", "alert_set", "analyze_coin", "correlate_coins", "debate", "generate_report",
    "market_context", "rank_coins", "top_coins", "train_regime_model", "watchlist_add",
    "watchlist_lists", "watchlist_remove", "watchlist_scan", "watchlist_show",
}


def _text(result) -> str:
    return "".join(getattr(c, "text", "") for c in result.content)


async def _session(params: StdioServerParameters, mode: str) -> dict:
    async with Client(params, mode=mode, read_timeout_seconds=120) as c:
        tools = await c.list_tools()
        listed = await c.call_tool("watchlist_lists", {})
        bad = await c.call_tool("analyze_coin", {})
        return {
            "protocol": c.protocol_version,
            "tools": {t.name for t in tools.tools},
            "schemas": {t.name: t.input_schema for t in tools.tools},
            "listed_is_error": listed.is_error,
            "bad_is_error": bad.is_error,
        }


@pytest.mark.parametrize("mode, protocol", [("auto", "2026-07-28"), ("legacy", "2025-11-25")])
def test_stdio_handshake_tools_and_call(tmp_path, mode, protocol):
    errlog = tmp_path / "stderr.log"
    params = StdioServerParameters(
        command="bash",
        args=["-c", f'exec "{sys.executable}" -m cryptoscholar.server 2>>"{errlog}"'],
        cwd=str(ROOT),
        env={**os.environ, "CRYPTOSCHOLAR_DATA_DIR": str(tmp_path), "CRYPTOSCHOLAR_LOG_DIR": str(tmp_path)},
    )
    s = asyncio.run(_session(params, mode))

    assert s["protocol"] == protocol
    assert s["tools"] == EXPECTED_TOOLS
    assert not s["listed_is_error"]
    assert s["bad_is_error"], "a call missing its required argument must be an error, not a crash"
    assert s["schemas"]["analyze_coin"]["required"] == ["symbol"]
    # The original symptom: a 2026 client's server/discover probe logged as a validation failure
    assert "Failed to validate" not in errlog.read_text()


def test_registered_tools_match_the_decorated_functions():
    """The in-process registry and the pinned list agree (catches a tool added without a pin)."""
    registered = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert registered == EXPECTED_TOOLS
