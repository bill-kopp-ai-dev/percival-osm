import asyncio
import json
import time

import httpx
import pytest

from percival_osm_mcp import server as server_mod


class _RecordingTransport(httpx.AsyncBaseTransport):
    """Records the timeout httpx applies to each outgoing request."""

    def __init__(self):
        self.timeouts = []

    async def handle_async_request(self, request):
        self.timeouts.append(request.extensions.get("timeout", {}))
        return httpx.Response(200, json=[], request=request)


def settings_for(tmp_path, **overrides):
    values = {
        "user_agent": "percival-osm-test/1.0",
        "from_header": "test@example.com",
        "ors_api_key": "fixture-ors-secret",
        "cache_allowed_dirs": str(tmp_path),
        "cache_file": str(tmp_path / "cache.json"),
        "upstream_allowed_hosts": "nominatim.openstreetmap.org,overpass-api.de,api.heigit.org",
    }
    values.update(overrides)
    return server_mod.Settings(**values)


@pytest.mark.asyncio
async def test_limiter_cancellation_is_not_consumed():
    limiter = server_mod.AsyncTokenBucket(rate_per_second=0.01, burst=1)
    await limiter.acquire()
    waiter = asyncio.create_task(limiter.acquire())
    await asyncio.sleep(0)
    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter


@pytest.mark.asyncio
async def test_limiter_lock_wait_cancellation_is_not_consumed():
    limiter = server_mod.AsyncTokenBucket(rate_per_second=1, burst=1)
    async with limiter._lock:
        waiter = asyncio.create_task(limiter.acquire())
        await asyncio.sleep(0)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter


@pytest.mark.parametrize(
    ("destination", "profile"),
    [
        ({"lat": 52.001, "lon": 13.002}, "foot-walking"),
        ({"lat": 52.5, "lon": 13.5}, "driving-car"),
    ],
)
@pytest.mark.asyncio
async def test_ors_async_transport_posts_expected_payload_without_retry(
    tmp_path, monkeypatch, destination, profile
):
    captured = {}
    original_client = httpx.AsyncClient

    async def handler(request):
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = await request.aread()
        return httpx.Response(
            200,
            json={"routes": [{"summary": {"distance": 1200.0}, "segments": []}]},
            request=request,
        )

    def client_factory(*args, **kwargs):
        return original_client(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(server_mod.httpx, "AsyncClient", client_factory)
    router = server_mod.OrsRouter(settings_for(tmp_path), user_valves=None)
    route = await router.calculate_route_async(
        {"lat": 52.0, "lon": 13.0}, destination
    )

    assert route["summary"]["distance"] == 1200.0
    assert captured["url"].endswith(f"/v2/directions/{profile}/json")
    assert captured["headers"]["authorization"] == "fixture-ors-secret"
    assert "fixture-ors-secret" not in captured["url"]
    body = json.loads(captured["body"])
    assert body["coordinates"] == [[13.0, 52.0], [destination["lon"], destination["lat"]]]
    assert body["preference"] == "fastest"
    assert body["units"] == "km"


@pytest.mark.asyncio
async def test_ors_transport_cancellation_reaches_request(tmp_path, monkeypatch):
    cancelled = asyncio.Event()
    original_client = httpx.AsyncClient

    async def handler(request):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    def client_factory(*args, **kwargs):
        return original_client(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(server_mod.httpx, "AsyncClient", client_factory)
    settings = settings_for(tmp_path, ors_request_timeout=90, upstream_tool_deadline_seconds=0.05)
    router = server_mod.OrsRouter(settings, user_valves=None)
    task = asyncio.create_task(
        router.calculate_route_async({"lat": 52.0, "lon": 13.0}, {"lat": 52.001, "lon": 13.002})
    )
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert cancelled.is_set()


@pytest.mark.parametrize("status_code", [401, 403, 429, 503])
@pytest.mark.asyncio
async def test_ors_provider_failures_are_controlled_without_retry(
    tmp_path, monkeypatch, status_code
):
    attempts = 0
    original_client = httpx.AsyncClient

    async def handler(request):
        nonlocal attempts
        attempts += 1
        return httpx.Response(status_code, request=request)

    def client_factory(*args, **kwargs):
        return original_client(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(server_mod.httpx, "AsyncClient", client_factory)
    router = server_mod.OrsRouter(settings_for(tmp_path), user_valves=None)
    with pytest.raises(server_mod.UpstreamRequestError, match=f"HTTP {status_code}"):
        await router.calculate_route_async(
            {"lat": 52.0, "lon": 13.0}, {"lat": 52.001, "lon": 13.002}
        )
    assert attempts == 1


@pytest.mark.asyncio
async def test_upstream_attempt_timeout_is_clamped_to_the_remaining_budget(
    tmp_path, monkeypatch
):
    """A request may not be given more time than the call budget still has.

    The per-request timeout used to be the configured ``http_timeout_seconds``
    regardless of the call budget, so a single attempt could consume the whole
    upstream deadline and the retry that followed ran past it.
    """
    transport = _RecordingTransport()
    original_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs.pop("transport", None)
        return original_client(*args, transport=transport, **kwargs)

    monkeypatch.setattr(server_mod.httpx, "AsyncClient", client_factory)
    monkeypatch.setattr(server_mod, "_PROVIDER_BUDGETS", {})
    monkeypatch.setattr(server_mod, "_FLIGHTS", {})
    settings = settings_for(tmp_path, http_timeout_seconds=12.0)
    searcher = server_mod.OsmSearcher(settings, user_valves=None)

    budget = 0.5
    token = server_mod._CALL_DEADLINE.set(time.monotonic() + budget)
    try:
        await searcher._http_get_json(
            "https://overpass-api.de/api/interpreter",
            params={"data": "out;"},
            headers={"User-Agent": "percival-osm-test/1.0", "From": "test@example.com"},
        )
    finally:
        server_mod._CALL_DEADLINE.reset(token)

    assert transport.timeouts
    for applied in transport.timeouts:
        assert applied["read"] <= budget
        assert applied["connect"] <= budget
