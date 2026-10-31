# percival-osm

Hardened OpenStreetMap MCP server — real-time geospatial queries, POI
discovery, and turn-by-turn navigation through open OSM and
OpenRouteService APIs.

## What it provides

- 8 curated MCP tools exposed by default for nearby searches, geocoding,
  reverse-geocoding, navigation, and operational visibility. Other tool
  handlers remain available for explicit reactivation.
- 3 prompt primitives that teach the agent which tool to call and how
  to render responses.
- 2 resource primitives (`osm://categories`,
  `osm://security/nanobot-policy`) for live policy / category reference.
- Strict URL allow-list, HTTPS-only upstreams, prompt-injection
  sanitization, and a 1 req/s rate limit on Nominatim.
- Privacy-respecting: no commercial tracking; cache file is
  permission-locked to 0600 and confined to `OSM_CACHE_ALLOWED_DIRS`.

## How to use

When this server is enabled in your Docker MCP Toolkit profile, the agent
discovers the tools selected by `OSM_EXPOSED_TOOLS`. The default profile
includes `osm_find_nearby`; for example:

> "Find pharmacies within 1 km of the Eiffel Tower."

The agent picks `osm_find_nearby` with `category=pharmacies`, `place=Eiffel Tower`,
and `radius=1000`.

## Configuration

Two environment variables are mandatory (OSM Nominatim usage policy):

- `USER_AGENT` — outgoing User-Agent header, e.g. `my-agent/1.0 (you@example.com)`.
- `FROM_HEADER` — contact email in the From header.

Optional:

- `ORS_API_KEY` — OpenRouteService key required by routing tools. Without it,
  `osm_navigate` and `osm_directions` return `provider_not_configured`.
- `MCP_OSM_AUTH_TOKEN` — bearer token for non-loopback HTTP transport.
- `OSM_EXPOSED_TOOLS` — comma-separated list of tool names; defaults to the
  eight curated names in `tools.json`. Set to `all` to expose all handlers.
- `OSM_EXPOSE_LEGACY_ALIASES` — additional gate for category aliases (default
  true); aliases also need to be selected by `OSM_EXPOSED_TOOLS`.

## Documentation

Full project documentation lives at:
https://github.com/bill-kopp-ai-dev/percival-osm

See especially:

- `README.md` — tool catalogue, configuration, and threat model.
- `docs/security/nanobot-policy.md` — minimum-safe integration baseline.
- `docs/security/threat-model.md` — trust boundaries and controls.

## License

MIT — see the upstream repository for the full text.
