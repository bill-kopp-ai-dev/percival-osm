# 🤖 Percival OSM — percival.OS MCP

**Version 0.4.0**

[![Python](https://img.shields.io/badge/python-3.11+-yellow.svg)]()
[![MCP](https://img.shields.io/badge/mcp-server-blue.svg)]()
[![percival.OS](https://img.shields.io/badge/percival.OS-ecosystem-orange.svg)](https://github.com/bill-kopp-ai-dev/percival.OS)
[![Tests](https://img.shields.io/badge/tests-45%20passed-brightgreen.svg)]()

---

## 📋 Description

**Percival OSM** is an MCP server that connects AI assistants (femtobot,
nanobot, claude-code, etc.) to **OpenStreetMap**, enabling real-time geospatial
queries, point-of-interest discovery, and turn-by-turn navigation through a
hardened, privacy-respecting interface.

This server is part of the **percival.OS** ecosystem — a Personal Agentic
Operating System designed for autonomy, security, and absolute privacy.

It was originally forked from `lowlyocean/mcp-osm` and re-engineered for
production use inside `percival.OS_Dev`:

- 30+ curated geospatial tools (`osm_find_*`, `osm_navigate`, `osm_directions`, …).
- 3 **prompt primitives** to teach the agent which tool to call.
- 2 **resource primitives** for live policy / category reference.
- Structured logging to stderr (preserves the MCP stdio stream).
- Per-tool call telemetry, token-bucket rate limiting for Nominatim (1 req/s).
- Input sanitization against prompt-injection, HTTPS-only upstreams, URL
  allow-listing, and an isolated `async` runtime.

---

## 🛡️ percival.OS Principles

Like all components of `percival.OS`, this MCP server strictly follows our
core principles:

- **Privacy & Governance** — queries go through open, respectful APIs
  (Nominatim, Overpass, OpenRouteService) with no commercial tracking.
- **Data Sovereignty** — coordinates and location queries stay under the
  operator's control; the cache file is configurable and bounded to
  `OSM_CACHE_ALLOWED_DIRS`.
- **Hardened Security** — compact responses reduce token usage, structured
  output is sanitized against prompt-injection, and all upstream calls are
  rate-limited + URL-allow-listed.
- **Transparency** — operations are observable via `osm_get_health` and
  `osm_get_security_metrics`; every shell output (logging) goes to stderr
  so the MCP stdio stream is never corrupted.

---

## 🚀 Features & Tools

### Canonical tools (always available)

| Tool | Purpose | Recommended when… |
|---|---|---|
| `osm_find_nearby` | Search POIs by category near a place | you know *what* and *where* |
| `osm_find_nearby_detailed` | Same, with full address + tags per result | you need deeper context per POI |
| `osm_find_place` | Find a named location by name + city | you have a specific name (e.g. "Eiffel Tower") |
| `osm_find_place_detailed` | Same, with full address breakdown | you need the same with extra detail |
| `osm_find_nearby_store` | Find a store near coordinates | you have GPS coords and a category |
| `osm_find_address` | Coordinates → address (via Nominatim `/reverse`) | the user has GPS and wants a place name |
| `osm_geocode` | Address / place name → coordinates only | you only need lat/lon |
| `osm_navigate` | Route summary between A and B | distance + ETA only |
| `osm_directions` | Step-by-step instructions A → B | the agent walks the user through each maneuver |
| `osm_get_health` | Uptime, per-tool call/error counters, last failure | on-call triage |
| `osm_get_version` | Server version, process start time | deployment auditing |
| `osm_get_security_metrics` | Security counter snapshot | audit / incident response |
| `osm_get_status` | Short human-readable status string | quick smoke check |

### Legacy category aliases (default ON, controlled by `OSM_EXPOSE_LEGACY_ALIASES`)

23 per-category shortcuts — each one is a thin alias for `osm_find_nearby`
with the `category` parameter pre-filled:

`osm_find_groceries`, `osm_find_bakeries`, `osm_find_food`,
`osm_find_swimming`, `osm_find_playgrounds`, `osm_find_recreation`,
`osm_find_attractions`, `osm_find_worship`, `osm_find_accommodation`,
`osm_find_alcohol`, `osm_find_drugs`, `osm_find_schools`,
`osm_find_universities`, `osm_find_libraries`, `osm_find_transport`,
`osm_find_bikes`, `osm_find_cars`, `osm_find_hardware`,
`osm_find_electrical`, `osm_find_electronics`, `osm_find_doctors`,
`osm_find_hospitals`, `osm_find_pharmacy`.

Set `OSM_EXPOSE_LEGACY_ALIASES=false` to expose only the canonical tools
(useful for new deployments where the per-category aliases would just
bloat the tool list shown to the agent).

---

## 🧭 Prompts & Resources

In addition to tools, the server exposes **3 prompt primitives** and **2
resource primitives** so AI agents can reason about *which* tool to call
and *how* to render responses, without guessing.

Femtobot surfaces these as `mcp_percival_osm_prompt_<name>` and
`mcp_percival_osm_resource_<name>` (see femtobot `docs/mcp.md`).

### Prompts — `get_prompt(...)`

| Prompt | Purpose |
|---|---|
| `osm_recipe_quick_search` | Step-by-step recipe for a quick POI search near a place. Includes the canonical `osm_find_nearby` decision tree and failure modes. |
| `osm_tool_chooser` | Decision table mapping user intents to the right tool (`find_nearby` vs `find_place` vs `geocode` vs `navigate` vs `directions`). |
| `osm_output_format` | Canonical markdown templates for rendering nearby-search, route, and geocode results. |

### Resources — `read_resource(...)`

| URI | MIME | Content |
|---|---|---|
| `osm://categories` | `text/markdown` | Canonical list of category keys accepted by `osm_find_nearby`, with the matching legacy alias for each. |
| `osm://security/nanobot-policy` | `text/markdown` | The security policy this server enforces (privacy, sanitization, URL allow-listing). Lets the agent self-audit against the policy without re-reading this README. |

Prompts are *intentionally short*. Each one is meant to be referenced once
per task. Resources are read **on demand** and do not consume system-prompt
tokens unless the agent explicitly asks for them.

---

## ⚙️ Configuration

### Recommended femtobot / nanobot registration

```json
{
  "tools": {
    "mcpServers": {
      "percival-osm": {
        "command": "/path/to/.venv/bin/python",
        "args": ["-m", "percival_osm_mcp"],
        "cwd": "/path/to/percival-osm",
        "env": {
          "user_agent": "percival-osm/1.0 (your-email@example.com)",
          "from_header": "your-email@example.com",
          "ORS_API_KEY": "your-openrouteservice-key",
          "OSM_RESPONSE_MODE": "compact"
        },
        "enabledTools": [
          "osm_find_nearby",
          "osm_find_place",
          "osm_find_address",
          "osm_navigate",
          "osm_directions",
          "osm_geocode",
          "osm_get_health",
          "osm_get_version"
        ]
      }
    }
  }
}
```

### Important notes on `cwd`

> The server loads its `pydantic-settings` from a `.env` file **relative to
> the current working directory**. Always set `cwd` to the `percival-osm`
> package directory — without it, the spawned process inherits femtobot's
> CWD and `.env` will not be loaded.

Prefer passing secrets via the `env` block instead of `.env` when running
under femtobot — `.env` is intentionally excluded from version control.

### Configuration flags

See [`.env.example`](./.env.example) for the full list. Highlights:

```bash
# Behavior
OSM_EXPOSE_LEGACY_ALIASES=true          # set false for a slim tool list
OSM_NOMINATIM_RATE_LIMIT_RPS=1.0        # respect Nominatim usage policy
OSM_NOMINATIM_RATE_LIMIT_BURST=2        # small burst above the average
OSM_RESPONSE_MODE=compact               # compact | detailed

# Logging (stderr only — stdout is reserved for MCP JSON-RPC)
OSM_LOG_FORMAT=plain                    # plain | json
OSM_LOG_LEVEL=INFO                      # DEBUG | INFO | WARNING | ERROR

# Security
OSM_REQUIRE_HTTPS_UPSTREAMS=true
OSM_UPSTREAM_ALLOWED_HOSTS=nominatim.openstreetmap.org,overpass-api.de,api.openrouteservice.org
OSM_HTTP_FOLLOW_REDIRECTS=false         # avoids SSRF via redirect
MCP_OSM_AUTH_TOKEN=…                    # required for non-loopback HTTP exposure

# Cache
OSM_CACHE_FILE=/tmp/osm-cache.json
OSM_CACHE_TTL_SECONDS=3600
OSM_CACHE_ALLOWED_DIRS=/tmp
```

---

## 📈 Observability

### Structured logging

All log records go to **stderr** (stdout is reserved for the MCP JSON-RPC
stream). Switch to one-line JSON via:

```bash
OSM_LOG_FORMAT=json OSM_LOG_LEVEL=INFO
```

Sample JSON record:

```json
{"ts": "2026-07-17T15:00:00-0300", "level": "INFO", "logger": "percival-osm", "msg": "Navigating from [A] to [B]."}
```

The format is stable: `ts` (ISO 8601 local), `level`, `logger`, `msg`, plus
any structured `extra={…}` fields attached via `logger.info("…", extra=…)`.

### Health & version

- `osm_get_version` — package version, server name, process start (ISO 8601).
- `osm_get_health` — uptime in seconds, per-tool call/error counters, the
  most recent upstream failure (`kind`, `message`, `ts`), and the active
  cache path.
- `osm_get_security_metrics` — security counter snapshot (URL policy
  blocks, auth failures, upstream failures, etc).

All three are read-only and safe to call repeatedly from an orchestrator.

### Rate limiting (Nominatim)

Nominatim's usage policy allows **at most 1 request per second** per agent.
The server enforces this with an `asyncio.Lock` + token-bucket:

```bash
OSM_NOMINATIM_RATE_LIMIT_RPS=1.0   # tokens per second
OSM_NOMINATIM_RATE_LIMIT_BURST=2   # initial bucket capacity
```

Setting `OSM_NOMINATIM_RATE_LIMIT_RPS=0` disables the limiter entirely
(use only for self-hosted Nominatim). Concurrent calls for the same
target collapse through a **single-flight** future so parallel tools
never stampede the upstream API.

### Performance / hardening knobs

- **Shared `httpx.AsyncClient`** — reuses the HTTP/2 connection pool across
  requests instead of opening a new client on every call.
- **Race-free URL validation** — the `_validated_upstreams` set is guarded
  by an `asyncio.Lock`, so concurrent tools never double-validate.
- **Headers always present** — `create_headers()` short-circuits with a
  `ValueError("Headers not set")` if `user_agent` / `from_header` are
  empty, so missing config is loud, not silent.

---

## 🛠️ Development & Testing

### Run locally

```bash
# Editable install + dev deps
uv sync

# Run the server (stdio transport for direct MCP use)
PYTHONPATH=src .venv/bin/python -m percival_osm_mcp --mode stdio

# Or streamable HTTP for direct API debugging
PYTHONPATH=src .venv/bin/python -m percival_osm_mcp --mode streamable-http --port 8000
```

### Tests

```bash
# Run the full suite (45 tests, ~1s)
uv run pytest -v

# Targeted suites
uv run pytest tests/test_s5_primitives.py       # prompts + resources + bug regressions
uv run pytest tests/test_s3_observability.py    # health, version, structured logging, rate limit
uv run pytest tests/test_runtime_security.py    # URL policy + sanitization
```

The suite covers:

- URL allow-listing, redirect validation, private-host blocking.
- Output sanitization (HTML, markdown, control characters).
- Prompt-injection regression corpus.
- Observability primitives (health, version, operational telemetry).
- Token-bucket rate-limit semantics (burst, throttle-after-burst, disabled).
- MCP prompt/resource registration and content integrity.
- Bug-fix regressions for: `main()` block, `@_track` decorator coverage,
  shared `httpx.AsyncClient`, single-flight ORS, static dead-code removal.

---

## 🔒 Security model

This server enforces the following defenses (see
`osm://security/nanobot-policy` resource for the canonical machine-readable
form):

| Layer | Protection |
|---|---|
| Transport | HTTPS-only to upstreams; `follow_redirects=false` by default |
| URL policy | Allow-list of upstream hosts; `inline_credentials` rejected |
| Headers | `User-Agent` + `From` headers mandatory; requests fail loud if missing |
| Rate limit | 1 req/s + burst 2 against Nominatim via token bucket |
| Single-flight | Concurrent duplicate calls share one upstream request |
| Sanitization | All upstream-rendered text goes through `sanitize_external_text` / `sanitize_external_markdown` |
| Cache | File must live under `OSM_CACHE_ALLOWED_DIRS`; TTL configurable |
| Auth | `MCP_OSM_AUTH_TOKEN` required for non-loopback HTTP transports |
| Logging | stderr only; never touches the MCP stdio stream |

Every blocking or failure path increments a counter exposed via
`osm_get_security_metrics`.

---

## 📝 Changelog

### 0.4.0 — current
- 3 prompt primitives + 2 resource primitives (`osm_primitives.py`).
- `osm_directions` (structured turn-by-turn, ordered steps with
  distance/duration) and `osm_geocode` (text → coords, no full address
  detail).
- `osm_get_health`, `osm_get_version` tools; structured operational
  telemetry.
- Async token-bucket rate limiter for Nominatim (1 req/s + burst 2).
- Structured logging (JSON) on stderr via `OSM_LOG_FORMAT=json`.
- Shared `httpx.AsyncClient` (lazy + double-checked lock).
- Single-flight pattern for concurrent ORS distance calls.
- Race-free URL policy validation (lock around `_validated_upstreams`).
- `@_track` decorator applied to all 14 canonical tools for accurate
  per-tool call counters in `osm_get_health`.
- Bug fixes: `main()` was historically invoked 11× in `__main__`; dead
  code removal (`pygments`, `pretty_print_thing_json`, `itertools`
  import); duplicate `datetime` import.
- Settings additions: `OSM_EXPOSE_LEGACY_ALIASES`, `OSM_LOG_FORMAT`,
  `OSM_LOG_LEVEL`, `OSM_NOMINATIM_RATE_LIMIT_RPS`,
  `OSM_NOMINATIM_RATE_LIMIT_BURST`.

### 0.3.0
- Initial structured observability + capacity flags.

### 0.0.x
- Pre-hardening forks of `lowlyocean/mcp-osm`.

---

## 📚 About the Project

This server is an integral module of the **percival.OS** project. It lets
`femtobot` (and any MCP-compatible client) interact with the physical world
through OpenStreetMap's open data.

- **Main Repository**: [https://github.com/bill-kopp-ai-dev/percival.OS](https://github.com/bill-kopp-ai-dev/percival.OS)
- **License**: MIT

---
*Developed with ❤️ by the percival.OS Team*
