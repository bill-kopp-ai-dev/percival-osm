FROM python:3.12-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.6.1 /uv /uvx /bin/

RUN apt update && apt install curl -y

ADD . /app

WORKDIR /app

RUN uv venv --python 3.12 venv

RUN uv sync --frozen

CMD ["uv", "run", "python", "osm.py" ]