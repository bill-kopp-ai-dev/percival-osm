import errno
import json

import pytest

from percival_osm_mcp import server as server_mod


def settings_for(path):
    return server_mod.Settings(
        upstream_allowed_hosts="nominatim.openstreetmap.org,overpass-api.de,api.heigit.org",
        cache_allowed_dirs=str(path.parent), cache_file=str(path),
    )


@pytest.mark.parametrize("error_number", [errno.EROFS, errno.EACCES, errno.ENOSPC])
def test_write_failure_keeps_values_in_shared_memory(tmp_path, monkeypatch, error_number):
    path = tmp_path / f"cache-{error_number}.json"
    cache = server_mod.OsmCache(settings_for(path))
    original_replace = server_mod.os.replace

    def fail_replace(src, dst):
        raise OSError(error_number, "simulated cache storage failure")

    monkeypatch.setattr(server_mod.os, "replace", fail_replace)
    cache.set("key", {"valid": True})
    other = server_mod.OsmCache(settings_for(path))
    assert other.get("key") == {"valid": True}
    snapshot = server_mod.get_operational_snapshot()["cache"]
    assert snapshot["mode"] == "memory"
    assert snapshot["degraded"] is True
    monkeypatch.setattr(server_mod.os, "replace", original_replace)


@pytest.mark.parametrize("content", [b"{", b"\xff", b"[]"])
def test_invalid_cache_file_is_ignored(tmp_path, content):
    path = tmp_path / "cache.json"
    path.write_bytes(content)
    cache = server_mod.OsmCache(settings_for(path))
    cache.set("fresh", 42)
    assert cache.get("fresh") == 42


def test_expired_and_invalid_expiration_are_cache_misses(tmp_path):
    path = tmp_path / "cache.json"
    cache = server_mod.OsmCache(settings_for(path))
    cache.data["entries"]["expired"] = {"value": 1, "expires_at": 0}
    cache.data["entries"]["invalid"] = {"value": 2, "expires_at": "later"}
    assert cache.get("expired") is None
    assert cache.get("invalid") is None


def test_writes_from_separate_instances_are_merged(tmp_path):
    path = tmp_path / "cache.json"
    first = server_mod.OsmCache(settings_for(path))
    second = server_mod.OsmCache(settings_for(path))
    first.set("one", 1)
    second.set("two", 2)
    reloaded = server_mod.OsmCache(settings_for(path))
    assert reloaded.get("one") == 1
    assert reloaded.get("two") == 2
    assert json.loads(path.read_text())["entries"]


def test_provider_identity_partitions_keys(tmp_path):
    path = tmp_path / "cache.json"
    first = server_mod.OsmCache(settings_for(path))
    other_settings = settings_for(path)
    other_settings.nominatim_url = "https://nominatim.openstreetmap.org/alternate"
    second = server_mod.OsmCache(other_settings)
    first.set("same", "first-provider")
    assert second.get("same") is None
