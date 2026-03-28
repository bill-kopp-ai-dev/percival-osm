FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.6.1 /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin app

ADD . /app
WORKDIR /app

RUN chown -R app:app /app
USER app

ENV UV_PROJECT_ENVIRONMENT=/app/.venv
RUN uv sync --frozen --no-dev

CMD ["uv", "run", "-m", "percival_osm_mcp"]
