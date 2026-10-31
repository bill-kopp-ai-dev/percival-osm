# MCP upstream deadline implementation plan

- **Status:** implemented, locally validated, and confirmed in managed MCP runtime
- **Owner / decision-maker:** Bill Kopp
- **Issue:** `docs/issues/2026-10-31-mcp-upstream-deadline-exceeds-client-timeout.md`
- **Decision:** Enforce a configurable end-to-end deadline on all tracked tools
  that perform upstream requests. Use 16 seconds by default and as the maximum,
  leaving 14 seconds against the observed 30-second MCP client timeout. The
  first 24-second candidate timed out at the MCP client despite recording its
  failure before 30 seconds.

## Scope

Apply the deadline in the tracked async tool wrapper for every upstream-backed
tool. Nearby search also enforces the deadline at its shared search boundary so
it can return the existing structured `upstream_error` payload. This includes
compact/detailed variants and aliases. On cancellation, searcher cleanup must
cancel in-flight distance tasks immediately rather than using its normal
shutdown-drain window.

## Implementation

1. Add `OSM_UPSTREAM_TOOL_DEADLINE_SECONDS` (default and maximum 16; positive) to
   settings and expose the default in `.env.example` and the Compose environment.
2. Enforce an `asyncio.timeout` around each upstream-backed async tool call,
   rather than shortening each HTTP attempt independently. Keep the nearby
   search boundary timeout so it can return its structured response.
3. Translate expiry to a safe `upstream_error` response and record a sanitized
   deadline failure. Ensure cancellation does not wait through the normal
   shutdown-drain window before closing HTTP clients/background tasks.
4. Preserve useful upstream status in `last_upstream_failure` when the outer
   provider wrapper handles an exception; do not include URLs or request data.
5. Add deterministic delayed-upstream regressions for generic upstream-backed
   tools and compact/detailed nearby paths. Verify elapsed time is bounded,
   MCP-visible response status is `upstream_error`, `tool_calls` increases once,
   and cleanup completes.
6. Update the issue with the selected budget, implementation, test evidence and
   any remaining applicability limits.

## Acceptance evidence

- Settings validation accepts the default and lower positive values and rejects
  zero/negative values and values above 16 seconds.
- A blocked Nominatim or Overpass fixture is cancelled at the end-to-end
  deadline; the caller gets a controlled `upstream_error` well before 30 s.
- The delayed request leaves no pending asyncio task and the HTTP client closes.
- A provider HTTP failure retains a sanitized status summary in health metadata.
- Focused tests and the full project suite pass; Docker conformance/smoke checks
  run if the local Docker environment is available.

## Limitations

The 30-second transport limit was observed for the client in the reported test,
not established as universal across all MCP consumers. The 16-second cap is a
conservative compatibility choice after the 24-second candidate failed to
deliver an error response before the client timeout.

## Implementation result — 2026-10-31

- Added `OSM_UPSTREAM_TOOL_DEADLINE_SECONDS` with a 16-second default and
  `(0, 16]`
  validation; documented it in `.env.example`, Compose and README.
- Applied one deadline to upstream-backed tracked tools and a structured timeout
  boundary to compact/detailed nearby search. Timeout returns `upstream_error`,
  records a sanitized deadline event, and closes HTTP clients without waiting
  through the normal background-task drain window.
- Made cancellation clean up distance futures/tasks and preserved sanitized
  provider HTTP status summaries in health metadata.
- Added deterministic tests for both nearby handlers, geocoding, and the real
  FastMCP callback over a delayed Overpass HTTP fixture; also covers bounded
  cleanup, deadline validation, call counting, and Overpass HTTP 503 diagnostics.
- Verification before runtime-retest adjustment: `99 passed`; Python compilation
  and `git diff --check` passed; Compose config and Docker smoke passed.
- After the runtime-retest adjustment: `100 passed`; Python compilation,
  `git diff --check`, and `docker compose config --quiet` passed. Rebuilt
  `percival-osm:deadline-local` as
  `sha256:67cbd63c83a231e5a98cb9a12ae28de115a8685dc906ba2d9eb320270d2ae5ff`;
  Docker smoke passed after the rebuild.
- Bill pinned the local candidate in the managed MCP runtime; no registry
  publication occurred. OCI revision remains `unknown` because the worktree was
  uncommitted at image build time.

## Runtime retest follow-up — 2026-10-31

- Bill tested image `sha256:a8df6ec22f69aeae3c27d1eb61e915e475d45da98fe610bb256626e65b31ed54`.
- For the MASP nearby call, `last_upstream_failure` recorded
  `end-to-end deadline exceeded after 24s` at 25.44 s after tool start, but the
  MCP client still returned its 30-second timeout without a JSON body.
- This disproves the assumption that a six-second margin suffices. The recorded
  failure timestamp precedes response delivery, so post-timeout cleanup or
  transport handoff remains a plausible source of delay; available evidence
  does not identify which one.
- Revised the default/maximum tool deadline to 16 s and bounded cancellation
  cleanup to 2 s. Added an in-process FastMCP callback regression with a delayed
  Overpass HTTP fixture that asserts the controlled JSON payload reaches the
  caller despite deliberately stalled cleanup; the separate nearby regression
  verifies normal HTTP-client closure.
- **Retest passed:** Bill pinned
  `sha256:67cbd63c83a231e5a98cb9a12ae28de115a8685dc906ba2d9eb320270d2ae5ff`.
  The real client received the `upstream_error` JSON before its 30-second
  timeout, with the expected “exceeded its execution deadline” message.
- Health reported `tool_calls.osm_find_nearby=1`,
  `last_upstream_failure.kind=NearbySearch` and the 16-second deadline. The
  search returned no POIs because the timeout path was intentionally exercised.
- `tool_errors` remained empty by design. A separate issue now tracks an
  aggregate per-tool/status outcome metric so dashboards need not rely only on
  propagated exceptions.
