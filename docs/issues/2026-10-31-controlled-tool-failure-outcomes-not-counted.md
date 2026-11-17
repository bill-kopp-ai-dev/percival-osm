# Issue: health não contabiliza falhas controladas por tool

- **Status:** aberta
- **Prioridade sugerida:** P2 — visibilidade operacional
- **Identificada em:** reteste real do timeout MCP em 2026-10-31
- **Verificada em:** 2026-11-16, auditoria documental sobre o estado real do código
- **Owner / decisão:** Bill Kopp

## Problema

Uma chamada `osm_find_nearby` retornou corretamente um payload MCP com
`status=upstream_error`, incrementou `tool_calls.osm_find_nearby` e atualizou
`last_upstream_failure`, mas `tool_errors` permaneceu vazio. Esse comportamento
é consistente com o contrato atual: `tool_errors` conta exceções Python
propagadas, e não respostas de erro tratadas pelo handler.

O limite desse contrato é operacional: um painel que use apenas `tool_errors`
não detecta falhas upstream tratadas. `last_upstream_failure` ajuda na triagem,
mas é um único registro global recente, não uma contagem por ferramenta nem um
histórico de resultados.

## Evidência

- A candidata `sha256:67cbd63c83a231e5a98cb9a12ae28de115a8685dc906ba2d9eb320270d2ae5ff`
  retornou ao cliente o payload `upstream_error` dentro do limite observado.
- No health pós-chamada: `tool_calls.osm_find_nearby=1`, `tool_errors={}` e
  `last_upstream_failure.kind=NearbySearch` com motivo de deadline.
- Não é uma regressão da correção do timeout; é uma limitação conhecida na
  granularidade da telemetria de resultados tratados.

## Critérios de aceite

- Definir um sinal de health por ferramenta que permita distinguir outcomes
  controlados de chamadas bem-sucedidas, sem alterar a semântica de
  `tool_errors` para exceções propagadas.
- Escolher e documentar quais statuses são outcomes de falha (`upstream_error`,
  `config_error`, `error`, `provider_not_configured`, entre outros) e como
  `no_results` é representado; não inferir falha apenas da ausência de dados.
- Adicionar regressões de contagem para sucesso, `no_results`, erro upstream
  controlado e exceção propagada, incluindo chamada MCP registrada.
- Evitar guardar query, URL, resposta upstream ou dados potencialmente pessoais
  nos novos contadores; preferir nomes de tool e status categóricos.
- Atualizar `osm_get_health` e a documentação de observabilidade com o contrato
  adotado.

## Limites

- Não mudar `tool_errors` para incluir status tratados; isso confundiria exceções
  propagadas com payloads MCP retornados normalmente.
- `last_upstream_failure` continua útil para diagnóstico, mas não substitui uma
  métrica agregada por tool/status.

## Verificação de auditoria — 2026-11-16

- A limitação **continua presente e não foi resolvida**. O snapshot operacional
  (`get_operational_snapshot`, `src/percival_osm_mcp/server.py:702`) expõe
  apenas `tool_calls`, `tool_errors` e `last_upstream_failure`; não existe
  contador por status de outcome controlado (`no_results`, `upstream_error`,
  `config_error`, `provider_not_configured`, `invalid_request`).
- Os contadores por tool existem e funcionam, mas respondem a uma pergunta
  diferente: quantas vezes cada tool foi chamada, e quantas vezes a chamada
  lançou uma exceção Python propagada.
- Escala do problema: qualquer painel que use apenas `tool_errors` continua
  invisível a falhas upstream tratadas. `last_upstream_failure` é um registro
  global único e sobrescrito, o que perde a contagem por tool e o histórico.
- Nenhuma regressão de contagem por status foi adicionada; os critérios de
  aceite abaixo permanecem integralmente aplicáveis.

## Encaminhamento — 2026-11-16

- Implementação proposta em [F6 do plano de atualização MCP](../plans/2026-11-16-mcp-api-refresh-and-reliability.md):
  `tool_outcomes[tool][outcome]`, com `no_results` distinto de falha, um outcome
  terminal por invocação MCP e sem dupla contagem em aliases/delegações internas.
- O plano preserva a semântica atual de `tool_errors` e inclui cancelamento,
  exceção propagada e respostas locais de health/version na matriz de aceite.
- Issue permanece aberta até implementação e regressões pelo callback registrado.
