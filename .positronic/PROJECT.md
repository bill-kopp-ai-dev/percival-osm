# Percival OSM

## Purpose and intended outcome

Servidor MCP que conecta assistentes de IA ao **OpenStreetMap** —
buscas geoespaciais em tempo real, descoberta de pontos de interesse e
navegação passo a passo — através de uma interface hardened e respeitosa
da privacidade, como módulo do ecossistema **percival.OS**. O resultado
útil é dar a agentes compatíveis (femtobot, nanobot, claude-code, …)
acesso ao mundo físico via dados abertos, sem tracking comercial e sob
controle do operador.

## Scope and success criteria

**Entregáveis:**

- Servidor MCP Python (≥ 3.11) com transporte **stdio** e
  **streamable-HTTP**.
- 30+ ferramentas canônicas (`osm_find_*`, `osm_navigate`,
  `osm_directions`, `osm_geocode`, `osm_find_address`, …) e aliases
  legados por categoria controláveis via `OSM_EXPOSE_LEGACY_ALIASES`.
- 3 primitivas de prompt (`osm_recipe_quick_search`, `osm_tool_chooser`,
  `osm_output_format`) e 2 primitivas de resource (`osm://categories`,
  `osm://security/nanobot-policy`).
- Hardening: HTTPS-only, URL allow-list, sanitização contra
  prompt-injection, rate-limit Nominatim (1 req/s + burst 2) com
  single-flight.
- Observabilidade: `osm_get_health`, `osm_get_version`,
  `osm_get_security_metrics`, logging estruturado em stderr.
- Suporte Docker "first-class": imagem multi-stage hardened (uid 10001,
  cap_drop ALL, no-new-privileges, read-only root, sem init embutido —
  a camada de init pertence ao launcher), entrypoint com validação de
  env (USER_AGENT/FROM_HEADER) e recusa de execução como root,
  `docker-compose.yml` com perfis stdio e http, e artefatos para submissão
  ao Docker MCP Catalog
  (`servers/percival-osm/{server.yaml,tools.json,readme.md}`).
- CI GitHub Actions (`.github/workflows/docker.yml`) com build
  linux/amd64 e smoke test da imagem.

**Evidência de sucesso:**

- `uv run pytest -v` — suíte completa (76 testes, alvo < 1s).
- `scripts/docker-smoke-test.sh` — 4 checks (non-root, env-var guard,
  stdio MCP round-trip, tools/list coverage) sobre `percival-osm:local`.
- `scripts/docker-inspect.sh` — confirma labels OCI, healthcheck,
  user/entrypoint/cmd e site-packages resolvido.
- `bandit` e `pip-audit` sem achados críticos.
- `osm_get_security_metrics` reporta zero falhas em operação normal.
- README e resources MCP alinhados: o agente consegue se auditar contra
  a política sem reler o repo.

## Methods and resources

- Stack: Python ≥ 3.11, `mcp[cli]`, `httpx`, `openrouteservice`,
  `pydantic-settings`, `starlette`, `uvicorn` (ver `pyproject.toml`).
- Build backend: `hatchling`; pacote `src/percival_osm_mcp`; entry point
  `percival-osm-mcp`.
- Execução local:
  - `uv sync` para ambiente editável com dev-deps.
  - `PYTHONPATH=src .venv/bin/python -m percival_osm_mcp --mode stdio`
    para uso direto como MCP.
  - `--mode streamable-http --port 8000` para depuração HTTP.
- Configuração 100 % via variáveis de ambiente; `OSM_CACHE_FILE`,
  `OSM_CACHE_ALLOWED_DIRS`, `ORS_API_KEY`, `USER_AGENT`, `FROM_HEADER` e
  flags de observabilidade/segurança listados em `.env.example`
  (documentação apenas — nada lê esse arquivo).
- Imagem Docker e `docker-compose.yml` fornecidos para deploy isolado.

## Risks and governance

- Cumprimento **obrigatório** da política de uso do Nominatim:
  `USER_AGENT` e `FROM_HEADER` não vazios (o servidor aborta com
  `ValueError` se faltarem) e rate-limit 1 req/s + burst 2 respeitado.
- Dependência do **OpenRouteService** (`ORS_API_KEY`) para tools de rota:
  sem chave, retornar `provider_not_configured`; haversine serve apenas para
  selecionar o perfil quando ORS está configurado.
- **Licença MIT** já presente; mudanças de licença exigem revisão.
- Privacidade / soberania: sem tracking comercial; cache confinado a
  `OSM_CACHE_ALLOWED_DIRS` (default `/tmp`); auth obrigatória
  (`MCP_OSM_AUTH_TOKEN`) para HTTP não-loopback.
- Upstreams permitidos (allow-list): `nominatim.openstreetmap.org`,
  `overpass-api.de`, `api.openrouteservice.org` — qualquer novo host
  precisa de revisão de política.

## Verification

- `uv run pytest -v` — suíte completa.
- `uv run pytest tests/test_s5_primitives.py` — prompts, resources,
  regressões.
- `uv run pytest tests/test_s3_observability.py` — health, version,
  logging estruturado, rate limit.
- `uv run pytest tests/test_runtime_security.py` — URL policy e
  sanitização.
- Inspeção manual via MCP inspector com `osm_get_health` e
  `osm_get_security_metrics` antes de qualquer release.

## Working conventions

- Stack Python, `uv` e layout `src/` são fixados; mudanças exigem ADR.
- Logs do servidor: **stderr apenas**; stdout é o stream MCP.
- Configuração: variáveis de ambiente; nada de `env_file` em disco.
- Falhas de configuração devem ser altas (`ValueError`), nunca
  silenciosas.
- Princípios `percival.OS` regem decisões: privacidade, soberania,
  hardening, transparência.
- Toda mutação remota (push, release, publicação) exige aprovação
  explícita do operador.
