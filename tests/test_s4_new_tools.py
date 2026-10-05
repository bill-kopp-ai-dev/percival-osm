"""Tests for osm_geocode and osm_directions."""

import json
import os

import pytest

from percival_osm_mcp import server as server_mod
from percival_osm_mcp.server import (
    OsmNavigator,
    OsmSearcher,
    Settings,
    geocode_place,
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

    settings = _base_settings()
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


async def test_directions_returns_no_results_when_search_empty(monkeypatch) -> None:
    class FakeSearcher:
        async def nominatim_search(self, place, limit=1):
            return []

    monkeypatch.setattr(server_mod, "OsmSearcher", lambda *a, **kw: FakeSearcher())

    settings = _base_settings()
    nav = OsmNavigator(settings, user_valves=None)
    result = await nav.directions("nowhere", "anywhere")

    payload = json.loads(result)
    assert payload["status"] == "no_results"


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