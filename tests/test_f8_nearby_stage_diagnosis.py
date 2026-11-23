"""Stage diagnosis and deadline accounting for the nearby search flow.

Regression coverage for the nearby-search issue diagnosed on 2026-11-23
(the detailed record is kept in the operator's private working records):

* the nearby path could not attribute an upstream failure or a deadline
  overrun to a stage, so the 2026-11-23 failure could not be classified;
* the deadline published to the transport and the timer that enforced it
  disagreed, and the cleanup reserve was added on top of the budget instead
  of being carved out of it;
* a retry could be started that the remaining budget could not fund.

Every fixture runs against an in-process transport: no public network, no
shared cache, and no real 16 s wait.
"""

import asyncio
from contextlib import asynccontextmanager
import json
import os
import time

import httpx
import pytest

from urllib.parse import urlsplit

from percival_osm_mcp import server as server_mod
from percival_osm_mcp.server import (
    OsmSearcher,
    Settings,
    get_operational_snapshot,
    reset_operational_metrics_for_tests,
)


PLACE = "Praça da Sé, São Paulo, Brazil"

NOMINATIM_PLACE = {
    "lat": "-23.5614",
    "lon": "-46.6559",
    "display_name": "MASP, São Paulo, Brazil",
    "boundingbox": ["-23.57", "-23.55", "-46.67", "-46.64"],
}

# A named node: usable as a final POI result.
NAMED_PHARMACY = {
    "type": "node",
    "id": 1001,
    "lat": -23.5600,
    "lon": -46.6500,
    "tags": {"amenity": "pharmacy", "name": "Farmácia Central"},
}

# A node without a name: only usable after a Nominatim lookup enrichment.
BARE_PHARMACY = {
    "type": "node",
    "id": 1002,
    "lat": -23.5600,
    "lon": -46.6500,
    "tags": {"amenity": "pharmacy", "operator": "Rede Fixture"},
}


class _UnlimitedBudget:
    """Provider budget stub that never delays admission.

    The production limiter deliberately spaces public Nominatim requests by a
    second. The fixtures below exercise the deadline arithmetic, not the
    limiter, so the wait is removed to keep them fast and deterministic.
    """

    def cooldown(self, seconds: float) -> None:
        return None

    @asynccontextmanager
    async def admission(self, interval: float):
        yield


class _Router:
    """Routes fixture requests to per-endpoint handlers without a network."""

    def __init__(self, *, nominatim=None, overpass=None, lookup=None):
        self.nominatim = nominatim
        self.overpass = overpass
        self.lookup = lookup
        self.calls: list[str] = []
        self.overpass_attempts = 0

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.calls.append(url)
        if urlsplit(url).path.endswith("/lookup"):
            handler = self.lookup
        elif "overpass" in url:
            handler = self.overpass
            self.overpass_attempts += 1
        else:
            handler = self.nominatim
        if handler is None:
            return httpx.Response(200, json=[], request=request)
        return await handler(request)


def _settings(tmp_path, **overrides) -> Settings:
    os.environ["USER_AGENT"] = "percival-osm-test/1.0"
    os.environ["FROM_HEADER"] = "test@example.com"
    values = {
        "user_agent": "percival-osm-test/1.0",
        "from_header": "test@example.com",
        "cache_allowed_dirs": str(tmp_path),
        "cache_file": str(tmp_path / "cache.json"),
        "upstream_allowed_hosts": "nominatim.openstreetmap.org,overpass-api.de,api.heigit.org",
    }
    values.update(overrides)
    return Settings(**values)


def _install(monkeypatch, router: _Router, tmp_path, **overrides) -> Settings:
    """Point the server at the fixture transport and an isolated cache."""
    settings = _settings(tmp_path, **overrides)
    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs.pop("transport", None)
        return original_client(
            *args, transport=httpx.MockTransport(router), **kwargs
        )

    monkeypatch.setattr(server_mod.httpx, "AsyncClient", client_factory)
    monkeypatch.setattr(server_mod, "valves", settings)
    monkeypatch.setattr(server_mod, "user_valves", None)
    monkeypatch.setattr(server_mod, "_PROVIDER_BUDGETS", {})
    monkeypatch.setattr(server_mod, "_FLIGHTS", {})
    monkeypatch.setattr(server_mod, "_provider_budget", lambda url: _UnlimitedBudget())
    # The Overpass QL timeout is expressed in whole seconds, so a sub-second
    # deadline cannot host one. The fixtures below exercise the deadline
    # arithmetic, not the Overpass query budget.
    monkeypatch.setattr(server_mod, "_overpass_ql_timeout", lambda remaining: 1)
    return settings


async def _nominatim_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=[NOMINATIM_PLACE], request=request)


async def _overpass_elements(elements) -> httpx.Response:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"elements": elements, "osm3s": {"timestamp_osm_base": "2026-11-23T00:00:00Z"}},
            request=request,
        )

    return handler


async def _call_nearby(**overrides):
    return await server_mod.mcp.call_tool(
        "osm_find_nearby",
        {
            "place": PLACE,
            "category": "pharmacies",
            "limit": 3,
            "radius": 1500,
        },
    )


def _payload(result) -> dict:
    content, structured = result
    payload = json.loads(structured["result"])
    assert json.loads(content[0].text) == payload
    return payload


async def test_overpass_http_failure_is_attributed_to_stage_and_reason(
    monkeypatch, tmp_path
):
    """A provider failure names the stage and the bounded reason."""
    reset_operational_metrics_for_tests()

    async def overpass(request):
        return httpx.Response(503, text="upstream detail", request=request)

    _install(
        monkeypatch,
        _Router(nominatim=_nominatim_ok, overpass=overpass),
        tmp_path,
        http_max_retries=0,
    )

    payload = _payload(await _call_nearby())
    assert payload["status"] == "upstream_error"

    failure = get_operational_snapshot()["last_upstream_failure"]
    assert failure["kind"] == "Overpass"
    assert failure["stage"] == "overpass"
    assert failure["reason"] == "http_error"
    assert failure["http_status"] == 503


async def test_nearby_deadline_is_attributed_to_the_overpass_stage(
    monkeypatch, tmp_path
):
    """A blocked provider is reported against the stage that consumed it."""
    reset_operational_metrics_for_tests()

    async def overpass(request):
        await asyncio.Event().wait()

    _install(
        monkeypatch,
        _Router(nominatim=_nominatim_ok, overpass=overpass),
        tmp_path,
        upstream_tool_deadline_seconds=0.4,
    )

    payload = _payload(await _call_nearby())
    assert payload["status"] == "upstream_error"

    failure = get_operational_snapshot()["last_upstream_failure"]
    assert failure["kind"] == "NearbySearch"
    assert failure["stage"] == "overpass"
    assert failure["reason"] == "deadline_exceeded"


async def test_nearby_deadline_after_valid_overpass_is_attributed_to_enrichment(
    monkeypatch, tmp_path
):
    """A valid provider response followed by a blocked lookup names the lookup."""
    reset_operational_metrics_for_tests()

    async def lookup(request):
        await asyncio.Event().wait()

    router = _Router(
        nominatim=_nominatim_ok,
        overpass=await _overpass_elements([BARE_PHARMACY]),
        lookup=lookup,
    )
    _install(monkeypatch, router, tmp_path, upstream_tool_deadline_seconds=0.4)

    payload = _payload(await _call_nearby())
    assert payload["status"] == "upstream_error"

    failure = get_operational_snapshot()["last_upstream_failure"]
    assert failure["kind"] == "NearbySearch"
    assert failure["stage"] == "enrich"
    assert failure["reason"] == "deadline_exceeded"


async def test_published_budget_and_enforced_timer_agree(monkeypatch, tmp_path):
    """The budget handed to the transport is the one the timer enforces.

    Before the fix the published deadline was the nominal timeout while the
    local timer used the inherited deadline, so the transport could believe
    it had more time than the call actually had.
    """
    reset_operational_metrics_for_tests()
    observed: dict = {}

    async def capture(*args, **kwargs):
        observed["published_remaining"] = (
            server_mod._CALL_DEADLINE.get() - time.monotonic()
        )
        observed["cleanup_budget"] = server_mod._CALL_CLEANUP_BUDGET.get()
        await asyncio.Event().wait()

    settings = _install(
        monkeypatch,
        _Router(nominatim=_nominatim_ok),
        tmp_path,
        upstream_tool_deadline_seconds=0.6,
    )
    monkeypatch.setattr(OsmSearcher, "search_nearby", capture)

    await _call_nearby()

    total = settings.upstream_tool_deadline_seconds
    reserve = min(
        server_mod.CANCELLATION_CLEANUP_TIMEOUT_SECONDS, total * 0.1
    )
    # The search body must stop where the cleanup reserve begins.
    assert observed["published_remaining"] <= total - reserve + 0.01
    assert observed["published_remaining"] >= total - reserve - 0.05
    # And the teardown must run inside the reserve, not on top of it.
    assert observed["cleanup_budget"] == pytest.approx(reserve)


async def test_teardown_runs_inside_the_configured_budget(monkeypatch, tmp_path):
    """The whole call, cleanup included, stays within the configured deadline."""
    reset_operational_metrics_for_tests()
    observed: dict = {}
    original_aclose = OsmSearcher.aclose

    async def spy_aclose(self, *, cancel_pending: bool = False):
        observed["cleanup_budget"] = server_mod._CALL_CLEANUP_BUDGET.get()
        observed["started_at"] = time.monotonic()
        await original_aclose(self, cancel_pending=cancel_pending)

    async def overpass(request):
        await asyncio.Event().wait()

    settings = _install(
        monkeypatch,
        _Router(nominatim=_nominatim_ok, overpass=overpass),
        tmp_path,
        upstream_tool_deadline_seconds=0.6,
    )
    monkeypatch.setattr(OsmSearcher, "aclose", spy_aclose)

    started = time.monotonic()
    payload = _payload(await _call_nearby())
    elapsed = time.monotonic() - started

    total = settings.upstream_tool_deadline_seconds
    reserve = min(
        server_mod.CANCELLATION_CLEANUP_TIMEOUT_SECONDS, total * 0.1
    )
    assert payload["status"] == "upstream_error"
    assert observed["cleanup_budget"] == pytest.approx(reserve)
    # The teardown starts no later than the search budget ends, so the
    # complete call fits inside the configured deadline.
    assert observed["started_at"] - started <= total - reserve + 0.05
    assert elapsed <= total + 0.1


async def test_retry_is_not_started_when_the_budget_cannot_fund_it(
    monkeypatch, tmp_path
):
    """A retry that the remaining budget cannot fund is not attempted."""
    reset_operational_metrics_for_tests()

    async def overpass(request):
        return httpx.Response(503, request=request)

    router = _Router(nominatim=_nominatim_ok, overpass=overpass)
    _install(
        monkeypatch,
        router,
        tmp_path,
        upstream_tool_deadline_seconds=0.4,
        http_max_retries=2,
        http_retry_backoff_seconds=0.6,
    )

    started = time.monotonic()
    payload = _payload(await _call_nearby())
    elapsed = time.monotonic() - started

    assert payload["status"] == "upstream_error"
    # One attempt: the configured backoff exceeds the whole budget.
    assert router.overpass_attempts == 1
    # The call must not have waited out the backoff it could not afford.
    assert elapsed < 0.4


async def test_nearby_failure_is_counted_once(monkeypatch, tmp_path):
    """A deadline failure is one MCP outcome, not an error plus an outcome."""
    reset_operational_metrics_for_tests()

    async def overpass(request):
        await asyncio.Event().wait()

    _install(
        monkeypatch,
        _Router(nominatim=_nominatim_ok, overpass=overpass),
        tmp_path,
        upstream_tool_deadline_seconds=0.4,
    )

    payload = _payload(await _call_nearby())
    assert payload["status"] == "upstream_error"

    snapshot = get_operational_snapshot()
    assert snapshot["tool_calls"]["osm_find_nearby"] == 1
    assert snapshot["tool_outcomes"]["osm_find_nearby"] == {"upstream_error": 1}
    assert "osm_find_nearby" not in snapshot["tool_errors"]


async def test_diagnosis_exposes_no_upstream_content(monkeypatch, tmp_path, caplog):
    """Neither the health snapshot nor the log leaks upstream content."""
    reset_operational_metrics_for_tests()

    async def overpass(request):
        return httpx.Response(
            503, text="upstream detail", request=request
        )

    _install(
        monkeypatch,
        _Router(nominatim=_nominatim_ok, overpass=overpass),
        tmp_path,
        http_max_retries=0,
    )

    with caplog.at_level("INFO", logger="percival-osm"):
        await _call_nearby()

    failure = get_operational_snapshot()["last_upstream_failure"]
    serialized = json.dumps(failure, default=str)
    logged = "\n".join(record.getMessage() for record in caplog.records)

    for haystack in (serialized, logged):
        assert "https://" not in haystack
        assert "overpass-api.de" not in haystack
        assert "nominatim.openstreetmap.org" not in haystack
        assert PLACE not in haystack
        assert "Praça" not in haystack
        assert "[out:json]" not in haystack
        assert "nwr[" not in haystack
        assert "upstream detail" not in haystack


async def test_successful_call_records_stage_durations(monkeypatch, tmp_path, caplog):
    """A healthy call still reports the stage breakdown it went through."""
    reset_operational_metrics_for_tests()

    router = _Router(
        nominatim=_nominatim_ok,
        overpass=await _overpass_elements([NAMED_PHARMACY]),
    )
    _install(monkeypatch, router, tmp_path)

    with caplog.at_level("INFO", logger="percival-osm"):
        payload = _payload(await _call_nearby())

    assert payload["status"] == "ok"
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "Nearby search diagnosis" in logged
    for stage in ("geocode", "overpass", "rank", "render", "cleanup"):
        assert stage in logged


async def test_timed_out_call_leaves_no_orphaned_task(monkeypatch, tmp_path):
    """A cancelled call does not leave the provider task running."""
    reset_operational_metrics_for_tests()
    cancelled = asyncio.Event()

    async def overpass(request):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    _install(
        monkeypatch,
        _Router(nominatim=_nominatim_ok, overpass=overpass),
        tmp_path,
        upstream_tool_deadline_seconds=0.4,
    )

    before = set(asyncio.all_tasks())
    payload = _payload(await _call_nearby())
    await asyncio.sleep(0.05)

    assert payload["status"] == "upstream_error"
    assert cancelled.is_set()
    leaked = [task for task in asyncio.all_tasks() if task not in before and not task.done()]
    assert leaked == []
