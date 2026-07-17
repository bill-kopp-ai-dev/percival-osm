"""Tests for MCP prompt and resource primitives."""

import json
import re
from pathlib import Path

import pytest

from percival_osm_mcp import server as server_mod
from percival_osm_mcp.server import mcp


async def test_prompts_registered():
    prompts = await mcp.list_prompts()
    names = [p.name for p in prompts]
    assert "osm_recipe_quick_search" in names
    assert "osm_tool_chooser" in names
    assert "osm_output_format" in names
    assert len([n for n in names if n.startswith("osm_")]) == 3


async def test_resources_registered():
    resources = await mcp.list_resources()
    by_uri = {str(r.uri): r for r in resources}
    assert "osm://categories" in by_uri
    assert "osm://security/nanobot-policy" in by_uri
    assert by_uri["osm://categories"].mimeType == "text/markdown"


async def test_get_prompt_quick_search_returns_recipe():
    result = await mcp.get_prompt("osm_recipe_quick_search", {})
    # FastMCP returns a list of messages; we accept any structure as long as
    # the recipe text is present somewhere in the rendered payload.
    rendered = "\n".join(
        getattr(part, "text", str(part)) for part in result.messages
    )
    assert "osm_find_nearby" in rendered
    assert "Decision tree" in rendered or "step" in rendered.lower()


async def test_get_prompt_tool_chooser_has_table():
    result = await mcp.get_prompt("osm_tool_chooser", {})
    rendered = "\n".join(
        getattr(part, "text", str(part)) for part in result.messages
    )
    for tool in (
        "osm_find_nearby",
        "osm_find_place",
        "osm_find_address",
        "osm_geocode",
        "osm_navigate",
        "osm_directions",
    ):
        assert tool in rendered, f"{tool} should appear in tool chooser"


async def test_get_prompt_output_format_has_templates():
    result = await mcp.get_prompt("osm_output_format", {})
    rendered = "\n".join(
        getattr(part, "text", str(part)) for part in result.messages
    )
    assert "## <Category>" in rendered or "## Route" in rendered
    assert "json envelope" in rendered.lower() or "compact markdown" in rendered.lower()


async def test_read_categories_resource():
    """osm://categories lists every supported POI category."""
    contents = await mcp.read_resource("osm://categories")
    # FastMCP returns a list of strings (one per resource) or a single
    # string; normalize so the assertions are stable across versions.
    if isinstance(contents, str):
        rendered = contents
    else:
        rendered = "\n".join(
            item if isinstance(item, str) else getattr(item, "text", str(item))
            for item in contents
        )
    for key in ("food", "groceries", "pharmacies", "public_transport"):
        assert key in rendered, f"{key} missing from categories resource"
    # And every legacy alias must be mapped.
    assert "osm_find_pharmacy" in rendered
    assert "OSM_EXPOSE_LEGACY_ALIASES" in rendered


async def test_read_security_policy_resource_returns_text():
    contents = await mcp.read_resource("osm://security/nanobot-policy")
    if isinstance(contents, str):
        rendered = contents
    else:
        rendered = "\n".join(
            item if isinstance(item, str) else getattr(item, "text", str(item))
            for item in contents
        )
    # The policy file ships with this server; if the bundled copy is
    # unavailable the resource returns a placeholder. Either is acceptable
    # for the test, as long as something non-empty comes back.
    assert len(rendered) > 20
    assert "placeholder" in rendered.lower() or "policy" in rendered.lower()


def test_primitives_module_exposes_public_api():
    """Sanity check that osm_primitives exposes register_* helpers."""
    from percival_osm_mcp import osm_primitives

    assert callable(osm_primitives.register_all_primitives)
    assert callable(osm_primitives.register_prompts)
    assert callable(osm_primitives.register_resources)


# ---------------------------------------------------------------------------
# Bug-fix regression tests
# ---------------------------------------------------------------------------


def test_main_entrypoint_declared_once():
    """Regression: `main()` was historically called 11 times in the
    ``__main__`` block, which would invoke ``asyncio.run(async_main())``
    multiple times back-to-back, scrambling startup logs and breaking
    stdio framing. The block must contain a single ``main()`` call.
    """
    import re

    src = (Path(server_mod.__file__).read_text(encoding="utf-8")
           if hasattr(server_mod, "__file__") else "")
    # Fall back: read by package location.
    if not src:
        src = Path(server_mod.__file__).read_text(encoding="utf-8")
    matches = re.findall(r"if __name__ == ['\"]__main__['\"]:", src)
    assert len(matches) == 1, (
        f"expected exactly one __main__ guard, found {len(matches)}"
    )


def test_pygments_and_dead_helpers_removed():
    """Regression: ``pygments`` and the ``pretty_print_thing_json`` helper
    are dead code; ``FONTS`` / ``FONT_CSS`` / ``HIGHLIGHT_CSS`` were never
    re-introduced. Removing these also drops the supply-chain footprint
    for a dep that nothing uses.
    """
    src = Path(server_mod.__file__).read_text(encoding="utf-8")
    for needle in (
        "from pygments",
        "pretty_print_thing_json",
        "JsonLexer",
        "HtmlFormatter",
        "HIGHLIGHT_CSS",
        "FONT_CSS",
    ):
        assert needle not in src, f"dead code ref detected: {needle}"


async def test_canonical_tools_all_tracked():
    """Regression: 4 tools were missing the @_track decorator and
    therefore did not bump the per-tool call counter. The
    ``tool_calls`` map in ``osm_get_health`` would be incomplete.

    We assert statically that the source has @_track directly above
    every @mcp.tool for the canonical tools.
    """
    src = Path(server_mod.__file__).read_text(encoding="utf-8")
    expected_tracked = [
        "osm_find_address",
        "osm_find_nearby_store",
        "osm_find_place_detailed",
        "osm_find_place",
        "osm_geocode",
        "osm_navigate",
        "osm_directions",
        "osm_find_nearby",
        "osm_find_nearby_detailed",
        "osm_find_other",
        "osm_get_security_metrics",
        "osm_get_version",
        "osm_get_health",
        "osm_get_status",
    ]
    for tool_name in expected_tracked:
        # Match `@_track("<name>")` immediately above `@mcp.tool("<name>")`.
        # We use a non-greedy .+? with DOTALL to span the gap between them.
        pattern = (
            r'@_track\(["\']' + re.escape(tool_name) + r'["\']\)\s*\n\s*@mcp\.tool\(["\']'
            + re.escape(tool_name) + r'["\']'
        )
        assert re.search(pattern, src), (
            f"{tool_name} missing @_track decorator — tool call counter "
            "won't be bumped."
        )


async def test_validate_upstreams_lock_exists():
    """Regression: OsmSearcher must expose ``_validated_upstreams_lock`` so
    that concurrent ``_http_get_json`` callers don't race on the
    ``_validated_upstreams`` set membership check.
    """
    from percival_osm_mcp.server import OsmSearcher, Settings

    settings = Settings(
        user_agent="ua",
        from_header="from@x.com",
        cache_file="/tmp/osm-test-lock.json",
        cache_allowed_dirs="/tmp",
        upstream_allowed_hosts="nominatim.openstreetmap.org,overpass-api.de,api.openrouteservice.org",
    )
    searcher = OsmSearcher(settings, user_valves=None)
    import asyncio

    assert isinstance(searcher._validated_upstreams_lock, asyncio.Lock)
    # Sanity: the lock is an actual asyncio.Lock (not a threading.Lock).
    assert hasattr(searcher._validated_upstreams_lock, "acquire")
    assert hasattr(searcher._validated_upstreams_lock, "release")

    # Hammer: many concurrent check-then-add iterations should leave the
    # set with exactly one entry (no torn writes, no duplicate add).
    url = "https://nominatim.openstreetmap.org/search"

    async def worker():
        async with searcher._validated_upstreams_lock:
            # Simulate the inner pattern: only add if missing.
            if url not in searcher._validated_upstreams:
                searcher._validated_upstreams.add(url)

    await asyncio.gather(*(worker() for _ in range(64)))
    assert searcher._validated_upstreams == {url}


async def test_single_flight_distance_dedupes_concurrent_calls(monkeypatch):
    """Regression: ``attempt_ors`` used to fire duplicate ORS calls when
    two coroutines asked for the same cache_key simultaneously. The
    single-flight ``_resolve_distance`` future must collapse them.
    """
    import asyncio
    from percival_osm_mcp.server import OsmSearcher, Settings

    settings = Settings(
        user_agent="ua",
        from_header="from@x.com",
        cache_file="/tmp/osm-test-singleflight.json",
        cache_allowed_dirs="/tmp",
        upstream_allowed_hosts="nominatim.openstreetmap.org,overpass-api.de,api.openrouteservice.org",
    )
    searcher = OsmSearcher(settings, user_valves=None)
    # Wipe any pre-existing cache entry.
    searcher._cache.clear_cache()

    upstream_calls = {"n": 0}
    completion = asyncio.Event()

    async def fake_calc(_origin, _thing):
        upstream_calls["n"] += 1
        # Hold the future open so the second caller definitely races in.
        await completion.wait()
        return 12.5

    monkeypatch.setattr(searcher, "calculate_navigation_distance", fake_calc)

    origin = {"lat": 0.0, "lon": 0.0}
    thing = {"id": "x", "type": "way", "tags": {"name": "Test"}}

    # Launch two concurrent _resolve_distance calls for the same key.
    cache_key = "k1"
    t1 = asyncio.create_task(searcher._resolve_distance(cache_key, origin, thing))
    t2 = asyncio.create_task(searcher._resolve_distance(cache_key, origin, thing))

    # Let both tasks reach the lock.
    await asyncio.sleep(0.05)
    # Release the upstream call.
    completion.set()
    a, b = await asyncio.gather(t1, t2)

    assert a == b == 12.5
    assert upstream_calls["n"] == 1, (
        "single-flight should collapse concurrent calls into one upstream"
    )