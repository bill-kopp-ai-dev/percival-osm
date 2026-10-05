#!/usr/bin/env bash
# =============================================================================
# percival-osm — smoke test the built image
# =============================================================================
#
# Runs a minimal, dependency-free check against a freshly built image:
#
#   1. ``osm_get_version`` is reachable via the MCP stdio transport
#      (proves the Python entrypoint imports cleanly under the image
#      user/permissions, and that all 30+ tools register without error).
#   2. The container's non-root user is in effect.
#   3. The required env-var guard rejects a misconfigured container
#      with a clear error and a non-zero exit code.
#
# Usage:
#   scripts/docker-smoke-test.sh                 # uses percival-osm:local
#   IMAGE=percival-osm:v0.5.0 scripts/docker-smoke-test.sh
# =============================================================================

set -euo pipefail

cd "$(dirname "$0")/.."

IMAGE="${IMAGE:-percival-osm:local}"

if ! command -v docker >/dev/null 2>&1; then
    echo "error: docker is not on PATH" >&2
    exit 127
fi

if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    echo "error: image '${IMAGE}' not found locally. Build it first with:" >&2
    echo "  scripts/docker-build.sh" >&2
    exit 127
fi

run() {
    local description="$1"
    shift
    printf '\n[smoke] %s\n' "${description}"
    if "$@"; then
        printf '[smoke]   OK\n'
    else
        local rc=$?
        printf '[smoke]   FAIL (exit %d)\n' "${rc}"
        return "${rc}"
    fi
}

# Print full command output for diagnostic purposes when set.
DEBUG="${DEBUG:-0}"

# ---------------------------------------------------------------------------
# 1. The container runs as a non-root user.
# ---------------------------------------------------------------------------
run "non-root user is in effect" \
    docker run --rm --entrypoint /bin/sh "${IMAGE}" -c 'test "$(id -u)" = "10001"'

# ---------------------------------------------------------------------------
# 2. Missing required env vars are rejected loudly (no silent launch).
# ---------------------------------------------------------------------------
run "missing env vars are rejected" \
    env IMAGE="${IMAGE}" bash -c '
        set -o pipefail
        # Capture the exit code separately from stderr. The entrypoint
        # returns 78 (EX_CONFIG) when required env vars are missing.
        out=$(docker run --rm -i \
            -e USER_AGENT="" -e FROM_HEADER="" \
            "${IMAGE}" 2>&1; echo "__EXIT__$?")
        echo "${out}"
        echo "${out}" | grep -qiE "(USER_AGENT|FROM_HEADER|required environment)" \
            && echo "${out}" | grep -q "__EXIT__78"
    '

# ---------------------------------------------------------------------------
# 3. ``osm_get_version`` round-trips through the MCP stdio transport.
# ---------------------------------------------------------------------------
run "osm_get_version round-trips via stdio MCP" \
    env IMAGE="${IMAGE}" bash -c '
        set -e
        req=$'\''{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0.0.0"}}}'\''
        req2=$'\''{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}'\''
        req3=$'\''{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"osm_get_version","arguments":{}}}'\''

        # Use a FIFO so the container sees EOF when we are done writing.
        fifo=$(mktemp -u)
        rm -f "${fifo}"
        mkfifo "${fifo}"

        (
            sleep 0.5
            printf "%s\n%s\n%s\n" "${req}" "${req2}" "${req3}" >"${fifo}"
            sleep 0.5
        ) &

        out=$(docker run --rm -i \
            -e USER_AGENT="smoke-test/1.0 (smoke@example.com)" \
            -e FROM_HEADER="smoke@example.com" \
            -e OSM_HTTP_TIMEOUT_SECONDS=2 \
            -e OSM_NOMINATIM_RATE_LIMIT_RPS=0 \
            --network=none \
            "${IMAGE}" <"${fifo}" 2>/dev/null || true)
        rm -f "${fifo}"

        # The response body for osm_get_version is a JSON string containing
        # the server name and a "Version snapshot" message.
        echo "${out}" | grep -q "percival-osm" \
            && echo "${out}" | grep -q "Version snapshot"
    '

printf '\n[smoke] all checks passed for %s\n' "${IMAGE}"
