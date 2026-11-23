# Issue: `osm_find_nearby` falha repetidamente em busca próxima

- **Status:** aberta — causa raiz atribuída; correção local aplicada; aceite
  operacional pendente por indisponibilidade externa do provedor
- **Prioridade sugerida:** P1 — ferramenta de descoberta de POIs indisponível nesta execução
- **Identificada em:** 2026-11-23, batelada de testes no servidor MCP `percival-osm` 0.5.0 pinado
- **Owner / decisão:** Bill Kopp
- **Diagnóstico e correção:** [plano de 2026-11-23](../plans/2026-11-23-nearby-search-upstream-failures.md)

## Problema

Duas chamadas consecutivas de `osm_find_nearby` para descobrir farmácias em um
raio de 1.500 m da Praça da Sé, São Paulo, falharam. A primeira retornou
`upstream_error` genérico; a repetição retornou timeout do deadline da busca
próxima. O snapshot de saúde do próprio servidor confirmou duas chamadas da
tool com outcome `upstream_error` e registrou a falha mais recente como
`NearbySearch`, com mensagem `end-to-end deadline exceeded after 16s`.

Isso impediu validar a descoberta de POIs nessa sessão. Como os demais testes
não falharam na consulta de busca nominal/reverse-geocode, a evidência aponta
para o fluxo de busca nearby ou seu upstream, mas não isola a causa raiz.
Não se conclui ainda que seja defeito persistente do servidor: indisponibilidade
ou lentidão transitória do provedor continua possível.

## Reprodução observada

Parâmetros em ambas as tentativas:

```json
{
  "place": "Praça da Sé, São Paulo, Brazil",
  "category": "pharmacies",
  "limit": 3,
  "radius": 1500
}
```

Resultados observados, em ordem:

1. `status=upstream_error`, `An OSM provider request failed; retry later.`
2. `status=upstream_error`, `Nearby search exceeded its execution deadline; retry later.`

O `osm_get_health` posterior apresentou `tool_calls.osm_find_nearby=2`,
`tool_outcomes.osm_find_nearby.upstream_error=2`, sem `tool_errors`, e
`last_upstream_failure.kind=NearbySearch` / `end-to-end deadline exceeded
after 16s`. Cache reportado como persistente e não degradado.

## Critérios de aceite

- Identificar, com testes/telemetria sanitizados, se o atraso ocorre em geocoding,
  consulta Overpass/HEIGIT ou etapa subsequente; não registrar URLs, credenciais
  ou conteúdo upstream bruto em resposta ao cliente.
- Garantir que o caminho de nearby complete no deadline configurado e converta
  falhas de upstream em resultado controlado, sem tarefa pendente.
- Adicionar regressão determinística para falha e timeout do upstream, cobrindo
  o contrato MCP e o outcome de observabilidade.
- Validar uma busca nearby bem-sucedida quando o upstream estiver disponível;
  falhas transitórias externas devem ser distinguidas de regressão local.

## Limites

- Não ampliar allow-list nem aumentar o deadline sem evidência da causa e análise
  do impacto na política de upstream.
- ORS ausente não está relacionado a esta falha: `osm_navigate` e
  `osm_directions` retornaram `provider_not_configured`, comportamento esperado
  sem `ORS_API_KEY`.

## Contexto da batelada

O servidor respondeu como `percival-osm` versão `0.5.0` (Python `3.12.15`),
saúde operacional `ok`, sem degradação reportada no cache. `osm_find_place`,
`osm_find_place_detailed`, `osm_geocode` e `osm_find_address` retornaram
resultados válidos para locais de São Paulo. A falha nearby foi reproduzida em
duas tentativas nesta mesma sessão; causa raiz ainda não determinada.

---

## Atribuição da causa raiz (2026-11-23, após a correção)

A causa deixou de ser indeterminada. Duas chamadas reais de validação pelo
callback MCP registrado, com os parâmetros exatos da issue, isolaram a etapa e
o provedor:

| Execução | Etapa que consumiu o prazo | Motivo | Evidência |
| --- | --- | --- | --- |
| 2026-11-23 08:07:58 | `overpass` (15,836 s de 15,904 s) | `deadline_exceeded` | `geocode=0,067 s`; espera local de `0,6 s` (backoff de retry); `SECURITY_EVENT upstream_request_failure` na primeira tentativa |
| 2026-11-23 08:09:04 | `overpass` (15,829 s de 15,903 s) | `deadline_exceeded`, `http_status=502` | `geocode=0,074 s`; duas `upstream_request_failure`; espera local de `1,8 s` (dois backoffs) |

Classificação: **falha externa observada na etapa do provedor**. O
geocoding (Nominatim) respondeu em ~70 ms nas duas execuções; o endpoint
público do Overpass respondeu `HTTP 502 Bad Gateway`, confirmado também por
checagem direta e fora do servidor. A indisponibilidade é do provedor, não do
código do servidor.

Duas lacunas locais foram identificadas e corrigidas, e são a razão de a
falha ter sido indistinguível de uma regressão:

1. **O orçamento publicado e o timer que o aplicava divergiam.** O contexto
   publicava o menor deadline herdado, enquanto o timer local usava o timeout
   nominal; o teardown (`aclose()`) era aguardado *depois* do limite, fora do
   orçamento reservado.
2. **O timeout por tentativa e o backoff de retry não eram limitados ao
   orçamento restante.** Com `OSM_HTTP_TIMEOUT_SECONDS=12` e duas retentativas,
   uma falha transitória do Overpass (502) consumia o prazo inteiro em
   tentativas que o orçamento já não podia sustentar.

Consequência observada: ambas as chamadas terminaram em 15,90 s, **dentro** do
deadline de 16 s configurado, com a etapa (`overpass`), o motivo
(`deadline_exceeded`) e o status HTTP (`502`) agora registrados em
`osm_get_health` — informação que a execução de 23/11 não produzia.

### Aceite operacional

**Pendente.** O critério `ok` com 1–3 POIs normalizados não pôde ser obtido
porque o provedor Overpass estava indisponível durante a validação. O aceite
permanece aberto até haver evidência de sucesso; a política de upstream não foi
alterada e nenhuma rajada de chamadas foi feita para forçar um resultado verde.

### Verificação por fixture (determinística, sem rede)

`tests/test_f8_nearby_stage_diagnosis.py` cobre, com transporte em processo e
cache isolado: falha HTTP do Overpass atribuída a `overpass`/`http_error`,
deadline atribuído a `overpass`, deadline após resposta válida atribuído a
`enrich`, concordância entre orçamento publicado e timer aplicado, teardown
dentro do orçamento, retry não iniciado quando o orçamento não o sustenta,
contagem de outcome única, ausência de conteúdo upstream na telemetria e no
log, e ausência de tarefa órfã após o cancelamento.

---

## Revalidação com cinco buscas distintas (2026-11-23)

Após confirmar que a imagem Positronic em execução corresponde à revisão
refatorada `ba61872b6b27c6a1da248e8e39b61bd265037c64` (imagem
`sha256:b9bf03a08a5e87d4e80c5c9cb6c207d2729d6aac3fe9cf5cb6ecde12ee947b92`),
foram feitas cinco chamadas reais e sequenciais de `osm_find_nearby`, variando
local e categoria:

| # | Local | Categoria solicitada | Resultado |
| --- | --- | --- | --- |
| 1 | Mercado Municipal de São Paulo, São Paulo | `bakeries` | `upstream_error`; sem POIs |
| 2 | Parque Ibirapuera, São Paulo | `food` (normalizada pela ferramenta como `restaurants and food`) | `upstream_error`; sem POIs |
| 3 | Praça da Liberdade, Belo Horizonte | `libraries` | `upstream_error`; sem POIs |
| 4 | Jardim Botânico do Rio de Janeiro, Rio de Janeiro | `tourist_attractions` (normalizada como `tourist attractions`) | `upstream_error`; sem POIs |
| 5 | Estação da Luz, São Paulo | `groceries` | `upstream_error`; sem POIs |

O snapshot de `osm_get_health` após a quinta chamada registrou seis chamadas de
`osm_find_nearby` desde a inicialização observada (incluindo a busca de
referência feita antes destas cinco), todas com outcome `upstream_error` e
nenhum `tool_error`. A última falha foi atribuída a `stage=overpass`,
`reason=deadline_exceeded`, `http_status=502`; `geocode=0,8241 s`,
`overpass=14,4882 s`, `elapsed=15,3124 s` e espera local `overpass=1,8 s`.
A última chamada terminou dentro do prazo configurado de 16 s; cache persistente
e não degradado.

As cinco respostas ao cliente não continham POIs. A telemetria detalhada acima
é o snapshot da falha mais recente, não uma medição individual preservada para
cada chamada. A evidência confirma falhas repetidas no upstream Overpass nesta
batelada, mas não determina a duração da indisponibilidade nem prova que todos
os endpoints ou toda a infraestrutura OSM estejam indisponíveis. O aceite
operacional (`ok` com 1–3 POIs) permanece pendente; não foram feitas chamadas
adicionais após a batelada solicitada.
