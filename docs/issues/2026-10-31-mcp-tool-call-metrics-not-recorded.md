# Issue: chamadas MCP não aparecem nas métricas operacionais

- **Status:** corrigida e validada; candidata combinada pinada no runtime MCP
- **Prioridade sugerida:** P2 — observabilidade operacional
- **Identificada em:** 2026-10-31, validação pós-deploy da superfície reduzida de tools

## Problema

`osm_get_health` retorna `tool_calls: {}` e `tool_errors: {}` mesmo após chamadas
MCP bem-sucedidas na mesma sessão. Isso faz a telemetria por tool subnotificar ou
parecer indisponível.

## Evidência

- No teste funcional do Percival, `osm_get_version` foi chamado antes de
  `osm_get_health`, mas o health reportou os contadores vazios.
- A reprodução com o candidato implantado (`sha256:37ae7ce709595b81e82e0802db8154eaab7c05d0c9c172d9663aa3ccc7eb5ae9`)
  chamou `osm_get_version` e em seguida `osm_get_health` na mesma sessão MCP
  stdio; o segundo payload continuou com `tool_calls: {}` e `tool_errors: {}`.
- O health ainda retornou uptime válido e `last_upstream_failure: null`; a falha
  posterior de `osm_find_nearby` no teste ocorreu depois desse snapshot.

## Causa confirmada no código antes da correção

Antes da correção, os handlers canônicos usavam decorators nesta ordem:

```python
@_track("osm_get_version")
@_conditionally_register_tool("osm_get_version")
def get_version(...):
    ...
```

`_conditionally_register_tool` registra o handler original com FastMCP e só
depois o decorator externo `_track` cria o wrapper. O callback mantido pelo
gerenciador MCP fica, portanto, sem instrumentação. A mesma forma de registro é
usada nos demais handlers canônicos expostos.

## Reprodução

1. Iniciar o servidor com a superfície padrão de 8 tools.
2. Inicializar uma sessão MCP e chamar `osm_get_version`.
3. Chamar `osm_get_health` na mesma sessão.
4. Observar que `data.tool_calls` não contém `osm_get_version` nem
   `osm_get_health`.

## Critérios de aceite

- FastMCP registra o callback já instrumentado por `_track` para cada handler
  canônico selecionado pela allowlist.
- Uma chamada real a cada tool exposta aparece no respectivo contador
  `tool_calls` de `osm_get_health`.
- Uma exceção Python propagada pelo handler incrementa `tool_errors` para essa
  tool, sem dupla contagem.
- O teste cobre o registro e a chamada via FastMCP, não apenas a presença textual
  do decorator no código.
- Os aliases reativáveis continuam contabilizando somente o alias chamado; o
  perfil padrão continua expondo exatamente as 8 tools escolhidas.

## Próximo passo

Após revisão/commit das alterações, construir uma imagem com revisão OCI
rastreável e, com autorização explícita para a mudança de deploy, atualizar o
pin Percival. A imagem local de validação desta execução foi construída a partir
de worktree ainda não commitado e está marcada `revision=unknown`; não deve ser
tratada como artefato de release.

## Resultado da correção — 2026-10-31

- Os callbacks canônicos agora são instrumentados antes de serem entregues ao
  gerenciador FastMCP. A camada de tracking incrementa erro sem incrementar
  novamente a chamada; aliases usam o mesmo wrapper sob o nome do alias.
- A regressão textual foi substituída por execução dos oito callbacks padrão
  através de `FastMCP.call_tool`, com dependências upstream controladas. Testes
  confirmam uma chamada por tool, exceções síncronas/assíncronas com uma chamada
  e um erro, contagem somente no alias chamado e superfície padrão inalterada.
- Verificação automatizada: `93 passed`.
- Imagem local `percival-osm:metrics-fix-local`, ID
  `sha256:a033fc6f957319413a80886bdd4971804e4465bcd614d6235bdc3bebee877764`.
  A sessão stdio real executou initialize, `tools/list`, `osm_get_version` e
  `osm_get_health`; o health contou version e health uma vez cada. O smoke test
  Docker completo também passou, incluindo HTTP.
- A candidata combinada de deadline/metrics foi pinada por Bill no runtime MCP
  como `sha256:67cbd63c83a231e5a98cb9a12ae28de115a8685dc906ba2d9eb320270d2ae5ff`.
  O reteste real confirmou `tool_calls` para a busca e health após o pin. OCI
  revision permanece `unknown` por ter sido construída de worktree não commitado.
