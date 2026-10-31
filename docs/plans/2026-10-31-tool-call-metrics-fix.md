# Tool call metrics fix

- **Status:** implemented, locally validated, and included in operator-pinned MCP image
- **Owner / decision-maker:** Bill Kopp
- **Issue:** `docs/issues/2026-10-31-mcp-tool-call-metrics-not-recorded.md`
- **Outcome:** FastMCP-invoked tools report one call each, and propagated
  exceptions increment the matching error counter without incrementing calls
  a second time.

## Findings at start of work

- `_conditionally_register_tool` currently registers the untracked handler;
  the outer `_track` decorator only wraps the Python module-level reference.
- The tracking wrapper currently calls `record_tool_call(..., error=True)` on
  exceptions, incrementing `tool_calls` a second time as well as `tool_errors`.
- Legacy alias handlers manually increment their alias counter before
  delegation and are registered without exception tracking.

## Implementation plan

1. Make the registered canonical callback the tracked wrapper by applying
   `_track` before conditional FastMCP registration.
2. Add an error-only counter operation and use it in `_track`; retain the
   existing `record_tool_call(..., error=True)` behavior for compatibility
   with callers that record a completed invocation and its error together.
3. Wrap each legacy alias handler with `_track(alias_name)` before FastMCP
   registration and remove its manual counter increment.
4. Replace the decorator-order source-text regression with tests that invoke
   registered FastMCP callbacks. Verify the default surface remains exactly
   eight tools, success calls are counted once, exceptions count one call and
   one error, and an alias increments only its own counter.
5. Run focused observability/exposure tests, the full suite, syntax/diff checks,
   and the Docker MCP smoke check if the available environment supports it.

## Acceptance criteria

- A callback stored in FastMCP's tool manager is instrumented and a real
  registered-handler invocation updates `tool_calls`.
- A propagated Python exception increments `tool_errors` once while the same
  invocation increments `tool_calls` exactly once.
- Calls through registered legacy aliases count only the alias, not a
  canonical tool.
- Default `tools/list` remains the curated eight; existing reactivation
  behavior is preserved.
- Relevant focused and full automated tests pass; any unavailable checks are
  reported with their reason.

## Validation notes

No network-dependent integration is needed: exercise the actual callback
registered in FastMCP's manager with deterministic arguments or controlled
stubs. Validate Docker/runtime packaging only after local behavioral tests
pass. This source change does not itself authorize image deployment or pin
updates.

## Implementation result — 2026-10-31

- Reordered canonical decorators so FastMCP registers the `_track` wrapper.
- Added an error-only recorder for propagated exceptions; call counts now
  represent invocations once, including failed invocations.
- Applied `_track(alias_name)` to registered legacy aliases and removed their
  manual counter increment.
- Replaced the static decorator-text assertion with FastMCP callback execution
  tests for all eight default tools, error behavior for sync and async tools,
  and alias-only accounting.
- Extended `scripts/docker-ci-conformance.py` to make version then health tool
  calls over one stdio MCP session and assert both counters equal one.
- Verification: full suite `93 passed`; Python compile check and
  `git diff --check` passed; `scripts/docker-smoke-test.sh` passed against the
  local candidate, including stdio MCP and HTTP checks.
- Local candidate: `percival-osm:metrics-fix-local`, image ID
  `sha256:a033fc6f957319413a80886bdd4971804e4465bcd614d6235bdc3bebee877764`.
  It has OCI revision `unknown` because the worktree was uncommitted at build
  time. It was not deployed or pinned.
- Runtime follow-up: the combined candidate
  `sha256:67cbd63c83a231e5a98cb9a12ae28de115a8685dc906ba2d9eb320270d2ae5ff` was
  pinned by Bill. The post-pin health snapshot counted `osm_find_nearby` once;
  OCI revision remains `unknown` because the image was built before commit.
- A future release should use a clean, committed source revision for OCI
  traceability.
