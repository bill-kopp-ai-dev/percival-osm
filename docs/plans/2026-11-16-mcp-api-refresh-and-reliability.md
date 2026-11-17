# Plano — atualização das APIs e confiabilidade do Percival OSM MCP

- **Data / revisão:** 2026-11-17 / 1.2
- **Estado:** em execução; F2/F3/F4 concluídas e verificadas, F1 aguarda validação em Python 3.11.
- **Owner / executor / decisor:** Bill Kopp, Positronic Bean Labs.
- **Objetivo:** resolver as três issues abertas e atualizar a integração com os
  provedores realmente utilizados, preservando o contrato MCP e os controles de
  privacidade, segurança e uso dos serviços.
- **Base examinada:** commit `42f1cf2f09739e8fe270118f6e2fd920b3762179`, versão
  `0.5.0`; revisão documental anterior versionada em `eda3de3`. Referências de
  linha abaixo pertencem a essa base de código, não a uma implementação futura.
- **Entradas:** [relatório de 2026-11-12](../reports/relatorio_openstreetmap_apis_autenticacao_2026-11-12.md),
  issues abertas e fontes consultadas diretamente em 2026-11-16 (§10).
- **Acompanhamento:** as caixas deste documento são a fonte de estado da
  campanha — painel por fase em [Painel de execução](#execucao) e tarefas em
  [§4](#sec-4).

<a id="execucao"></a>

## Painel de execução

O plano é executado fase a fase. As listas com caixas em [§4](#sec-4) são a fonte
única de estado: marque cada tarefa ao concluí-la e marque a caixa da fase somente
depois de verificar o aceite daquela fase.

**Estado atual:** F1 implementada, aguardando a validação de startup em Python
3.11; F2, F3 e F4 implementadas e verificadas. Próximo incremento: completar F1
com Python 3.11 ou avançar F5.

- [ ] [F1](#f1) — Migração ORS e baseline portável — P1 — R1, R11
- [x] [F2](#f2) — Cache resiliente e fixtures isolados — P1 — R2
- [x] [F3](#f3) — Orçamento único de prazo, transporte e cancelamento — P1 — R2, R5, R6
- [x] [F4](#f4) — Políticas dos provedores e controle agregado — P1 — R4, R7
- [ ] [F5](#f5) — Resultados compatíveis e procedência — P2 — R7–R9
- [ ] [F6](#f6) — Telemetria dos outcomes MCP — P2 — R3
- [ ] [F7](#f7) — Documentação, pacote e verificação integrada — P2 — R9–R11

**Convenções de acompanhamento**

- `- [ ]` = tarefa pendente; `- [x]` = tarefa concluída e verificada.
- A caixa da fase só fecha após o aceite da fase estar verificado; a evidência
  correspondente é registrada no bloco **Evidência** da fase.
- Concluir uma fase exige atualizar a [matriz de encerramento das issues](#sec-6)
  e mover a issue correspondente para `closed/`.
- As referências a linhas de código (R1–R11) valem para a base `42f1cf2`;
  revalidar após cada fase que tocar aquele arquivo.
- Bill escolheu o Nominatim público para o perfil individual; a configuração
  operacional de cada manager continua distinta da implementação local.
- P1 indica disponibilidade, prazo ou uso efetivo de serviço público; P2 indica
  qualidade ou visibilidade. São prioridades deste plano, não SLAs.

**Mapa do documento**

| Seção | Conteúdo |
|---|---|
| 1 | Conclusão da análise — o que muda nas APIs e por quê |
| 2 | Estado real e lacunas — R1–R11 com evidência no checkout |
| 3 | Escopo e contrato-alvo — o que entra, o que não entra, o que não muda |
| 4 | **Execução — fases, tarefas e critérios de aceite** |
| 5 | Dependências e ordem prática entre as fases |
| 6 | Matriz de encerramento das issues abertas |
| 7 | Estratégia de verificação |
| 8 | Decisões pendentes que afetam a implementação |
| 9 | Handoff e próxima ação |
| 10 | Fontes e limites da pesquisa |

<a id="sec-1"></a>

## 1. Conclusão da análise

**Recomendação:** atualizar ORS imediatamente, corrigir cache/cancelamento e
centralizar os controles de acesso aos provedores antes de ampliar o uso do MCP.
Depois, completar a telemetria de outcomes, a qualidade dos resultados e a
documentação operacional.

A página solicitada, [OSM API][S1], continua apontando para a **Editing API
v0.6**. A v0.7 é uma proposta, não a versão para a qual devemos migrar. A
documentação v0.6 registra mudanças recentes: estatísticas de changesets em
fevereiro/2026, erro de criação de notas por zonas de moderação em maio/2026 e
restrições de visibilidade de uploads GPX em agosto/2026 [S2]. Nenhuma dessas
operações é implementada pelo servidor atual.

O MCP consulta **Nominatim**, **Overpass** e **OpenRouteService (ORS)**; não usa a
Editing API para suas buscas. OAuth 2.0 substituiu Basic/OAuth 1.0a na autenticação
da API principal em 2024 [S3]. Isso não cria uma API Key universal nem torna
OAuth necessário para as consultas públicas atuais do Nominatim/Overpass. A
chave `ORS_API_KEY` é do provedor de rotas; `MCP_OSM_AUTH_TOKEN` autentica o
transporte HTTP do nosso servidor. São credenciais independentes.

A mudança de endpoint que afeta diretamente o código é a do ORS:
`https://api.openrouteservice.org` →
`https://api.heigit.org/openrouteservice`. O aviso do próprio provedor agenda o
desligamento legado para 2026-11-02 a 2026-11-06 e informa que as chaves
existentes funcionam na URL nova [S9]–[S10]. A janela já passou; não houve teste de
disponibilidade ou requisição autenticada nesta análise.

### Como utilizar o relatório

- Adotar a separação de serviços, a identificação do cliente, a atribuição e a
  configuração substituível de endpoints recomendadas no relatório.
- Não transformar seus exemplos de tiles, OAuth, edição ou infraestrutura
  PostGIS em requisitos desta atualização: eles atendem necessidades distintas.
- Interpretar com precisão a seção de Nominatim/LLMs: a política pública [S4]
  restringe sua oferta genérica por plataformas no-code/low-code/vibe-coding e
  exige escolha deliberada do desenvolvedor. Não é uma proibição textual de
  todo uso individual via MCP, tampouco permissão automática para um produto de
  agentes. Para uso compartilhado recorrente, recomendar instância própria ou
  provedor contratado com termos compatíveis.
- Os números de Overpass citados são orientações por instância, não cotas
  garantidas. O manual do operador [S8] e a tabela comunitária de instâncias
  [S7] têm níveis diferentes de detalhe; validar a política aplicável ao backend
  escolhido, sem tomar o maior número disponível como orçamento autorizado.

<a id="sec-2"></a>

## 2. Estado real e lacunas

Nesta seção, `server.py` designa `src/percival_osm_mcp/server.py`.

| ID | Evidência no checkout | Consequência / ação |
|---|---|---|
| R1 | Fallback ORS legado em `server.py:1703`; allowlist em `:151`; exemplos e fixtures também legados. | Migrar host e prefixo, incluindo overrides efetivos na futura integração. |
| R2 | `OsmCache._load/:1614`, `_persist/:1636` e expiração `:1652` não tratam todos os erros de I/O; `aclose/:1908` pode aguardar sem prazo. | Cache degradado não pode derrubar nem reter a resposta MCP. |
| R3 | `get_operational_snapshot/:702` só tem calls/errors/última falha. | Outcomes controlados precisam de contagem separada. |
| R4 | `AsyncTokenBucket` é criado por `OsmSearcher` (`:1806`), com burst padrão 2 (`:213`); cada handler cria outro searcher. | O controle não agrega chamadas sucessivas/concorrentes do servidor; não assegura o máximo público de 1 req/s. |
| R5 | `AsyncTokenBucket.acquire/:1577` captura `CancelledError` e continua esperando. | Há caminho que pode engolir cancelamento; requer regressão específica antes de alegar prazo garantido. |
| R6 | ORS usa SDK síncrono via `asyncio.to_thread` (`:1779`, `:3171`, `:3297`), timeout default 90 s; SDK tem retries próprios. | Cancelar o await não interrompe a thread nem garante cessar a chamada externa. A camada HTTP ORS também não passa pelo controle de redirects/tamanho de `_http_get_json`. |
| R7 | Overpass usa `out geom` sem timeout QL explícito (`:2528`), filtra `limit` só depois e ignora relations no loop (`:2567`); lookup associa só por número de ID (`:2362`). | Carga excessiva possível, relações perdidas e colisão node/way/relation com o mesmo número. |
| R8 | `attempt_ors/:2238` pode guardar haversine como `nav_distance` após erro ORS. `travel_type/:3190,:3316` é inferido do total, não do perfil executado. | Uma aproximação pode parecer distância viária; modo de deslocamento pode ser rotulado incorretamente. |
| R9 | Logs DEBUG contêm query/coordenadas (`:2391–2423`, `:2454–2462`) e `ctx.info` contém entradas (`:3487`, `:3575`, `:3606`). `build_tool_response/:835` não preserva atribuição sistemática. | Sanitização contra injection não equivale à remoção de dados pessoais; falta procedência explícita no contrato de saída. |
| R10 | `osm_primitives.py:263` tenta carregar `docs/security/nanobot-policy.md`, ausente neste checkout; `pyproject.toml` não declara inclusão desse documento. | Resource pode devolver placeholder em vez da política efetiva; verificar também no pacote instalado. |
| R11 | `pyproject.toml` declara Python >=3.11, mas `server.py:38` importa `itertools.batched`, introduzido em 3.12. | Corrigir compatibilidade com 3.11 e testá-la; não aumentar silenciosamente o requisito mínimo. |

Os achados R4–R11 foram de inspeção estática na análise inicial; as falhas de
cache R2 já tinham reprodução registrada na issue. As fases seguem o painel;
os achados de fases posteriores continuam pendentes. Não reabrir
automaticamente as issues históricas de tracking/deadline: testar e tratar os
caminhos adicionais nas fases correspondentes.

**Correções de precisão em evidências anteriores:** JSON corrompido já é
capturado por `_load` (`JSONDecodeError`); faltam outros erros de leitura e a
persistência/expiração. O SDK ORS instalado/lockado é `2.3.3`, cujo
`directions(..., format='json')` monta `/v2/directions/{profile}/json`.
`OrsRouter.calculate_route` não pede GeoJSON e consome `routes[]`. Portanto, a
URL-alvo atual termina em **`/json`**, não `/geojson` como constava na auditoria
da issue ORS. Ambos os formatos existem [S11], mas seus envelopes diferem.

<a id="sec-3"></a>

## 3. Escopo e contrato-alvo

### Incluído

- Correções R1–R11 nos pontos concretos acima, com testes determinísticos.
- Backend Nominatim-compatível e Overpass-compatível substituíveis por ambiente,
  com estado de uso/limites compartilhado por processo e por provedor.
- Cliente ORS assíncrono mínimo para Directions, reutilizando `httpx` e a
  política de URL/timeout/limite de bytes do projeto. Não é um framework de
  provedores nem uma reescrita do servidor inteiro.
- Campos aditivos para outcomes, procedência e qualidade dos resultados; manter
  os nomes e argumentos existentes e as variantes compact/detailed.
- Preservar superfície default de 8 tools, 14 canônicas e 23 aliases opt-in,
  três prompts e dois resources, Python >=3.11, `uv` e layout `src/`.

### Limites desta entrega

Edição OSM, login OAuth, tiles/mapas, novo motor de roteamento e hospedagem de
bases/serviços próprios dependem de necessidade e escolha de infraestrutura
específicas; não são requisitos para resolver estas issues. O plano prepara a
troca de backend sem contratar ou implantar serviços. Código, build e implantação
são marcos distintos; as fases F1–F3 executam código/testes, enquanto build de
candidata e implantação continuam fora do escopo desta campanha.

HTTPS, allowlist explícita, recusa de destinos privados, redirects off,
autenticação HTTP não-loopback, processo non-root, cache confinado e stdout
exclusivo de JSON-RPC continuam requisitos. Uma instância própria em rede privada
exigirá desenho específico de acesso; não remover globalmente a recusa SSRF para
viabilizá-la.

<a id="sec-4"></a>

## 4. Execução — fases, tarefas e critérios de aceite

Cada fase tem uma caixa de conclusão e tarefas individuais marcáveis. A ordem
das fases respeita as dependências do §5. Todas as tarefas começam pendentes.

<a id="f1"></a>

### Fase F1 — Migração ORS e baseline portável

*P1 · lacunas R1, R11 · fecha a issue de migração ORS ao final da fase.*

**Tarefas**

- [x] **F1.1** Trocar fallback para `https://api.heigit.org/openrouteservice` e
  default de allowlist para `api.heigit.org`; manter `ORS_INSTANCE`/`ORS_URL` e
  precedência compatíveis. Normalizar barra final sem perder prefixos de
  instâncias próprias.
- [x] **F1.2** Atualizar `.env.example`, Compose, README, integração e fixtures.
  Compose hoje não encaminha `ORS_INSTANCE`; passar a encaminhar o override
  explicitamente. Host legado só pode ser escolha explícita, não fallback ou
  redirect automático.
- [x] **F1.3** Corrigir o import de `batched` com helper compatível com Python
  3.11, mantendo comportamento e layout. A migração ORS não depende de
  atualizar todo o lock.

**Aceite:** captura HTTP sem internet demonstra POST em
`https://api.heigit.org/openrouteservice/v2/directions/{profile}/json`, coordenadas
`[lon, lat]`, chave apenas no header e parsing de `routes/summary/segments/steps`.
Testar prefixo customizado e host não autorizado. Sem chave, devolver
`provider_not_configured` **antes de geocodificar** os extremos. Import/startup
passa em Python 3.11 e na versão usada pelo container. Esta fase fecha a issue
de migração apenas após implementar e verificar seu escopo; R6 continua em F3.

**Evidência (2026-11-17):** `tests/test_f1_ors_migration.py` e
`tests/test_d6_docker.py`: **32 passed**. Request SDK capturado sem rede comprova
POST no path `/openrouteservice/v2/directions/foot-walking/json`, coordenadas
lon/lat, chave no header sem query, normalização de barras e preservação do
prefixo. Host não autorizado é rejeitado; alias `ORS_URL` funciona. As duas
regressões `tests/test_s4_new_tools.py -k missing_ors_provider` passaram e
comprovam `provider_not_configured` antes de geocodificar. `docker compose config
--quiet`, import/startup local em Python 3.12.15 e `git diff --check` passaram.
Não foi feita chamada ao serviço ORS real. Este ambiente não tem interpretador
Python 3.11; por isso a caixa de conclusão da fase permanece pendente até essa
verificação.

- [ ] **F1 concluída** — aceite verificado e evidência registrada.

<a id="f2"></a>

### Fase F2 — Cache resiliente e fixtures isolados

*P1 · lacuna R2 · prepara o fechamento da issue de cache com F3.*

**Tarefas**

- [x] **F2.1** Adotar cache compartilhado em memória por processo, com
  persistência best-effort: erro de leitura/escrita degrada para memória e não
  invalida um resultado upstream válido. Não registrar I/O esperado como falha
  de segurança.
- [x] **F2.2** Tratar `OSError`, JSON/encoding inválido e estrutura/expiração
  inválida de forma categorizada; preservar validação de confinamento e falhas
  de configuração explícitas como `ValueError`.
- [x] **F2.3** Serializar atualizações entre instâncias para evitar sobrescrever
  entradas com snapshots distintos; escrita atômica, permissões 0600 e
  temporários limpos quando possível. Incluir identidade do backend/formato na
  chave: trocar de serviço não pode reutilizar resultado de outro provedor
  inadvertidamente.
- [x] **F2.4** Expor `cache.mode` (`persistent`/`memory`), estado degradado e
  contadores categóricos de I/O em health. Não incluir conteúdo, caminho novo ou
  query.
- [x] **F2.5** Cobrir persistência e falhas com fixtures `tmp_path`; injetar
  falhas de I/O, inclusive EROFS/EACCES/ENOSPC, sem depender de permissões do
  usuário executor.

**Aceite:** resposta válida continua `ok` com cache em memória após falha de
disco; leitura inacessível, JSON inválido e expiração não escapam como exceção.
Repetir consulta atendida da memória não gera nova chamada. Cache indisponível
não autoriza ignorar limites do provedor. F3 completa o aceite de prazo da issue.

**Evidência (2026-11-17):** `tests/test_f2_cache_resilience.py` cobre cache
compartilhado/mesclado, namespaces por provedor, expiração/estrutura inválida,
falha de escrita EROFS/EACCES/ENOSPC, leitura de JSON inválido e limite de corpo
streaming. A regressão de persistência encontrou e corrigiu a serialização do
envelope. O conjunto focado (F2/F3 e regressões S1/S3/S4/S5/F1) passou: **84
passed** em Python 3.12.12, via container `uv` com lock congelado; em seguida, a
suíte completa passou: **124 passed**. Nenhuma chamada a upstream real. Fixtures
novas usam `tmp_path`.

- [x] **F2 concluída** — aceite verificado e evidência registrada.

<a id="f3"></a>

### Fase F3 — Orçamento único de prazo, transporte e cancelamento

*P1 · lacunas R2, R5, R6 · fecha a issue de cache/cleanup junto com F2.*

**Tarefas**

- [x] **F3.1** Propagar cancelamento do limiter imediatamente (`CancelledError` não
  é retry). Testar cancelamento aguardando lock, limiter, upstream,
  single-flight e close.
- [x] **F3.2** Usar um prazo monotônico para a chamada completa: fila, rate limit,
  retries, processamento e cleanup. Preservar setting `(0, 16]` e reservar
  cleanup dentro do orçamento, sem somar 16 s de execução a múltiplos drains
  de 25 s.
- [x] **F3.3** Recomenda-se trocar apenas o caminho ORS por POST assíncrono
  `httpx`, eliminando thread não cancelável e retries ocultos do SDK. Manter
  JSON, perfis/unidades, `ORS_REQUEST_TIMEOUT` como teto adicional limitado pelo
  saldo da chamada. Remover a dependência SDK/ajustar lock somente se não
  restar uso.
- [x] **F3.4** Reutilizar validação de URL antes do envio, redirects off, tamanho
  máximo medido **durante streaming** e close limitado em todos os caminhos,
  inclusive erro precoce. O GET atual verifica tamanho após `response.content`,
  quando o corpo já foi carregado (`:1946–1990`); estender a correção aos três
  provedores.
- [x] **F3.5** Mapear falhas ORS 401/403/429/5xx e transporte para outcome
  controlado, sem retry de credencial inválida e sem chave/URL/corpo em logs ou
  respostas.

**Aceite:** callbacks FastMCP registrados entregam payload ou propagam
cancelamento de cliente dentro do prazo configurado + pequena tolerância de
scheduler documentada. Fixtures de upstream/close que não terminam não deixam
tasks ou executor workers desta chamada. Resposta excessiva é interrompida sem
bufferizar todo o corpo. Com F2, fecha-se a issue de cache/cleanup.

**Evidência (2026-11-17):** F3 usa cancelamento imediato no limiter; o decorator
reserva até 100 ms (10% em prazos curtos) de cleanup dentro do deadline total
configurado e `OsmSearcher.aclose()` compartilha um limite monotônico entre tasks,
lock e cliente HTTP. ORS de
produção faz POST JSON assíncrono, validado pela política de URL, redirects
desativados e corpo limitado durante streaming; Nominatim/Overpass também usam
streaming. Fixtures verificam cancelamento no limiter, lock, transporte ORS e
cleanup, payload/perfil ORS e outcomes 401/403/429/503 sem retry. Regressões
F1, F2, S1, S3, S4 e S5: **84 passed** em Python 3.12.12 via container `uv`, lock
congelado; a suíte completa passou: **124 passed**. Sem acesso a upstream real.
Decisão registrada em
[ADR de transporte assíncrono](../ADR-2026-11-17-async-upstream-transport.md).

- [x] **F3 concluída** — aceite verificado e evidência registrada.

<a id="f4"></a>

### Fase F4 — Políticas dos provedores e controle agregado

*P1 · lacunas R4, R7 · backend selecionado por Bill.*

**Decisão (2026-11-17):** Bill escolheu o Nominatim público para uso
individual, com agentes pessoais auto-hospedados e poucas consultas semanais.
O limite é agregado por aplicação; processos separados exigem coordenação.

**Resultado:** controles compartilhados por host no processo e seleção explícita
de backend; o limite entre processos exige gateway comum ou outro backend.

**Tarefas**

- [x] **F4.1** Criar contexto mínimo compartilhado por processo/backend para
  limiter, concorrência, cooldown e single-flight. Dois `OsmSearcher` não podem
  reiniciar o orçamento. Coalescer chamadas idênticas de Nominatim/Overpass, com
  cancelamento isolado por consumidor e encerramento quando não houver
  consumidores.
- [x] **F4.2** Para `nominatim.openstreetmap.org`, impor espaçamento >=1 s entre
  partidas, sem burst inicial de duas requisições, concorrência máxima 1 e
  validação que rejeite desativação/aumento desse limite. Aplicar a
  search/reverse/lookup e retries/redirects eventualmente habilitados.
  Instâncias próprias/contratadas usam parâmetros explícitos correspondentes
  aos seus termos.
- [x] **F4.3** Tornar explícita a seleção do backend geocodificador na
  configuração de integração. Recomendação para distribuição genérica: não
  selecionar o serviço público implicitamente; migrar com erro de configuração
  claro e instrução de escolha. O uso individual existente pode ser configurado
  deliberadamente por Bill uma vez, sem criar aceite por chamada. Documentar
  restrições LLM, ausência de SLA e proibição de autocomplete/coleta
  sistemática [S4].
- [x] **F4.4** Agregar por aplicação: um limiter em processo não coordena os dois
  gestores Percival/Positronic ou réplicas. Para compartilharem Nominatim
  público, usar gateway único ou outro backend; não alegar conformidade global
  só por processo.
- [x] **F4.5** Overpass público: concorrência conservadora 1, cache, timeout QL
  explícito menor que o saldo da chamada e `[maxsize]` limitado. Impor teto de
  trabalho/enriquecimento; `limit` de saída não é limite de custo da consulta.
- [x] **F4.6** Respeitar `Retry-After` (segundos/data HTTP) e cooldown
  compartilhado. Em Overpass 429/406, aplicar pausa mínima de 30 s conforme
  orientação da instância [S7]; como supera nosso deadline, retornar
  `upstream_error` com indicação categórica e `retry_after_seconds`, sem dormir
  dentro da tool ou tentar outro host para contornar a limitação. 5xx têm retry
  limitado ao saldo. Não criar fallback automático entre serviços com termos ou
  jurisdições diferentes.

**Aceite:** relógio/HTTP simulados comprovam espaçamento inclusive entre
instâncias novas, single-flight, cache hit sem requisição, cooldown e respeito ao
deadline. Configuração pública inválida falha alto. Não implementar circuito
complexo ou quotas por usuário sem necessidade: cooldown por provedor resolve o
risco constatado; orçamento multiusuário fica para o perfil escolhido.

**Evidência (2026-11-17):** suíte completa **143 passed** em Python 3.12.15,
sem upstream real; fixture de relógio verifica concorrência e espaçamento,
fixtures HTTP verificam single-flight inclusive entre event loops, cancelamento,
cache, cooldown 406/429 e `Retry-After`, timeout/maxsize QL e teto de 20
enriquecimentos. Teste stdio inicializa MCP e chama health com backend explícito.
Controle compartilhado é por processo, não entre managers; não houve deploy.

- [x] **F4 concluída** — aceite verificado e evidência registrada.

<a id="f5"></a>

### Fase F5 — Resultados compatíveis e procedência

*P2 · lacunas R7, R8, R9.*

**Tarefas**

- [ ] **F5.1** Manter `format=json` explícito no Nominatim (continua suportado
  [S5]–[S6]); normalizar `class`/`category` se suportar jsonv2 futuramente. Não
  migrar formato junto com endpoint sem necessidade. Preservar ausência legítima
  de campos, tratar erro semântico/JSON malformado e validar coordenadas
  finitas/faixas.
- [ ] **F5.2** Lookup: associar por `(osm_type, osm_id)`, não apenas ID numérico;
  chunk <=50 [S6]. TTL/chave devem respeitar backend, formato e parâmetros
  relevantes.
- [ ] **F5.3** Avaliar `out center` para POIs e processar nodes, ways e relations.
  Adaptar o normalizador antes da troca; centro de bbox não é entrada nem ponto
  exato do estabelecimento. Rejeitar/indicar resposta parcial com `remark` de
  erro, sem armazená-la como sucesso vazio; preservar timestamp da base quando
  informado.
- [ ] **F5.4** Em falha ORS, manter apenas distância em linha reta com fonte
  explícita; não gravar haversine no cache/campo de distância viária. Perfil
  executado informa `travel_type`; caminhada não deve ser rotulada como
  bicicleta.
- [ ] **F5.5** Acrescentar metadados estruturados de fonte, atribuição
  `© OpenStreetMap contributors`, link de licença e provedor [S12]. Incluir no
  markdown quando apresentado e orientar o consumidor a preservar o crédito; não
  inventar timestamp de atualização da base quando só há data da consulta.

**Aceite:** fixtures de node/way/relation com mesmo ID não se misturam; relations
aparecem; erro/resultado parcial não vira `no_results`. Distância aproximada e
viária são distinguíveis nos modos compact/detailed. Chaves públicas existentes
são preservadas; correções semânticas são descritas em nota de migração.

**Evidência:** _(a registrar)_

- [ ] **F5 concluída** — aceite verificado e evidência registrada.

<a id="f6"></a>

### Fase F6 — Telemetria dos outcomes MCP

*P2 · lacuna R3 · fecha a issue de outcomes controlados.*

**Vocabulário fechado dos outcomes**

| Outcome | Significado |
|---|---|
| `ok` | Resposta bem-sucedida; inclui tools locais de health/version/metrics. |
| `no_results` | Consulta válida vazia; não é falha. |
| `invalid_request` | Solicitação inválida retornada pelo handler. |
| `provider_not_configured`, `config_error` | Capacidade ausente / configuração inadequada. |
| `upstream_error` | Falha externa tratada, inclusive timeout/cooldown. |
| `error` | Falha interna tratada. |
| `exception` | Exceção Python propagada; também incrementa `tool_errors`. |
| `cancelled` | Cancelamento pelo cliente; não simular falha upstream nem engolir cancelamento. |
| `unknown` | Retorno fora do contrato; não converter silenciosamente em sucesso. |

**Tarefas**

- [ ] **F6.1** Adicionar `tool_outcomes[tool][outcome]` no health, usando o
  vocabulário fechado acima.
- [ ] **F6.2** Contar uma chamada e um outcome terminal por invocação MCP
  validada que chegue ao handler, no ponto de instrumentação registrado;
  chamadas internas entre handlers e aliases não podem duplicar métricas.
  Rejeições de schema antes do handler não integram esse denominador.
- [ ] **F6.3** Durante chamadas em andamento, calls pode superar a soma dos
  outcomes; em repouso devem coincidir. O snapshot de `osm_get_health` pode
  preceder o próprio outcome; documentar essa diferença temporal.
- [ ] **F6.4** Nomes/status são enumerados; nenhuma query, URL, coordenada, ID de
  usuário ou credencial vira label. Contadores são em memória por processo, não
  histórico persistente.

**Aceite:** sucesso, vazio, erro controlado, exceção e cancelamento contados via
callback MCP real, incluindo alias e delegação `osm_find_nearby_store` →
`osm_find_place`. `tool_errors` mantém exclusivamente exceções propagadas.
Nomes/status são enumerados; nenhuma query, URL, coordenada, ID de usuário ou
credencial vira label. Contadores são em memória por processo, não histórico
persistente. Fecha a issue de outcomes.

**Evidência:** _(a registrar)_

- [ ] **F6 concluída** — aceite verificado e evidência registrada.

<a id="f7"></a>

### Fase F7 — Documentação, pacote e verificação integrada

*P2 · lacunas R9, R10, R11.*

**Tarefas**

- [ ] **F7.1** Remover entradas pessoais de logs DEBUG/`ctx.info` e erros com
  traceback upstream; manter tool, provedor e categoria operacional. Testar
  redaction com dados sentinela, inclusive URLs com tokens no path/query de
  provedores.
- [ ] **F7.2** Disponibilizar política real no resource existente, empacotada sob
  `src/` e incluída no wheel. Validar no pacote instalado; não usar lookup no
  checkout como prova de que o resource estará no container.
- [ ] **F7.3** Alinhar README, `.env.example` (documentação, sem carregamento de
  arquivo), Compose, perfil de integração, prompts/resources e
  `servers/percival-osm/{server.yaml,tools.json,readme.md}` aos novos contratos.
  Atualizar a documentação de burst antigo, auth e limites de uso.
- [ ] **F7.4** Revisar dependências pelo risco concreto: lock consistente com
  transporte escolhido, Python 3.11 e build. Evitar atualização indiscriminada
  ou MCP 2.x nesta campanha. Definir versão de release somente após estabilizar
  o escopo.

**Aceite:** testes funcionais focados por fase e uma suíte integrada ao final;
handshake stdio/HTTP e policy resource do pacote instalado passam sem internet.
Tools/list mantém a exposição configurada e stdout só JSON-RPC. Para uma futura
candidata Docker que altere runtime, usar o smoke existente uma vez e evidência
de imagem correspondente, sem duplicar a mesma prova em vários gestores.

**Evidência:** _(a registrar)_

- [ ] **F7 concluída** — aceite verificado e evidência registrada.

<a id="sec-5"></a>

## 5. Dependências e ordem prática

```text
F1 (ORS + Python) ────────────────┐
F2 (cache) → F3 (I/O e prazo) ───┼→ F4 (controle agregado) → F5 (resultados)
                                └→ F6 (outcomes) ─────────────┬→ F7 (integração)
F4: seleção/configuração de backend por Bill ──────────────────┘
```

Executar em incrementos pequenos, reutilizando testes/evidências do mesmo código.
F1 pode ser implementada primeiro para reduzir o risco do endpoint legado. F2/F3
removem o bloqueio da suíte; F4 torna o uso do backend público controlado. F5/F6
completam contrato e observabilidade. Não usar serviço público real como fixture
de falha, teste de carga ou requisito da suíte.

Não há estimativa de calendário comprometida: F3/F4 concentram a incerteza de
ciclo de vida e compatibilidade. Reestimar após suas regressões focadas, antes de
agendar uma atualização de runtime.

<a id="sec-6"></a>

## 6. Matriz de encerramento das issues

| Issue | Trabalho necessário | Evidência para fechar |
|---|---|---|
| [Migração ORS](../issues/2026-11-04-ors-api-endpoint-migration.md) | F1 | URL final POST/json correta, prefixo/override/allowlist, exemplos coerentes e ausência de chave controlada. |
| [Cache / cleanup](../issues/closed/2026-11-16-cache-persist-failure-escapes-as-raw-exception.md) | F2 + F3 concluídas | Falhas de I/O e cache inválido sem exceção crua; close/cancelamento dentro do orçamento; regressões isoladas em `tmp_path`. Issue movida para `closed/` após 84 testes focados aprovados em 2026-11-17. |
| [Outcomes controlados](../issues/2026-10-31-controlled-tool-failure-outcomes-not-counted.md) | F6 | Matriz de status, exceção e cancelamento via callbacks MCP; sem dupla contagem ou labels pessoais. |

Manter cada issue aberta até obter sua evidência; então registrar resultado e
mover para `closed/`, ajustando os links deste plano. Encerrar o plano somente
após F1–F7, ou revisão explícita de escopo que indique os itens adiados.

<a id="sec-7"></a>

## 7. Estratégia de verificação

- **Durante a implementação:** menor conjunto de regressões que cubra o risco
  da fase, com HTTP/relógio/I/O simulados; execução Python via `uv`.
- **Integração final:** `uv run pytest -v`, usando `TMPDIR`/`--basetemp` gravável
  quando o ambiente exigir; sem o plugin temporário da auditoria. O resultado
  anterior (`100 passed` com redirecionamento de cache) é baseline histórico,
  não evidência das mudanças propostas.
- **Compatibilidade:** import/startup em Python 3.11 e teste dos caminhos
  alterados no Python da imagem; pacote instalado entrega resource real.
- **Runtime alterado:** smoke stdio/HTTP com mocks ou respostas locais
  determinísticas; health não gera sondagens aos provedores. Reutilizar esse
  resultado para a mesma candidata, sem inspector obrigatório adicional.
- **Disponibilidade real ORS:** eventual consulta pontual com chave já entregue
  pelo ambiente seguro testa o serviço externo; falta de chave não impede testes
  locais nem autoriza guardar credenciais no repo/chat. Não prometer disponibilidade
  real com base apenas em fixtures.

Na análise inicial foram feitas leitura de código e consultas à documentação;
nenhum teste, benchmark, build ou deploy tinha sido executado naquela etapa.
Evidências posteriores de F1–F4 estão registradas em cada fase acima. Não foram
feitos benchmark, build de release ou deploy nesta execução.

<a id="sec-8"></a>

## 8. Decisões pendentes que afetam a implementação

1. **Instância em rede privada:** se for escolhida no futuro, definir acesso restrito por
   gateway/rede e política de destino específica. Não abrir uma exceção genérica
   para hosts privados ou ampliar allowlist por descoberta automática.

O transporte assíncrono ORS e o ciclo de vida compartilhado são recomendações
arquiteturais deste plano, ainda propostas. Ao adotá-los na implementação,
registrar a decisão durável em um único ADR; não exigir ADR para cada correção.

<a id="sec-9"></a>

## 9. Handoff e próxima ação

Próximo incremento recomendado: validar startup em **Python 3.11** para fechar
F1 ou avançar F5. F2/F3/F4 estão concluídas. Bill é o único decisor; não há revisão
externa ou aceite duplicado como condição de conclusão.

O acompanhamento de execução está no [Painel de execução](#execucao) e nas
caixas de [§4](#sec-4): cada tarefa concluída é marcada individualmente e a
caixa da fase fecha somente com o aceite verificado.

<a id="sec-10"></a>

## 10. Fontes e limites da pesquisa

Consultadas em **2026-11-16**. O wiki documenta o ecossistema e pode divergir do
serviço em operação; políticas OSMF e anúncios do operador prevalecem para uso e
migração. A página ORS de referência consultada identifica o backend como
`10.2.0-SNAPSHOT`; não significa que o serviço hospedado execute essa versão.
Usamos seu contrato JSON/GeoJSON junto ao aviso específico de migração de host.

- **S1:** [OSM API][S1], revisão apresentada `oldid=3079265`, editada em 2026-09-14.
- **S2:** [OSM API v0.6][S2], versão atual, changelog e autenticação.
- **S3:** [Atualização de autenticação de 2024][S3].
- **S4:** [OSMF — Nominatim Usage Policy][S4], inclusive “Usage in LLMs”.
- **S5:** [Nominatim Search][S5], [Reverse][S5R] e [Output][S5O]; manual servido
  como `5.3.3`. Não implica versão de toda instância pública/privada.
- **S6:** [Nominatim Address Lookup][S6], IDs tipados e máximo de 50 por lote.
- **S7:** [Overpass API][S7], tabela de instâncias e orientações de uso.
- **S8:** [Overpass — Commons][S8], manual do operador: quotas, slots e timeout.
- **S9:** [ORS — depreciação do host legado][S9], anúncio de 2026-04-28 atualizado.
- **S10:** [ORS — redução de quota e cronograma][S10], anúncio de 2026-08-27 atualizado.
- **S11:** [ORS — Requests and Return Types][S11], POST JSON versus GeoJSON.
- **S12:** [OSMF — Attribution Guidelines][S12], revisão `oldid=14786`.
- **S13:** [OSMF — Editing API Usage Policy][S13], finalidade distinta de leitura genérica.

[S1]: https://wiki.openstreetmap.org/wiki/API
[S2]: https://wiki.openstreetmap.org/wiki/API_v0.6
[S3]: https://wiki.openstreetmap.org/wiki/2024_authentication_update
[S4]: https://operations.osmfoundation.org/policies/nominatim/
[S5]: https://nominatim.org/release-docs/latest/api/Search/
[S5R]: https://nominatim.org/release-docs/latest/api/Reverse/
[S5O]: https://nominatim.org/release-docs/latest/api/Output/
[S6]: https://nominatim.org/release-docs/latest/api/Lookup/
[S7]: https://wiki.openstreetmap.org/wiki/Overpass_API
[S8]: https://dev.overpass-api.de/overpass-doc/en/preface/commons.html
[S9]: https://ask.openrouteservice.org/t/deprecating-api-openrouteservice-org-in-favour-of-api-heigit-org/7912
[S10]: https://ask.openrouteservice.org/t/reducing-the-quota-of-deprecated-api-api-openrouteservice-org/8013
[S11]: https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/requests-and-return-types
[S12]: https://osmfoundation.org/wiki/Licence/Attribution_Guidelines
[S13]: https://operations.osmfoundation.org/policies/api/
