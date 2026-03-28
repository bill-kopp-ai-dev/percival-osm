import json
from pathlib import Path

from percival_osm_mcp.server import (
    RESPONSE_MODE_COMPACT,
    build_tool_response,
    convert_and_validate_results,
    get_security_metrics,
    record_security_event,
    reset_security_metrics_for_tests,
    sanitize_external_text,
)


def _load_corpus():
    fixture = Path(__file__).parent / "fixtures" / "prompt_injection_corpus.json"
    return json.loads(fixture.read_text(encoding="utf-8"))


def _mk_thing(payload: str):
    return {
        "type": "node",
        "lat": 40.0,
        "lon": -73.0,
        "distance": 1.0,
        "tags": {
            "name": payload,
            "amenity": "cafe",
            "addr:street": "Main",
            "opening_hours": payload,
        },
    }


def test_prompt_injection_corpus_stays_sanitized() -> None:
    corpus = _load_corpus()
    for case in corpus:
        payload = case["payload"]
        rendered = convert_and_validate_results(
            "New York",
            [_mk_thing(payload)],
            response_mode=RESPONSE_MODE_COMPACT,
        )
        assert rendered is not None

        sanitized = sanitize_external_text(payload)
        response = json.loads(
            build_tool_response(
                status="ok",
                message="test",
                data={"sample": sanitized},
            )
        )
        assert "warnings" in response
        for forbidden in case["expected_absent"]:
            assert forbidden not in rendered
            assert forbidden not in response["data"]["sample"]


def test_security_metrics_tool_reports_counters() -> None:
    reset_security_metrics_for_tests()
    record_security_event("custom_event_for_test")
    payload = json.loads(get_security_metrics())
    assert payload["status"] == "ok"
    assert payload["data"]["security_metrics"].get("custom_event_for_test", 0) == 1
