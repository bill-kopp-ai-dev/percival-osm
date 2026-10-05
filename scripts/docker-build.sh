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
#   scripts/docker-build.sh v0.5.0 ghcr.io/me/x   # custom registry
#
# Environment overrides:
#   DOCKER_BUILDKIT=1   (default: enabled if available)
#   BUILDX_NO_DEFAULT_ATTESTATIONS=1  (skips SBOM/provenance for faster local builds)
# =============================================================================

set -euo pipefail

cd "$(dirname "$0")/.."

IMAGE_NAME="${IMAGE_NAME:-percival-osm}"
DEFAULT_TAG="${DEFAULT_TAG:-local}"

tags=("${IMAGE_NAME}:${DEFAULT_TAG}")
for extra in "$@"; do
    tags+=("${IMAGE_NAME}:${extra}")
done

# BuildKit is the default in modern Docker; opt in explicitly for older hosts.
export DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-1}"

build_args=(
    build
    --pull
    --label "org.opencontainers.image.revision=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
    --label "org.opencontainers.image.created=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
)

for tag in "${tags[@]}"; do
    build_args+=(--tag "${tag}")
done

# Slightly more verbose output for CI logs; trim with --progress=plain locally.
if [ -n "${CI:-}" ]; then
    build_args+=(--progress=plain)
fi

build_args+=(.)

echo "Building ${tags[*]} from $(pwd)"
docker "${build_args[@]}"

echo
echo "Built: ${tags[*]}"
echo
echo "Quick smoke test:"
echo "  ${tags[0]} --rm -i -e USER_AGENT=probe -e FROM_HEADER=probe@example.com ${tags[0]}"
