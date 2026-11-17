# Issue: falha de persistência do cache escapa como exceção crua

- **Status:** aberta
- **Prioridade sugerida:** P1 — robustez do runtime e prazo de entrega das respostas
- **Identificada em:** 2026-11-16, auditoria documental sobre o estado real do
  código (sandbox com `/tmp` somente-leitura)
- **Owner / decisão:** Bill Kopp

## Problema

`OsmCache._persist()` grava o arquivo de cache em disco. Quando essa gravação
falha, a exceção sobe sem tratamento e atravessa a camada de tools: o cliente
MCP recebe uma falha interna do servidor em vez do payload controlado que o
contrato do projeto promete (`upstream_error`, `config_error`, `no_results`).

Além disso, o caminho de erro resultante deixa o fechamento do cliente HTTP sem
prazo: `OsmSearcher.aclose()` só limita `client.aclose()` quando é chamado com
`cancel_pending=True`. Uma exceção que ocorra **antes** do vencimento do
deadline end-to-end leva o handler a `aclose(cancel_pending=False)`, onde
`await client.aclose()` não tem limite de tempo.

## Evidência

- Reprodução determinística: com `cache_file=/tmp/osm-cache.json` em um
  filesystem somente-leitura, `OsmSearcher.nominatim_search()` levanta
  `OSError: [Errno 30] Read-only file system: '/tmp/osm-cache.json.tmp'`.
- A chamada de cache em `OsmSearcher.nominatim_search()`
  (`src/percival_osm_mcp/server.py:2426`) está fora do `try/except` que
  converte falhas de upstream em `UpstreamRequestError`; `search_nearby()`
  (linha 2651) só captura `ValueError` e `UpstreamRequestError`.
- `OsmCache._persist()` (`src/percival_osm_mcp/server.py:1636`) escreve
  `<arquivo>.tmp` e faz `replace`; nenhuma falha de I/O é capturada.
- Efeito observável na suíte: com `/tmp` somente-leitura, o teste
  `tests/test_s4_new_tools.py::test_registered_nearby_timeout_reaches_mcp_caller`
  **pendura indefinidamente**. A causa é encadeada: o `OSError` do cache aborta a
  busca antes do vencimento do deadline, o handler entra em
  `aclose(cancel_pending=False)`, e o fixture `FakeClient.aclose()` do teste
  só termina por cancelamento.
- Com um diretório de cache gravável, a suíte completa passa (`100 passed`).
- `OsmCache.get()` também pode levantar `OSError` ao tentar persistir a remoção
  de uma entrada expirada. A leitura inicial em `_load()` trata JSON inválido,
  mas não erros de acesso ao arquivo.

## Critérios de aceite

- Falha de persistência ou leitura do cache não pode escapar como exceção
  Python: o cache é uma otimização best-effort, e o erro deve virar um payload
  controlado e sanitizado, sem URL, caminho ou traceback no corpo da resposta.
- Definir explicitamente o comportamento para o cache indisponível: ou a
  ferramenta responde com `upstream_error`/`config_error` controlado, ou segue
  sem cache e registra um evento de segurança/operacional categorizado.
- `OsmSearcher.aclose()` deve ter prazo também no caminho sem cancelamento, para
  que o fechamento do cliente HTTP não possa exceder o orçamento end-to-end da
  chamada.
- Regressões: cache somente-leitura (falha de escrita) e cache corrompido
  (JSON inválido ou falha de leitura) devem produzir resposta controlada, sem tarefa pendente e
  sem estouro de prazo.
- A suíte completa deve passar em ambiente com `/tmp` somente-leitura, ou os
  fixtures de teste devem usar um diretório temporário gravável em vez de um
  caminho fixo em `/tmp`.

## Limites

- Não alterar o contrato de `tool_errors`: exceções realmente propagadas
  continuam sendo contadas como erro.
- Não expor caminho de arquivo, permissão ou conteúdo de cache nas respostas ao
  cliente; os detalhes ficam no log sanitizado e nas métricas.
- Não remover o cache: a migração best-effort do cache legado continua
  documentada em
  `docs/plans/closed/2026-10-27-stage-2-remediation-plan.md` (A-008) e não faz
  parte desta issue.

## Encaminhamento — 2026-11-16

- Implementação proposta em [F2/F3 do plano de atualização MCP](../plans/2026-11-16-mcp-api-refresh-and-reliability.md):
  cache em memória compartilhado com persistência best-effort, sinal de degradação
  e cleanup dentro do orçamento da chamada.
- Precisão da evidência: JSON corrompido já é capturado por `_load` como
  `JSONDecodeError`; erros de acesso/encoding e erros de persistência/expiração
  ainda precisam de tratamento. A reprodução registrada foi de escrita EROFS;
  os demais casos serão verificados por fixtures, não são reproduções já feitas.
- Issue permanece aberta; comportamento recomendado é preservar resultado
  válido e cache em memória, sem transformar falha de disco em falha upstream.
