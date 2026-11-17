import pytest

from percival_osm_mcp import server as server_mod
from percival_osm_mcp.server import OsmSearcher, Settings, UpstreamRequestError


def make_searcher(tmp_path):
    settings = Settings(
        user_agent="test/1.0",
        from_header="test@example.com",
        cache_file=str(tmp_path / "cache.json"),
        cache_allowed_dirs=str(tmp_path),
    )
    return OsmSearcher(settings, None)


@pytest.mark.parametrize(
    ("point", "valid"),
    [
        ({"lat": 90, "lon": 180}, True),
        ({"lat": -90, "lon": -180}, True),
        ({"lat": 90.01, "lon": 0}, False),
        ({"lat": 0, "lon": float("nan")}, False),
        ({"lat": 1}, False),
        ({}, True),
    ],
)
def test_coordinate_validation(point, valid):
    assert server_mod._valid_coordinate_pair(point) is valid


@pytest.mark.asyncio
async def test_nominatim_search_explicit_json_and_rejects_semantic_error(tmp_path, monkeypatch):
    searcher = make_searcher(tmp_path)
    requests = []

    async def response(_url, params, **_kwargs):
        requests.append(params)
        return [{"lat": "1", "lon": "2", "display_name": "fixture"}]

    monkeypatch.setattr(searcher, "_http_get_json", response)
    assert await searcher.nominatim_search("fixture")
    assert requests[0]["format"] == "json"

    async def semantic_error(*_args, **_kwargs):
        return {"error": "invalid query"}

    monkeypatch.setattr(searcher, "_http_get_json", semantic_error)
    with pytest.raises(UpstreamRequestError):
        await searcher.nominatim_search("fixture", limit=2)
    await searcher.aclose()


@pytest.mark.asyncio
async def test_lookup_matches_typed_osm_identity(tmp_path, monkeypatch):
    searcher = make_searcher(tmp_path)
    captured = {}

    async def lookup(_url, params, **_kwargs):
        captured.update(params)
        return [
            {"osm_type": "node", "osm_id": 17, "address": {"road": "Node Road"}},
            {"osm_type": "way", "osm_id": 17, "address": {"road": "Way Road"}},
            {"osm_type": "relation", "osm_id": 17, "address": {"road": "Relation Road"}},
        ]

    monkeypatch.setattr(searcher, "_http_get_json", lookup)
    things = [
        {"type": "node", "id": 17, "tags": {"amenity": "cafe"}},
        {"type": "way", "id": 17, "tags": {"amenity": "cafe"}},
        {"type": "relation", "id": 17, "tags": {"amenity": "cafe"}},
    ]
    result = await searcher.nominatim_lookup_by_id(things)
    assert captured["format"] == "json"
    assert captured["osm_ids"] == "N17,W17,R17"
    assert [thing["tags"]["addr:road"] for thing in result] == [
        "Node Road", "Way Road", "Relation Road"
    ]
    await searcher.aclose()


@pytest.mark.asyncio
async def test_nominatim_lookup_requests_are_chunked_at_fifty(tmp_path, monkeypatch):
    searcher = make_searcher(tmp_path)
    sizes = []

    async def empty_lookup(_url, params, **_kwargs):
        sizes.append(len(params["osm_ids"].split(",")))
        return []

    monkeypatch.setattr(searcher, "_http_get_json", empty_lookup)
    things = [
        {"type": "node", "id": idx, "tags": {"amenity": "cafe"}}
        for idx in range(51)
    ]
    assert await searcher.nominatim_lookup_by_id(things) == []
    assert sizes == [50, 1]
    await searcher.aclose()


@pytest.mark.asyncio
async def test_overpass_relations_center_timestamp_and_partial_response(tmp_path, monkeypatch):
    searcher = make_searcher(tmp_path)
    requests = []

    async def response(_url, params, **_kwargs):
        requests.append(params["data"])
        return {
            "elements": [
                {
                    "type": "relation",
                    "id": 17,
                    "center": {"lat": 1.25, "lon": 2.5},
                    "tags": {"amenity": "cafe", "name": "Fixture Cafe"},
                }
            ],
            "osm3s": {"timestamp_osm_base": "2026-11-17T00:00:00Z"},
        }

    monkeypatch.setattr(searcher, "_http_get_json", response)
    nodes, ways = await searcher.overpass_search(
        "fixture", ["amenity=cafe"],
        {"minlat": 1, "maxlat": 2, "minlon": 2, "maxlon": 3},
    )
    assert not nodes
    assert ways[0]["type"] == "relation"
    assert (ways[0]["lat"], ways[0]["lon"]) == (1.25, 2.5)
    assert searcher._overpass_base_timestamp == "2026-11-17T00:00:00Z"
    assert "out center;" in requests[0]

    async def partial(_url, params, **_kwargs):
        return {"elements": [], "remark": "runtime error"}

    monkeypatch.setattr(searcher, "_http_get_json", partial)
    with pytest.raises(UpstreamRequestError):
        await searcher.overpass_search(
            "another fixture", ["amenity=cafe"],
            {"minlat": 1, "maxlat": 2, "minlon": 2, "maxlon": 3},
        )
    await searcher.aclose()


@pytest.mark.asyncio
async def test_ors_failure_does_not_become_route_distance(tmp_path, monkeypatch):
    searcher = make_searcher(tmp_path)

    async def fail(*_args, **_kwargs):
        raise UpstreamRequestError("fixture ORS failure")

    monkeypatch.setattr(searcher, "_resolve_distance", fail)
    thing = {"id": 9, "lat": 1, "lon": 1, "distance": 3.2, "tags": {"name": "Fixture"}}
    assert await searcher.attempt_ors({"lat": 0, "lon": 0}, [thing]) is False
    assert "nav_distance" not in thing
    result = server_mod.build_result_items([thing])[0]
    assert result["distance_method"] == "straight_line_estimate"
    assert "route unavailable" in result["travel_distance"]
    assert "travel_distance_km" not in result
    markdown = server_mod.convert_and_validate_results("fixture", [thing])
    assert "Straight-line estimate" in markdown
    assert "© OpenStreetMap contributors" in markdown
    assert "ODbL" in markdown
    await searcher.aclose()


def test_osm_provenance_includes_only_dataset_timestamp_when_available():
    source = server_mod.osm_provenance(base_timestamp="2026-11-17T00:00:00Z")
    assert source["attribution"] == "© OpenStreetMap contributors"
    assert source["license"] == "ODbL-1.0"
    assert source["data_timestamp"] == "2026-11-17T00:00:00Z"
    assert "query_timestamp" not in source


def test_route_and_straight_line_distances_are_distinct_in_both_modes():
    thing = {
        "type": "node",
        "id": 5,
        "lat": 1,
        "lon": 1,
        "tags": {"name": "Fixture"},
        "distance": 2.0,
        "nav_distance": 3.4,
        "travel_type": "car",
    }
    item = server_mod.build_result_items([thing])[0]
    assert item["distance_method"] == "openrouteservice"
    assert item["distance_km"] == "2.000"
    assert item["travel_distance_km"] == 3.4
    for mode in ("compact", "detailed"):
        markdown = server_mod.convert_and_validate_results(
            "fixture", [thing], response_mode=mode
        )
        assert "Straight-line estimate" in markdown
        assert "Route Distance" in markdown


def test_router_profile_is_the_executed_mode_not_a_distance_label(tmp_path):
    searcher = make_searcher(tmp_path)
    assert searcher._ors.profile_for_pair(
        {"lat": 0, "lon": 0}, {"lat": 0, "lon": 0.005}
    ) == "foot-walking"
    assert searcher._ors.profile_for_pair(
        {"lat": 0, "lon": 0}, {"lat": 0, "lon": 0.05}
    ) == "driving-car"
