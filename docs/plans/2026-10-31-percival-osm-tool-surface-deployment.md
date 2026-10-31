# Percival OSM tool-surface deployment

- **Status:** deployed to local Percival manager and superseded image removed
- **Owner / decision-maker:** Bill Kopp
- **Request:** deploy the reduced tool surface to the local Percival OSM MCP and
  remove superseded Percival OSM images afterward.
- **Boundary:** local Percival manager only; no Positronic mutation, registry
  push, public release, VPS deployment or data migration.

## Target and candidate

- Percival server ID: `osm`, owner `percival`, stdio.
- Current pin (A): `sha256:3e6cc7ddf291ec5f06aa86bd21baab7ef7a6648d9f48968b7dae421cceadc8bc`.
- Candidate (B) tag: `percival-osm:0.5.0-aa8000e-f3-96de7f9b77a1`.
- Candidate image ID: `sha256:37ae7ce709595b81e82e0802db8154eaab7c05d0c9c172d9663aa3ccc7eb5ae9`.
- Source revision: `aa8000e588467943c5675ce720aa7ce41915f7d9` plus tracked-diff
  SHA-256 `96de7f9b77a1074f2fd21a21aadb3fd42272aa178a4fe764b2b1e5b2e2ce1686`.
- The older Positronic OSM image `sha256:805b81ae60cb6726dc9d0590641abb0432557f96ed28ca5a617d7408a81f738e`
  is outside scope and must remain intact.

## Execution and acceptance

1. Build a local immutable worktree candidate with version, source revision,
   platform, phase and diff identity labels. Do not publish the image.
2. Verify container hardening, MCP `initialize`/`tools/list` (exactly eight
   default tools), and a read-only `osm_get_version` call.
3. Re-read the Percival manager server/global revisions, config, current pin and
   target; update only server `osm` to B through the authenticated/elevated
   Percival WebUI/API using compare-and-swap.
4. Verify the manager's image pin, running container, MCP connectivity, exact
   eight-tool list, safe `osm_get_version` call and committed audit/transition.
5. Re-inventory references. Remove only superseded Percival OSM image IDs that
   have no remaining container/config/compose/fixture reference. Never remove
   Positronic-owned pins or use image/system prune.

## Rollback and retention

The previous Percival image A is the immediate rollback image. Bill requested
cleanup after a successful deployment; deleting A removes local rollback for
that image ID. Preserve A until B passes the manager handshake and safe call,
then apply the requested cleanup only to the explicitly identified old
Percival OSM image. If deployment or verification fails, restore A through the
Percival manager and retain B for diagnosis; do not clean either image during
recovery.

## Evidence to record at completion

- Image inspect labels and exact image ID.
- Manager before/after revisions, pin, container state and observed tools.
- MCP safe-call response and audit/transition status.
- Explicit image IDs removed and post-cleanup reference inventory.

## Execution result — 2026-10-31

- The canonical Nanobot build wrapper omitted `SOURCE_DATE_EPOCH`, so its first
  candidate build stopped at the Dockerfile timestamp-normalization step. The
  candidate was then built locally with the same source/version/platform and
  worktree identity, supplying the expected epoch explicitly; no wrapper or
  manager state was edited.
- B is image ID `sha256:37ae7ce709595b81e82e0802db8154eaab7c05d0c9c172d9663aa3ccc7eb5ae9`,
  `linux/amd64`, version `0.5.0`, revision `aa8000e588467943c5675ce720aa7ce41915f7d9`,
  worktree diff `96de7f9b77a1074f2fd21a21aadb3fd42272aa178a4fe764b2b1e5b2e2ce1686`.
- `scripts/docker-smoke-test.sh` passed all checks; an isolated hardened stdio
  container initialized, listed the exact eight tools, and returned a successful
  `osm_get_version` response.
- Bill applied the image update through the Percival UI. The supplied UI evidence
  shows `osm` running/connected at B with eight observed tools. The redacted
  read-only inventory independently confirms the Percival OSM container and
  `~/.nanobot` pin both reference B. The Positronic OSM container remains on
  `sha256:805b81ae60cb6726dc9d0590641abb0432557f96ed28ca5a617d7408a81f738e`.
- The Percival audit records one `update-image started` at revision 21 and two
  `committed` rows at revision 22 with the same correlation ID. The config and
  container show one image transition; the duplicate audit event is an existing
  manager audit anomaly, not evidence of a second revision change.
- After checking there were no remaining Percival container/config references,
  the old A image ID `sha256:3e6cc7ddf291ec5f06aa86bd21baab7ef7a6648d9f48968b7dae421cceadc8bc`
  was removed, including tags `stage2-312964c-clean2` and
  `stage2-312964c-clean3`. Post-cleanup inventory confirms A is absent and B is
  active/pinned. The prior local rollback image is therefore no longer available.
- No registry publication, code commit, Positronic update, or deployment outside
  the local Percival manager was performed.

## Post-deployment functional test — 2026-10-31

- Bill's eight-tool test passed `osm_get_version`, `osm_get_health`,
  `osm_get_security_metrics`, `osm_geocode`, `osm_find_address` and
  `osm_find_place` (6/8). `osm_find_nearby` timed out after 30 seconds without a
  partial result; the test correctly did not retry. `osm_directions` returned
  `provider_not_configured` because `ORS_API_KEY` is not configured; no route
  was estimated.
- The `osm_get_health` report showed empty per-tool counters after the earlier
  version call. Reproduction against candidate B using one MCP stdio session
  (`osm_get_version`, then `osm_get_health`) also returned empty `tool_calls`
  and `tool_errors`. Source review identifies the cause: `@_track` wraps the
  result of `@_conditionally_register_tool`, but the latter registers the
  original handler with FastMCP before the tracking wrapper is applied. Thus the
  live MCP callback is not tracked. The empty security metrics are expected in
  the absence of security events; the health snapshot was taken before the later
  nearby timeout, so its `last_upstream_failure=null` is not contradictory.
- Follow-up: change registration so FastMCP receives the tracked callback, add
  a runtime regression asserting that exposed canonical calls update their
  counters, then rebuild and update the local Percival pin. Re-test `osm_find_nearby`
  with a smaller bounded query if another attempt is approved. To test routing,
  configure `ORS_API_KEY` through the supported Percival interface and then
  exercise `osm_directions`; do not send the key in chat.
