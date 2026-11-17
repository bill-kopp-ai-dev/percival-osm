# MCP tool exposure reduction

- **Status:** implemented and verified locally — **closed** (audited 2026-11-16)
- **Owner / decision-maker:** Bill Kopp
- **Scope:** reduce the default MCP `tools/list` surface from 37 to 8 tools while
  retaining every existing implementation for explicit future reactivation.

## Decision

Keep these eight tools exposed by default:

- `osm_find_nearby`
- `osm_find_place`
- `osm_find_address`
- `osm_geocode`
- `osm_directions`
- `osm_get_health`
- `osm_get_security_metrics`
- `osm_get_version`

Do not delete handlers or category definitions for other tools. Add
`OSM_EXPOSED_TOOLS` as a comma-separated exposure allowlist. Its default is the
eight names above. The special value `all` exposes all canonical tools and,
subject to `OSM_EXPOSE_LEGACY_ALIASES`, all 23 category aliases. Explicitly
listed tools can be re-enabled individually. Unknown names and invalid
combinations must fail startup clearly rather than being silently ignored.

`OSM_EXPOSE_LEGACY_ALIASES` remains an independent safety/compatibility gate:
when false, no category aliases are exposed even if `OSM_EXPOSED_TOOLS=all`
or an alias name is listed explicitly.

## Implementation plan

1. Add exposure configuration and conditional registration around existing
   canonical and alias handlers; keep handler implementations intact.
2. Make the MCP prompts recommend only the default exposed tools; keep category
   reference data and legacy aliases documented as opt-in.
3. Align Docker Catalog `tools.json`, catalog configuration, README and project
   brief with the eight-tool default and reactivation settings.
4. Update tests to verify the exact default surface, individual/all reactivation,
   alias gating, and preservation of handler behavior.
5. Run focused tests, full test suite, lint/diff checks, and a real MCP
   `tools/list` smoke check for the default and `all` configurations.

## Acceptance criteria

- Default `tools/list` contains exactly the eight names above.
- All original canonical handlers remain in source and can be re-exposed via
  configuration; all 23 alias definitions remain intact.
- `OSM_EXPOSED_TOOLS=all` exposes 37 tools when legacy aliases are enabled.
- Explicit allowlists can re-expose selected tools; aliases remain suppressed
  when `OSM_EXPOSE_LEGACY_ALIASES=false`.
- Invalid names or malformed allowlists produce a clear startup error.
- Prompts and catalog artifacts do not recommend unavailable tools by default.
- Tests and MCP smoke verification pass.

## Compatibility and risk

This intentionally changes the default protocol-visible tool list. Existing
clients relying on a tool outside the eight-tool default must set an explicit
`OSM_EXPOSED_TOOLS` allowlist before upgrading. Implementations and legacy names
remain available for rollback/reactivation by configuration; no behavior is
deleted. The currently active Percival deployment is not changed by this local
source refactor.

## Implementation result — 2026-10-31

- The eight-tool default is registered with FastMCP; all 14 canonical
  implementations and 23 alias handlers remain in source and are selectable
  through the exposure configuration.
- README, project brief, prompt/category primitives, Docker Catalog metadata,
  sample environment and smoke-test expectations now describe the default
  surface and opt-in behavior.
- Verification: full suite `91 passed`; actual stdio MCP initialize +
  `tools/list` returned the exact 8 default names; the same wire-level check
  with `OSM_EXPOSED_TOOLS=all` returned 37 tools; focused tests also confirmed
  alias gating and selected alias execution. `git diff --check` passed.
- Ruff was not run because it is not installed in the project virtualenv.
- This changes the local source/configuration only. The already running Percival
  MCP deployment has not been rebuilt or changed and will continue to report its
  current tool list until a separately authorized image update/re-pin.

## Audit verification — 2026-11-16

- Default surface reconfirmed at runtime: `mcp.list_tools()` returns exactly
  `osm_directions`, `osm_find_address`, `osm_find_nearby`, `osm_find_place`,
  `osm_geocode`, `osm_get_health`, `osm_get_security_metrics`,
  `osm_get_version` — 8 tools, matching
  `Settings.exposed_tools` (`src/percival_osm_mcp/server.py:191`).
- `OSM_EXPOSED_TOOLS=all` with legacy aliases enabled returns 37 tools, as
  specified in the acceptance criteria.
- Inventory reconfirmed: 14 canonical handlers (`CANONICAL_TOOL_NAMES`) and 23
  category aliases (`LEGACY_CATEGORY_ALIASES`) remain in source; no handler was
  deleted.
- Alias gating reconfirmed: the alias registration block is skipped entirely
  when `OSM_EXPOSE_LEGACY_ALIASES=false`, and each alias is additionally
  filtered by `_tool_is_exposed` (`src/percival_osm_mcp/server.py:3925-3944`).
- Invalid exposure configuration still fails fast:
  `validate_tool_exposure_configuration()` raises `ValueError` for an empty
  allowlist, for `all` combined with explicit names, and for unknown tool
  names (`src/percival_osm_mcp/server.py:432-447`).
- Full suite: `100 passed`.
- Note on the deployment follow-up: the eight-tool surface was deployed to the
  local Percival manager in the campaign recorded in
  `docs/plans/closed/2026-10-31-percival-osm-tool-surface-deployment.md`.
