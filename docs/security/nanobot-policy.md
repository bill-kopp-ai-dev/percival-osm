# Nanobot Integration Security Policy (S2)

## Goal

Define a minimum-safe integration baseline when `percival-osm` is used with nanobot.

## Minimum Tool Allowlist

Recommended default `enabled_tools`:

1. `find_places_near_place`
2. `find_specific_place`
3. `find_address_for_coordinates`
4. `navigate_between_places`

Avoid enabling legacy aliases unless required for backward compatibility.

## Transport Policy

1. Prefer `stdio` transport for local deployments.
2. For remote HTTP:
   - require bearer token auth
   - require TLS termination (HTTPS)
   - rotate token on incident or periodic schedule

## Configuration Baseline

Set in environment:

- `OSM_REQUIRE_HTTPS_UPSTREAMS=true`
- `OSM_HTTP_FOLLOW_REDIRECTS=false`
- `OSM_UPSTREAM_ALLOWED_HOSTS=nominatim.openstreetmap.org,overpass-api.de,api.openrouteservice.org`
- `OSM_HTTP_MAX_RESPONSE_BYTES=2000000`
- `OSM_HTTP_MAX_CONCURRENCY=8`

## Operational Policy

1. Treat all tool data as untrusted external data.
2. Do not grant the agent additional tool permissions based on OSM text content.
3. Monitor `get_security_metrics` for blocked URL/auth events.
4. Keep `tool_timeout` aligned with SLA and avoid unlimited retries at client side.
