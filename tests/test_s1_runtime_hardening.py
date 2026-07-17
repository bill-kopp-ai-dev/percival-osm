import os
import stat
from pathlib import Path

import pytest

import percival_osm_mcp.server as server_mod
from percival_osm_mcp.server import (
    OsmCache,
    OsmSearcher,
    Settings,
    get_security_metrics_snapshot,
    reset_security_metrics_for_tests,
    resolve_secure_cache_path,
    validate_upstream_url_policy,
)


def _base_settings(**overrides):
    values = {
        "upstream_allowed_hosts": "nominatim.openstreetmap.org,overpass-api.de,api.openrouteservice.org",
        "cache_allowed_dirs": "/tmp",
        "cache_file": "/tmp/osm-cache.json",
    }
    values.update(overrides)
    return Settings(**values)


def test_validate_upstream_policy_rejects_http_when_https_required() -> None:
    reset_security_metrics_for_tests()
    settings = _base_settings(require_https_upstreams=True)
    with pytest.raises(ValueError, match="must use https"):
        validate_upstream_url_policy(
            "http://nominatim.openstreetmap.org/search",
            settings=settings,
            label="nominatim_url",
        )
    metrics = get_security_metrics_snapshot()
    assert metrics.get("upstream_url_blocked", 0) >= 1


def test_validate_upstream_policy_rejects_non_allowlisted_host() -> None:
    reset_security_metrics_for_tests()
    settings = _base_settings()
    with pytest.raises(ValueError, match="not in OSM_UPSTREAM_ALLOWED_HOSTS"):
        validate_upstream_url_policy(
            "https://example.com/search",
            settings=settings,
            label="nominatim_url",
        )
    metrics = get_security_metrics_snapshot()
    assert metrics.get("upstream_url_blocked", 0) >= 1


def test_validate_upstream_policy_rejects_private_target() -> None:
    reset_security_metrics_for_tests()
    settings = _base_settings(upstream_allowed_hosts="127.0.0.1")
    with pytest.raises(ValueError, match="private/local host"):
        validate_upstream_url_policy(
            "https://127.0.0.1/search",
            settings=settings,
            label="nominatim_url",
        )
    metrics = get_security_metrics_snapshot()
    assert metrics.get("upstream_url_blocked", 0) >= 1


def test_resolve_secure_cache_path_rejects_outside_allowed_dirs(tmp_path: Path) -> None:
    reset_security_metrics_for_tests()
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir(parents=True, exist_ok=True)
    outside.mkdir(parents=True, exist_ok=True)
    settings = _base_settings(cache_allowed_dirs=str(allowed))
    blocked = outside / "cache.json"
    with pytest.raises(ValueError, match="OSM_CACHE_ALLOWED_DIRS"):
        resolve_secure_cache_path(str(blocked), settings=settings)
    metrics = get_security_metrics_snapshot()
    assert metrics.get("cache_path_blocked", 0) >= 1


def test_osm_cache_persist_enforces_0600(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "osm-cache.json"
    settings = _base_settings(
        cache_allowed_dirs=str(cache_dir),
        cache_file=str(cache_file),
    )
    cache = OsmCache(settings=settings, filename=str(cache_file), default_ttl_seconds=30)
    cache.set("k", {"v": 1})
    mode = stat.S_IMODE(os.stat(cache_file).st_mode)
    assert mode == 0o600


@pytest.mark.asyncio
async def test_http_get_json_uses_follow_redirect_setting_and_size_limit(monkeypatch) -> None:
    reset_security_metrics_for_tests()
    observed = {}

    class DummyResponse:
        def __init__(self):
            self.headers = {"content-length": "999999"}
            self.history = []
            self.url = "https://nominatim.openstreetmap.org/search"
            self.content = b"{}"

        def raise_for_status(self):
            return None

        def json(self):
            return {}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            observed["follow_redirects"] = kwargs.get("follow_redirects")

        async def get(self, url, params=None, headers=None):
            return DummyResponse()

        async def aclose(self):
            return None

    async def fake_get_http_client(self):
        # Mirror the production wiring: the shared client is built with
        # follow_redirects sourced from the searcher's valves.
        return DummyClient(follow_redirects=self.valves.http_follow_redirects)

    monkeypatch.setattr(OsmSearcher, "_get_http_client", fake_get_http_client)

    settings = _base_settings(
        http_follow_redirects=False,
        http_max_response_bytes=1024,
    )
    searcher = OsmSearcher(settings, user_valves=None, event_emitter=None)
    with pytest.raises(ValueError, match="OSM_HTTP_MAX_RESPONSE_BYTES"):
        await searcher._http_get_json(
            "https://nominatim.openstreetmap.org/search",
            params={"q": "x"},
            headers={"User-Agent": "ua", "From": "from@example.com"},
        )
    # The shared client is created lazily on first request and must honor
    # the configured follow_redirects setting.
    assert searcher.valves.http_follow_redirects is False
    assert observed["follow_redirects"] is False
    metrics = get_security_metrics_snapshot()
    assert metrics.get("upstream_response_blocked", 0) >= 1


@pytest.mark.asyncio
async def test_http_get_json_validates_redirect_chain(monkeypatch) -> None:
    class Hop:
        def __init__(self, url: str):
            self.url = url

    class DummyResponse:
        def __init__(self):
            self.headers = {"content-length": "2"}
            self.history = [Hop("https://127.0.0.1/internal")]
            self.url = "https://nominatim.openstreetmap.org/search"
            self.content = b"{}"

        def raise_for_status(self):
            return None

        def json(self):
            return {}

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def get(self, url, params=None, headers=None):
            return DummyResponse()

        async def aclose(self):
            return None

    async def fake_get_http_client(self):
        return DummyClient()

    monkeypatch.setattr(OsmSearcher, "_get_http_client", fake_get_http_client)

    settings = _base_settings(http_follow_redirects=True, http_max_response_bytes=1024)
    searcher = OsmSearcher(settings, user_valves=None, event_emitter=None)
    with pytest.raises(ValueError, match="private/local host"):
        await searcher._http_get_json(
            "https://nominatim.openstreetmap.org/search",
            params={"q": "x"},
            headers={"User-Agent": "ua", "From": "from@example.com"},
        )
