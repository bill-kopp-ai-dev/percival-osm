#!/usr/bin/env bash
# =============================================================================
# percival-osm — image inspector
# =============================================================================
#
# Prints a structured view of a built ``percival-osm`` image: OCI labels,
# exposed ports, healthcheck, entrypoint, file ownership of critical paths,
# and the resolved Python environment. Useful for verifying a release
# artifact matches the documented baseline before pushing to a registry.
#
# Usage:
#   scripts/docker-inspect.sh                # uses percival-osm:local
#   IMAGE=percival-osm:v0.5.0 scripts/docker-inspect.sh
#   IMAGE=ghcr.io/bill-kopp-ai-dev/percival-osm:v0.5.0 scripts/docker-inspect.sh
# =============================================================================

set -euo pipefail

cd "$(dirname "$0")/.."

IMAGE="${IMAGE:-percival-osm:local}"

if ! command -v docker >/dev/null 2>&1; then
    echo "error: docker is not on PATH" >&2
    exit 127
fi

if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    echo "error: image '${IMAGE}' not found locally. Pull it first with:" >&2
    echo "  docker pull ${IMAGE}" >&2
    echo "Or build it with:" >&2
    echo "  scripts/docker-build.sh" >&2
    exit 127
fi

section() {
    printf '\n\033[1m== %s ==\033[0m\n' "$1"
}

# Inspect output as JSON via the docker CLI.
inspect() {
    docker image inspect --format "$1" "${IMAGE}"
}

section "image"
printf 'repository: %s\n' "${IMAGE}"
printf 'id:         %s\n' "$(inspect '{{.Id}}')"
printf 'created:    %s\n' "$(inspect '{{.Created}}')"
printf 'size:       %s bytes\n' "$(inspect '{{.Size}}')"
printf 'arch:       %s\n' "$(inspect '{{.Architecture}}')"

section "OCI / MCP labels"
docker image inspect --format '{{range $k, $v := .Config.Labels}}{{printf "%-44s %s\n" $k $v}}{{end}}' "${IMAGE}"

section "exposed ports"
docker image inspect --format '{{range $p, $conf := .Config.ExposedPorts}}{{printf "%s\n" $p}}{{end}}' "${IMAGE}"

section "healthcheck"
docker image inspect --format '{{json .Config.Healthcheck}}' "${IMAGE}" | python3 -m json.tool || true

section "user / entrypoint / cmd"
printf 'User:      %s\n' "$(inspect '{{.Config.User}}')"
printf 'Entrypoint:%s\n' "$(inspect '{{range .Config.Entrypoint}}{{printf " %s" .}}{{end}}')"
printf 'Cmd:       %s\n' "$(inspect '{{range .Config.Cmd}}{{printf " %s" .}}{{end}}')"

section "env (filtered to OSM_*, USER_*, FROM_*, ORS_*, MCP_*, MODE, PORT)"
docker image inspect --format '{{range .Config.Env}}{{.}}{{"\n"}}{{end}}' "${IMAGE}" \
    | grep -E "^(OSM_|USER_|FROM_|ORS_|MCP_|MODE|PORT)=" \
    | sort \
    || true

section "filesystem (entrypoint + cache dir)"
docker run --rm --entrypoint /bin/sh "${IMAGE}" -c '
    ls -ld /app /app/src /cache /usr/local/bin/docker-entrypoint.sh 2>&1
    echo
    echo "package site-packages listing:"
    ls /app/.venv/lib/python3.12/site-packages | grep -E "^(percival|mcp|httpx|openrouteservice|pydantic|starlette|uvicorn)" | head -20
    echo
    echo "PYTHONPATH / sys.path (effective):"
    /app/.venv/bin/python -c "import sys; [print(p) for p in sys.path if p]" | head -10
    echo
    echo "Can we import percival_osm_mcp?"
    /app/.venv/bin/python -c "import percival_osm_mcp; print(percival_osm_mcp.__file__)" || echo "  FAIL"
' 2>&1