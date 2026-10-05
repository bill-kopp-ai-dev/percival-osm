# Docker deployment guide

This document is the long-form reference for running `percival-osm` as a
container. For the 5-minute quickstart, see the [Docker section of the
README](../../README.md#-docker-deployment).

## Contents

1. [Why a container at all?](#why-a-container-at-all)
2. [Image architecture](#image-architecture)
3. [Build](#build)
4. [Run modes](#run-modes)
   - [stdio (the common case)](#stdio-the-common-case)
   - [streamable-http](#streamable-http)
   - [SSE](#sse)
5. [Wire into MCP clients](#wire-into-mcp-clients)
6. [docker-compose](#docker-compose)
7. [Docker MCP Catalog / Toolkit](#docker-mcp-catalog--toolkit)
8. [Operating](#operating)
9. [Troubleshooting](#troubleshooting)
10. [Submitting to the Docker MCP Catalog](#submitting-to-the-docker-mcp-catalog)

---

## Why a container at all?

The server is a single Python module that depends on the OSM / Overpass /
OpenRouteService public APIs. Most operators will run it through their
MCP client of choice (nanobot, opencode, Claude Desktop, …) directly via
`uv run`. So why ship a Docker image?

1. **Reproducibility** — the build resolves a frozen lockfile into a
   relocatable venv. The same image runs on Linux, macOS, or Windows
   hosts (via Docker Desktop) without re-installing Python or any
   system library.
2. **Isolation** — the image runs as a dedicated non-root user, drops
   all capabilities, mounts `noexec` tmpfs on `/tmp`, and confines the
   cache to a named volume. The host filesystem stays untouched.
3. **Distribution** — the `servers/percival-osm/` artifacts are
   pre-formatted for the [Docker MCP Catalog](https://hub.docker.com/mcp)
   so the server can be installed from the Toolkit UI without touching
   a JSON config.
4. **Operational ergonomics** — the same image runs as a one-shot
   `docker run` for development or as a long-lived compose stack for
   production; healthchecks, resource caps, and log routing come for
   free.

## Image architecture

```
ghcr.io/astral-sh/uv:python3.12-bookworm-slim   ← builder stage
│   uv sync --frozen --no-dev
│   uv pip install --no-deps /build             ← wheel install
│
└─▶ python:3.12-slim-bookworm                   ← runtime stage
        bash, ca-certificates, curl, tini
        USER percival (uid 10001)
        ENTRYPOINT ["/usr/bin/tini", "--", "docker-entrypoint.sh"]
        HEALTHCHECK pgrep in stdio / curl in http mode
        EXPOSE 8080
```

The two stages are kept in the same `Dockerfile` so the build context
is self-contained. The final image is ~249 MB uncompressed and contains:

- the resolved Python venv at `/app/.venv` (copied from the builder)
- the source at `/app/src/percival_osm_mcp/`
- the bundled `docs/security/nanobot-policy.md` resource
- the entrypoint at `/usr/local/bin/docker-entrypoint.sh`
- a `tini` PID 1 wrapper

What is *not* in the image: dev dependencies, the test tree, the
`docs/` HTML renderings, the project metadata under `.positronic/`,
`AGENTS.md`, or the `servers/` catalog submission. These are all
blocked in `.dockerignore`.

## Build

```bash
# Default: host arch (linux/amd64 on x86_64, linux/arm64 on Apple Silicon)
scripts/docker-build.sh

# Pin an extra tag (e.g. for a release)
scripts/docker-build.sh v0.5.0

# Multi-arch build (use a buildx builder; --load is skipped because
# the local daemon can't hold two architectures at once)
PLATFORMS=linux/amd64,linux/arm64 scripts/docker-build.sh v0.5.0

# Or use docker buildx directly for advanced scenarios
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag ghcr.io/bill-kopp-ai-dev/percival-osm:v0.5.0 \
  --push \
  .
```

The build is reproducible thanks to:

- `uv sync --frozen` — pins the dependency tree to `uv.lock`
- `python -m pip install --no-deps /build` — installs the resolved wheel
  (not editable mode, so the path inside the container is stable)
- OCI labels carry `org.opencontainers.image.revision` and
  `org.opencontainers.image.created` for traceability

## Run modes

The container supports the same `--mode {stdio, sse, streamable-http}`
flags as the bare Python entrypoint. The `MODE` environment variable
selects the mode; `PORT` and `ALLOW_REMOTE_HTTP` are only consulted in
HTTP modes.

### stdio (the common case)

The `mcpServers.percival-osm.command` in any MCP client is the
canonical way to launch the container:

```bash
docker run --rm -i \
  -e USER_AGENT='percival-osm/0.5.0 (you@example.com)' \
  -e FROM_HEADER='you@example.com' \
  -e ORS_API_KEY='eyJvcmciOi...' \
  percival-osm:local
```

`--rm` cleans up the container on exit, `-i` keeps stdin open for the
JSON-RPC stream. The container is *not* bound to any host port — the
client talks to it over stdio.

### streamable-http

For browser-based debug tools, the Docker MCP Toolkit, or remote
deployments:

```bash
docker run --rm -p 8080:8080 \
  -e USER_AGENT='percival-osm/0.5.0 (you@example.com)' \
  -e FROM_HEADER='you@example.com' \
  -e MODE=streamable-http \
  -e ALLOW_REMOTE_HTTP=true \
  -e MCP_OSM_AUTH_TOKEN="$(openssl rand -hex 32)" \
  percival-osm:local
```

The MCP endpoint is exposed at `http://127.0.0.1:8080/mcp`. The
`Authorization: Bearer <token>` header (or `X-MCP-Auth-Token`) is
required for any request.

### SSE

`sse` is also supported for clients that pre-date the streamable
transport:

```bash
docker run --rm -p 8080:8080 \
  -e USER_AGENT='percival-osm/0.5.0 (you@example.com)' \
  -e FROM_HEADER='you@example.com' \
  -e MODE=sse \
  -e ALLOW_REMOTE_HTTP=true \
  -e MCP_OSM_AUTH_TOKEN="$(openssl rand -hex 32)" \
  percival-osm:local
```

SSE is on `/sse` + `/messages/`; streamable-HTTP is on `/mcp`.

## Wire into MCP clients

The same `docker run` invocation works for every stdio-based MCP
client. Below are the canonical snippets; consult your client's own
docs for the exact path of the config file.

### nanobot (`~/.nanobot/config.json`)

```json
{
  "tools": {
    "mcpServers": {
      "percival-osm": {
        "command": "docker",
        "args": [
          "run", "--rm", "-i",
          "-e", "USER_AGENT=percival-osm/0.5.0 (you@example.com)",
          "-e", "FROM_HEADER=you@example.com",
          "-e", "ORS_API_KEY=${OPENROUTESERVICE_API_KEY}",
          "percival-osm:local"
        ],
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

`${OPENROUTESERVICE_API_KEY}` is expanded by the launcher from the
agent's `.env` (or your shell). Wrap it in a placeholder so the
secret never lands in the JSON file itself.

### opencode (`~/.config/opencode/opencode.json` or workspace
`opencode.json`)

```json
{
  "mcp": {
    "percival-osm": {
      "type": "stdio",
      "command": [
        "docker", "run", "--rm", "-i",
        "-e", "USER_AGENT=percival-osm/0.5.0 (you@example.com)",
        "-e", "FROM_HEADER=you@example.com",
        "percival-osm:local"
      ]
    }
  }
}
```

### Claude Desktop

Add the same `docker run … percival-osm:local` invocation under
`mcpServers.percival-osm` in
`~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows).

## docker-compose

```bash
cp .env.example .env
$EDITOR .env                # set USER_AGENT, FROM_HEADER, optional ORS_API_KEY

# Stdio service (default; referenced by the MCP client)
docker compose up -d percival-osm

# Streamable-HTTP service (behind the ``http`` profile)
docker compose --profile http up -d percival-osm-http
```

The compose file declares:

- `user: 10001:10001` — matches the Dockerfile's `percival` user
- `read_only: true` plus a `tmpfs /tmp` for ephemeral scratch
- `cap_drop: [ALL]` and `security_opt: no-new-privileges:true`
- `deploy.resources.limits.cpus: "1"` and `memory: 1G` — matches
  the Docker MCP Toolkit caps
- a named volume `percival-cache` mounted at `/cache` so the
  permission-locked cache file survives container restarts

Stop and remove the stack with `docker compose down`. To also wipe the
cache volume, pass `--volumes`.

## Docker MCP Catalog / Toolkit

The catalog submission under
[`servers/percival-osm/`](../../servers/percival-osm/) declares the
required env vars (`USER_AGENT`, `FROM_HEADER`), the optional routing
key (`ORS_API_KEY`), and the optional bearer token (`MCP_OSM_AUTH_TOKEN`)
as configurable UI fields. When the upstream PR is accepted, Docker
rebuilds the image under the `mcp/percival-osm` namespace with
cryptographic signatures, provenance, and SBOMs.

For local development, the catalog entry can be imported directly:

```bash
# Build the local image first
scripts/docker-build.sh

# Import the catalog entry into the Toolkit
docker mcp catalog import servers/percival-osm/catalog.yaml

# Enable the server in your default profile
docker mcp server enable percival-osm
```

## Operating

### Healthcheck

The container ships a `HEALTHCHECK` directive that:

- In stdio mode: verifies the `percival_osm_mcp` process is alive via
  `pgrep -f`. An upstream failure does *not* flap the container's
  health — only the process itself.
- In HTTP mode: issues a `curl` to the bound port and treats any of
  `200 / 401 / 404 / 405` as "the server is up". A 401 is acceptable
  because the auth middleware rejects unauthenticated traffic before
  the app layer.

Use `docker inspect --format '{{.State.Health.Status}}' <container>`
to read the current state from outside.

### Logs

All log records go to **stderr** (stdout is the MCP JSON-RPC stream in
stdio mode). Use `docker logs --follow <container>` to tail them.

The server respects `OSM_LOG_FORMAT=plain|json` and
`OSM_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR`. Switch to JSON in production:

```bash
docker run --rm -i \
  -e OSM_LOG_FORMAT=json -e OSM_LOG_LEVEL=INFO \
  -e USER_AGENT=... -e FROM_HEADER=... \
  percival-osm:local |& jq
```

### Cache lifecycle

The cache file lives at `/cache/osm-cache.json` (override with
`OSM_CACHE_FILE`) inside the container. Its permissions are forced
to `0600` on every write. The default `OSM_CACHE_ALLOWED_DIRS=/cache`
restricts the path to that directory — pointing the cache at
`/etc` is blocked by `resolve_secure_cache_path`.

For a persistent cache, use a named volume (`percival-cache` in the
compose file). For a one-shot dev run, leave the path default and the
container's writable layer holds the cache until it exits.

### Resource tuning

The compose stack caps at 1 CPU and 1 GB memory. To raise the caps,
edit `deploy.resources.limits` in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: "2"
      memory: 2G
```

For raw `docker run`, pass `--cpus` and `--memory`:

```bash
docker run --rm -i --cpus=2 --memory=2g \
  -e USER_AGENT=... -e FROM_HEADER=... \
  percival-osm:local
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `error: required environment variables are not set: USER_AGENT FROM_HEADER` and the container exits 78 | Nominatim policy env vars missing or empty | Pass `-e USER_AGENT=... -e FROM_HEADER=...`; the server refuses to start without them. |
| `error: refusing to run as root (current uid=0)` and the container exits 77 | The host passed `--user 0` or the compose file dropped `user: "10001:10001"` | Remove the `--user` override or set `user: "10001:10001"` in compose. |
| HTTP 401 on every request | `MCP_OSM_AUTH_TOKEN` not set or wrong | Set the env var, or hit the loopback host where the auth middleware is not required. |
| HTTP 401 in HTTP mode but agent should not need auth | Loopback expectation wrong | The auth middleware is only bypassed on `127.0.0.1` / `localhost` / `::1`. Any other host needs the token. |
| `ModuleNotFoundError: No module named 'percival_osm_mcp'` | Wrong entrypoint or stale image | Rebuild with `scripts/docker-build.sh --no-cache` and check `scripts/docker-inspect.sh` confirms the wheel is installed. |
| Container starts but the agent's tool list is empty | `OSM_EXPOSE_LEGACY_ALIASES=true` is on but no canonical tools either | The image always exposes the 14 canonical tools. Check `OSM_LOG_LEVEL=DEBUG` and `docker logs` for registration errors. |
| `httpx.ConnectError` for every upstream call | The container is on a network that blocks the OSM upstreams | Verify outbound DNS and HTTPS to `nominatim.openstreetmap.org`, `overpass-api.de`, `api.openrouteservice.org`. |
| Rate limit false-positives | `OSM_NOMINATIM_RATE_LIMIT_RPS` too low for the agent's call rate | Raise to 2-3 for self-hosted Nominatim; lower is fine for the public instance. |

For more, see the [incident response playbook](../../security/incident-response.md).

## Submitting to the Docker MCP Catalog

The artifacts in `servers/percival-osm/` follow the registry format
defined in
[`docker/mcp-registry/CONTRIBUTING.md`](https://github.com/docker/mcp-registry/blob/main/CONTRIBUTING.md).
To submit:

1. Fork [`docker/mcp-registry`](https://github.com/docker/mcp-registry).
2. Copy `servers/percival-osm/{server.yaml,tools.json,readme.md}` into
   `servers/` of your fork.
3. Update the `source.commit` field in `server.yaml` to the SHA of the
   release tag being imported.
4. Open a PR. CI will build the image, run the `task wizard`-driven
   smoke test, and queue a review.
5. After approval Docker rebuilds the image under
   `docker.io/mcp/percival-osm` with cryptographic signatures and
   publishes it to [hub.docker.com/mcp](https://hub.docker.com/mcp).
