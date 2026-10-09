# =============================================================================
# percival-osm MCP server — production image
# =============================================================================
#
# Two-stage build:
#   1. builder: install Python dependencies into a relocatable uv venv.
#   2. runtime: copy the venv + application source and run as a non-root user.
#
# The image is intentionally small (no compilers, no dev deps) and hardened
# (read-only root, no-new-privileges, dropped capabilities, dedicated
# non-root user). It defaults to stdio MCP transport; pass
# ``MODE=streamable-http`` to the entrypoint to expose HTTP.
#
# Build:
#   docker build -t percival-osm:local .
#
# Run (stdio — works with nanobot / opencode / any MCP client that
# connects via the docker CLI):
#   docker run --rm -i \
#     -e USER_AGENT='percival-osm/0.4.1 (you@example.com)' \
#     -e FROM_HEADER='you@example.com' \
#     percival-osm:local
#
# Run (streamable-http for Docker MCP Toolkit / browser clients):
#   docker run --rm -p 8080:8080 \
#     -e USER_AGENT='percival-osm/0.4.1 (you@example.com)' \
#     -e FROM_HEADER='you@example.com' \
#     -e MCP_OSM_AUTH_TOKEN=$(openssl rand -hex 32) \
#     -e MODE=streamable-http \
#     -e ALLOW_REMOTE_HTTP=true \
#     percival-osm:local
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: builder
# -----------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim@sha256:5d275ca5f0da33c3368ac8fbb85fafabad023b3b8a7cff39a94ac0baecfd9a50 AS builder

WORKDIR /build

# Install build deps for any wheel that needs compiling (httpx, pydantic, etc).
# These are discarded in the runtime stage so the final image stays slim.
ARG DEBIAN_SNAPSHOT=20261009T000000Z
RUN printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s bookworm main\n' "$DEBIAN_SNAPSHOT" > /etc/apt/sources.list && \
    printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s bookworm-security main\n' "$DEBIAN_SNAPSHOT" >> /etc/apt/sources.list && \
    rm -f /etc/apt/sources.list.d/debian.sources && \
    apt-get -o Acquire::Check-Valid-Until=false update && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends \
        build-essential=12.9 gcc=4:12.2.0-3 libffi-dev=3.4.4-1 && \
    rm -rf /var/lib/apt/lists/*

# Copy only what `uv sync` needs to resolve the lockfile so this layer
# is cached across source-only edits.
COPY pyproject.toml uv.lock /build/
RUN mkdir -p src/percival_osm_mcp && \
    touch src/percival_osm_mcp/__init__.py && \
    UV_PROJECT_ENVIRONMENT=/build/.venv \
    uv sync --frozen --no-dev --no-install-project

# Now copy the application source and finish the install. README is
# required by hatchling's metadata step (``[project].readme = "README.md"``).
COPY README.md /build/README.md
COPY src /build/src
COPY docs /build/docs
RUN UV_PROJECT_ENVIRONMENT=/build/.venv \
    uv sync --frozen --no-dev && \
    UV_PROJECT_ENVIRONMENT=/build/.venv \
    uv pip install --no-cache --no-deps /build

# -----------------------------------------------------------------------------
# Stage 2: runtime
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm@sha256:2ed6491b93cd49272ee6de2b5a38440c3448360322c089fc23e370722d74179d AS runtime

ARG DEBIAN_SNAPSHOT=20261009T000000Z
ARG VERSION=0.0.0
ARG GIT_SHA=unknown

# https://github.com/opencontainers/image-spec/blob/main/annotations.md
LABEL org.opencontainers.image.title="percival-osm" \
      org.opencontainers.image.description="Percival OSM MCP server — hardened OpenStreetMap / OpenRouteService bridge for AI agents" \
      org.opencontainers.image.source="https://github.com/bill-kopp-ai-dev/percival-osm" \
      org.opencontainers.image.documentation="https://github.com/bill-kopp-ai-dev/percival-osm/blob/main/README.md" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="Positronic Bean Labs" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      io.modelcontextprotocol.server.name="io.github.bill-kopp-ai-dev/percival-osm"

# Create the non-root user up-front so ownership on COPY targets is stable.
# UID/GID 10001 matches the default in docker-compose.yml so bind-mounted
# cache files land with the right owner.
RUN groupadd --gid 10001 percival && \
    useradd  --uid 10001 --gid percival \
             --create-home --shell /usr/sbin/nologin percival && \
    mkdir -p /app /cache && \
    chown -R percival:percival /app /cache

# Copy the resolved venv from the builder. ``--chown`` keeps the runtime
# non-root user able to read it.
COPY --from=builder --chown=percival:percival /build/.venv /app/.venv
COPY --chown=percival:percival src /app/src
COPY --chown=percival:percival docs /app/docs
COPY --chown=percival:percival docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Strip the build-only system packages we needed in the builder stage. The
# runtime image only needs ca-certificates (for TLS upstreams), tini (PID 1
# reaper — the upstream recommends tini for MCP servers), curl (for the
# HEALTHCHECK below) and bash (the entrypoint uses bash arrays to thread
# flags through to the Python module).
RUN printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s bookworm main\n' "$DEBIAN_SNAPSHOT" > /etc/apt/sources.list \
    && printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s bookworm-security main\n' "$DEBIAN_SNAPSHOT" >> /etc/apt/sources.list \
    && rm -f /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get install -y --no-install-recommends \
        bash=5.2.15-2+b13 \
        ca-certificates=20250419~deb12u1 \
        curl=7.88.1-10+deb12u15 \
        tini=0.19.0-1+b3 \
    && apt-get upgrade -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/* && \
    chmod +x /usr/local/bin/docker-entrypoint.sh

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/app/.venv/bin:${PATH}" \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    OSM_CACHE_FILE=/cache/osm-cache.json \
    OSM_CACHE_ALLOWED_DIRS=/cache \
    OSM_LOG_FORMAT=plain \
    OSM_LOG_LEVEL=INFO

USER percival

# Default to stdio MCP transport. Override with MODE=streamable-http.
ENV MODE=stdio
ENV PORT=8080
EXPOSE 8080

# Stdio is the image default and has no truthful Docker health probe: process
# presence cannot prove the MCP handshake. The HTTP Compose service supplies
# its own listener probe; it never checks an upstream API.
HEALTHCHECK NONE

# tini reaps zombies and forwards signals; the entrypoint validates env,
# drops to a known state, and exec's the MCP server.
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/docker-entrypoint.sh"]
CMD ["stdio"]
