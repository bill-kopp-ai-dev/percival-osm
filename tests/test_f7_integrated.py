"""Offline transport checks for the integrated MCP surface."""

import asyncio
import os
import socket
import subprocess
import sys
import time

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


@pytest.mark.asyncio
async def test_streamable_http_handshake_tools_and_packaged_policy(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    env = os.environ.copy()
    env.update(
        {
            "USER_AGENT": "f7-test/1.0 (test@example.invalid)",
            "FROM_HEADER": "test@example.invalid",
            "NOMINATIM_URL": "https://nominatim.openstreetmap.org/",
            "OSM_CACHE_FILE": str(tmp_path / "cache.json"),
            "OSM_CACHE_ALLOWED_DIRS": str(tmp_path),
            "OSM_LOG_LEVEL": "ERROR",
            "PYTHONPATH": os.pathsep.join(
                filter(None, [os.environ.get("PYTHONPATH"), os.path.abspath("src")])
            ),
        }
    )
    log_path = tmp_path / "http-server.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "percival_osm_mcp", "--mode", "streamable-http", "--port", str(port)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=log,
        )
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail(f"HTTP MCP server exited early: {log_path.read_text(encoding='utf-8')}")
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                        break
                except OSError:
                    await asyncio.sleep(0.05)
            else:
                pytest.fail("HTTP MCP server did not open its local listener")

            async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    assert "osm_get_health" in {tool.name for tool in tools.tools}
                    health = await session.call_tool("osm_get_health", {})
                    assert not health.isError
                    policy = await session.read_resource("osm://security/nanobot-policy")
                    text = "\n".join(item.text for item in policy.contents)
                    assert "# Percival OSM MCP" in text
                    assert "MCP_OSM_AUTH_TOKEN" in text
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
