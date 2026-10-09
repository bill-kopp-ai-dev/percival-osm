#!/usr/bin/env bash
# =============================================================================
# percival-osm — smoke test the built image
# =============================================================================
#
# Runs local, no-upstream-call checks against a freshly built image:
#
#   1. ``osm_get_version`` is reachable via the MCP stdio transport
#      (proves the Python entrypoint imports cleanly under the image
#      user/permissions, and that all 30+ tools register without error).
#   2. The container's non-root user is in effect.
#   3. The required env-var guard rejects a misconfigured container
#      with a clear error and a non-zero exit code.
#   4. Stdio has no Docker healthcheck or TTY; authenticated HTTP starts on
#      loopback, responds to MCP initialize, and shuts down through one tini.
#
# Usage:
#   scripts/docker-smoke-test.sh                 # uses percival-osm:local
#   IMAGE=percival-osm:v0.5.0 scripts/docker-smoke-test.sh
# =============================================================================

set -euo pipefail

cd "$(dirname "$0")/.."

IMAGE="${IMAGE:-percival-osm:local}"
HTTP_NAME="percival-osm-f1-smoke-$$"
HTTP_CID=""
HTTP_LOG="/tmp/percival-osm-http-smoke-$$.log"

cleanup() {
    if [ -n "${HTTP_CID}" ]; then
        docker rm -f "${HTTP_CID}" >/dev/null 2>&1 || true
    fi
    rm -f "${HTTP_LOG}"
}
trap cleanup EXIT

if ! command -v docker >/dev/null 2>&1; then
    echo "error: docker is not on PATH" >&2
    exit 127
fi

if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    echo "error: image '${IMAGE}' not found locally. Build it first with:" >&2
    echo "  scripts/docker-build.sh" >&2
    exit 127
fi

IMAGE_HEALTHCHECK=$(docker image inspect --format '{{if .Config.Healthcheck}}{{json .Config.Healthcheck.Test}}{{else}}null{{end}}' "${IMAGE}")
if [ "${IMAGE_HEALTHCHECK}" != '["NONE"]' ] && [ "${IMAGE_HEALTHCHECK}" != "null" ]; then
    echo "error: stdio image must not carry a healthcheck: ${IMAGE_HEALTHCHECK}" >&2
    exit 1
fi
IMAGE_ENTRYPOINT=$(docker image inspect --format '{{json .Config.Entrypoint}}' "${IMAGE}")
case "${IMAGE_ENTRYPOINT}" in
    *"/usr/bin/tini"*) ;;
    *) echo "error: image entrypoint must include the sole tini init: ${IMAGE_ENTRYPOINT}" >&2; exit 1 ;;
esac

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

# ---------------------------------------------------------------------------
# 4. All canonical tools register through the MCP stdio transport.
# ---------------------------------------------------------------------------
run "all canonical tools are registered" \
    env IMAGE="${IMAGE}" bash -c '
        set -e
        req1=$'\''{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0.0.0"}}}'\''
        req2=$'\''{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}'\''
        req3=$'\''{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'\''

        fifo=$(mktemp -u)
        rm -f "${fifo}"
        mkfifo "${fifo}"

        (
            sleep 0.5
            printf "%s\n%s\n%s\n" "${req1}" "${req2}" "${req3}" >"${fifo}"
            sleep 0.5
        ) &

        out=$(docker run --rm -i \
            -e USER_AGENT="smoke-test/1.0 (smoke@example.com)" \
            -e FROM_HEADER="smoke@example.com" \
            --network=none \
            "${IMAGE}" <"${fifo}" 2>/dev/null || true)
        rm -f "${fifo}"

        # The tools/list response carries every tool name. Verify the
        # canonical ones are present. Legacy aliases are gated behind
        # OSM_EXPOSE_LEGACY_ALIASES=true (the default), so we accept them.
        for tool in osm_find_nearby osm_find_place osm_find_address \
                    osm_geocode osm_navigate osm_directions \
                    osm_get_health osm_get_version osm_get_security_metrics; do
            if ! echo "${out}" | grep -q "\"name\":\"${tool}\""; then
                printf "  missing canonical tool: %s\n" "${tool}"
                exit 1
            fi
        done
    '

# ---------------------------------------------------------------------------
# 5. HTTP profile contract: required auth, loopback binding, explicit
#    listener health probe, and graceful stop through image tini.
# ---------------------------------------------------------------------------
HTTP_TOKEN="f1-smoke-token-$$"
HTTP_CID=$(docker run -d \
    --name "${HTTP_NAME}" \
    -p 127.0.0.1::8080 \
    --health-cmd 'code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "http://127.0.0.1:8080/" || echo "000"); case "$code" in 200|401|404|405) exit 0 ;; *) exit 1 ;; esac' \
    --health-interval=2s \
    --health-timeout=5s \
    --health-retries=3 \
    --health-start-period=5s \
    -e USER_AGENT="smoke-test/1.0 (smoke@example.invalid)" \
    -e FROM_HEADER="smoke@example.invalid" \
    -e MODE=streamable-http \
    -e PORT=8080 \
    -e ALLOW_REMOTE_HTTP=true \
    -e MCP_OSM_AUTH_TOKEN="${HTTP_TOKEN}" \
    "${IMAGE}" streamable-http)

HTTP_PORT=$(docker inspect --format '{{(index (index .NetworkSettings.Ports "8080/tcp") 0).HostPort}}' "${HTTP_CID}")
HTTP_BIND=$(docker port "${HTTP_CID}" 8080/tcp)
if [ "${HTTP_BIND}" != "127.0.0.1:${HTTP_PORT}" ]; then
    echo "error: HTTP smoke container is not loopback-only: ${HTTP_BIND}" >&2
    exit 1
fi
HTTP_PID1=$(docker inspect --format '{{.Path}}' "${HTTP_CID}")
HTTP_INIT=$(docker inspect --format '{{.HostConfig.Init}}' "${HTTP_CID}")
if [ "${HTTP_PID1}" != "/usr/bin/tini" ] || [ "${HTTP_INIT}" = "true" ]; then
    echo "error: expected exactly one init (image tini), Path=${HTTP_PID1}, HostConfig.Init=${HTTP_INIT}" >&2
    exit 1
fi

UNAUTH_CODE=""
for _ in {1..40}; do
    UNAUTH_CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 2 \
        "http://127.0.0.1:${HTTP_PORT}/mcp" 2>/dev/null || true)
    [ "${UNAUTH_CODE}" = "401" ] && break
    sleep 1
done
if [ "${UNAUTH_CODE}" != "401" ]; then
    docker logs "${HTTP_CID}" >"${HTTP_LOG}" 2>&1 || true
    echo "error: unauthenticated HTTP request should receive 401 (got ${UNAUTH_CODE})" >&2
    exit 1
fi

INIT_REQ='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0.0.0"}}}'
AUTH_CODE=$(curl -sS -o "${HTTP_LOG}" -w '%{http_code}' --max-time 10 \
    -H "Authorization: Bearer ${HTTP_TOKEN}" \
    -H 'Accept: application/json, text/event-stream' \
    -H 'Content-Type: application/json' \
    --data "${INIT_REQ}" \
    "http://127.0.0.1:${HTTP_PORT}/mcp" || true)
if [ "${AUTH_CODE}" != "200" ] || ! grep -q '"jsonrpc"' "${HTTP_LOG}"; then
    printf 'HTTP initialize failed (status=%s):\n' "${AUTH_CODE}" >&2
    python3 -c 'import sys; print(open(sys.argv[1]).read()[:1000])' "${HTTP_LOG}" >&2 || true
    exit 1
fi

HTTP_HEALTH=""
for _ in {1..20}; do
    HTTP_HEALTH=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${HTTP_CID}")
    [ "${HTTP_HEALTH}" = "healthy" ] && break
    sleep 1
done
if [ "${HTTP_HEALTH}" != "healthy" ]; then
    echo "error: HTTP liveness probe did not become healthy (got ${HTTP_HEALTH})" >&2
    exit 1
fi
printf '\n[smoke] HTTP auth, initialize, loopback bind and health probe passed\n'

docker stop --time 10 "${HTTP_CID}" >/dev/null
HTTP_EXIT=$(docker inspect --format '{{.State.ExitCode}}' "${HTTP_CID}")
if [ "${HTTP_EXIT}" = "137" ]; then
    echo "error: HTTP server failed to stop before SIGKILL" >&2
    exit 1
fi
printf '[smoke] single-tini HTTP shutdown passed (exit=%s)\n' "${HTTP_EXIT}"
printf '\n[smoke] all checks passed for %s\n' "${IMAGE}"
