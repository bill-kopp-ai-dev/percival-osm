# percival-osm

Hardened OpenStreetMap MCP server — real-time geospatial queries, POI
discovery, and turn-by-turn navigation through open OSM and
OpenRouteService APIs.

## What it provides

- 30+ tools for nearby searches, geocoding, reverse-geocoding, and
  navigation.
- 3 prompt primitives that teach the agent which tool to call and how
  to render responses.
- 2 resource primitives (`osm://categories`,
  `osm://security/nanobot-policy`) for live policy / category reference.
- Strict URL allow-list, HTTPS-only upstreams, prompt-injection
  sanitization, and a 1 req/s rate limit on Nominatim.
- Privacy-respecting: no commercial tracking; cache file is
  permission-locked to 0600 and confined to `OSM_CACHE_ALLOWED_DIRS`.

## How to use

When this server is enabled in your Docker MCP Toolkit profile, the
agent automatically discovers all of the `osm_*` tools. You can call
them from natural language, e.g.:

> "Find pharmacies within 1 km of the Eiffel Tower."

The agent picks `osm_find_nearby` with `category=pharmacies`, `place=Eiffel Tower`,
and `radius=1000`.

## Configuration

Two environment variables are mandatory (OSM Nominatim usage policy):

- `USER_AGENT` — outgoing User-Agent header, e.g. `my-agent/1.0 (you@example.com)`.
- `FROM_HEADER` — contact email in the From header.

Optional:

- `ORS_API_KEY` — OpenRouteService key for accurate routing. Without it,
  the routing tools fall back to haversine distance (less precise).
- `MCP_OSM_AUTH_TOKEN` — bearer token for non-loopback HTTP transport.
- `OSM_EXPOSE_LEGACY_ALIASES` — toggle the 23 per-category legacy tool
  aliases (default true).

## Documentation

Full project documentation lives at:
https://github.com/bill-kopp-ai-dev/percival-osm

See especially:

- `README.md` — tool catalogue, configuration, and threat model.
- `docs/security/nanobot-policy.md` — minimum-safe integration baseline.
- `docs/security/threat-model.md` — trust boundaries and controls.

## License

MIT — see the upstream repository for the full text.
