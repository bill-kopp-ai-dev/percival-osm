# Issue: prazo upstream pode exceder o timeout do cliente MCP

- **Status:** resolvida e confirmada no runtime MCP — 2026-10-31
- **Prioridade sugerida:** P2 — confiabilidade e diagnóstico operacional
- **Identificada em:** 2026-10-31, teste funcional pós-pin do servidor `osm`
- **Owner / decisão:** Bill Kopp

## Problema

Uma chamada a `osm_find_nearby` atingiu o timeout de 30 s do transporte MCP
durante uma falha do Overpass. O cliente não recebeu uma resposta utilizável.
O health subsequente registrou `tool_calls.osm_find_nearby = 1` e uma falha
Overpass, mas não permite distinguir uma operação ainda em andamento de uma
resposta que chegou depois do prazo do cliente.

Isso cria uma incompatibilidade potencial: o servidor pode continuar fazendo
retries depois que o cliente já encerrou a espera, deixando o usuário com um
timeout opaco em vez do resultado controlado `upstream_error` previsto pelo
servidor.

## Evidência e causa provável

- **Relato do teste pós-pin:** as chamadas de health, version, security metrics,
  geocode e place concluíram; `osm_find_nearby` excedeu 30 s durante uma falha
  Overpass. `osm_directions` retornou `provider_not_configured` por ausência de
  `ORS_API_KEY`, comportamento esperado e independente desta issue.
- **Configuração observada no código:** `http_timeout_seconds=12`,
  `http_max_retries=2` e `http_retry_backoff_seconds=0.6`. Para uma requisição
  que esgote as três tentativas, o orçamento nominal é até 36 s de timeout mais
  1,8 s de backoff (37,8 s), sem contar processamento adicional.
- **Fluxo observado no código:** `osm_find_nearby` resolve o lugar via Nominatim
  e depois consulta Overpass. Uma falha Overpass é convertida em
  `UpstreamRequestError` e tratada por `search_nearby`, que prepara um payload
  `upstream_error`; essa resposta pode ser produzida depois do timeout do
  cliente.
- O orçamento de 37,8 s é um limite potencial, não uma medição da duração da
  chamada relatada. O relatório não prova que o servidor travou nem que a
  resposta `upstream_error` chegou ao cliente.
- `tool_errors` vazio é compatível com o contrato atual: o handler trata a
  falha upstream e retorna resposta controlada, em vez de propagar uma exceção
  Python. `tool_errors` permanece destinado a exceções propagadas; a falha de
  upstream é exposta separadamente em `last_upstream_failure`.

## Reprodução reportada

1. Em uma sessão MCP, executar chamadas de health/version e buscas de lugar.
2. Chamar `osm_find_nearby` para uma categoria em São Paulo com limite 3 e
   raio de 1000 m.
3. Observar o timeout do cliente MCP em 30 s durante a falha Overpass.
4. Chamar `osm_get_health` depois e observar `tool_calls` incrementado para a
   busca e `last_upstream_failure` com provedor Overpass.

No momento da abertura, ainda faltava uma fixture determinística que
reproduzisse a latência e observasse a resposta MCP efetivamente entregue ou
perdida após o prazo. Ela foi adicionada durante a implementação descrita abaixo.

## Critérios de aceite

- Definir um orçamento end-to-end para tools com upstream que seja compatível
  com o limite de transporte observado de 30 s, com margem para protocolo e
  processamento local. O orçamento deve considerar retries, backoff e chamadas
  sequenciais de upstream; não basta limitar cada tentativa isoladamente.
- Em uma falha upstream reproduzida dentro desse orçamento, o cliente MCP recebe
  uma resposta `upstream_error` antes do próprio timeout, sem aguardar retries
  que já não podem produzir uma resposta útil.
- A regressão usa upstreams simulados com atrasos/falhas determinísticos e mede o
  prazo total; verifica também que o cliente recebe a resposta controlada e que
  `tool_calls` é incrementado uma vez.
- Cancelamento/timeout não deixa tarefas pendentes nem recursos HTTP abertos; a
  limpeza de `OsmSearcher` continua garantida.
- `last_upstream_failure` preserva informação sanitizada útil para triagem
  (provedor e resumo/status), sem expor URL ou payload da requisição.
- O contrato de `tool_errors` continua explícito: resposta controlada
  `upstream_error` não é exceção propagada e não precisa incrementar esse
  contador.
- Os testes focados, a suíte completa e o teste de conformance MCP passam.

## Decisões e limites

- O timeout observado de 30 s é evidência do cliente usado no teste; confirmar
  se esse é o limite aplicável a todos os clientes suportados antes de fixar um
  valor global.
- Comparar opções: reduzir o orçamento de retry/timeout do servidor, impor um
  prazo end-to-end por chamada, ou elevar o timeout do cliente quando a
  integração permitir. Priorizar uma resposta controlada e previsível em vez de
  manter retries após o cliente abandonar a chamada.
- Não configurar ou compartilhar `ORS_API_KEY` como parte desta issue.
- Não reclassificar `provider_not_configured`, `no_results` ou respostas
  controladas `upstream_error` como exceções Python apenas para preencher
  `tool_errors`.
- Mudanças de pin/deploy exigem autorização explícita e artefato com revisão
  rastreável.

## Resolução — 2026-10-31

- A primeira candidata usou `OSM_UPSTREAM_TOOL_DEADLINE_SECONDS=24`. No teste MCP
  real, o timeout interno foi registrado após 25,44 s, mas o cliente ainda
  estourou seu limite de 30 s sem receber JSON. A margem de 6 s foi insuficiente.
- Revisto para default e máximo de 16 s, intervalo `(0, 16]`, deixando 14 s de
  margem ao cliente observado.
- Todas as tools assíncronas instrumentadas que fazem chamadas upstream usam o
  prazo end-to-end; busca próxima também o aplica no limite compartilhado para
  poder devolver o payload estruturado `upstream_error`. Isso cobre geocoding,
  Nominatim, Overpass, chamadas de rota e aliases de categoria.
- O vencimento retorna `upstream_error` sanitizado e registra o tool/provider
  em `last_upstream_failure`; `tool_errors` permanece reservado a exceções
  Python propagadas.
- Em timeout, tarefas de distância em background e futures são canceladas; o
  cancelamento/fechamento de HTTP fica limitado a 2 s, em vez de aguardar a
  janela normal de drain de shutdown.
- Falhas encapsuladas de Overpass/Nominatim mantêm no health um resumo
  sanitizado — incluindo status HTTP, quando presente — sem URL ou payload.
- Testes determinísticos verificam as variantes nearby, uma tool geocode,
  validação, cancelamento/fechamento, `tool_calls` e diagnóstico `HTTP 503`. Um
  teste in-process da chamada FastMCP com HTTP Overpass atrasado verifica entrega
  do payload `upstream_error` ao chamador.
- **Verificação antes da revisão:** `99 passed`, compilação Python,
  `git diff --check`, `docker compose config --quiet` e smoke Docker passaram
  para a candidata de 24 s.
- **Candidata revisada localmente:** `100 passed`, compilação Python,
  `git diff --check` e `docker compose config --quiet` passaram. Inclui teste
  FastMCP com Overpass HTTP atrasado e limpeza que não termina; valida que o
  payload chega ao chamador apesar do cleanup demorado. A imagem local revisada
  foi construída como `percival-osm:deadline-local`, hash
  `sha256:67cbd63c83a231e5a98cb9a12ae28de115a8685dc906ba2d9eb320270d2ae5ff`;
  Docker smoke passou.
- **Reteste MCP real:** Bill pinou a imagem revisada acima. Para MASP, uma
  chamada única retornou ao cliente `status=upstream_error` e a mensagem
  `Nearby search exceeded its execution deadline; retry later.`. O health
  registrou `NearbySearch / end-to-end deadline exceeded after 16s` e
  `tool_calls.osm_find_nearby=1`. O cliente recebeu o payload antes do limite de
  30 s; portanto o caminho de timeout está confirmado no runtime MCP.
- A busca não retornou POIs; esse teste valida entrega do erro controlado, não
  uma busca bem-sucedida. A reprodução anterior com a candidata de 24 s falhou
  em entregar o payload; a margem e o limite de cleanup foram reduzidos antes
  deste reteste.
- `tool_errors={}` permaneceu conforme o contrato, pois o status foi tratado e
  retornado normalmente. A limitação de monitoramento por `tool_errors` apenas
  está registrada em
  `docs/issues/2026-10-31-controlled-tool-failure-outcomes-not-counted.md`.
- O limite de 30 s foi observado num cliente, não é garantia universal para
  todos os consumidores MCP. A imagem foi pinada pelo operador; esta alteração
  não publicou nem enviou a imagem a um registry.

## Reteste MCP real — 2026-10-31

- Imagem testada: `sha256:a8df6ec22f69aeae3c27d1eb61e915e475d45da98fe610bb256626e65b31ed54`.
- `osm_find_nearby` para MASP levou o cliente a retornar
  `(MCP tool call timed out after 30s)`, sem JSON. O health posterior registrou
  `NearbySearch / end-to-end deadline exceeded after 24s`; isso comprova que o
  deadline disparou, mas não que a resposta foi entregue.
- `tool_errors` vazio segue o contrato deliberado: a falha é convertida numa
  resposta controlada, não numa exceção Python propagada. Não é critério de
  sucesso ou causa demonstrada da resposta perdida.
- O atraso pode estar no cancelamento/fechamento após o registro ou na entrega do
  transporte; o dado disponível não identifica a etapa exata. A issue fica
  **aberta** até um reteste no runtime MCP com a nova candidata.
