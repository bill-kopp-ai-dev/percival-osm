#!/bin/bash
# =============================================================================
# percival-osm MCP server — container entrypoint
# =============================================================================
#
# Responsibilities (in order):
#   1. Validate required environment variables. The server itself will
#      refuse to start without them, but failing here gives a clearer
#      error message in container logs before the JSON-RPC stream is up.
#   2. Normalize the ``MODE`` variable: ``stdio`` (default) and
#      ``streamable-http`` map to the existing CLI flags the server
#      already understands.
#   3. Refuse to run as root (the Dockerfile sets ``USER percival`` so
#      this only fires when someone overrides ``--user``).
#
# Uses bash because POSIX /bin/sh (dash on Debian) doesn't support arrays
# and we need one to pass arbitrary flags to the Python module.
# =============================================================================

set -euo pipefail

log() {
    # Stderr only — stdout is reserved for the MCP JSON-RPC stream when
    # running in stdio mode. Use printf so we get a single line per call.
    printf '[entrypoint] %s\n' "$*" >&2
}

# -----------------------------------------------------------------------------
# 1. Required environment validation
# -----------------------------------------------------------------------------
missing=""
for var in USER_AGENT FROM_HEADER; do
    eval "value=\${$var:-}"
    if [ -z "${value}" ]; then
        missing="${missing} ${var}"
    fi
done

if [ -n "${missing}" ]; then
    log "error: required environment variables are not set:${missing}"
    log "  The OpenStreetMap Nominatim usage policy requires both"
    log "  USER_AGENT and FROM_HEADER to be non-empty. See the project"
    log "  README and .env.example for details."
    exit 78  # EX_CONFIG — see sysexits.h
fi

# Optional but recommended. The server falls back to haversine distance
# if ORS_API_KEY is empty, so we only warn (never fail) here.
if [ -z "${ORS_API_KEY:-}" ]; then
    log "warning: ORS_API_KEY not set — routing tools will fall back to haversine distance"
fi

# -----------------------------------------------------------------------------
# 2. Mode normalization
# -----------------------------------------------------------------------------
MODE_NORMALIZED="$(printf '%s' "${MODE:-stdio}" | tr '[:upper:]' '[:lower:]')"
case "${MODE_NORMALIZED}" in
    stdio|sse|streamable-http)
        ;;
    *)
        log "error: invalid MODE='${MODE}' (expected stdio | sse | streamable-http)"
        exit 78
        ;;
esac

ARGS=("--mode" "${MODE_NORMALIZED}")
if [ "${MODE_NORMALIZED}" = "streamable-http" ] || [ "${MODE_NORMALIZED}" = "sse" ]; then
    ARGS+=("--host" "0.0.0.0" "--port" "${PORT:-8080}")
    if [ "${ALLOW_REMOTE_HTTP:-false}" = "true" ]; then
        ARGS+=("--allow-remote-http")
    fi
fi

# -----------------------------------------------------------------------------
# 3. Privilege check + exec
# -----------------------------------------------------------------------------
# The Dockerfile sets ``USER percival`` (uid 10001) so under Docker defaults
# we never start as root. We refuse to start as root instead of trying to
# drop privileges — that keeps the runtime image small (no util-linux for
# ``setpriv``) and makes the security posture explicit.

if [ "$(id -u)" = "0" ]; then
    log "error: refusing to run as root (current uid=0)."
    log "  The Dockerfile already declares USER percival (10001)."
    log "  If you overrode --user, drop the alias and use --user 10001:10001"
    log "  (or remove the override to inherit the image's USER)."
    exit 77  # EX_NOPERM — see sysexits.h
fi

log "starting percival-osm (mode=${MODE_NORMALIZED}, user=$(id -un))"
exec python -m percival_osm_mcp "${ARGS[@]}"
