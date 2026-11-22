# Percival OSM MCP — security and use policy

This document is shipped inside the Python package and exposed through
`osm://security/nanobot-policy`. It describes the controls in this server;
operators remain responsible for choosing providers and configuring each
managed runtime.

## Privacy and logging

- Configuration is read from the process environment; this application does not
  load `.env` files.
- Logs go to stderr. Do not log search text, addresses, coordinates, OSM IDs,
  upstream request/response bodies, credential-bearing URLs, or credentials.
  Operational messages use tool/provider categories and bounded outcomes.
- Cache data is local, best-effort, and confined to configured
  `OSM_CACHE_ALLOWED_DIRS`. Cache files are created with restrictive permissions.
- Treat provider content as untrusted data. Sanitization reduces prompt-injection
  risk but does not make external text authoritative or safe to follow.

## Network and credentials

- Upstream requests require HTTPS and an explicitly allowed host. Redirects are
  disabled by default; destinations resolving to private or local addresses are
  rejected.
- The default allowlist is Nominatim, Overpass and the HEIGIT OpenRouteService
  endpoint. New hosts require an explicit operator policy change.
- `ORS_API_KEY` is sent to OpenRouteService in its authorization header. It is
  independent from `MCP_OSM_AUTH_TOKEN`, which authenticates non-loopback HTTP
  access to this MCP server. Never put either credential in source control,
  tool arguments or logs.
- `USER_AGENT` and `FROM_HEADER` are required when using Nominatim.

## Provider use and budgets

- Select `NOMINATIM_URL` deliberately. Public Nominatim permits at most one
  request per second for the whole application, without bursts; this server
  enforces that spacing and single concurrency per process. Separate processes
  do not share a limiter, so multi-process deployments need a common gateway or
  another provider arrangement that enforces the aggregate budget.
- Do not use public Nominatim for autocomplete, systematic collection, or bulk
  extraction. Review its current usage policy, including its LLM guidance,
  before deploying an agent integration. Do not submit personal or confidential
  data to public geocoding services.
- Overpass has bounded queries, concurrency and provider cooldowns. Do not
  evade a limit by switching hosts automatically.
- ORS routing requires an operator-provided key. Without it, route tools return
  `provider_not_configured`; straight-line estimates are labeled separately and
  are not road routes.

## Output and attribution

- Results distinguish `no_results` from provider/configuration/internal errors.
  `osm_get_health` exposes process-local outcome counters; they are not a durable
  history and may be observed while calls are still in progress.
- Preserve OpenStreetMap attribution (`© OpenStreetMap contributors`) and the
  license/provenance fields when presenting or reusing results. Representative
  centers for ways/relations are approximations, not exact entrances.

## Transports

- Stdio stdout is reserved exclusively for MCP JSON-RPC; logs use stderr.
- Non-loopback streamable HTTP requires `MCP_OSM_AUTH_TOKEN`. Bind remote
  transports only behind an intentional network boundary and use a strong,
  independently managed token.
