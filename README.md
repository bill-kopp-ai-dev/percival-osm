# percival-osm

> A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that connects AI assistants to [OpenStreetMap](https://www.openstreetmap.org/), enabling real-time geospatial queries, point-of-interest discovery, and navigation — developed as a component of [percival.OS](https://github.com/bill-kopp-ai-dev/percival.OS_Dev).

---

## Overview

**percival-osm** gives your AI agent the ability to explore the physical world. It provides a rich set of MCP tools backed by the Overpass API (OpenStreetMap data), Nominatim (geocoding), and OpenRouteService (routing), all without requiring any proprietary map API.

This project is derived from [lowlyocean/mcp-osm](https://github.com/lowlyocean/mcp-osm), which was itself based on [projectmoon's OSM tool for Open-WebUI](https://git.agnos.is/projectmoon/open-webui-filters/src/branch/master/osm.py). percival-osm extends the original work with Docker support, improved configuration, and integration with the percival.OS agent ecosystem.

---

## Features

- 🗺️ **Geocoding** — Reverse-geocode coordinates to human-readable addresses
- 📍 **POI Search** — Find points of interest near any place or GPS coordinates
- ⚡ **Compact-by-default responses** — Lower token usage for agent workflows
- 🛡️ **Structured safe outputs** — Tool responses are JSON payloads with sanitized external text
- 🧪 **Detailed mode tools** — Rich metadata when debugging or automating
- 🧭 **Navigation** — Get driving, cycling, or walking routes between locations
- 🐳 **Docker-ready** — Ships with `Dockerfile` and `docker-compose.yml`
- 🔌 **MCP-native** — Works out of the box with any MCP-compatible AI agent (nanobot, Claude Desktop, etc.)
- 🆓 **No proprietary APIs** — Powered entirely by open-source and free-tier services

---

## MCP Tools

| Tool | Description |
|---|---|
| `find_places_near_place` | Generic compact POI search by category (recommended for nanobot) |
| `find_places_near_place_detailed` | Detailed POI search with richer metadata |
| `find_address_for_coordinates` | Reverse geocode GPS coordinates to an address |
| `find_store_or_place_near_coordinates` | Search for any type of place near coordinates |
| `find_specific_place` | Find a specific named place by name and city |
| `find_specific_place_detailed` | Detailed variant of specific place lookup |
| `navigate_between_places` | Get route directions between two places |
| `find_grocery_stores_near_place` | Find supermarkets and grocery stores |
| `find_bakeries_near_place` | Find bakeries and bread shops |
| `find_food_near_place` | Find restaurants, cafés, and eateries |
| `find_swimming_near_place` | Find swimming pools and beaches |
| `find_playgrounds_near_place` | Find parks and playgrounds |
| `find_recreation_near_place` | Find gyms, sports centers, leisure activities |
| `find_tourist_attractions_near_place` | Find museums, monuments, and sights |
| `find_place_of_worship_near_place` | Find churches, mosques, synagogues, etc. |
| `find_accommodation_near_place` | Find hotels, hostels, and lodging |
| `find_alcohol_near_place` | Find bars, pubs, and liquor stores |
| `find_schools_near_place` | Find schools and primary education |
| `find_universities_near_place` | Find universities and colleges |
| `find_libraries_near_place` | Find public libraries |
| `find_public_transport_near_place` | Find bus stops, metro stations, etc. |
| `find_bike_rentals_near_place` | Find bicycle rental stations |
| `find_car_rentals_near_place` | Find car rental agencies |
| `find_hardware_store_near_place` | Find hardware and home improvement stores |
| `find_electrical_store_near_place` | Find electrical and lighting stores |
| `find_electronics_store_near_place` | Find consumer electronics stores |
| `find_doctor_near_place` | Find doctors and clinics |
| `find_hospital_near_place` | Find hospitals |
| `find_pharmacy_near_place` | Find pharmacies and health stores |
| `find_drugs_near_place` | Find pharmacies (alias) |
| `find_other_things_near_place` | Catch-all tool for unsupported categories |
| `get_security_metrics` | Return in-memory security counters for monitoring/audit |

`find_*_near_place` category tools remain available as backward-compatible aliases.

Supported categories for `find_places_near_place`:
`accommodation`, `alcohol`, `bakeries`, `bike_rentals`, `car_rentals`, `doctors`, `drugs`, `electrical`, `electronics`, `food`, `groceries`, `hardware`, `hospitals`, `libraries`, `pharmacies`, `places_of_worship`, `playgrounds`, `public_transport`, `recreation`, `schools`, `swimming`, `tourist_attractions`, `universities`.

---

## Requirements

- Python 3.11+
- `uv`
- An [OpenRouteService API key](https://openrouteservice.org/dev) (free tier available)
- Internet access to Nominatim and Overpass API (no API keys required)

---

## Installation

### Standalone clone (optional)

```bash
git clone https://github.com/bill-kopp-ai-dev/percival-osm.git
cd percival-osm
uv sync --dev
```

### Using `pip`

```bash
git clone https://github.com/bill-kopp-ai-dev/percival-osm.git
cd percival-osm
pip install -e .
```

### percival.OS_Dev workspace (current setup)

In this monorepo setup:
- Git tracking is managed by `percival.OS_Dev/.git`
- Shared virtual environment is `percival.OS_Dev/.venv`
- This folder does not need its own `.venv` or local Git automation files

---

## Configuration

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Nominatim policy-required headers
user_agent=percival-osm/1.0 (your-email@example.com)
from_header=your-email@example.com

# Optional routing key
ORS_API_KEY=your-openrouteservice-api-key

# Optional endpoint overrides
nominatim_url=https://nominatim.openstreetmap.org/
overpass_turbo_url=https://overpass-api.de/api/interpreter
ors_instance=https://api.openrouteservice.org

# Runtime behavior
instruction_oriented_interpretation=true
car_only=false
status_indicators=false
OSM_RESPONSE_MODE=compact

# HTTP hardening
OSM_HTTP_TIMEOUT_SECONDS=12
OSM_HTTP_MAX_RETRIES=2
OSM_HTTP_RETRY_BACKOFF_SECONDS=0.6
OSM_HTTP_FOLLOW_REDIRECTS=false
OSM_HTTP_MAX_RESPONSE_BYTES=2000000
OSM_HTTP_MAX_CONCURRENCY=8
OSM_REQUIRE_HTTPS_UPSTREAMS=true
OSM_UPSTREAM_ALLOWED_HOSTS=nominatim.openstreetmap.org,overpass-api.de,api.openrouteservice.org

# Cache
OSM_CACHE_FILE=/tmp/osm-cache.json
OSM_CACHE_TTL_SECONDS=3600
OSM_CACHE_ALLOWED_DIRS=/tmp
```

---

## Running

### Canonical package entrypoint (standalone install)

```bash
python -m percival_osm_mcp --mode stdio
```

### Shared `percival.OS_Dev/.venv` entrypoint (workspace mode)

```bash
PYTHONPATH=src ../../.venv/bin/python -m percival_osm_mcp --mode stdio
```

### Legacy compatibility entrypoint

```bash
python osm.py
```

### SSE mode

```bash
PYTHONPATH=src ../../.venv/bin/python -m percival_osm_mcp --mode sse --host 127.0.0.1 --port 8080
```

### Streamable HTTP mode

```bash
PYTHONPATH=src ../../.venv/bin/python -m percival_osm_mcp --mode streamable-http --host 127.0.0.1 --port 8080
```

### Remote HTTP exposure (secured)

Remote host binding requires:
- `--allow-remote-http`
- auth token in env (default env var: `MCP_OSM_AUTH_TOKEN`)

Example:

```bash
export MCP_OSM_AUTH_TOKEN="replace-this-token"
PYTHONPATH=src ../../.venv/bin/python -m percival_osm_mcp \
  --mode streamable-http \
  --host 0.0.0.0 \
  --port 8080 \
  --allow-remote-http
```

### With Docker

```bash
docker-compose up -d
```

Container defaults are hardened in S1:
- runs as non-root (`uid/gid 10001`)
- root filesystem is read-only
- `/tmp` is tmpfs-mounted
- Linux capabilities dropped and `no-new-privileges` enabled

### Response format (S0 hardening)

Tool outputs are JSON strings in this format:

```json
{
  "status": "ok|no_results|error|invalid_request|config_error",
  "message": "short summary",
  "query": {},
  "data": {},
  "warnings": []
}
```

Notes:
- External OSM/ORS text is sanitized before being returned.
- Error payloads are redacted (no internal stack/exception details).
- Source citations are emitted as plain text metadata (`html=false`).

### S1 transport/runtime hardening

- Upstream endpoints are validated against `OSM_UPSTREAM_ALLOWED_HOSTS`.
- Local/private upstream targets are blocked to reduce SSRF risk.
- HTTPS is enforced by default (`OSM_REQUIRE_HTTPS_UPSTREAMS=true`).
- Redirects are disabled by default (`OSM_HTTP_FOLLOW_REDIRECTS=false`).
- Response size is capped (`OSM_HTTP_MAX_RESPONSE_BYTES`).
- Upstream request concurrency is bounded (`OSM_HTTP_MAX_CONCURRENCY`).
- Cache file path must stay under `OSM_CACHE_ALLOWED_DIRS`.

### S2 governance and continuous security

- Full security gates require dev dependencies (`pytest`, `bandit`, `pip-audit`).
- Recommended execution context: standalone clone after `uv sync --dev`.
- Command set:
  - `uv run pytest -q`
  - `uv pip check`
  - `uv run bandit -q -c .bandit -r src/percival_osm_mcp -x tests`
  - `uv export --format requirements-txt --no-dev | sed '/^-e \\./d' > /tmp/requirements.audit.txt`
  - `uv run pip-audit --strict --cache-dir /tmp/pip-audit-cache -r /tmp/requirements.audit.txt --no-deps --disable-pip --ignore-vuln CVE-2025-43859 --ignore-vuln CVE-2026-4539`
- Prompt injection regression corpus:
  - `tests/fixtures/prompt_injection_corpus.json`
- Threat model:
  - `docs/security/threat-model.md`
- Nanobot integration policy:
  - `docs/security/nanobot-policy.md`
- Incident response playbook:
  - `docs/security/incident-response.md`
- Vulnerability exception register:
  - `docs/security/vulnerability-exceptions.md`

Security telemetry:
- Runtime counters are available through `get_security_metrics`.
- Security events are logged with `SECURITY_EVENT ...` markers for audit pipelines.

---

## Integrating with nanobot / Claude Desktop

Add the following entry to your `config.json`:

```json
"percival-osm": {
  "command": "/path/to/.venv/bin/python",
  "args": ["-m", "percival_osm_mcp"],
  "enabled_tools": [
    "find_places_near_place",
    "find_specific_place",
    "navigate_between_places",
    "find_address_for_coordinates"
  ],
  "tool_timeout": 45,
  "env": {
    "user_agent": "percival-osm/1.0",
    "from_header": "your-email@example.com",
    "nominatim_url": "https://nominatim.openstreetmap.org/",
    "overpass_turbo_url": "https://overpass-api.de/api/interpreter",
    "instruction_oriented_interpretation": "true",
    "car_only": "false",
    "status_indicators": "false",
    "OSM_RESPONSE_MODE": "compact",
    "ORS_API_KEY": "your-openrouteservice-api-key",
    "OSM_HTTP_TIMEOUT_SECONDS": "12",
    "OSM_HTTP_MAX_RETRIES": "2",
    "OSM_HTTP_MAX_RESPONSE_BYTES": "2000000",
    "OSM_UPSTREAM_ALLOWED_HOSTS": "nominatim.openstreetmap.org,overpass-api.de,api.openrouteservice.org",
    "OSM_CACHE_TTL_SECONDS": "3600"
  }
}
```

For remote HTTP transport in nanobot, use:

```json
"percival-osm-http": {
  "url": "https://your-host.example.com/mcp",
  "headers": {
    "Authorization": "Bearer replace-this-token"
  },
  "enabled_tools": ["find_places_near_place", "find_specific_place"]
}
```

Production note: when exposing remote HTTP, terminate TLS in front of the MCP server (reverse proxy/load balancer). Do not expose bearer tokens over plaintext HTTP.

## Compatibility and Migration

- Legacy `python osm.py` still works.
- Canonical form is now `python -m percival_osm_mcp`.
- Category-specific tools remain available as aliases.
- Recommended for nanobot: keep `enabled_tools` focused on compact generic tools.

---

## Attribution

This project is built upon the work of:

- **[lowlyocean/mcp-osm](https://github.com/lowlyocean/mcp-osm)** — The direct upstream, providing the original MCP wrapper and Docker setup.
- **[projectmoon's OSM tool for Open-WebUI](https://git.agnos.is/projectmoon/open-webui-filters/src/branch/master/osm.py)** — The original OSM query engine on which `mcp-osm` was based.
- **[OpenStreetMap contributors](https://www.openstreetmap.org/copyright)** — All map data is © OpenStreetMap contributors, available under the [ODbL license](https://opendatacommons.org/licenses/odbl/).
- **[Nominatim](https://nominatim.org/)** — Open-source geocoding powered by OSM data.
- **[OpenRouteService](https://openrouteservice.org/)** — Open routing engine for directions and navigation.

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.
