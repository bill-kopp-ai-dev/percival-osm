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
FROM python:3.12-slim-trixie@sha256:2b4f19dae3a777dfc3b76730bda1e82e1f66ab2a2686fa93ca78edbfb4f04ffe AS python-runtime

FROM ghcr.io/astral-sh/uv:0.9.30-python3.12-trixie-slim@sha256:eacce4ec0ff855c8be0cca407d8c5e8e20139dd3f8f64c018fb654bac0a40bd8 AS builder

WORKDIR /build

# Install build deps for any wheel that needs compiling (httpx, pydantic, etc).
# These are discarded in the runtime stage so the final image stays slim.
ARG DEBIAN_SNAPSHOT=20261009T000000Z
RUN printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s trixie main\n' "$DEBIAN_SNAPSHOT" > /etc/apt/sources.list && \
    printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s trixie-security main\n' "$DEBIAN_SNAPSHOT" >> /etc/apt/sources.list && \
    rm -f /etc/apt/sources.list.d/debian.sources && \
    apt-get -o Acquire::Check-Valid-Until=false update && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends \
        build-essential=12.12 gcc=4:14.2.0-1 libffi-dev=3.4.8-2 && \
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
COPY LICENSE /build/LICENSE
COPY scripts/normalize_venv_metadata.py /build/normalize_venv_metadata.py
COPY src /build/src
COPY docs /build/docs
RUN UV_PROJECT_ENVIRONMENT=/build/.venv \
    uv sync --frozen --no-dev && \
    UV_PROJECT_ENVIRONMENT=/build/.venv \
    uv pip install --no-cache --no-deps /build && \
    python /build/normalize_venv_metadata.py /build/.venv

# -----------------------------------------------------------------------------
# Stage 2: runtime
# -----------------------------------------------------------------------------
FROM debian:forky-slim@sha256:4cee6ff3ebc49e32d55a857e25164ef8e5f8fecff2a186c6393f7e8bd8c23b53 AS runtime

COPY --from=python-runtime /usr/local/bin/python3.12 /usr/local/bin/python3.12
COPY --from=python-runtime /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=python-runtime /usr/local/lib/libpython3.12.so.1.0 /usr/local/lib/libpython3.12.so.1.0

ARG DEBIAN_SNAPSHOT=20261020T000000Z
ARG VERSION=0.0.0
ARG GIT_SHA=unknown
ARG SOURCE_DATE_EPOCH
ENV SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH}

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
COPY --chown=percival:percival LICENSE /app/LICENSE
COPY --chown=percival:percival docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Strip the build-only system packages we needed in the builder stage. Runtime
# keeps ca-certificates for TLS and bash for the entrypoint.
#
# The image deliberately embeds no init: the launcher owns the init layer
# (``docker run --init`` / Compose ``init: true``). A tini embedded here plus
# the launcher's own init would stack two supervision layers, and the outer
# one masks which process is actually responsible for SIGTERM.
RUN printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/%s forky main\n' "$DEBIAN_SNAPSHOT" > /etc/apt/sources.list \
    && printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/%s forky-security main\n' "$DEBIAN_SNAPSHOT" >> /etc/apt/sources.list \
    && rm -f /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get upgrade -y --no-install-recommends \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        bash=5.3-4 ca-certificates=20260816 \
        libssl3t64=3.6.5-1 libffi8=3.8.0-2 libsqlite3-0=3.53.4-2 \
        libreadline8t64=8.3-4 libncursesw6=6.6+20260608-2 libtinfo6=6.6+20260608-2 \
        libdb5.3t64=5.3.28+dfsg2-11+b1 libgdbm6t64=1.26-1+b2 \
        libbz2-1.0=1.0.8-6+b2 liblzma5=5.8.4-1 libuuid1=2.42.4-1 \
        libzstd1=1.5.7+dfsg-4 zlib1g=1:1.3.dfsg+really1.3.2-3 \
        libtk8.6=8.6.18-1 libtcl8.6=8.6.18+dfsg-1 \
    && ln -sf /usr/local/lib/libpython3.12.so.1.0 /usr/local/lib/libpython3.12.so \
    && ln -sf /usr/local/bin/python3.12 /usr/local/bin/python3 \
    && ln -sf /usr/local/bin/python3.12 /usr/local/bin/python \
    && rm -rf /usr/local/lib/python3.12/site-packages/pip \
        /usr/local/lib/python3.12/site-packages/pip-*.dist-info \
        /usr/local/lib/python3.12/ensurepip/_bundled \
    && chmod u-s /usr/bin/mount && \
    rm -f /usr/bin/nsenter /usr/bin/infocmp && \
    rm -rf /var/lib/apt/lists/* /var/cache/ldconfig/aux-cache && \
    rm -f /var/log/apt/history.log /var/log/apt/term.log /var/log/dpkg.log && \
    chmod +x /usr/local/bin/docker-entrypoint.sh

WORKDIR /app
# Build tools and package installation write wall-clock mtimes even when all
# package inputs are pinned. Normalize the final filesystem to the candidate
# source timestamp so layer digests do not depend on build time.
RUN find / -xdev \
    ! -path '/proc*' ! -path '/sys*' ! -path '/dev*' ! -path '/run*' \
    -exec touch -h -d "@${SOURCE_DATE_EPOCH}" {} +

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

# The entrypoint validates env, drops to a known state, and exec's the MCP
# server. The init layer belongs to the launcher (``docker run --init``),
# so this image must not embed a second one.
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["stdio"]
