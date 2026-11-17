"""Outcome counters are recorded at the registered MCP callback boundary."""

import asyncio
import json

import pytest
from mcp.server.fastmcp import Context
from mcp.server.fastmcp.exceptions import ToolError

from percival_osm_mcp import server as server_mod


def _payload(result):
    content = result[0][0] if isinstance(result, tuple) else result[0]
    return json.loads(content.text)


async def test_registered_mcp_callbacks_count_outcomes_and_exceptions(monkeypatch):
    server_mod.reset_operational_metrics_for_tests()
    # The standalone FastMCP callback has no live transport session; suppress
    # context logging rather than creating un-awaited logging coroutines.
    monkeypatch.setattr(Context, "info", lambda *args, **kwargs: None)
    statuses = iter(("no_results", "upstream_error"))

    async def controlled_result(*args, **kwargs):
        return server_mod.build_tool_response(
            status=next(statuses), message="fixture", include_untrusted_warning=False
        )

    monkeypatch.setattr(server_mod, "find_specific_place_impl", controlled_result)
    assert _payload(await server_mod.mcp.call_tool(
        "osm_find_place", {"address_or_place": "fixture"}
    ))["status"] == "no_results"
    assert _payload(await server_mod.mcp.call_tool(
        "osm_find_place", {"address_or_place": "fixture"}
    ))["status"] == "upstream_error"

    async def raises(*args, **kwargs):
        raise RuntimeError("private fixture detail")

    monkeypatch.setattr(server_mod, "find_specific_place_impl", raises)
    with pytest.raises(ToolError, match="private fixture detail"):
        await server_mod.mcp.call_tool("osm_find_place", {"address_or_place": "fixture"})

    async def cancelled(*args, **kwargs):
        raise asyncio.CancelledError

    monkeypatch.setattr(server_mod, "find_specific_place_impl", cancelled)
    with pytest.raises(asyncio.CancelledError):
        await server_mod.mcp.call_tool("osm_find_place", {"address_or_place": "fixture"})

    # Local health succeeds and its snapshot is allowed to precede this call's
    # terminal outcome, which is recorded after the handler returns.
    health = _payload(await server_mod.mcp.call_tool("osm_get_health", {}))
    assert health["status"] == "ok"
    snapshot = server_mod.get_operational_snapshot()
    assert snapshot["tool_calls"]["osm_find_place"] == 4
    assert snapshot["tool_errors"]["osm_find_place"] == 1
    assert snapshot["tool_outcomes"]["osm_find_place"] == {
        "no_results": 1,
        "upstream_error": 1,
        "exception": 1,
        "cancelled": 1,
    }
    assert snapshot["tool_outcomes"]["osm_get_health"]["ok"] == 1


def test_unknown_response_status_is_not_counted_as_success():
    assert server_mod._response_outcome('{"status":"unexpected"}') == "unknown"
    assert server_mod._response_outcome("not-json") == "unknown"
