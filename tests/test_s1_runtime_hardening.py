import os
import stat
from pathlib import Path

import pytest
import httpx

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


def test_runtime_configuration_rejects_nominatim_search_endpoint() -> None:
    from percival_osm_mcp.server import validate_upstream_runtime_configuration

    settings = _base_settings(nominatim_url="https://nominatim.openstreetmap.org/search")
    with pytest.raises(ValueError, match="nominatim_url"):
        validate_upstream_runtime_configuration(settings)


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
            self.status_code = 200
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
        # Redirects are handled one hop at a time after URL policy validation.
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
            self.headers = {"content-length": "2", "location": "https://127.0.0.1/internal"}
            self.status_code = 302
            self.history = []
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
            observed_urls.append(url)
            return DummyResponse()

        async def aclose(self):
            return None

    async def fake_get_http_client(self):
        return DummyClient()

    monkeypatch.setattr(OsmSearcher, "_get_http_client", fake_get_http_client)

    settings = _base_settings(http_follow_redirects=True, http_max_response_bytes=1024)
    observed_urls = []
    searcher = OsmSearcher(settings, user_valves=None, event_emitter=None)
    with pytest.raises(ValueError, match="private/local host"):
        await searcher._http_get_json(
            "https://nominatim.openstreetmap.org/search",
            params={"q": "x"},
            headers={"User-Agent": "ua", "From": "from@example.com"},
        )
    assert len(observed_urls) == 1


@pytest.mark.asyncio
async def test_http_get_json_does_not_follow_redirect_when_disabled(monkeypatch) -> None:
    observed_urls = []

    class DummyResponse:
        headers = {"content-length": "2", "location": "https://overpass-api.de/allowed"}
        status_code = 302
        history = []
        url = "https://nominatim.openstreetmap.org/search"
        content = b"{}"

        def raise_for_status(self):
            return None

        def json(self):
            return {}

    class DummyClient:
        async def get(self, url, params=None, headers=None):
            observed_urls.append(url)
            return DummyResponse()

    async def fake_get_http_client(self):
        return DummyClient()

    monkeypatch.setattr(OsmSearcher, "_get_http_client", fake_get_http_client)
    settings = _base_settings(http_follow_redirects=False, http_max_response_bytes=1024)
    searcher = OsmSearcher(settings, user_valves=None, event_emitter=None)

    await searcher._http_get_json(
        "https://nominatim.openstreetmap.org/search",
        params={"q": "fixture"},
        headers={"User-Agent": "ua", "From": "from@example.com"},
    )

    assert observed_urls == ["https://nominatim.openstreetmap.org/search"]


@pytest.mark.asyncio
async def test_http_get_json_allows_validated_allowlisted_redirect(monkeypatch) -> None:
    observed_urls = []

    class Redirect:
        headers = {"content-length": "2", "location": "https://overpass-api.de/allowed"}
        status_code = 302
        history = []
        url = "https://nominatim.openstreetmap.org/search"
        content = b"{}"

        def raise_for_status(self):
            return None

        def json(self):
            return {}

    class Success:
        headers = {"content-length": "2"}
        status_code = 200
        history = []
        url = "https://overpass-api.de/allowed"
        content = b"{}"

        def raise_for_status(self):
            return None

        def json(self):
            return {"allowed": True}

    class DummyClient:
        async def get(self, url, params=None, headers=None):
            observed_urls.append(url)
            return Redirect() if len(observed_urls) == 1 else Success()

    async def fake_get_http_client(self):
        return DummyClient()

    monkeypatch.setattr(OsmSearcher, "_get_http_client", fake_get_http_client)
    settings = _base_settings(http_follow_redirects=True, http_max_response_bytes=1024)
    searcher = OsmSearcher(settings, user_valves=None, event_emitter=None)

    result = await searcher._http_get_json(
        "https://nominatim.openstreetmap.org/search",
        params={"q": "fixture"},
        headers={"User-Agent": "ua", "From": "from@example.com"},
    )

    assert result == {"allowed": True}
    assert observed_urls == [
        "https://nominatim.openstreetmap.org/search",
        "https://overpass-api.de/allowed",
    ]


@pytest.mark.asyncio
async def test_nominatim_http_failures_raise_explicit_upstream_error(monkeypatch, caplog) -> None:
    settings = _base_settings(
        user_agent="percival-osm-test/1.0",
        from_header="test@example.com",
        http_max_retries=0,
    )
    searcher = OsmSearcher(settings, user_valves=None)

    class FailingClient:
        async def get(self, url, params=None, headers=None):
            request = httpx.Request("GET", url, params=params)
            if params["q"] == "fixture-429":
                response = httpx.Response(429, request=request)
                raise httpx.HTTPStatusError("rate limited", request=request, response=response)
            if params["q"] == "fixture-503":
                response = httpx.Response(503, request=request)
                raise httpx.HTTPStatusError("unavailable", request=request, response=response)
            raise httpx.ReadTimeout("private-query-token", request=request)

        async def aclose(self):
            return None

    async def fake_get_http_client(self):
        return FailingClient()

    monkeypatch.setattr(OsmSearcher, "_get_http_client", fake_get_http_client)
    for query in ("fixture-429", "fixture-503", "fixture-timeout"):
        with pytest.raises(server_mod.UpstreamRequestError):
            await searcher.nominatim_search(query, limit=1)

    assert "private-query-token" not in caplog.text
