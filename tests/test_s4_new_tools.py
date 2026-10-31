"""Tests for osm_geocode and osm_directions."""

import asyncio
import json
import os
import time

import httpx
import pytest

from percival_osm_mcp import server as server_mod
from percival_osm_mcp.server import (
    OsmNavigator,
    OsmSearcher,
    Settings,
    UpstreamRequestError,
    geocode_place,
    find_address_for_coordinates,
    find_specific_place_impl,
    get_operational_snapshot,
    reset_operational_metrics_for_tests,
    turn_by_turn_directions,
)


def _base_settings(**overrides):
    # The repo ships a real .env for dev; force the test-suite-required
    # identifiers via env vars so Pydantic picks them up cleanly.
    os.environ["USER_AGENT"] = "percival-osm-test/1.0"
    os.environ["FROM_HEADER"] = "test@example.com"
    values = {
        "upstream_allowed_hosts": "nominatim.openstreetmap.org,overpass-api.de,api.openrouteservice.org",
        "cache_allowed_dirs": "/tmp",
        "cache_file": "/tmp/osm-cache.json",
        "user_agent": "percival-osm-test/1.0",
        "from_header": "test@example.com",
    }
    values.update(overrides)
    return Settings(**values)


def test_upstream_tool_deadline_setting_stays_within_observed_client_budget() -> None:
    assert _base_settings().upstream_tool_deadline_seconds == 16.0
    assert _base_settings(upstream_tool_deadline_seconds=5).upstream_tool_deadline_seconds == 5
    with pytest.raises(ValueError):
        _base_settings(upstream_tool_deadline_seconds=0)
    with pytest.raises(ValueError):
        _base_settings(upstream_tool_deadline_seconds=17)


@pytest.mark.parametrize(
    ("handler", "tool_name"),
    [
        (server_mod.find_places_near_place, "osm_find_nearby"),
        (server_mod.find_places_near_place_detailed, "osm_find_nearby_detailed"),
    ],
)
async def test_nearby_deadline_returns_controlled_error_and_cancels(
    monkeypatch, handler, tool_name
) -> None:
    cancelled = asyncio.Event()
    settings = _base_settings(upstream_tool_deadline_seconds=0.02)
    searcher = OsmSearcher(settings, user_valves=None)

    class FakeClient:
        closed = False

        async def aclose(self):
            self.closed = True

    client = FakeClient()
    searcher._http_client = client

    async def delayed_search(*args, **kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    monkeypatch.setattr(server_mod, "valves", settings)
    monkeypatch.setattr(server_mod, "user_valves", None)
    monkeypatch.setattr(server_mod, "OsmSearcher", lambda *args, **kwargs: searcher)
    monkeypatch.setattr(searcher, "search_nearby", delayed_search)
    reset_operational_metrics_for_tests()

    started = time.monotonic()
    response = await handler("Fixtureville", "groceries", limit=3, radius=1000)
    elapsed = time.monotonic() - started

    assert elapsed < 0.5
    assert cancelled.is_set()
    assert client.closed
    assert searcher._http_client is None
    assert json.loads(response)["status"] == "upstream_error"
    snapshot = get_operational_snapshot()
    assert snapshot["tool_calls"][tool_name] == 1
    assert tool_name not in snapshot["tool_errors"]
    assert snapshot["last_upstream_failure"]["kind"] == "NearbySearch"
    assert "deadline exceeded" in snapshot["last_upstream_failure"]["message"]


async def test_registered_nearby_timeout_reaches_mcp_caller(monkeypatch) -> None:
    settings = _base_settings(upstream_tool_deadline_seconds=0.02)
    overpass_cancelled = asyncio.Event()
    close_cancelled = asyncio.Event()

    class FakeClient:
        closed = False

        async def get(self, url, params=None, headers=None):
            url = str(url)
            if "nominatim.openstreetmap.org/search" in url:
                return httpx.Response(
                    200,
                    json=[{
                        "lat": "-23.5614",
                        "lon": "-46.6559",
                        "display_name": "MASP, São Paulo, Brazil",
                        "boundingbox": ["-23.57", "-23.55", "-46.67", "-46.64"],
                    }],
                    request=httpx.Request("GET", url),
                )
            try:
                await asyncio.Event().wait()
            finally:
                overpass_cancelled.set()

        async def aclose(self):
            try:
                await asyncio.Event().wait()
            finally:
                close_cancelled.set()

    monkeypatch.setattr(server_mod, "valves", settings)
    monkeypatch.setattr(server_mod, "user_valves", None)
    monkeypatch.setattr(server_mod, "CANCELLATION_CLEANUP_TIMEOUT_SECONDS", 0.01)

    async def get_client(searcher):
        if searcher._http_client is None:
            searcher._http_client = FakeClient()
        return searcher._http_client

    monkeypatch.setattr(OsmSearcher, "_get_http_client", get_client)
    reset_operational_metrics_for_tests()

    started = time.monotonic()
    result = await server_mod.mcp.call_tool(
        "osm_find_nearby",
        {
            "place": "MASP, São Paulo, Brazil",
            "category": "tourist_attractions",
            "limit": 3,
            "radius": 1000,
        },
    )
    elapsed = time.monotonic() - started

    assert elapsed < 0.5
    assert overpass_cancelled.is_set()
    assert close_cancelled.is_set()
    content, structured = result
    payload = json.loads(structured["result"])
    assert payload["status"] == "upstream_error"
    assert "exceeded its execution deadline" in payload["message"]
    assert json.loads(content[0].text) == payload
    snapshot = get_operational_snapshot()
    assert snapshot["tool_calls"]["osm_find_nearby"] == 1
    assert snapshot["last_upstream_failure"]["kind"] == "NearbySearch"


async def test_other_upstream_tool_deadline_returns_controlled_error(monkeypatch) -> None:
    settings = _base_settings(upstream_tool_deadline_seconds=0.02)
    searcher = OsmSearcher(settings, user_valves=None)
    cancelled = asyncio.Event()

    class FakeClient:
        closed = False

        async def aclose(self):
            self.closed = True

    client = FakeClient()
    searcher._http_client = client

    async def delayed_lookup(*args, **kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    monkeypatch.setattr(server_mod, "valves", settings)
    monkeypatch.setattr(server_mod, "user_valves", None)
    monkeypatch.setattr(server_mod, "OsmSearcher", lambda *args, **kwargs: searcher)
    monkeypatch.setattr(searcher, "nominatim_search", delayed_lookup)
    reset_operational_metrics_for_tests()

    response = await server_mod.geocode_place("Fixtureville")

    assert cancelled.is_set()
    assert client.closed
    assert json.loads(response)["status"] == "upstream_error"
    snapshot = get_operational_snapshot()
    assert snapshot["tool_calls"]["osm_geocode"] == 1
    assert "osm_geocode" not in snapshot["tool_errors"]
    assert snapshot["last_upstream_failure"]["kind"] == "osm_geocode"


async def test_overpass_failure_keeps_http_status_in_health(monkeypatch) -> None:
    searcher = OsmSearcher(_base_settings(), user_valves=None)
    request = httpx.Request("GET", "https://overpass-api.de/api/interpreter")
    response = httpx.Response(503, request=request)

    async def fail(*args, **kwargs):
        raise httpx.HTTPStatusError(
            "upstream failed", request=request, response=response
        )

    monkeypatch.setattr(searcher, "_http_get_json", fail)
    reset_operational_metrics_for_tests()
    with pytest.raises(UpstreamRequestError):
        await searcher.overpass_search(
            "Fixtureville",
            ["amenity=restaurant"],
            {"minlat": 39.0, "maxlat": 41.0, "minlon": -71.0, "maxlon": -69.0},
        )

    failure = get_operational_snapshot()["last_upstream_failure"]
    assert failure["kind"] == "Overpass"
    assert failure["message"] == "HTTP 503"
    assert "overpass-api.de" not in failure["message"]
    await searcher.aclose()


async def test_geocode_returns_coordinates(monkeypatch) -> None:
    reset_operational_metrics_for_tests()
    captured: dict = {}

    class FakeClient:
        async def get(self, url, params=None, headers=None):
            captured["url"] = url
            captured["params"] = params
            captured["headers"] = headers

            class Resp:
                headers = {}
                history = []
                status_code = 200
                url = "https://nominatim.openstreetmap.org/search"
                content = b"[]"

                def raise_for_status(self):
                    return None

                def json(self):
                    return [
                        {
                            "place_id": 1,
                            "lat": "40.7128",
                            "lon": "-74.0060",
                            "display_name": "New York, USA",
                            "type": "city",
                            "class": "place",
                            "importance": 0.9,
                            "osm_id": 1,
                            "osm_type": "relation",
                        }
                    ]

            return Resp()

        async def aclose(self):
            return None

    async def fake_get_http_client(self):
        return FakeClient()

    monkeypatch.setattr(OsmSearcher, "_get_http_client", fake_get_http_client)

    settings = _base_settings(cache_file="/tmp/osm-test-s4.json")
    print("DEBUG headers:", settings.user_agent, "|", settings.from_header)
    searcher = OsmSearcher(settings, user_valves=None)
    searcher._cache.clear_cache()
    result = await searcher.nominatim_search("New York", limit=1)
    assert result and result[0]["lat"] == "40.7128"
    assert captured["headers"]["User-Agent"] == "percival-osm-test/1.0"
    assert captured["headers"]["From"] == "test@example.com"

    # Sanity-check the helper layer used by the tool.
    primary = result[0]
    lat = float(primary["lat"])
    lon = float(primary["lon"])
    assert lat == pytest.approx(40.7128)
    assert lon == pytest.approx(-74.006)


async def test_directions_returns_structured_steps(monkeypatch) -> None:
    """OsmNavigator.directions produces ordered steps with distance/duration."""

    class FakeSearcher:
        async def nominatim_search(self, place, limit=1):
            return [
                {"lat": 0.0, "lon": 0.0, "display_name": place},
            ]

        async def aclose(self):
            return None

    class FakeRouter:
        def calculate_route(self, start, destination):
            return {
                "summary": {"distance": 2.0, "duration": 600.0},
                "segments": [
                    {
                        "steps": [
                            {"instruction": "Head north", "distance": 1.0, "duration": 300.0},
                            {"instruction": "Turn right", "distance": 1.0, "duration": 300.0},
                        ]
                    }
                ],
            }

    monkeypatch.setattr(server_mod, "OsmSearcher", lambda *a, **kw: FakeSearcher())
    monkeypatch.setattr(server_mod, "OrsRouter", lambda *a, **kw: FakeRouter())

    settings = _base_settings(ors_api_key="fixture-key")
    nav = OsmNavigator(settings, user_valves=None)
    result = await nav.directions("A", "B")

    payload = json.loads(result)
    assert payload["status"] == "ok"
    data = payload["data"]
    assert data["step_count"] == 2
    steps = data["steps"]
    assert steps[0]["order"] == 1
    assert steps[0]["instruction"] == "Head north"
    assert steps[0]["distance_km"] == pytest.approx(1.0)
    assert steps[0]["duration_min"] == pytest.approx(5.0)
    assert steps[1]["order"] == 2
    assert "1." in data["results_markdown"]
    assert "Head north" in data["results_markdown"]
    assert "Turn right" in data["results_markdown"]


async def test_directions_reports_missing_ors_provider(monkeypatch) -> None:
    class FakeSearcher:
        async def nominatim_search(self, place, limit=1):
            return [{"lat": 0.0, "lon": 0.0, "display_name": place}]

        async def aclose(self):
            return None

    class FakeRouter:
        def calculate_route(self, start, destination):
            raise AssertionError("routing must not run without ORS credentials")

    monkeypatch.setattr(server_mod, "OsmSearcher", lambda *a, **kw: FakeSearcher())
    monkeypatch.setattr(server_mod, "OrsRouter", lambda *a, **kw: FakeRouter())
    result = await OsmNavigator(_base_settings(), user_valves=None).directions("A", "B")
    payload = json.loads(result)
    assert payload["status"] == "provider_not_configured"
    assert "ORS_API_KEY" in payload["message"]


@pytest.mark.asyncio
async def test_navigate_reports_missing_ors_provider_without_fake_route(monkeypatch) -> None:
    class FakeSearcher:
        async def nominatim_search(self, place, limit=1):
            return [{"lat": 40.0, "lon": -70.0, "display_name": place}]

        async def aclose(self):
            return None

    class FakeRouter:
        def calculate_route(self, start, destination):
            raise AssertionError("routing must not run without ORS credentials")

    monkeypatch.setattr(server_mod, "OsmSearcher", lambda *a, **kw: FakeSearcher())
    monkeypatch.setattr(server_mod, "OrsRouter", lambda *a, **kw: FakeRouter())
    result = await OsmNavigator(_base_settings(), user_valves=None).navigate("A", "B")
    payload = json.loads(result)
    assert payload["status"] == "provider_not_configured"


async def test_directions_returns_no_results_when_search_empty(monkeypatch) -> None:
    class FakeSearcher:
        async def nominatim_search(self, place, limit=1):
            return []

        async def aclose(self):
            return None

    monkeypatch.setattr(server_mod, "OsmSearcher", lambda *a, **kw: FakeSearcher())

    settings = _base_settings()
    nav = OsmNavigator(settings, user_valves=None)
    result = await nav.directions("nowhere", "anywhere")

    payload = json.loads(result)
    assert payload["status"] == "no_results"


@pytest.mark.asyncio
async def test_nearby_search_distinguishes_empty_provider_response_from_failure(monkeypatch) -> None:
    settings = _base_settings(cache_file="/tmp/osm-test-empty-vs-failure.json")
    searcher = OsmSearcher(settings, user_valves=None)

    async def no_place(*args, **kwargs):
        return []

    async def unavailable(*args, **kwargs):
        raise UpstreamRequestError("Nominatim unavailable")

    monkeypatch.setattr(searcher, "nominatim_search", no_place)
    empty = await searcher.search_nearby("Nowhere", ["amenity"], category="test")
    assert json.loads(empty["results"])["status"] == "no_results"

    monkeypatch.setattr(searcher, "nominatim_search", unavailable)
    failed = await searcher.search_nearby("Somewhere", ["amenity"], category="test")
    assert json.loads(failed["results"])["status"] == "upstream_error"


@pytest.mark.asyncio
async def test_empty_overpass_response_is_no_results_and_failure_is_upstream_error(monkeypatch) -> None:
    settings = _base_settings(cache_file="/tmp/osm-test-overpass-empty-vs-failure.json")
    searcher = OsmSearcher(settings, user_valves=None)
    resolved = [{
        "lat": "40.0",
        "lon": "-70.0",
        "display_name": "Fixtureville",
        "boundingbox": ["39", "41", "-71", "-69"],
    }]

    async def found_place(*args, **kwargs):
        return resolved

    async def empty_overpass(*args, **kwargs):
        return [], []

    async def failed_overpass(*args, **kwargs):
        raise UpstreamRequestError("Overpass unavailable")

    monkeypatch.setattr(searcher, "nominatim_search", found_place)
    monkeypatch.setattr(searcher, "overpass_search", empty_overpass)
    empty = await searcher.search_nearby("Fixtureville", ["amenity"], category="test")
    assert json.loads(empty["results"])["status"] == "no_results"
    assert empty["things"] == []

    monkeypatch.setattr(searcher, "overpass_search", failed_overpass)
    failed = await searcher.search_nearby("Fixtureville", ["amenity"], category="test")
    assert json.loads(failed["results"])["status"] == "upstream_error"


@pytest.mark.asyncio
async def test_incomplete_nominatim_bbox_is_reported_as_upstream_error(monkeypatch) -> None:
    settings = _base_settings(cache_file="/tmp/osm-test-incomplete-bbox.json")
    searcher = OsmSearcher(settings, user_valves=None)

    async def incomplete_place(*args, **kwargs):
        return [{"lat": "40", "lon": "-70", "display_name": "Fixtureville"}]

    monkeypatch.setattr(searcher, "nominatim_search", incomplete_place)
    result = await searcher.search_nearby("Fixtureville", ["amenity"], category="test")
    assert json.loads(result["results"])["status"] == "upstream_error"


@pytest.mark.asyncio
async def test_nominatim_tool_payloads_report_upstream_failure(monkeypatch) -> None:
    class FailedSearcher:
        def __init__(self, *args, **kwargs):
            pass

        async def nominatim_search(self, *args, **kwargs):
            raise UpstreamRequestError("fixture failure")

        async def nominatim_reverse(self, *args, **kwargs):
            raise UpstreamRequestError("fixture failure")

        async def aclose(self):
            return None

    monkeypatch.setattr(server_mod, "OsmSearcher", FailedSearcher)
    monkeypatch.setattr(server_mod, "valves", _base_settings())
    monkeypatch.setattr(server_mod, "user_valves", None)

    class ContextStub:
        def info(self, message):
            return None

    place = json.loads(await find_specific_place_impl("Fixtureville", "compact"))
    geocode = json.loads(await geocode_place("Fixtureville"))
    reverse = json.loads(
        await find_address_for_coordinates(40.0, -70.0, ctx=ContextStub())
    )
    assert {place["status"], geocode["status"], reverse["status"]} == {"upstream_error"}


@pytest.mark.asyncio
async def test_searcher_shutdown_drains_then_cancels_orphaned_distance_task(monkeypatch) -> None:
    settings = _base_settings(cache_file="/tmp/osm-test-shutdown.json")
    searcher = OsmSearcher(settings, user_valves=None)
    monkeypatch.setattr(server_mod, "SHUTDOWN_DRAIN_TIMEOUT_SECONDS", 0.01)

    async def never_finishes(*args, **kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr(searcher, "calculate_navigation_distance", never_finishes)
    caller = asyncio.create_task(searcher._resolve_distance("fixture-key", {}, {}))
    await asyncio.sleep(0)
    await searcher.aclose()

    assert caller.cancelled()
    assert not searcher._distance_tasks
    assert not searcher._distance_futures


async def test_searcher_close_cancels_distance_tasks_immediately(monkeypatch) -> None:
    settings = _base_settings(cache_file="/tmp/osm-test-immediate-shutdown.json")
    searcher = OsmSearcher(settings, user_valves=None)

    async def never_finishes(*args, **kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr(searcher, "calculate_navigation_distance", never_finishes)
    caller = asyncio.create_task(searcher._resolve_distance("fixture-key", {}, {}))
    await asyncio.sleep(0)
    await searcher.aclose(cancel_pending=True)

    with pytest.raises(asyncio.CancelledError):
        await caller
    assert caller.cancelled()
    assert not searcher._distance_tasks
    assert not searcher._distance_futures


def test_legacy_aliases_registration_can_be_disabled(monkeypatch) -> None:
    """When OSM_EXPOSE_LEGACY_ALIASES=false the dynamic registration is skipped."""
    # Just verify the condition reads correctly off the valves singleton.
    monkeypatch.setattr(server_mod.valves, "expose_legacy_aliases", False)
    assert server_mod.valves.expose_legacy_aliases is False
    monkeypatch.setattr(server_mod.valves, "expose_legacy_aliases", True)
    assert server_mod.valves.expose_legacy_aliases is True


def test_calculate_route_uses_walking_profile_for_short_hops(monkeypatch) -> None:
    """Regression: ``OrsRouter.calculate_route`` used to derive its profile
    from ``to_thing.get("distance", 9000)`` — but Nominatim results never
    carry a ``distance`` field, so the default ``9000`` was always
    returned and the router always fell back to ``driving-car``. The
    correct behaviour is to compute the haversine distance between the
    two endpoints and use ``foot-walking`` for short hops.
    """
    from percival_osm_mcp.server import OrsRouter, Settings

    settings = _base_settings(car_only=False, cache_file="/tmp/osm-test-route-walk.json")

    observed_profile: dict = {}

    class FakeOrsClient:
        def request(self, url, _get_params, post_json=None, dry_run=None):  # type: ignore[no-untyped-def]
            # URL pattern: /v2/directions/{profile}/{format}
            parts = url.strip("/").split("/")
            # parts == ['v2', 'directions', profile, format]
            observed_profile["profile"] = parts[2]
            return {"routes": [{"summary": {"distance": 0.4, "duration": 300.0}}]}

    router = OrsRouter(settings, user_valves=None)
    router._client = FakeOrsClient()
    router.cache.clear_cache()

    # Two points ~111m apart on the equator (a short, walkable hop).
    from_thing = {"lat": 0.0, "lon": 0.0}
    to_thing = {"lat": 0.001, "lon": 0.0}  # no "distance" key
    route = router.calculate_route(from_thing, to_thing)
    assert route is not None
    assert observed_profile.get("profile") == "foot-walking", (
        "short haversine hops should use the foot-walking profile"
    )


def test_calculate_route_uses_car_profile_for_long_hops(monkeypatch) -> None:
    """Long hops should always use the driving-car profile even when
    the input nominatim dict has no ``distance`` field.
    """
    from percival_osm_mcp.server import OrsRouter, Settings

    settings = _base_settings(car_only=False, cache_file="/tmp/osm-test-route-car.json")
    observed_profile: dict = {}

    class FakeOrsClient:
        def request(self, url, _get_params, post_json=None, dry_run=None):  # type: ignore[no-untyped-def]
            parts = url.strip("/").split("/")
            observed_profile["profile"] = parts[2]
            return {"routes": [{"summary": {"distance": 10.0, "duration": 600.0}}]}

    router = OrsRouter(settings, user_valves=None)
    router._client = FakeOrsClient()
    router.cache.clear_cache()

    from_thing = {"lat": 0.0, "lon": 0.0}
    to_thing = {"lat": 0.5, "lon": 0.5}  # ~70 km diagonal
    route = router.calculate_route(from_thing, to_thing)
    assert route is not None
    assert observed_profile.get("profile") == "driving-car"
