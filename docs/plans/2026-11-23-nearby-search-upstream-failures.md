# Plano — diagnosticar e corrigir falhas de upstream em `osm_find_nearby`

- **Data:** 2026-11-23 · **Estado:** executado · **Prioridade:** P1
- **Owner:** Bill Kopp
- **Issue:** [Falhas repetidas na busca próxima](../issues/2026-11-23-nearby-search-upstream-failures.md)
- **Base inspecionada:** checkout `a5aa792` (confirmado como commit da validação
  real: `a5aa7928cf97`). A versão `0.5.0` por si só não identifica o código
  executado; a validação abaixo foi feita sobre este checkout.

## Resultado esperado

A busca próxima distingue ausência de POIs de falha do provedor, termina dentro do prazo configurado e não deixa trabalho órfão. Em caso de falha ou timeout, a resposta MCP permanece controlada e a telemetria permite identificar a etapa que falhou ou consumiu o prazo.

**Evidência inicial:** na versão pinada `0.5.0`, duas buscas por `pharmacies` em `Praça da Sé, São Paulo, Brazil`, com `limit=3` e `radius=1500`, retornaram `upstream_error`: primeiro uma falha genérica, depois o deadline de 16 s. O snapshot final registrou `NearbySearch`, mas não identificou a etapa nem preservou a causa da primeira falha. Consultas nominais e reversas bem-sucedidas na mesma batelada não descartam atraso no geocoding dessa chamada ou no lookup posterior. Indisponibilidade externa e regressão local ainda são hipóteses.

**Fora de escopo:** ampliar a allow-list, aumentar o deadline, trocar automaticamente de provedor ou alterar ORS para resolver esta issue. Sem `ORS_API_KEY`, `provider_not_configured` nas ferramentas de rota é esperado. Build, publicação e deploy não fazem parte deste plano.

## Resultado da execução

- **Causa atribuída:** falha externa na etapa do provedor. O Overpass público
  respondeu `HTTP 502`; o geocoding (Nominatim) respondeu em ~70 ms. Duas
  validações reais pelo callback MCP, com os parâmetros da issue, terminaram
  em 15,90 s — dentro do deadline de 16 s — com `stage=overpass`,
  `reason=deadline_exceeded` e `http_status=502` registrados.
- **Lacunas locais corrigidas:** orçamento publicado divergente do timer
  aplicado; teardown fora do orçamento reservado; timeout por tentativa e
  backoff de retry não limitados ao orçamento restante.
- **Aceite operacional:** pendente por indisponibilidade externa do provedor.
  Ver [issue](../issues/2026-11-23-nearby-search-upstream-failures.md).
- **Nenhuma mudança de política:** allow-list, deadline nominal, `USER_AGENT` /
  `FROM_HEADER`, rate limit e formato de retorno MCP inalterados.

## F1 — Isolar a etapa e o motivo da falha

- [x] Mapear o caminho em [`server.py`](../../src/percival_osm_mcp/server.py): `find_places_near_place` → `search_category_near_place` → `do_osm_search` → `_search_nearby_with_deadline` → `OsmSearcher.search_nearby`. Backend Overpass selecionado: `overpass-api.de` (`OSM_UPSTREAM_ALLOWED_HOSTS`, padrão `nominatim.openstreetmap.org,overpass-api.de,api.heigit.org`). Reproduções locais usaram cache isolado (`tmp_path`); o cache do operador não foi tocado nem limpo.
- [x] Diagnóstico por chamada com relógio monotônico: geocoding inicial (`geocode`), consulta Overpass (`overpass`), enriquecimento/lookup Nominatim (`enrich`), distância ORS (`route`), ranking (`rank`), renderização (`render`) e limpeza (`cleanup`). Espera local (limite de taxa, cooldown, backoff de retry) é medida separadamente do tempo de rede e reportada em `waits`. Etapas e motivos usam vocabulário fixo (`http_error`, `timeout`, `transport_error`, `invalid_response`, `partial_response`, `cooldown`, `deadline_exceeded`, `validation_error`, `cancelled`); duração e status HTTP quando disponível. No timeout, a etapa ativa é preservada (`active_stage`, com fallback para `last_stage` quando o cancelamento já a fechou) sem contar duas vezes o outcome MCP. `osm_get_health` permanece compatível (campos novos são aditivos) e o diagnóstico é emitido em stderr. Nenhuma URL, header, credencial, endereço consultado, consulta Overpass, exceção bruta ou corpo upstream entra na telemetria ou no erro ao cliente.
- [x] Fixtures para separar as hipóteses:

| Hipótese | Evidência para distinguir | Resultado observado |
| --- | --- | --- |
| Geocoding inicial ou espera local pelo Nominatim | Overpass não é alcançado e a maior parte do prazo é consumida no geocoding, no rate limit ou na espera por uma consulta em andamento. | **Refutada.** `geocode=0,067 s` e `0,074 s` nas duas execuções reais; o prazo foi consumido em `overpass`. |
| Falha ou lentidão do Overpass/HEIGIT | Geocoding termina com orçamento restante; a consulta retorna falha HTTP, timeout ou resposta inválida/parcial, ou consome o restante do prazo. | **Confirmada.** Overpass respondeu `HTTP 502`; o `overpass` consumiu 15,8 s de 15,9 s. |
| Etapa posterior ou limpeza extrapola o prazo | Uma resposta Overpass válida já chegou; enriquecimento, processamento local ou fechamento concentra o atraso. | **Refutada** no caminho real (nenhuma resposta Overpass válida chegou). Coberta por fixture: deadline após resposta válida é atribuído a `enrich`. |

## F2 — Corrigir o caminho identificado sem ampliar o orçamento

- [x] Verificar primeiro um descompasso no checkout: confirmado. `_search_nearby_with_deadline` publicava o menor deadline herdado mas armava `asyncio.timeout(timeout_seconds)` com o timeout nominal; `do_osm_search` e `do_osm_search_full` aguardavam `aclose()` depois desse limite; e o timeout por tentativa (`OSM_HTTP_TIMEOUT_SECONDS=12`, padrão) e o backoff de retry (`0,6 s`, `1,2 s`) não eram limitados ao orçamento restante — uma falha transitória do Overpass consumia o prazo inteiro em tentativas que o orçamento não sustentava. Medição da entrada do callback à resposta, incluindo fechamento: 15,90 s para um deadline de 16 s, com `cleanup=0,000 s`.
- [x] Aplicar apenas a mudança sustentada pelo diagnóstico: um único prazo absoluto efetivo. `_split_call_budget()` reserva a fatia de cancelamento/fechamento *dentro* do deadline configurado (`min(0,1 s, 10 % do prazo)`); o deadline publicado e o timer aplicado passam a ser o mesmo valor absoluto; o transporte limita o timeout por tentativa e o backoff de retry ao orçamento restante e não inicia retry que o orçamento não sustenta. Sem fallback silencioso; sem tratar resposta parcial como sucesso; sem converter falha em `no_results`.
- [x] No deadline ou cancelamento, encerrar e aguardar os recursos exclusivos da chamada: o teardown passou a ocorrer dentro da fatia reservada do orçamento, para os consumidores canônico, detalhado e legados que compartilham o fluxo. A consulta compartilhada por single-flight continua sob o regime existente — cada consumidor pode cancelar sem cancelar os demais, e o último consumidor não deixa consulta órfã. O esquema de retorno MCP e a distinção entre `ok`, `no_results` e `upstream_error` não mudaram.

## F3 — Verificar e encerrar

- [x] Testes de regressão determinísticos: `tests/test_f8_nearby_stage_diagnosis.py` (transporte em processo, cache isolado, sem rede pública) e `tests/test_f3_deadline_transport.py` (clamp do timeout por tentativa). Cobrem: geocoding válido seguido de falha HTTP do Overpass; consulta bloqueada até o deadline; timeout após resposta Overpass válida (atribuição ao enriquecimento); concordância entre orçamento publicado e timer aplicado; teardown dentro do orçamento; retry não iniciado quando o orçamento não o sustenta; envelope MCP intacto; incremento único em `tool_calls` e `tool_outcomes.osm_find_nearby.upstream_error`; nenhum incremento em `tool_errors`; etapa/motivo sanitizados sem conteúdo bruto; ausência de tarefa órfã após o cancelamento.
- [x] Rodar os testes focados com `uv run pytest`: suíte completa passa (174 testes). `bandit` sem achados (0 low/medium/high). `pip-audit` reporta achados apenas em `filelock`, `msgpack`, `pip` e `pytest` — ferramentas de desenvolvimento, não dependências de runtime do pacote; nenhuma dependência foi alterada por este plano. `ruff` não está instalado no ambiente, portanto não foi executado.
- [x] Chamada real pelo MCP com os parâmetros da issue, em ambiente de validação, respeitando cooldown e limites: duas execuções, com intervalo, e sem rajada. Registro: versão `0.5.0`, commit `a5aa7928cf97`, backend `overpass` (rotulado por função, sem expor host), cache `persistent` e não degradado, duração 15,903 s e 15,904 s (dentro do deadline de 16 s), status `upstream_error`, contagem de POIs 0, `stage=overpass`, `reason=deadline_exceeded`, `http_status=502`.
- [x] Verificação real bloqueada por indisponibilidade externa: classificação registrada na [issue](../issues/2026-11-23-nearby-search-upstream-failures.md) — **falha externa observada na etapa do provedor**. O aceite operacional (`ok` com 1–3 POIs) permanece pendente até obter evidência de sucesso; a política de upstream não foi alterada e nenhuma rajada foi feita para obter um resultado verde.

## Revalidação da imagem refatorada (2026-11-23)

Após a refatoração e o pin da imagem, foi feita uma nova chamada real pela interface MCP ativa, usando os parâmetros da reprodução da issue (`Praça da Sé, São Paulo, Brazil`, `pharmacies`, `limit=3`, `radius=1500`). A identidade da imagem em execução havia sido verificada no container Positronic como revisão `ba61872b6b27c6a1da248e8e39b61bd265037c64`, imagem `sha256:b9bf03a08a5e87d4e80c5c9cb6c207d2729d6aac3fe9cf5cb6ecde12ee947b92`, versão OCI `0.5.0`. A chamada observada foi atendida pelo servidor `percival-osm` versão `0.5.0`, Python `3.12.15`, iniciado em `2026-11-23T12:39:29.585563+00:00`.

- Resultado MCP: `status=upstream_error`; nenhum POI retornado.
- `osm_get_health`: uma chamada `osm_find_nearby`, um outcome `upstream_error`, nenhum `tool_error`; `last_upstream_failure.kind=Overpass`, `stage=overpass`, `reason=deadline_exceeded`, `http_status=502`.
- Duração registrada: `geocode=0,1146 s`, `overpass=14,8324 s`, `elapsed=14,9472 s`; espera local `overpass=1,8 s`. A chamada terminou dentro do deadline configurado de 16 s. Cache persistente e não degradado.
- `osm_get_version` e `osm_get_health` retornaram `status=ok`.
- Interpretação: a execução real confirma que a imagem refatorada expõe etapa, motivo e status HTTP sanitizados, mantém o outcome MCP controlado e encerra dentro do orçamento. A falha funcional da consulta persiste porque o upstream Overpass respondeu HTTP 502; esta tentativa não demonstra sucesso com 1–3 POIs e não permite inferir a disponibilidade geral ou duração da indisponibilidade do provedor.
- Regressões determinísticas: `./.venv/bin/python -m pytest -q tests/test_f8_nearby_stage_diagnosis.py tests/test_f3_deadline_transport.py` — **20 passed**. `uv run` não estava disponível no PATH desta sessão; os testes foram executados pelo Python do ambiente virtual local.
- Não houve repetição imediata da chamada real após o 502, para respeitar cooldown e evitar pressão desnecessária no provedor. O aceite operacional continua pendente até uma execução bem-sucedida quando o upstream estiver disponível.

## Revalidação ampliada: cinco buscas distintas (2026-11-23)

A pedido do operador, foram executadas cinco chamadas reais e sequenciais de `osm_find_nearby`, cada uma para local/categoria diferentes:

| # | Local | Categoria solicitada | Resultado MCP |
| --- | --- | --- | --- |
| 1 | Mercado Municipal de São Paulo, São Paulo | `bakeries` | `upstream_error`, sem POIs |
| 2 | Parque Ibirapuera, São Paulo | `food` (normalizada para `restaurants and food`) | `upstream_error`, sem POIs |
| 3 | Praça da Liberdade, Belo Horizonte | `libraries` | `upstream_error`, sem POIs |
| 4 | Jardim Botânico do Rio de Janeiro, Rio de Janeiro | `tourist_attractions` (normalizada para `tourist attractions`) | `upstream_error`, sem POIs |
| 5 | Estação da Luz, São Paulo | `groceries` | `upstream_error`, sem POIs |

A imagem executada foi previamente identificada como revisão `ba61872b6b27c6a1da248e8e39b61bd265037c64`, digest `sha256:b9bf03a08a5e87d4e80c5c9cb6c207d2729d6aac3fe9cf5cb6ecde12ee947b92` (versão OCI `0.5.0`). Após as cinco chamadas, `osm_get_health` reportou seis chamadas `osm_find_nearby` desde a inicialização observada (incluindo a chamada de revalidação anterior), seis outcomes `upstream_error` e nenhum `tool_error`. A última falha observada foi `stage=overpass`, `reason=deadline_exceeded`, `http_status=502`; durações `geocode=0,8241 s`, `overpass=14,4882 s`, `elapsed=15,3124 s`, com espera local `overpass=1,8 s`. A chamada encerrou dentro do deadline de 16 s; cache persistente e não degradado.

**Conclusão:** as cinco respostas confirmam falhas repetidas de busca nesta batelada; o diagnóstico detalhado final atribui a falha mais recente ao Overpass (HTTP 502/deadline). O snapshot não preserva telemetria por chamada, portanto não atribuímos estes mesmos tempos individualmente às cinco buscas. O resultado não determina a duração ou abrangência da indisponibilidade do provedor. A refatoração demonstra retorno controlado, atribuição de etapa e respeito ao deadline, mas o critério operacional de uma busca bem-sucedida com 1–3 POIs permanece pendente. Nenhuma chamada extra foi feita após as cinco solicitadas.
