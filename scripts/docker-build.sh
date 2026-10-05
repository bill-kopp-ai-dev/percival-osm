#!/usr/bin/env bash
# =============================================================================
# percival-osm — build helper for the Docker image
# =============================================================================
#
# Builds the production image with the canonical ``percival-osm:local`` tag
# (and any extra tags you pass on the command line) using the repository's
# multi-stage Dockerfile. The build is reproducible: ``uv sync --frozen``
# pins the dependency tree, and the runtime stage only copies the
# pre-resolved venv + source.
#
# Usage:
#   scripts/docker-build.sh                       # tag as percival-osm:local
#   scripts/docker-build.sh v0.5.0                # also tag as :v0.5.0
#   scripts/docker-build.sh --platform linux/arm64 v0.5.0  # multi-arch
#   PLATFORMS=linux/amd64,linux/arm64 scripts/docker-build.sh
#
# Environment overrides:
#   DOCKER_BUILDKIT=1   (default: enabled if available)
#   PLATFORMS=linux/amd64  (single-arch build; default when no --platform)
#   BUILDX_NO_DEFAULT_ATTESTATIONS=1  (skips SBOM/provenance for faster local builds)
# =============================================================================

set -euo pipefail

cd "$(dirname "$0")/.."

IMAGE_NAME="${IMAGE_NAME:-percival-osm}"
DEFAULT_TAG="${DEFAULT_TAG:-local}"

# Parse --platform=<value> out of the argument list so it can be passed
# to ``docker buildx build`` instead of becoming an image tag.
platforms=""
positional=()
for arg in "$@"; do
    case "${arg}" in
        --platform=*)
            platforms="${arg#--platform=}"
            ;;
        *)
            positional+=("${arg}")
            ;;
    esac
done

# Default to the host platform when nothing was requested. Multi-arch
# requires ``docker buildx`` and a builder; the smoke test is then run
# against the host arch (typically linux/amd64).
if [ -z "${platforms}" ]; then
    platforms="${PLATFORMS:-}"
fi

if [ -n "${platforms}" ] && [ "${platforms}" != *","* ]; then
    # Single platform: load the result into the local docker so the
    # downstream smoke test can run without ``--load``.
    load_flag="--load"
else
    # Multi-platform: ``docker buildx build`` cannot load multiple
    # images into a single daemon; the caller is expected to handle
    # registry push separately.
    load_flag="--load"
    if [ -n "${platforms}" ]; then
        load_flag=""
    fi
fi

tags=("${IMAGE_NAME}:${DEFAULT_TAG}")
for extra in "${positional[@]}"; do
    tags+=("${IMAGE_NAME}:${extra}")
done

# BuildKit is the default in modern Docker; opt in explicitly for older hosts.
export DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-1}"

build_args=(buildx build --pull)
if [ -n "${platforms}" ]; then
    build_args+=(--platform "${platforms}")
fi
build_args+=(
    --label "org.opencontainers.image.revision=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
    --label "org.opencontainers.image.created=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
)
if [ -n "${load_flag}" ]; then
    build_args+=("${load_flag}")
fi

for tag in "${tags[@]}"; do
    build_args+=(--tag "${tag}")
done

# Slightly more verbose output for CI logs; trim with --progress=plain locally.
if [ -n "${CI:-}" ]; then
    build_args+=(--progress=plain)
fi

build_args+=(.)

echo "Building ${tags[*]} for platform(s): ${platforms:-host}"
docker "${build_args[@]}"

echo
echo "Built: ${tags[*]}"
echo
echo "Quick smoke test (single-arch local image):"
echo "  scripts/docker-smoke-test.sh"
echo
if [ -z "${load_flag}" ]; then
    echo "Note: multi-arch build was selected; the image is NOT loaded into the local"
    echo "      daemon. Push it (or run ``docker buildx imagetools inspect <tag>``) to"
    echo "      verify, or re-run with PLATFORMS=<host-arch> for a local smoke test."
fi
