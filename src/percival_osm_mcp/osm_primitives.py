"""MCP prompt and resource primitives for the percival-osm server.

These primitives help downstream agents (e.g. femtobot) choose the right
tool and produce well-shaped output. They are intentionally short and
focused — anything that drifts toward encyclopedic content should live in
the README or docs/ folder instead.

Each prompt is exposed via ``@mcp.prompt()`` and surfaces to the agent as
a discoverable intent. Each resource is exposed via ``@mcp.resource()``
and is fetched lazily when the agent asks for it (e.g. via
``read_resource("osm://security/nanobot-policy")``).

Femtobot wraps these as ``mcp_percival_osm_prompt_<name>`` and
``mcp_percival_osm_resource_<name>`` (see femtobot docs/mcp.md).
"""

from __future__ import annotations

import logging
from importlib import resources
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("percival-osm")


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

# Intentionally short. Each prompt becomes part of the system prompt when
# referenced, so verbosity hurts. See femtobot docs/mcp.md for prefixing.

_PROMPT_QUICK_SEARCH = """\
You are about to do a quick local search with percival-osm MCP.

Goal: find POIs near a place the user already named (an address, a
neighborhood, a city, or GPS coordinates).

Decision tree:

1. If the user named a category AND a place (e.g. "cafés near Vila Madalena"):
   - Call `osm_find_nearby` with `place`, `category="food"`, `limit=5`.
   - DO NOT call `osm_find_food` (or other legacy aliases) unless you've
     verified they're exposed via `osm_get_health` or `OSM_EXPOSE_LEGACY_ALIASES=true`.
2. If the user only gave coordinates:
   - Call `osm_find_address` first to get a human-readable place, then use
     that place string for `osm_find_nearby`.
3. If the user only gave a category without a place, ask for a place.
4. If the user wants GPS coordinates only (no details), use `osm_geocode`.

Output expectations:

- Compact markdown, sanitized. The server already removes prompt-injection
  patterns from upstream responses.
- Include distance (km) and the OSM map link when available.
- If no results, say so explicitly — do not hallucinate.

Failure modes to surface to the user:

- 0 results → "No POIs found near <place> for category <category>."
- Multiple results → list up to the requested `limit`, sorted by distance.
"""


_PROMPT_TOOL_CHOOSER = """\
Use this guide to pick the right percival-osm tool.

| User intent                                           | Tool to call             |
|-------------------------------------------------------|--------------------------|
| Find POIs of a category near a place                  | `osm_find_nearby`        |
| Find POIs with extra context (opening hours, website) | `osm_find_nearby_detailed` |
| Find a specific named place ("Eiffel Tower")          | `osm_find_place`         |
| Same with full details                                | `osm_find_place_detailed` |
| GPS coordinates → address / place name                | `osm_find_address`       |
| Address / place name → GPS coordinates only           | `osm_geocode`            |
| Route summary (distance + travel time) between A→B   | `osm_navigate`           |
| Step-by-step instructions A→B                         | `osm_directions`         |
| Check server status / uptime                          | `osm_get_health`         |
| Get server version                                    | `osm_get_version`        |
| Read the security policy the server enforces          | `osm://security/nanobot-policy` |
| List supported POI categories                         | `osm://categories`       |

Defaults:

- `limit=5` is a good starting point. Increase to 10-20 only when the user
  asks for "all" or a specific number.
- Always include city and country in `place` when known. This avoids
  cross-region ambiguity ("Springfield" exists in many US states).

Hard rule:

- Never invent coordinates, place names, or routing. If a tool returns no
  results, report that honestly and ask the user for clarification.
"""


_PROMPT_OUTPUT_FORMAT = """\
percival-osm responses are sanitized JSON wrapped in a tool-call envelope.
Render the relevant fields to the user as compact markdown.

Canonical output template (for category / nearby searches):

  ## <Category> near <Place>
  - <name> — <distance_km> km
    <address or short description>
    Map: <osm_link>
  - ...

Canonical output template (for routes):

  ## Route from <A> to <B>
  - Total distance: <distance_km> km
  - Travel time: <travel_time_min> min
  - Travel type: <car | walking/biking>

  Steps:
    1. <instruction> (<distance>, <duration>)
    2. ...

Canonical output template (for geocode / reverse):

  ## <place_name>
  - Coordinates: <lat>, <lon>
  - Type: <osm_type>
  - Map: <osm_link>

Hard rules:

- Never include the raw JSON envelope in the user-facing reply.
- Never quote the server's internal warning strings verbatim; paraphrase.
- If the response says `status: "config_error"`, the server is missing a
  required setting (e.g. `ORS_API_KEY`). Tell the user, do not retry.
- If the response says `status: "no_results"`, just say you found nothing.
"""


def register_prompts(mcp: FastMCP) -> None:
    """Register MCP prompt primitives on the given server instance."""

    @mcp.prompt(
        name="osm_recipe_quick_search",
        description="Step-by-step recipe for a quick POI search near a place.",
    )
    async def osm_recipe_quick_search() -> str:
        """Return the recipe prompt for quick POI searches."""
        return _PROMPT_QUICK_SEARCH

    @mcp.prompt(
        name="osm_tool_chooser",
        description="Decision table mapping user intents to the right percival-osm tool.",
    )
    async def osm_tool_chooser() -> str:
        """Return the tool-chooser prompt."""
        return _PROMPT_TOOL_CHOOSER

    @mcp.prompt(
        name="osm_output_format",
        description="Canonical markdown templates for rendering percival-osm responses.",
    )
    async def osm_output_format() -> str:
        """Return the output-format guide."""
        return _PROMPT_OUTPUT_FORMAT

    logger.debug("Registered 3 MCP prompt primitives")


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


def _read_package_text(rel_path: str) -> str:
    """Load a UTF-8 text file shipped with the package.

    Falls back to ``Path`` lookup against the source tree (useful for
    editable installs) and finally raises FileNotFoundError so the caller
    can decide how to surface the failure.
    """
    try:
        return (
            resources.files("percival_osm_mcp")
            .joinpath(rel_path)
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, ModuleNotFoundError, AttributeError):
        candidate = Path(__file__).resolve().parent.parent.parent / rel_path
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
        raise


_CATEGORIES_RESOURCE = """\
# Supported POI categories

The `category` parameter of `osm_find_nearby` accepts the following values.
Each one maps to a curated set of OpenStreetMap tags.

| Category              | Aliases (when `OSM_EXPOSE_LEGACY_ALIASES=true`) |
|-----------------------|------------------------------------------------|
| `food`                | `osm_find_food`                                |
| `groceries`           | `osm_find_groceries`                           |
| `bakeries`            | `osm_find_bakeries`                            |
| `swimming`            | `osm_find_swimming`                            |
| `playgrounds`         | `osm_find_playgrounds`                         |
| `recreation`          | `osm_find_recreation`                          |
| `tourist_attractions` | `osm_find_attractions`                         |
| `places_of_worship`   | `osm_find_worship`                             |
| `accommodation`       | `osm_find_accommodation`                       |
| `alcohol`             | `osm_find_alcohol`                             |
| `drugs`               | `osm_find_drugs`                               |
| `schools`             | `osm_find_schools`                             |
| `universities`        | `osm_find_universities`                        |
| `libraries`           | `osm_find_libraries`                           |
| `public_transport`    | `osm_find_transport`                           |
| `bike_rentals`        | `osm_find_bikes`                               |
| `car_rentals`         | `osm_find_cars`                                |
| `hardware`            | `osm_find_hardware`                            |
| `electrical`          | `osm_find_electrical`                          |
| `electronics`         | `osm_find_electronics`                         |
| `doctors`             | `osm_find_doctors`                             |
| `hospitals`           | `osm_find_hospitals`                           |
| `pharmacies`          | `osm_find_pharmacy`                            |

Notes:

- If `OSM_EXPOSE_LEGACY_ALIASES=false`, the agent MUST use
  `osm_find_nearby` with one of the canonical category keys above. The
  aliases will not be present in the tool list.
- The fallback tool (`osm_find_other`) accepts arbitrary category strings
  but is best-effort: it picks the closest match from the canonical list
  above.
"""


def register_resources(mcp: FastMCP) -> None:
    """Register MCP resource primitives on the given server instance."""

    @mcp.resource(
        uri="osm://categories",
        name="Supported POI categories",
        description="Canonical list of category keys accepted by osm_find_nearby.",
        mime_type="text/markdown",
    )
    async def osm_categories_resource() -> str:
        """Return the canonical categories reference."""
        return _CATEGORIES_RESOURCE

    @mcp.resource(
        uri="osm://security/nanobot-policy",
        name="Percival-OSM Nanobot policy",
        description=(
            "Security policy this MCP server enforces on its host (privacy, "
            "sanitization, URL allow-listing, etc)."
        ),
        mime_type="text/markdown",
    )
    async def osm_security_policy_resource() -> str:
        """Return the nanobot security policy shipped with the package."""
        try:
            return _read_package_text("docs/security/nanobot-policy.md")
        except FileNotFoundError:
            logger.warning("nanobot-policy.md not found; returning placeholder")
            return (
                "# Percival-OSM Nanobot Policy\n\n"
                "The bundled policy document is not available in this "
                "installation. Refer to the project README for the canonical "
                "policy text."
            )

    logger.debug("Registered 2 MCP resource primitives")


# ---------------------------------------------------------------------------
# Convenience: register everything in one call
# ---------------------------------------------------------------------------


def register_all_primitives(mcp: FastMCP) -> None:
    """Register all prompt and resource primitives on the given MCP server."""
    register_prompts(mcp)
    register_resources(mcp)
    logger.info(
        "Registered %d MCP primitives (prompts + resources)",
        3 + 2,
    )