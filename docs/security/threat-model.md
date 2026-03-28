# Threat Model (S2)

## Scope

This document covers the `percival-osm` MCP server runtime and its trust boundaries:

- MCP client/agent (for example nanobot or Claude Desktop)
- HTTP transport (`sse` / `streamable-http`)
- External upstreams (Nominatim, Overpass, OpenRouteService)
- Local cache file
- Container/runtime environment

## Trust Boundaries

1. Client request boundary:
   - Tool inputs from MCP clients are untrusted.
2. Upstream data boundary:
   - OSM/ORS payloads are untrusted third-party data.
3. Transport boundary:
   - Remote HTTP transport is authenticated but must rely on TLS termination.
4. Filesystem boundary:
   - Cache file and `.env` data must be scoped and permission-controlled.

## Main Threats and Controls

1. Prompt injection in upstream text:
   - Control: structured JSON responses and sanitization.
   - Control: explicit untrusted-data warning in tool outputs.
   - Residual risk: downstream agent may still misuse untrusted fields.

2. SSRF / unsafe upstream destinations:
   - Control: upstream host allowlist + private/local target blocking.
   - Control: HTTPS required by default.

3. Abuse / resource exhaustion:
   - Control: request timeout, retries, response-size cap, concurrency cap.

4. Credential/token exposure:
   - Control: no inline upstream credentials.
   - Control: remote bind requires auth token.
   - Control: error redaction in end-user output.

5. Cache data exposure:
   - Control: cache path restricted to allowed directories.
   - Control: cache file permissions forced to `0600`.

6. Runtime/container breakout blast radius:
   - Control: non-root container user.
   - Control: read-only root FS, `no-new-privileges`, capability drop.

## Security Telemetry

In-memory counters and audit log events are emitted for:

- `auth_rejected`
- `remote_bind_blocked`
- `upstream_url_blocked`
- `upstream_response_blocked`
- `upstream_request_failure`
- `cache_path_blocked`

Metrics can be inspected through the `get_security_metrics` tool.

## Assumptions

- TLS is terminated by trusted infrastructure in remote HTTP deployments.
- Secrets are supplied via environment variables and not hardcoded.
- MCP client policy (tool allowlist) is managed externally.

## Out of Scope

- Compromise of upstream providers.
- Host/kernel-level compromise.
- End-user prompt safety policies outside this repository.
