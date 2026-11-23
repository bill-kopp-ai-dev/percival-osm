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
- Entrega **docker-first**: a imagem de container é o artefato e o contrato;
  o pacote Python é biblioteca interna da imagem. O entrypoint valida o
  ambiente (exit 78) e recusa execução como root (exit 77); a camada de init
  pertence ao launcher; a imagem não embute healthcheck (stdio não tem probe
  verdadeiro) e o perfil HTTP do Compose faz handshake MCP real. O
  `docker-compose.yml` é **fixture local** — containers de produção são
  configurados pelo manager Positronic/Percival, owner da configuração.
- 8 ferramentas MCP expostas por padrão. Todas as 14 ferramentas canônicas e
  23 aliases por categoria permanecem implementados e podem ser selecionados
  via `OSM_EXPOSED_TOOLS`, com aliases ainda sujeitos a
  `OSM_EXPOSE_LEGACY_ALIASES`.
- 3 primitivas de prompt (`osm_recipe_quick_search`, `osm_tool_chooser`,
  `osm_output_format`) e 2 primitivas de resource (`osm://categories`,
  `osm://security/nanobot-policy`).
- Hardening: HTTPS-only, URL allow-list, sanitização contra
  prompt-injection, rate-limit Nominatim (1 req/s sem burst) com
  single-flight.
- Observabilidade: `osm_get_health`, `osm_get_version`,
  `osm_get_security_metrics`, logging estruturado em stderr.
- Imagem multi-stage digest-pinned e reprodutível (uid 10001, cap_drop ALL,
  no-new-privileges, read-only root, sem init embutido), `docker-compose.yml`
  com perfis stdio e http e secrets por arquivo, e artefatos para submissão
  ao Docker MCP Catalog
  (`servers/percival-osm/{server.yaml,tools.json,readme.md}`).
- CI GitHub Actions (`.github/workflows/docker.yml`) com build
  linux/amd64, probe de conformidade stdio, smoke test da imagem, render dos
  contratos Compose, manifesto de build, SBOM CycloneDX e suíte Python.

**Evidência de sucesso:**

- `uv run pytest -v` — suíte completa (174 testes, alvo < 1s).
- `scripts/docker-smoke-test.sh` — 4 checks (non-root, env-var guard,
  probe de conformidade stdio com initialize/tools/list, e contrato HTTP com
  auth/bind/health/shutdown) sobre `percival-osm:local`.
- `scripts/docker-inspect.sh` — confirma labels OCI, healthcheck,
  user/entrypoint/cmd e site-packages resolvido.
- `bandit` e `pip-audit` sem achados críticos.
- `osm_get_security_metrics` reporta zero falhas em operação normal.
- README e resources MCP alinhados: o agente consegue se auditar contra
  a política sem reler o repo.

## Methods and resources

- Stack: Python ≥ 3.11, `mcp[cli]`, `httpx` (incl. ORS via async HTTP),
  `pydantic-settings`, `starlette`, `uvicorn` (ver `pyproject.toml`).
- Build backend: `hatchling`; pacote `src/percival_osm_mcp`; entry point
  `percival-osm-mcp`.
- Execução local (caminho de **desenvolvimento**, não de deploy):
  - `uv sync` para ambiente editável com dev-deps.
  - `PYTHONPATH=src .venv/bin/python -m percival_osm_mcp --mode stdio`
    para uso direto como MCP.
  - `--mode streamable-http --port 8000` para depuração HTTP.
- Configuração 100 % via variáveis de ambiente; `OSM_CACHE_FILE`,
  `OSM_CACHE_ALLOWED_DIRS`, `ORS_API_KEY`, `USER_AGENT`, `FROM_HEADER` e
  flags de observabilidade/segurança listados em `.env.example`
  (documentação apenas — nada lê esse arquivo).
- `NOMINATIM_URL` é obrigatório e explícito: sem backend selecionado o
  servidor aborta no startup.
- Imagem Docker (`Dockerfile`) e `docker-compose.yml` fornecidos. O Compose
  é fixture local; o deploy de produção é configurado pelo manager
  Positronic/Percival, que é o owner do runtime.

## Risks and governance

- Cumprimento **obrigatório** da política de uso do Nominatim:
  `USER_AGENT` e `FROM_HEADER` não vazios (o servidor aborta com
  `ValueError` se faltarem) e rate-limit por processo de 1 req/s sem burst;
  processos separados exigem coordenação para o limite agregado da aplicação.
- Dependência do **OpenRouteService** (`ORS_API_KEY`) para tools de rota:
  sem chave, retornar `provider_not_configured`; haversine serve apenas para
  selecionar o perfil quando ORS está configurado.
- **Licença MIT** já presente; mudanças de licença exigem revisão.
- Privacidade / soberania: sem tracking comercial; cache confinado a
  `OSM_CACHE_ALLOWED_DIRS` (default `/tmp`); auth obrigatória
  (`MCP_OSM_AUTH_TOKEN`) para HTTP não-loopback.
- Upstreams permitidos (allow-list): `nominatim.openstreetmap.org`,
  `overpass-api.de`, `api.heigit.org` — qualquer novo host
  precisa de revisão de política.
- **Issue aberta (2026-11-23)**: `osm_find_nearby` falha contra o endpoint
  público do Overpass (`HTTP 502` → `upstream_error` com `stage=overpass`).
  O geocoding público estava saudável na mesma batelada. A causa raiz foi
  atribuída ao provedor; o aceite operacional (busca nearby bem-sucedida)
  permanece pendente de disponibilidade externa. O registro detalhado da
  issue é mantido no repositório privado do operador e não é publicado no
  repositório público. A política de
  upstream não foi afrouxada para contornar a indisponibilidade.

## Verification

- `uv run pytest -v` — suíte completa (174 testes).
- `uv run pytest tests/test_s5_primitives.py` — prompts, resources,
  regressões.
- `uv run pytest tests/test_s3_observability.py` — health, version,
  logging estruturado, rate limit.
- `uv run pytest tests/test_runtime_security.py` — URL policy e
  sanitização.
- `uv run pytest tests/test_d6_docker.py` — Dockerfile, entrypoint,
  fixture Compose e artefatos do catálogo.
- `uv run pytest tests/test_f8_nearby_stage_diagnosis.py` — atribuição de
  etapa upstream, orçamento de deadline e retry limitado.
- Inspeção manual via MCP inspector com `osm_get_health` e
  `osm_get_security_metrics` antes de qualquer release.

## Working conventions

- Stack Python, `uv` e layout `src/` são fixados; mudanças exigem ADR.
- Entrega é **docker-first**: a imagem é o artefato, o entrypoint é o
  contrato e o manager Positronic/Percival é o owner do runtime. O Compose
  é fixture local e não define produção.
- Logs do servidor: **stderr apenas**; stdout é o stream MCP.
- Configuração: variáveis de ambiente; nada de `env_file` em disco.
- Falhas de configuração devem ser altas (`ValueError`), nunca
  silenciosas.
- Princípios `percival.OS` regem decisões: privacidade, soberania,
  hardening, transparência.
- Toda mutação remota (push, release, publicação) exige aprovação
  explícita do operador.
