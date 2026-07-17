"""Tests for observability features: structured logging, health/version/rate-limit."""

import asyncio
import json
import logging
import time

import pytest

from percival_osm_mcp import server as server_mod
from percival_osm_mcp.server import (
    AsyncTokenBucket,
    SERVER_NAME,
    SERVER_VERSION,
    Settings,
    _JsonFormatter,
    _configure_logging,
    get_health,
    get_operational_snapshot,
    get_security_metrics_snapshot,
    get_version,
    record_tool_call,
    record_upstream_failure,
    reset_operational_metrics_for_tests,
    reset_security_metrics_for_tests,
)


def _base_settings(**overrides):
    values = {
        "upstream_allowed_hosts": "nominatim.openstreetmap.org,overpass-api.de,api.openrouteservice.org",
        "cache_allowed_dirs": "/tmp",
        "cache_file": "/tmp/osm-cache.json",
        "log_format": "plain",
        "log_level": "DEBUG",
    }
    values.update(overrides)
    return Settings(**values)


def test_json_formatter_emits_required_fields() -> None:
    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="percival-osm",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    rendered = formatter.format(record)
    payload = json.loads(rendered)
    assert payload["level"] == "INFO"
    assert payload["logger"] == "percival-osm"
    assert payload["msg"] == "hello world"
    assert "ts" in payload


def test_configure_logging_can_switch_to_json() -> None:
    original = server_mod.valves.log_format
    try:
        server_mod.valves.log_format = "json"
        _configure_logging()
        root = logging.getLogger()
        assert any(
            isinstance(h.formatter, _JsonFormatter) for h in root.handlers
        ), "expected at least one JSON handler"
    finally:
        server_mod.valves.log_format = original
        _configure_logging()


def test_operational_snapshot_includes_uptime_and_counters() -> None:
    reset_operational_metrics_for_tests()
    record_tool_call("osm_find_place")
    record_tool_call("osm_find_place", error=True)
    record_upstream_failure("ConnectError", "boom")
    snapshot = get_operational_snapshot()
    assert snapshot["uptime_seconds"] >= 0
    assert snapshot["tool_calls"]["osm_find_place"] == 2
    assert snapshot["tool_errors"]["osm_find_place"] == 1
    assert snapshot["last_upstream_failure"]["kind"] == "ConnectError"
    assert "ts" in snapshot["last_upstream_failure"]


def test_get_version_returns_expected_fields() -> None:
    reset_operational_metrics_for_tests()
    payload = json.loads(get_version())
    assert payload["status"] == "ok"
    assert payload["data"]["version"] == SERVER_VERSION
    assert payload["data"]["server"] == SERVER_NAME
    assert payload["data"]["started_at"].endswith("+00:00")


def test_get_health_includes_cache_file_and_failure() -> None:
    reset_operational_metrics_for_tests()
    record_tool_call("osm_navigate")
    record_upstream_failure("HTTPStatusError", "503")
    payload = json.loads(get_health())
    assert payload["status"] == "ok"
    data = payload["data"]
    assert "uptime_seconds" in data
    assert data["tool_calls"]["osm_navigate"] == 1
    assert data["last_upstream_failure"]["kind"] == "HTTPStatusError"
    assert data["cache_file"] == server_mod.valves.cache_file


async def test_token_bucket_initial_burst() -> None:
    bucket = AsyncTokenBucket(rate_per_second=1.0, burst=3)
    started = time.monotonic()
    for _ in range(3):
        await bucket.acquire()
    elapsed = time.monotonic() - started
    # First burst of 3 should complete instantly (well under 100ms total).
    assert elapsed < 0.1


async def test_token_bucket_throttles_after_burst() -> None:
    bucket = AsyncTokenBucket(rate_per_second=5.0, burst=1)
    started = time.monotonic()
    for _ in range(3):
        await bucket.acquire()
    elapsed = time.monotonic() - started
    # 5 rps => 0.2s per token. 3 calls: first instant, then 2x ~0.2s = ~0.4s
    assert elapsed >= 0.3


async def test_token_bucket_disabled_when_rate_zero() -> None:
    bucket = AsyncTokenBucket(rate_per_second=0.0, burst=1)
    assert bucket.disabled is True
    started = time.monotonic()
    for _ in range(10):
        await bucket.acquire()
    elapsed = time.monotonic() - started
    assert elapsed < 0.05


def test_settings_accept_new_flags() -> None:
    settings = _base_settings(
        expose_legacy_aliases=False,
        log_format="json",
        log_level="WARNING",
        nominatim_rate_limit_rps=2.0,
        nominatim_rate_limit_burst=5,
    )
    assert settings.expose_legacy_aliases is False
    assert settings.log_format == "json"
    assert settings.log_level == "WARNING"
    assert settings.nominatim_rate_limit_rps == 2.0
    assert settings.nominatim_rate_limit_burst == 5