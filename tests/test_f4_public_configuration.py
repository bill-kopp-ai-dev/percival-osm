import asyncio
import time
import threading
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from types import SimpleNamespace

import httpx
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from percival_osm_mcp import server as server_mod
from percival_osm_mcp.server import Settings, validate_upstream_runtime_configuration
from percival_osm_mcp.server import OsmSearcher


@pytest.mark.parametrize("overrides", [
    {"nominatim_rate_limit_rps": 0},
    {"nominatim_rate_limit_rps": 1.1},
    {"nominatim_rate_limit_rps": float("nan")},
    {"nominatim_rate_limit_burst": 2},
])
def test_public_nominatim_rejects_unsafe_rate(overrides):
    with pytest.raises(ValueError, match="Public Nominatim requires"):
        validate_upstream_runtime_configuration(Settings(**overrides))


def test_public_nominatim_accepts_conservative_limits():
    validate_upstream_runtime_configuration(Settings(nominatim_rate_limit_rps=0.5))


async def test_overpass_enrichment_is_bounded(tmp_path, monkeypatch):
    settings = Settings(user_agent="test/1.0", from_header="test@example.com",
                        cache_file=str(tmp_path / "cache.json"), cache_allowed_dirs=str(tmp_path))
    searcher = OsmSearcher(settings, None)
    candidates = [{"type": "node", "id": i, "tags": {"shop": "bakery", "source": "survey"}}
                  for i in range(100)]
    batches = []

    async def fetch(*args, **kwargs):
        return {"elements": candidates}

    async def lookup(things):
        batches.append(things)
        return []

    monkeypatch.setattr(searcher, "_http_get_json", fetch)
    monkeypatch.setattr(searcher, "nominatim_lookup_by_id", lookup)
    await searcher.overpass_search("test", ["shop=bakery"],
                                 {"minlat": 0, "maxlat": 1, "minlon": 0, "maxlon": 1})
    assert [len(batch) for batch in batches] == [20]
    await searcher.aclose()


def test_selection_must_be_explicit():
    with pytest.raises(ValueError, match="NOMINATIM_URL"):
        server_mod.validate_geocoder_selection(Settings())
    server_mod.validate_geocoder_selection(Settings(nominatim_url="https://nominatim.openstreetmap.org/"))
    with pytest.raises(ValueError, match="explicit OSM_NOMINATIM"):
        server_mod.validate_geocoder_selection(Settings(nominatim_url="https://geocoder.example/"))
    server_mod.validate_geocoder_selection(Settings(nominatim_url="https://geocoder.example/",
        nominatim_rate_limit_rps=2, nominatim_rate_limit_burst=1))


def test_retry_after_and_overpass_timeout():
    assert server_mod._retry_after_seconds("45") == 45
    future = datetime.now(timezone.utc) + timedelta(seconds=90)
    assert 88 <= server_mod._retry_after_seconds(format_datetime(future)) <= 90
    assert server_mod._retry_after_seconds("invalid") == 0
    assert server_mod._overpass_ql_timeout(4.5) == 4
    with pytest.raises(server_mod.UpstreamRequestError):
        server_mod._overpass_ql_timeout(1)


async def test_budget_with_simulated_clock(monkeypatch):
    clock = SimpleNamespace(now=100.0)
    monkeypatch.setattr(server_mod, "time", SimpleNamespace(monotonic=lambda: clock.now))
    budget = server_mod.ProviderBudget()
    first_entered = asyncio.Event()
    release = asyncio.Event()

    async def first():
        async with budget.admission(1.0):
            first_entered.set()
            await release.wait()

    async def second():
        async with budget.admission(1.0):
            return clock.now

    first_task = asyncio.create_task(first())
    await first_entered.wait()
    second_task = asyncio.create_task(second())
    await asyncio.sleep(0.06)
    assert not second_task.done()  # concurrency is one
    release.set()
    await first_task
    clock.now = 100.99
    await asyncio.sleep(0.06)
    assert not second_task.done()  # less than one second since the start
    clock.now = 101.0
    assert await asyncio.wait_for(second_task, 0.2) == 101.0


def searcher_for(tmp_path):
    return OsmSearcher(Settings(user_agent="test/1", from_header="test@example.com",
        cache_file=str(tmp_path / "cache.json"), cache_allowed_dirs=str(tmp_path),
        http_max_retries=0), None)


async def test_shared_budget_spaces_distinct_searchers(tmp_path, monkeypatch):
    monkeypatch.setattr(server_mod, "_PROVIDER_BUDGETS", {})
    starts = []
    original = httpx.AsyncClient

    async def handle(request):
        starts.append(time.monotonic())
        return httpx.Response(200, json=[], request=request)

    monkeypatch.setattr(server_mod.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    one, two = searcher_for(tmp_path), searcher_for(tmp_path)
    url = "https://nominatim.openstreetmap.org/search"
    await asyncio.gather(one._http_get_json(url, {"q": "one"}, {}), two._http_get_json(url, {"q": "two"}, {}))
    assert len(starts) == 2 and starts[1] - starts[0] >= 0.99
    await one.aclose()
    await two.aclose()


async def test_single_flight_cancellation_isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(server_mod, "_PROVIDER_BUDGETS", {})
    entered, release = asyncio.Event(), asyncio.Event()
    calls = 0
    original = httpx.AsyncClient

    async def handle(request):
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        return httpx.Response(200, json=[{"id": 1}], request=request)

    monkeypatch.setattr(server_mod.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    one, two = searcher_for(tmp_path), searcher_for(tmp_path)
    url = "https://nominatim.openstreetmap.org/search"
    first = asyncio.create_task(one._http_get_json(url, {"q": "same"}, {}))
    await entered.wait()
    second = asyncio.create_task(two._http_get_json(url, {"q": "same"}, {}))
    await asyncio.sleep(0)
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    await one.aclose()
    release.set()
    assert await second == [{"id": 1}]
    assert calls == 1
    await two.aclose()


async def test_last_consumer_cancels_flight(tmp_path, monkeypatch):
    monkeypatch.setattr(server_mod, "_PROVIDER_BUDGETS", {})
    entered, cancelled = asyncio.Event(), asyncio.Event()
    original = httpx.AsyncClient

    async def handle(request):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    monkeypatch.setattr(server_mod.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    searcher = searcher_for(tmp_path)
    task = asyncio.create_task(searcher._http_get_json("https://nominatim.openstreetmap.org/search", {}, {}))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cancelled.is_set()
    await searcher.aclose()


def test_single_flight_spans_event_loops(tmp_path, monkeypatch):
    monkeypatch.setattr(server_mod, "_PROVIDER_BUDGETS", {})
    entered, release = threading.Event(), threading.Event()
    calls = []
    original = httpx.AsyncClient

    async def handle(request):
        calls.append(1)
        entered.set()
        await asyncio.to_thread(release.wait)
        return httpx.Response(200, json=[1], request=request)

    monkeypatch.setattr(server_mod.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handle), **kw))

    async def invoke():
        searcher = searcher_for(tmp_path)
        try:
            return await searcher._http_get_json("https://nominatim.openstreetmap.org/search", {"q": "same"}, {})
        finally:
            await searcher.aclose()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(asyncio.run, invoke())
        assert entered.wait(3)
        second = pool.submit(asyncio.run, invoke())
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            with server_mod._FLIGHTS_LOCK:
                if any(flight["waiters"] == 2 for flight in server_mod._FLIGHTS.values()):
                    break
            time.sleep(0.01)
        else:
            release.set()
            pytest.fail("second loop did not join the flight")
        release.set()
        assert first.result(timeout=3) == second.result(timeout=3) == [1]
    assert len(calls) == 1


@pytest.mark.parametrize("status", [406, 429])
async def test_overpass_cooldown_is_shared_and_immediate(tmp_path, monkeypatch, status):
    monkeypatch.setattr(server_mod, "_PROVIDER_BUDGETS", {})
    calls = 0
    original = httpx.AsyncClient

    async def handle(request):
        nonlocal calls
        calls += 1
        return httpx.Response(status, headers={"Retry-After": "35"}, request=request)

    monkeypatch.setattr(server_mod.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    one, two = searcher_for(tmp_path), searcher_for(tmp_path)
    url = "https://overpass-api.de/api/interpreter"
    with pytest.raises(server_mod.ProviderCooldown) as exc:
        await one._http_get_json(url, {"data": "one"}, {})
    assert exc.value.retry_after_seconds == 35
    with pytest.raises(server_mod.ProviderCooldown) as exc:
        await asyncio.wait_for(two._http_get_json(url, {"data": "two"}, {}), 0.2)
    assert 34 <= exc.value.retry_after_seconds <= 35
    assert calls == 1
    await one.aclose()
    await two.aclose()


async def test_overpass_query_limits_and_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(server_mod, "_PROVIDER_BUDGETS", {})
    requests = []
    original = httpx.AsyncClient

    async def handle(request):
        requests.append(request)
        return httpx.Response(200, json={"elements": []}, request=request)

    monkeypatch.setattr(server_mod.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    first, second = searcher_for(tmp_path), searcher_for(tmp_path)
    bbox = {"minlat": 0, "maxlat": 1, "minlon": 0, "maxlon": 1}
    token = server_mod._CALL_DEADLINE.set(time.monotonic() + 5)
    try:
        await first.overpass_search("example", ["shop=bakery"], bbox)
        await second.overpass_search("example", ["shop=bakery"], bbox)
    finally:
        server_mod._CALL_DEADLINE.reset(token)
    assert len(requests) == 1
    query = requests[0].url.params["data"]
    assert "[maxsize:67108864]" in query and "[timeout:4]" in query
    await first.aclose()
    await second.aclose()


async def test_overpass_5xx_retry_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(server_mod, "_PROVIDER_BUDGETS", {})
    requests = []
    original = httpx.AsyncClient

    async def handle(request):
        requests.append(request)
        return httpx.Response(503, request=request)

    monkeypatch.setattr(server_mod.httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    searcher = searcher_for(tmp_path)
    searcher.valves.http_max_retries = 1
    searcher.valves.http_retry_backoff_seconds = 0
    with pytest.raises(httpx.HTTPStatusError):
        await asyncio.wait_for(searcher._http_get_json("https://overpass-api.de/api/interpreter", {"data": "test"}, {}), 0.5)
    assert len(requests) == 2
    await searcher.aclose()


async def test_cooldown_is_returned_to_nearby_tool(tmp_path, monkeypatch):
    searcher = searcher_for(tmp_path)

    async def fail(*args, **kwargs):
        raise server_mod.ProviderCooldown(30)

    monkeypatch.setattr(searcher, "nominatim_search", fail)
    result = await searcher.search_nearby("test", ["shop=bakery"], category="bakeries")
    import json
    payload = json.loads(result["results"])
    assert payload["status"] == "upstream_error"
    assert payload["data"] == {"reason": "provider_cooldown", "retry_after_seconds": 30}
    await searcher.aclose()


async def test_stdio_handshake_with_explicit_backend(tmp_path):
    env = {"PATH": os.environ.get("PATH", ""), "USER_AGENT": "test/1 (test@example.com)",
           "FROM_HEADER": "test@example.com", "NOMINATIM_URL": "https://nominatim.openstreetmap.org/",
           "OSM_CACHE_FILE": str(tmp_path / "cache.json"), "OSM_CACHE_ALLOWED_DIRS": str(tmp_path)}
    params = StdioServerParameters(command=sys.executable, args=["-m", "percival_osm_mcp", "--mode", "stdio"], env=env)
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool("osm_get_health", {})
            assert not result.isError
