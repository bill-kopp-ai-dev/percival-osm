from __future__ import annotations

from urllib.parse import urlsplit

import pytest

from percival_osm_mcp.server import OrsRouter, Settings, chunk_list


def _settings(tmp_path, **overrides) -> Settings:
    values = {
        "user_agent": "percival-osm-test/1.0",
        "from_header": "test@example.com",
        "ors_api_key": "test-ors-key",
        "cache_file": str(tmp_path / "cache.json"),
        "cache_allowed_dirs": str(tmp_path),
        "upstream_allowed_hosts": (
            "nominatim.openstreetmap.org,overpass-api.de,api.heigit.org"
        ),
    }
    values.update(overrides)
    return Settings(**values)


def test_ors_directions_uses_heigit_prefix_json_and_lon_lat(tmp_path) -> None:
    captured: dict[str, object] = {}

    class Response:
        status_code = 200
        request = None

        def json(self):
            return {
                "routes": [
                    {"summary": {"distance": 2.3, "duration": 300}, "segments": []}
                ]
            }

    class Session:
        get = None

        def post(self, url, **kwargs):
            captured["url"] = url
            captured.update(kwargs)
            return Response()

    settings = _settings(
        tmp_path,
        ors_instance="https://api.heigit.org/openrouteservice///",
    )
    router = OrsRouter(settings, user_valves=None)
    router._client._session = Session()

    route = router.calculate_route(
        {"lat": 52.0, "lon": 13.0},
        {"lat": 52.001, "lon": 13.002},
    )

    assert route is not None
    parsed_url = urlsplit(captured["url"])
    assert (parsed_url.scheme, parsed_url.netloc, parsed_url.path) == (
        "https",
        "api.heigit.org",
        "/openrouteservice/v2/directions/foot-walking/json",
    )
    assert parsed_url.query == ""
    assert captured["json"]["coordinates"] == ((13.0, 52.0), (13.002, 52.001))
    assert captured["headers"]["Authorization"] == "test-ors-key"


def test_ors_instance_override_remains_subject_to_allowlist(tmp_path) -> None:
    settings = _settings(
        tmp_path,
        ors_instance="https://routing.example.test/openrouteservice",
    )

    with pytest.raises(ValueError, match="not in OSM_UPSTREAM_ALLOWED_HOSTS"):
        OrsRouter(settings, user_valves=None)


def test_ors_default_base_uses_heigit_service_prefix(tmp_path) -> None:
    router = OrsRouter(_settings(tmp_path, ors_instance=None), user_valves=None)

    assert router._client._base_url == "https://api.heigit.org/openrouteservice"


def test_legacy_ors_url_environment_alias_is_preserved(monkeypatch) -> None:
    monkeypatch.setenv("USER_AGENT", "percival-osm-test/1.0")
    monkeypatch.setenv("FROM_HEADER", "test@example.com")
    monkeypatch.setenv("ORS_URL", "https://router.example.test/openrouteservice")
    monkeypatch.delenv("ORS_INSTANCE", raising=False)

    assert Settings().ors_instance == "https://router.example.test/openrouteservice"


def test_chunk_list_works_without_itertools_batched() -> None:
    assert chunk_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert chunk_list([], 2) == []
    with pytest.raises(ValueError, match="chunk_size must be at least one"):
        chunk_list([1], 0)
