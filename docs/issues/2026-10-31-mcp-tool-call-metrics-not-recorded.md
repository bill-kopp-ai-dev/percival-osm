# Issue: chamadas MCP não aparecem nas métricas operacionais

- **Status:** aberta
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

## Causa provável confirmada no código

Handlers canônicos usam decorators nesta ordem:

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

Corrigir a ordem/composição dos decorators para que o callback entregue ao
FastMCP seja o wrapper instrumentado, adicionar a regressão de execução real e
validar a imagem candidata antes de atualizar o pin Percival.
