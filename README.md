# 🤖 Percival OSM — percival.OS MCP (docker-first)

**Version 0.5.0** · container image is the unit of delivery

[![Python](https://img.shields.io/badge/python-3.11+-yellow.svg)]()
[![MCP](https://img.shields.io/badge/mcp-server-blue.svg)]()
[![percival.OS](https://img.shields.io/badge/percival.OS-ecosystem-orange.svg)](https://github.com/bill-kopp-ai-dev/percival.OS)
[![Tests](https://img.shields.io/badge/tests-pytest-brightgreen.svg)]()

---

## 📋 Description

**Percival OSM** is an MCP server that connects AI assistants (femtobot,
nanobot, claude-code, opencode, …) to **OpenStreetMap**, enabling real-time
geospatial queries, point-of-interest discovery, and turn-by-turn navigation
through a hardened, privacy-respecting interface.

This server is part of the **percival.OS** ecosystem — a Personal Agentic
Operating System designed for autonomy, security, and absolute privacy.

It was originally forked from `lowlyocean/mcp-osm` and re-engineered for
production use inside `percival.OS_Dev`:

- 8 curated geospatial tools exposed by default; all 14 canonical tools and 23
  category aliases remain implemented and can be selectively re-exposed through
  configuration.
- 3 **prompt primitives** to teach the agent which tool to call.
- 2 **resource primitives** for live policy / category reference.
- Structured logging to stderr (preserves the MCP stdio stream).
- Per-tool call/error/outcome telemetry, shared process-local provider budgets,
  and public Nominatim at 1 req/s with no burst.
- Input sanitization against prompt-injection, HTTPS-only upstreams, URL
  allow-listing, and an isolated `async` runtime.

---

## 🐳 Docker-first

This server is **docker-first**: the container image is the product, and the
Python package is a library that ships *inside* the image. The local
`pip`/`uv` install exists for development and tests — it is not a deployment
path.

| Layer | What it is | Owner |
|---|---|---|
| **Artifact** | `Dockerfile` → digest-pinned multi-stage image (`percival-osm:local`), reproducible timestamps, OCI labels for version/revision/created | this repository (`scripts/docker-build.sh`) |
| **Contract** | `docker-entrypoint.sh`: env validation, mode normalization, root refusal — the container's observable behaviour | this repository |
| **Runtime** | the running container, its configuration and its secrets | the operator: production containers are managed through the supported Positronic/Percival interface |

`docker-compose.yml` is a **local fixture**, not the production definition. It
exists to render and exercise the same contracts on a workstation; it does not
decide how a production container is configured.

### What "docker-first" changes, concretely

- **Required configuration is validated by the container, not by the caller.**
  A missing `USER_AGENT`/`FROM_HEADER` aborts startup with exit code `78`
  (`EX_CONFIG`) and an actionable stderr message. A missing geocoding backend
  aborts the server itself.
- **Secrets are delivered by reference.** The Compose fixture mounts the
  OpenRouteService key and the HTTP bearer token as file-backed secrets; they
  are absent from the rendered recipe and from the container creation
  environment.
- **Process supervision belongs to the launcher.** The image deliberately
  embeds **no init** (`docker run --init` / Compose `init: true`). Two stacked
  supervision layers would hide which process actually owns SIGTERM.
- **Health is a transport property.** The image carries `HEALTHCHECK NONE`:
  process presence cannot prove an MCP handshake. The HTTP fixture supplies a
  probe that performs a real MCP `initialize` against `/mcp`.
- **Stdout stays clean.** In stdio mode stdout is the JSON-RPC stream and
  nothing else; every log line goes to stderr.

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

### Tools exposed by default

| Tool | Purpose | Recommended when… |
|---|---|---|
| `osm_find_nearby` | Search POIs by category near a place | you know *what* and *where* |
| `osm_find_place` | Find a named location by name + city | you have a specific name (e.g. "Eiffel Tower") |
| `osm_find_address` | Coordinates → address (via Nominatim `/reverse`) | the user has GPS and wants a place name |
| `osm_geocode` | Address / place name → coordinates only | you only need lat/lon |
| `osm_directions` | Route summary and structured step-by-step instructions A → B | route details are needed |
| `osm_get_health` | Uptime, per-tool call/error/outcome counters, cache state and last upstream failure category | on-call triage |
| `osm_get_security_metrics` | Security counter snapshot | audit / incident response |
| `osm_get_version` | Server version, process start time | deployment auditing |

### All 14 canonical tools

Every handler below is implemented and registered. The six not listed in the
table above are still selectable via `OSM_EXPOSED_TOOLS`.

| Tool | Purpose |
|---|---|
| `osm_find_nearby` | Generic nearby POI search by category (the recommended default). |
| `osm_find_nearby_detailed` | Same search, `detailed` response mode. |
| `osm_find_place` | Resolve a named place / landmark / address. |
| `osm_find_place_detailed` | Same resolution, `detailed` response mode. |
| `osm_find_address` | Reverse-geocode coordinates via Nominatim `/reverse`. |
| `osm_find_nearby_store` | Find a named business near a coordinate anchor. |
| `osm_geocode` | Place/address → coordinates only. |
| `osm_navigate` | Route summary between two places. |
| `osm_directions` | Route summary **plus** ordered turn-by-turn steps. |
| `osm_find_other` | Reports whether a requested category is supported (routing fallback). |
| `osm_get_health` | Structured operational snapshot. |
| `osm_get_status` | One-line human-readable status string. |
| `osm_get_security_metrics` | Security counter snapshot. |
| `osm_get_version` | Version, server name, process start time, Python version. |

### Optional category aliases (23)

These are thin shortcuts for `osm_find_nearby` with `category` pre-filled:

`osm_find_groceries`, `osm_find_bakeries`, `osm_find_food`,
`osm_find_swimming`, `osm_find_playgrounds`, `osm_find_recreation`,
`osm_find_attractions`, `osm_find_worship`, `osm_find_accommodation`,
`osm_find_alcohol`, `osm_find_drugs`, `osm_find_schools`,
`osm_find_universities`, `osm_find_libraries`, `osm_find_transport`,
`osm_find_bikes`, `osm_find_cars`, `osm_find_hardware`,
`osm_find_electrical`, `osm_find_electronics`, `osm_find_doctors`,
`osm_find_hospitals`, `osm_find_pharmacy`.

### Supported POI categories (23)

`accommodation`, `alcohol`, `bakeries`, `bike_rentals`, `car_rentals`,
`doctors`, `drugs`, `electrical`, `electronics`, `food`, `groceries`,
`hardware`, `hospitals`, `libraries`, `pharmacies`, `places_of_worship`,
`playgrounds`, `public_transport`, `recreation`, `schools`, `swimming`,
`tourist_attractions`, `universities`.

The same list is served live by the `osm://categories` resource.

### Controlling the tool surface

The default `OSM_EXPOSED_TOOLS` allowlist contains only the eight tools above.

- Set it to a comma-separated list of exact tool names to re-expose selected
  handlers.
- Set it to `all` to expose all 14 canonical tools and (when enabled) all 23
  category aliases.
- `OSM_EXPOSE_LEGACY_ALIASES=false` remains an independent gate that suppresses
  every category alias, including when `all` is selected.
- Unknown names, an empty list, or mixing `all` with individual names **fail
  server startup** with a `ValueError` — a misconfigured surface is never
  silently served.

Apply changes by restarting the MCP server process.

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
| `osm_tool_chooser` | Decision table mapping user intents to the default tools (`find_nearby`, `find_place`, geocoding, and directions). |
| `osm_output_format` | Canonical markdown templates for rendering nearby-search, route, and geocode results. |

### Resources — `read_resource(...)`

| URI | MIME | Content |
|---|---|---|
| `osm://categories` | `text/markdown` | Canonical list of category keys accepted by `osm_find_nearby`, with the matching legacy alias for each. |
| `osm://security/nanobot-policy` | `text/markdown` | The security policy this server enforces (privacy, sanitization, URL allow-listing). Lets the agent self-audit against the policy without re-reading this README. |

The policy resource is shipped **inside the wheel** (`percival_osm_mcp/docs/security/nanobot-policy.md`),
so it is available in the container without any host file.

Prompts are *intentionally short*. Each one is meant to be referenced once
per task. Resources are read **on demand** and do not consume system-prompt
tokens unless the agent explicitly asks for them.

---

## ⚙️ Configuration

### Configuration model

> The server reads **all** of its configuration from the **process
> environment**. It does **not** load a `.env` file from disk — the previous
> `env_file=".env"` behaviour has been removed.
>
> Practical consequences:
> - No more `cwd` requirement: the server can be launched from any
>   directory; it no longer matters where you start it from.
> - Secrets never sit on disk under the package: the launcher is the only
>   component that needs to inject them, and the recommended path
>   (`mcpServers.*.env` in the agent's config) keeps them out of version
>   control.
> - The shipped `.env.example` is **documentation only** — it lists every
>   environment variable the server understands, but nothing reads it.
>
> In the docker-first model the launcher is `docker run` / the container
> manager, and secrets arrive as file-backed mounts rather than as values
> written into the image or the recipe.

### Required configuration

| Variable | Why it is required |
|---|---|
| `USER_AGENT` | Nominatim usage policy: every request must identify the application. |
| `FROM_HEADER` | Nominatim usage policy: a contact address must accompany the request. |
| `NOMINATIM_URL` | The geocoding backend must be **selected explicitly**. Startup fails if it is unset or empty; there is no implicit default backend. |

The container entrypoint enforces the first two before the server starts
(exit `78` / `EX_CONFIG`); the server itself enforces the third.

### Configuration flags

[`.env.example`](./.env.example) is the canonical reference (every variable the
server recognises, with its default). Highlights:

```bash
# Tool exposure (default: the eight tools listed above)
OSM_EXPOSED_TOOLS=osm_find_nearby,osm_find_place,osm_find_address,osm_geocode,osm_directions,osm_get_health,osm_get_security_metrics,osm_get_version
OSM_EXPOSE_LEGACY_ALIASES=true          # additional gate for category aliases

# Backend selection (mandatory) and provider policy
NOMINATIM_URL=https://nominatim.openstreetmap.org/
OVERPASS_TURBO_URL=https://overpass-api.de/api/interpreter
ORS_INSTANCE=https://api.heigit.org/openrouteservice   # ORS_URL is a compat alias
USER_AGENT=percival-osm/0.5.0 (you@example.com)
FROM_HEADER=you@example.com

# Public Nominatim policy: at most 1 req/s for the whole application, no burst.
# Startup rejects a higher RPS or a burst != 1 against the public service.
OSM_NOMINATIM_RATE_LIMIT_RPS=1.0
OSM_NOMINATIM_RATE_LIMIT_BURST=1

# OpenRouteService routing (required for route/directions tools; without it,
# those tools return provider_not_configured. Haversine is only used to choose
# the routing profile when ORS is configured.)
ORS_API_KEY=…
ORS_REQUEST_TIMEOUT=90                  # per-request setting; tool deadline below is the overall cap

# Upstream budget
OSM_HTTP_TIMEOUT_SECONDS=12             # per attempt
OSM_HTTP_MAX_RETRIES=2
OSM_HTTP_RETRY_BACKOFF_SECONDS=0.6
OSM_UPSTREAM_TOOL_DEADLINE_SECONDS=16    # end-to-end upstream tool limit (max 16)
OSM_HTTP_MAX_RESPONSE_BYTES=2000000     # response body ceiling, enforced while streaming
OSM_HTTP_MAX_CONCURRENCY=8              # in-process upstream concurrency

# Result shaping and routing profile
OSM_RESPONSE_MODE=compact               # compact | detailed
INSTRUCTION_ORIENTED_INTERPRETATION=true # instruction-oriented result text
CAR_ONLY=false                           # force driving-car; when false, hops <= 1.5 km may use foot-walking
STATUS_INDICATORS=false                  # emit MCP status notifications during long searches

# Logging (stderr only — stdout is reserved for MCP JSON-RPC)
OSM_LOG_FORMAT=plain                    # plain | json
OSM_LOG_LEVEL=INFO                      # DEBUG | INFO | WARNING | ERROR

# Security
OSM_REQUIRE_HTTPS_UPSTREAMS=true
OSM_UPSTREAM_ALLOWED_HOSTS=nominatim.openstreetmap.org,overpass-api.de,api.heigit.org
OSM_HTTP_FOLLOW_REDIRECTS=false         # avoids SSRF via redirect

# HTTP transport auth (name of the variable that carries the token)
MCP_OSM_AUTH_TOKEN_ENV=MCP_OSM_AUTH_TOKEN
MCP_OSM_AUTH_TOKEN=…                    # required for non-loopback HTTP

# Cache
OSM_CACHE_FILE=/cache/osm-cache.json
OSM_CACHE_TTL_SECONDS=3600
OSM_CACHE_ALLOWED_DIRS=/cache
```

Container-level variables that only the launcher reads:

| Variable | Consumer | Meaning |
|---|---|---|
| `MODE` | entrypoint | `stdio` (default), `sse`, or `streamable-http`. |
| `PORT` | entrypoint | Listen port for the HTTP transports (default `8080`). |
| `ALLOW_REMOTE_HTTP` | entrypoint | `true` permits binding the HTTP transport to a non-loopback host. Requires a bearer token. |
| `ORS_API_KEY_FILE` | Compose | Host path of the file-backed OpenRouteService secret. |
| `MCP_OSM_AUTH_TOKEN_FILE` | Compose | Host path of the file-backed HTTP bearer token (default `~/.config/percival/osm_auth_token`). |
| `HTTP_BIND_ADDRESS` / `HTTP_PORT` | Compose | Host bind for the HTTP profile (default `127.0.0.1:8080`). |

### Client registration

**Docker-first means the client launches the container.** The image is the
command; there is no Python interpreter to provision on the client host.

nanobot / femtobot (`~/.nanobot/config.json`):

```json
{
  "tools": {
    "mcpServers": {
      "percival-osm": {
        "command": "docker",
        "args": [
          "run", "--rm", "-i",
          "-e", "NOMINATIM_URL=https://nominatim.openstreetmap.org/",
          "-e", "USER_AGENT=percival-osm/0.5.0 (you@example.com)",
          "-e", "FROM_HEADER=you@example.com",
          "percival-osm:local"
        ]
      }
    }
  }
}
```

opencode (`opencode.json` or `~/.config/opencode/opencode.json`):

```json
{
  "mcp": {
    "percival-osm": {
      "type": "stdio",
      "command": [
        "docker", "run", "--rm", "-i",
        "-e", "NOMINATIM_URL=https://nominatim.openstreetmap.org/",
        "-e", "USER_AGENT=percival-osm/0.5.0 (you@example.com)",
        "-e", "FROM_HEADER=you@example.com",
        "percival-osm:local"
      ]
    }
  }
}
```

Claude Desktop / any generic stdio MCP client: configure the same
`docker run --rm -i … percival-osm:local` invocation under
`mcpServers.percival-osm`.

---

## 🐳 Deploying the image

### Build

```bash
# Build percival-osm:local (host architecture) with version/revision derived
# from this checkout. A dirty worktree is reported as revision "unknown".
scripts/docker-build.sh

# Extra tags
scripts/docker-build.sh v0.5.0

# Multi-arch (requires buildx; the result is not loaded into the local daemon)
PLATFORMS=linux/amd64,linux/arm64 scripts/docker-build.sh
scripts/docker-build.sh --platform=linux/arm64
```

The build is reproducible: `uv sync --frozen` pins the dependency tree, all
base images are digest-pinned, and `SOURCE_DATE_EPOCH` normalizes filesystem
and metadata timestamps. `VERSION` and `GIT_SHA` are passed explicitly and
recorded as OCI labels.

On linux/amd64 the image is ≈378 MB uncompressed (re-measure with
`docker image inspect --format '{{.Size}}' percival-osm:local`). The runtime
stage carries only the Python runtime and its shared libraries, the
application, `bash` and the CA bundle — no compilers and no development
dependencies.

### Run — stdio (the common case)

```bash
docker run --rm -i --init \
  -e NOMINATIM_URL='https://nominatim.openstreetmap.org/' \
  -e USER_AGENT='percival-osm/0.5.0 (you@example.com)' \
  -e FROM_HEADER='you@example.com' \
  percival-osm:local
```

`--init` is required: the image ships no init of its own.

### Run — streamable HTTP

```bash
docker run --rm -p 127.0.0.1:8080:8080 \
  -e NOMINATIM_URL='https://nominatim.openstreetmap.org/' \
  -e USER_AGENT='percival-osm/0.5.0 (you@example.com)' \
  -e FROM_HEADER='you@example.com' \
  -e MODE=streamable-http \
  -e ALLOW_REMOTE_HTTP=true \
  -e MCP_OSM_AUTH_TOKEN="$(openssl rand -hex 32)" \
  percival-osm:local
```

The endpoint is `http://<host>:8080/mcp`. A non-loopback bind requires both
`ALLOW_REMOTE_HTTP=true` and a bearer token; without them startup fails
closed with a `remote_bind_blocked` security event.

### Run — docker compose (local fixture)

```bash
# The fixture expects a secret file for the HTTP bearer token and, optionally,
# one for the OpenRouteService key. The file must be readable by uid 10001
# inside a host directory that other users cannot traverse.
mkdir -p -m 0700 ~/.config/percival
printf '%s' "$(openssl rand -hex 32)" > ~/.config/percival/osm_auth_token
chmod 0644 ~/.config/percival/osm_auth_token

export USER_AGENT='percival-osm/0.5.0 (you@example.com)'
export FROM_HEADER='you@example.com'

# stdio as an on-demand MCP process: no TTY, no port, no healthcheck, no restart.
docker compose run --rm -T mcp-osm

# Authenticated streamable HTTP on host loopback.
docker compose --profile http up -d mcp-osm-http
```

The Compose stack is a fixture: it renders the same contracts on a workstation
so they can be tested. Production containers are configured through the
supported manager interface, not by editing this file.

### Docker MCP Catalog

The submission artifacts live in [`servers/percival-osm/`](./servers/percival-osm/):

- `server.yaml` — registry-format definition (name, image, meta, env vars)
- `tools.json` — exposed tool catalogue (no runtime introspection needed)
- `readme.md` — documentation pointer

To submit, follow the upstream
[contributing guidelines](https://github.com/docker/mcp-registry/blob/main/CONTRIBUTING.md)
and open a PR against `docker/mcp-registry`. After approval Docker will
rebuild the image under the `mcp/percival-osm` namespace with signatures,
provenance, and SBOMs attached.

To try the entry locally with the Docker MCP Toolkit, register the image
reference directly (commands verified against Docker MCP Toolkit `v0.44.3`):

```bash
# Build a local catalog from the local image reference
docker mcp catalog create percival-osm-local:latest \
  --title "Percival OSM (local image)" \
  --server docker://percival-osm:local

# Or create a profile that runs the local image, connected to a client
docker mcp profile create --name percival-osm \
  --server docker://percival-osm:local \
  --connect opencode
```

The catalog entry declares the mandatory `NOMINATIM_URL`, `USER_AGENT` and
`FROM_HEADER`, and the optional `ORS_API_KEY` as configurable UI fields, so
operators don't need to edit a `.env`.

### Image security baseline

The shipped image is hardened by construction. The CI workflow at
`.github/workflows/docker.yml` and the static checks in
`tests/test_d6_docker.py` enforce:

| Control | Value |
|---|---|
| User | `percival` (uid/gid 10001) — non-root by default; Compose pins `10001:10001` |
| `cap_drop` | `ALL` |
| `security_opt` | `no-new-privileges:true` |
| PID 1 | launcher-owned init (`docker run --init` / Compose `init: true`) — the image embeds none |
| Read-only root FS | `read_only: true` in the Compose fixture |
| `/tmp` | `tmpfs: size=64m, mode=1777, noexec, nosuid, nodev` |
| Resources | 1 CPU / 1 GB limit, 0.25 CPU / 256 MB reservation |
| Cache | `/cache/osm-cache.json` on the named volume `percival-cache`; file mode `0600` |
| Healthcheck | `HEALTHCHECK NONE` in the image; the Compose HTTP service probes a real MCP `initialize` |
| Base images | digest-pinned (`uv`, `debian`, `python3.12` runtime) |
| Secrets | file-backed Compose secrets; absent from the rendered recipe and from `Config.Env` |

### Verification scripts

```bash
# Smoke test: non-root user, env-var guard, stdio MCP conformance probe,
# HTTP auth/bind/health/shutdown.
scripts/docker-smoke-test.sh

# Print OCI labels, healthcheck, user/entrypoint/cmd and resolved site-packages.
scripts/docker-inspect.sh

# Shared stdio conformance probe used by both the smoke test and CI.
python3 scripts/docker-ci-conformance.py --image percival-osm:local \
  --env 'USER_AGENT=smoke-test/1.0 (smoke@example.invalid)' \
  --env FROM_HEADER=smoke@example.invalid \
  --env NOMINATIM_URL=https://nominatim.openstreetmap.org/ \
  --expected-uid 10001 --expected-tool osm_find_nearby
```

---

## 📈 Observability

### Structured logging

All log records go to **stderr** (stdout is reserved for the MCP JSON-RPC
stream). Switch to one-line JSON via:

```bash
OSM_LOG_FORMAT=json OSM_LOG_LEVEL=INFO
```

Sample JSON record (operational messages omit queries and locations):

```json
{"ts": "2026-07-17T15:00:00-0300", "level": "INFO", "logger": "percival-osm", "msg": "Navigation request started."}
```

The format is stable: `ts` (ISO 8601 local), `level`, `logger`, and `msg`.
URLs, common inline credentials, exception details and tracebacks are removed;
security-event logs retain the event category but not request details
(`SECURITY_EVENT <category>`).

### Health & version

- `osm_get_version` — package version, server name, process start (ISO 8601),
  Python version.
- `osm_get_health` — `uptime_seconds`, per-tool `tool_calls` / `tool_errors` /
  `tool_outcomes`, `last_upstream_failure`, `cache` (`mode`, `degraded`,
  `io_errors`) and `cache_file`. Counters are in-memory per process; calls in
  progress may not yet have an outcome, and health can snapshot before
  counting its own outcome.
- Outcomes: `ok`, `no_results`, `invalid_request`, `provider_not_configured`,
  `config_error`, `upstream_error`, `error`, `exception`, `cancelled`, and
  `unknown`. `tool_errors` counts only propagated Python exceptions.
- `last_upstream_failure` may also carry the **stage** that failed or consumed
  the deadline (`geocode`, `overpass`, `enrich`, `route`, `rank`, `render`,
  `cleanup`), a bounded **reason** (`http_error`, `timeout`,
  `transport_error`, `invalid_response`, `partial_response`, `cooldown`,
  `deadline_exceeded`, `validation_error`, `cancelled`, `none`), the HTTP
  status when one is known, and the per-stage duration breakdown plus the time
  spent waiting locally. The vocabulary is fixed and carries no upstream
  content: no URL, header, credential, queried place, Overpass query, exception
  text, or response body.
- `osm_get_security_metrics` — security counter snapshot (URL policy blocks,
  cache-path blocks, remote-bind blocks, response-size blocks, auth failures,
  upstream failures).
- `osm_get_status` — one-line human-readable status (prefer `osm_get_health`
  for structured data).

All of them are read-only and safe to call repeatedly from an orchestrator.

### Rate limiting (Nominatim)

The [public Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/)
limits the entire application to **at most 1 request per second**, not each
agent. Select it deliberately with `NOMINATIM_URL`; startup fails if no backend
is selected. It has limited capacity and no service-level guarantee.

```bash
OSM_NOMINATIM_RATE_LIMIT_RPS=1.0
OSM_NOMINATIM_RATE_LIMIT_BURST=1
```

For the public service, disabling the rate limit, exceeding 1 req/s or using
burst greater than 1 is rejected. Nominatim and Overpass share per-process
concurrency and cooldowns; concurrent duplicate OpenRouteService distance
resolutions collapse into a single upstream request (single-flight).
Different processes, managers and replicas do not share this state: use one
shared gateway or another backend to enforce the application-wide budget.
For custom backends configure the endpoint, host allowlist, rate and burst
explicitly according to their terms; this client is conservative and sends
requests without bursts.

The public service forbids autocomplete and systematic collection, including
grid reverse geocoding and downloading complete POI lists. Its LLM section
restricts generic offerings and requires a deliberate informed developer
decision; review the policy before use. Do not send personal or confidential
data to the public service. Display OpenStreetMap attribution as appropriate.

### Deadlines and per-stage budgets

Every upstream-backed tool runs under an end-to-end deadline
(`OSM_UPSTREAM_TOOL_DEADLINE_SECONDS`, max 16 s) that covers queueing, rate
limiting, retries, body streaming and cleanup. The per-attempt timeout and the
retry backoff are bounded by the *remaining* budget, so a retry is never
started when the budget cannot sustain it, and teardown is awaited inside the
budget rather than after it. The stage that consumed the deadline is reported
in `osm_get_health`.

### Performance / hardening knobs

- **Shared `httpx.AsyncClient`** — reuses the HTTP/2 connection pool across
  requests instead of opening a new client on every call.
- **Race-free URL validation** — the `_validated_upstreams` set is guarded
  by an `asyncio.Lock`, so concurrent tools never double-validate.
- **Headers always present** — `create_headers()` short-circuits with a
  `ValueError("Headers not set")` if `user_agent` / `from_header` are
  empty, so missing config is loud, not silent.
- **Bounded response bodies** — bodies are read by streaming and aborted as
  soon as `OSM_HTTP_MAX_RESPONSE_BYTES` is exceeded.

---

## 🔒 Security model

This server enforces the following defenses (see
`osm://security/nanobot-policy` resource for the canonical machine-readable
form):

| Layer | Protection |
|---|---|
| Transport | HTTPS-only to upstreams; `follow_redirects=false` by default |
| URL policy | Allow-list of upstream hosts; `inline_credentials` rejected; private/local targets rejected |
| Headers | `User-Agent` + `From` headers mandatory; requests fail loud if missing |
| Rate limit | Public Nominatim: at most 1 req/s, no burst, one concurrent request per process |
| Single-flight | Concurrent duplicate OpenRouteService distance resolutions share one upstream request |
| Sanitization | All upstream-rendered text goes through `sanitize_external_text` / `sanitize_external_markdown` |
| Response size | Upstream bodies are capped by `OSM_HTTP_MAX_RESPONSE_BYTES` |
| Cache | File must live under `OSM_CACHE_ALLOWED_DIRS`; symlinks and directories rejected; created with mode `0600`; TTL configurable |
| Auth | Non-loopback HTTP requires `MCP_OSM_AUTH_TOKEN`; host bind is loopback by default |
| Container | Non-root uid 10001, `cap_drop ALL`, `no-new-privileges`, read-only root, launcher-owned init, secrets by reference |
| Logging | stderr only; never touches the MCP stdio stream |

Every blocking or failure path increments a counter exposed via
`osm_get_security_metrics`.

---

## 🛠️ Development & Testing

The Python install is a **development** path. It is how the code is tested and
iterated on; it is not how the server is deployed.

```bash
# Editable install + dev deps
uv sync

# Run the server (stdio transport for direct MCP use)
PYTHONPATH=src .venv/bin/python -m percival_osm_mcp --mode stdio

# Or streamable HTTP for direct API debugging
PYTHONPATH=src .venv/bin/python -m percival_osm_mcp --mode streamable-http --port 8000
```

The container entrypoint accepts the same three modes (`stdio`, `sse`,
`streamable-http`) and normalizes `MODE` into the equivalent CLI flags.

### Tests

```bash
# Run the full suite (174 tests)
uv run pytest -v

# Targeted suites
uv run pytest tests/test_s5_primitives.py       # prompts + resources + bug regressions
uv run pytest tests/test_d6_docker.py          # Dockerfile / compose / catalog artifacts
uv run pytest tests/test_s3_observability.py    # health, version, structured logging, rate limit
uv run pytest tests/test_runtime_security.py    # URL policy + sanitization
uv run pytest tests/test_f8_nearby_stage_diagnosis.py  # upstream stage attribution + deadline
```

The suite covers:

- URL allow-listing, redirect validation, private-host blocking.
- Output sanitization (HTML, markdown, control characters).
- Prompt-injection regression corpus.
- Observability primitives (health, version, operational telemetry, outcomes).
- Public Nominatim no-burst spacing, shared provider limits and cooldowns.
- Explicit backend selection and the public-service configuration guards.
- Upstream stage attribution, deadline accounting and bounded retries.
- Cache persistence resilience (corrupt/legacy payloads degrade to memory).
- ORS async migration (profile, units, auth header, cancellation).
- MCP prompt/resource registration and content integrity.
- Dockerfile, entrypoint, Compose fixture and catalog-artifact contracts.

### CI

`.github/workflows/docker.yml` runs on every push and pull request against
`main`:

1. **build** (linux/amd64) — BuildKit build with `VERSION`/`GIT_SHA` labels,
   the shared stdio conformance probe, `scripts/docker-smoke-test.sh`, a
   Compose contract render for both profiles, a build manifest and a
   CycloneDX SBOM uploaded as artifacts.
2. **catalog** — static validation of `server.yaml` + `tools.json`.
3. **test** — the full Python suite.

---

## 📚 Project records

| Path | Contents |
|---|---|
| `docs/ADR-2026-11-17-async-upstream-transport.md` | Accepted decision on the async upstream transport and the end-to-end deadline |
| `docs/integrations/percival-osm.md` | Managed-runtime integration profile (pt-BR) |
| `docs/issues/` | Open and closed issues with diagnosis and acceptance evidence |
| `docs/plans/` | Remediation plans tied to the issues |
| `docs/reports/` | Provider/authentication research reports |
| `servers/percival-osm/` | Docker MCP Catalog submission artifacts |
| `src/percival_osm_mcp/docs/security/nanobot-policy.md` | The policy shipped inside the wheel and served as `osm://security/nanobot-policy` |

### Known operational issue

`osm_find_nearby` failed repeatedly against the public Overpass endpoint
during the 2026-11-23 validation batch: the provider answered `HTTP 502` and
the call was reported as `upstream_error` with `stage=overpass`,
`reason=deadline_exceeded`, attributed by the new stage diagnostics. The
public geocoding path was healthy in the same batch. The operational
acceptance (a successful nearby search) is still pending provider
availability — see
[`docs/issues/2026-11-23-nearby-search-upstream-failures.md`](./docs/issues/2026-11-23-nearby-search-upstream-failures.md).
No upstream policy was relaxed to work around it.

---

## 📝 Changelog

### Unreleased
- Documentation revision: the README now describes the server as a
  **docker-first** component — image as artifact, entrypoint as contract,
  manager as runtime owner, Compose as local fixture — and every claim is
  re-derived from the code at this revision.
- Removed stale statements: the 0.5.0 changelog no longer claims a
  `HEALTHCHECK` covering stdio (the image ships `HEALTHCHECK NONE`), no longer
  names the superseded bookworm base images, and the catalog import command
  points at `server.yaml` instead of a non-existent `catalog.yaml`.
- Corrected the suite size (174 tests), the image size, the CI job list and
  the `USER_AGENT` examples that still carried `0.4.x`.
- Documented the environment variables that were missing from the reference
  list (HTTP timeouts, retries, response-size and concurrency caps, response
  shaping flags) and the launcher-only variables (`MODE`, `PORT`,
  `ALLOW_REMOTE_HTTP`, secret file paths).

### 0.5.0 — current
- **Bug fixes (code review round 1)**:
  - `main()` is now called exactly once in the `__main__` block (the
    CHANGELOG for 0.4.0 had claimed the 11× → 1× fix but three copies
    were still below the guard).
  - `OrsRouter.calculate_route` now computes the haversine distance
    between the two endpoints to choose the ORS profile. Previously it
    always read `to_thing.get("distance", 9000)`, but Nominatim search
    results never carry a `distance` field, so the router always used
    `driving-car` even for foot-walkable hops.
  - `osm_get_security_metrics` no longer double-counts its own
    invocation. The `@_track` decorator already bumps the counter,
    so the inline `record_tool_call(...)` in the body is gone.
  - `create_result_document` only emits an OSM link when the
    coordinates are real numbers; broken `/unknown/unknown` URLs are
    dropped, and `emit_result_citation` skips the citation entirely
    when no link is available.
  - Removed dead code at the bottom of `_http_get_json`'s retry loop
    (the loop always returns or re-raises), with a clarifying comment.
- **First-class Docker support**:
  - Multi-stage, digest-pinned Dockerfile (`ghcr.io/astral-sh/uv` builder →
    `debian:forky-slim` runtime with a copied `python3.12` runtime), with
    reproducible timestamps.
  - Hardened: non-root user (uid 10001), launcher-owned init (the image
    embeds none), `cap_drop ALL`, `no-new-privileges`, read-only root FS,
    `tmpfs /tmp` with `noexec,nosuid,nodev`, and `HEALTHCHECK NONE` —
    stdio has no truthful Docker health probe.
  - `docker-entrypoint.sh` validates `USER_AGENT` + `FROM_HEADER` (exit `78`
    / `EX_CONFIG`) and refuses to run as root (exit `77` / `EX_NOPERM`).
  - `docker-compose.yml` defaults to stdio transport (the common case)
    and exposes the streamable-http service behind an `http` profile,
    with 1 CPU / 1 GB resource caps and file-backed secrets.
  - `scripts/docker-build.sh`, `scripts/docker-smoke-test.sh` and
    `scripts/docker-inspect.sh` — reproducible build (multi-arch via
    `PLATFORMS=...` / `--platform=`), a 4-step smoke test and an image
    inspector.
  - Docker MCP Catalog submission artifacts under `servers/percival-osm/`
    (`server.yaml`, `tools.json`, `readme.md`).
  - GitHub Actions workflow (`.github/workflows/docker.yml`) runs the
    build + smoke test + conformance probe on every PR and push to main.
- **Test coverage**: the suite grew from 45 to 74 tests across the review
  rounds, with `tests/test_d6_docker.py` locking in the Dockerfile, compose,
  entrypoint and catalog artifacts.

### 0.4.1
- **Security**: removed `env_file=".env"` from `Settings`. The server no
  longer reads secrets from disk; all configuration comes from the
  process environment. Eliminates the on-disk secret leak surface and
  removes the `cwd`-dependent behaviour that forced callers to point
  `cwd` at the package directory.
- **Reliability**: added `ORS_REQUEST_TIMEOUT` (default `90`) so the
  OpenRouteService client is constructed with an explicit `timeout=`,
  raising it above the `openrouteservice` library default of 60s.
  Public-instance traffic at peak hours no longer trips false
  `openrouteservice.exceptions.Timeout` on valid routes.
- **DX**: `percival-osm/.env` removed (gitignored template is now
  documentation only); README updated to drop the `cwd` requirement
  and call out the new env-only model.

### 0.4.0
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
- **This repository**: [https://github.com/bill-kopp-ai-dev/percival-osm](https://github.com/bill-kopp-ai-dev/percival-osm)
- **Maintainer**: Positronic Bean Labs — <https://labs.positronicbean.com>
- **License**: MIT

---
*Developed with ❤️ by the percival.OS Team*
