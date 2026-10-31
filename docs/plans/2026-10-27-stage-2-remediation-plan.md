# Stage-2 — Remediação do Percival OSM MCP

**Data / revisão:** 2026-10-31 / 1.4 (emissão original: 2026-10-27 / 1.0).
**ID / estado:** S2-OS / 13/13 ações técnicas qualificadas localmente. A-013 repinado e verificado nos dois gestores; Bill autorizou remover a imagem anterior, então não há rollback local para o pin Percival. Distribuição externa não integra este escopo.
**Checkout executor:** `/home/bill/Projects/percival-osm`.  
**Owner e decisor único do produto e da infraestrutura IaC:** Bill Kopp,
Positronic Bean Labs (`bill.kopp.dev@gmail.com`).
**Site da empresa:** `labs.positronicbean.com` (em desenvolvimento).
**Execução:** Bill é o único owner, executor, decisor e assinante. Interfaces de
gestão são apenas o meio operacional para alterar runtimes geridos; não criam uma
etapa de aprovação adicional.

## 1. Objetivo e fontes

Tratar os 13 achados da **seção 6** do
[relatório OSM](../../../positronic-bean-IaC/docs/reports/2026-10-27-percival-osm-iac-readiness-report.md#6-achados-issues-e-inconsistências),
com ações e revalidação das seções 7/9: 13 ações (2 P1, 4 P2, 7 P3), sem P0.
Baseline e HEAD na emissão: `06484259a3bb5371c5c1551dcab0c23ccc166479`.
Há exclusões documentais locais preexistentes em `docs/`, incluindo segurança,
deployment e nota F3; preservá-las. `R-05` definiu `pblabs-mcp-index` como
tracker F3 canônico por image ID; não restaurar uma cópia local concorrente.

[Coordenador stage-2](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md)
— retorno S2-OS, seções 3 e 7. Fontes comuns:
[consolidação](../../../positronic-bean-IaC/docs/reports/2026-10-26-stage-1-consolidated-readiness-report.md)
e [D-01..D-06](../../../positronic-bean-IaC/docs/decisions/2026-10-27-iac-stage-1-scope-and-pilot-decisions.md).

Emissão documental; execução futura local. Cada aceite deve ter a evidência
técnica suficiente para o risco daquela ação; não repetir validações nem exigir
aprovações cruzadas para a mesma decisão. Preservar layout `src/`, tools/aliases,
prompts/resources, guards HTTPS/URL/credenciais, rate limit e conteúdo não confiável.
Não é o piloto D-01. Provas de falhas de upstream usam fixtures. Operações externas
devem permanecer dentro do escopo solicitado; se o pedido identificar claramente
alvo e impacto, não solicitar uma segunda aprovação para a mesma operação.

## 2. Preparação e decisões

- [x] Ler instruções/README/CI/config atuais; registrar SHA/worktree/toolchain e
  reconciliar docs removidos sem restaurar ou substituir alterações do operador.
- [x] Owner decidiu A-001: sem `ORS_API_KEY`, retornar status explícito
  `provider_not_configured`, nunca distância haversine como rota. Decisão alinhada
  com a recomendação de preservar precisão.
- [x] Bill decidiu em 2026-10-29 que redirects não serão seguidos automaticamente:
  cada destino será validado antes de qualquer conexão e destinos fora da allowlist
  serão rejeitados. Fixtures de regressão confirmam zero requisições ao destino
  bloqueado e seguimento apenas do destino permitido validado.
- [x] Atualização de decisão do operador em 2026-10-29: `R-10` supersede `R-02`
  quanto ao default do broker Percival, que permanece amplo conforme B14/B22/B23–B25.
  O perfil OSM deve declarar explicitamente `mounts=[]` se não exigir bind; binds
  estreitos continuam explícitos; mudanças de perfil ficam limitadas ao escopo
  definido por Bill, sem auditoria ou aceite redundante.
  `R-03` remove estimativas de esforço, custo e prazo; `R-05`
  centraliza o tracker F3 por imagem em `pblabs-mcp-index`, com referências nos
  checkouts; `R-06` adota o contrato de metadados externo e `pblabs.app.yaml`
  como extensão operacional versionada, com o índice PBLabs como destino, sem
  dependência do Docker MCP Catalog; `R-07` exige VEX por CVE associado ao image
  ID e assinado pelo owner, com CVEs da imagem base tratados por herança; `R-08`
  fixa pin aprovado e janela única datada para operações que dependem dela.
- [x] Bill decidiu em 2026-10-29 os critérios de build reproduzível (A-004), a
  semântica de erros e lifecycle (S2-C01), a nota OSM versionada e o perfil de
  mounts (A-008), o tratamento mínimo de CVEs/cache legado (A-011) e a sequência
  de inventário read-only e repin condicional (A-013). Naquela data, implementação
  e evidências continuavam abertas; o estado atual consta da tabela de execução.
- [x] `R-11` (2026-10-29): Trivy é o scanner padrão e está instalado; o agente
  pode executá-lo autonomamente para scans locais quando necessário, cobrindo
  todas as severidades, atualizando a DB e registrando scanner/DB, SHA e image ID.
  Preferir TAR do candidato limpo, sem Docker socket. Scan não assina VEX; a
  decisão de risco continua com o owner.
- [x] Registrar as decisões operacionais S2-C01; a qualificação local de sinais e
  lifecycle consta na seção 6.
- [x] Materializar e validar os metadados operacionais locais OSM 0.2 conforme
  R-06; schema e draft do índice passaram `scripts/catalog.py --check`.
- [x] Repinar o runtime Percival OSM: update confirmado na UI e inventário
  read-only posterior confirma pin no candidato
  `sha256:3e6cc7ddf291ec5f06aa86bd21baab7ef7a6648d9f48968b7dae421cceadc8bc`.
  Bill autorizou remover o pin anterior `sha256:67f8ada639897af9ca4ca8f02e38932376f73f454db76028a3920f076011cfeb`; a remoção elimina rollback local para esse ID, risco explicitamente aceito.

### 2.1. Decisões do owner — 2026-10-29

Bill Kopp é o único owner, executor, decisor e assinante do servidor MCP Percival
OSM e da infraestrutura IaC da Positronic Bean Labs. As decisões abaixo são
vinculantes; gestores e interfaces são meios operacionais, não aprovadores.

| ID | Decisão de Bill | Limite / próximo passo |
|---|---|---|
| A-003 | Desativar seguimento automático de redirects; validar cada destino antes de conectar e rejeitar destinos fora da allowlist. | Criar fixture que prove zero requisições ao destino bloqueado e verificar o caminho permitido. |
| S2-C01 | Falhas de upstream nunca serão apresentadas como resultado vazio. O shutdown será observável, terá prazo limitado para drenar chamadas em voo e depois cancelá-las, sem tarefas órfãs. Mounts serão declarados por aplicação. | Implementar e fazer uma verificação focada do comportamento; não bloqueia correções locais independentes. |
| A-004 | Comparar builds do mesmo SHA, com mesmo builder, bases e argumentos. Aceite exige image ID e digests de camadas idênticos; divergência exige comparação por arquivo e causa registrada. | Executar dois builds limpos do mesmo candidato e guardar a comparação. |
| A-008 | Criar nota OSM versionada sem restaurar documentos excluídos. Declarar `mounts=[]` sem necessidade de bind; caso contrário, documentar somente mounts estreitos e justificados. | Atualizar a documentação contra o perfil efetivo e preservar as exclusões preexistentes. |
| A-011 | Fazer scan Trivy do candidato limpo (`R-11`) e registrar resultado e image ID no tracker F3 canônico. Marcar exceções antigas como obsoletas quando não aplicáveis ao scan; criar VEX assinado por Bill apenas para CVEs encontrados. Documentar o cache legado como migração best-effort, sem mudança de código ou migração agora. | Atualizar a DB quando necessário; executar o scan autonomamente no candidato limpo; registrar versão/data da DB, SHA, image ID e resultado no tracker; incluir nota curta sobre compatibilidade best-effort do cache. |
| A-013 | Fazer inventário somente leitura dos runtimes incluídos no escopo e repin apenas onde necessário, em uma única operação. | Preparar candidato de SHA limpo; o pedido de Bill deve identificar imagem, runtimes e janela. Registrar o estado anterior/posterior e rollback uma vez. |

## 3. Backlog integral e critérios de aceite

Prioridades de origem preservadas. O estado de execução consta no registro da
seção 6; esta tabela mantém o backlog e os critérios de aceite.

| Ação | Achado / P | Trabalho e áreas previstas | Dependência / responsável pela execução | Aceite verificável |
|---|---|---|---|---|
| A-001 | F-001 / P1 | Alinhar ORS/fallback e docs em server/entrypoint/server.yaml/README | Decisão de Bill registrada; falta validar os fluxos com fixture | Sem chave: status/mensagem de configuração ou fallback honestamente rotulado; com chave fixture, rota correta; nenhuma falsa afirmação de no_results |
| A-002 | F-002 / P1 | Distinguir falha de upstream de resultado vazio em payload de tools | S2-C01 como referência, sem bloquear fix local | Fixture diferencial comprova que resposta 200 vazia retorna `no_results`, enquanto indisponibilidade/timeout, 429/5xx e URL bloqueada retornam erro explícito (nunca `no_results`); payloads e logs concordam em cada caminho e por ferramenta |
| A-003 | F-003 / P2 | Manter redirects desativados por default; validar cada destino antes de qualquer requisição manual de redirect e rejeitar destinos fora da allowlist | Decisão de Bill registrada em 2026-10-29 | Fixture comprova zero requisições ao destino bloqueado e funcionamento do destino permitido; verificar tanto `follow_redirects=false` no cliente HTTP quanto a configuração efetiva `http_follow_redirects=false` (redirects manuais também ficam desativados) |
| A-004 | F-004 / P2 | Normalizar timestamps/metadados uv/logs apt/dpkg/ldconfig no build | Mesmo SHA, builder, imagens-base e argumentos; etapa 2 IaC | Dois builds limpos têm image ID e digests de camadas idênticos; se divergirem, comparar arquivos e registrar causa |
| A-005 | F-005 / P2 | Derivar versão do pacote em SERVER_VERSION e serverInfo | Fonte única de versão | Status/version/initialize e labels concordam com pacote (0.5.0 somente se vigente), não SDK |
| A-006 | F-006 / P2 | Passar VERSION/GIT_SHA como build args no wrapper e atualizar metadata a cada build candidato | Candidato limpo | OCI labels registram a versão do pacote e o SHA completo do candidato; verificado no image ID local. |
| A-007 | F-007 / P3 | Corrigido no código deste checkout: captura de nome/categoria por valor no gerador de aliases | Sem dependência externa | Qualificado: `test_legacy_aliases_increment_only_the_called_alias` comprova contadores isolados para aliases chamados. |
| A-008 | F-008 / P3 | Criar nota OSM versionada com UID, upstreams, perfil de mounts e semântica de rota; não restaurar documentos excluídos | A-001; perfil OSM e `R-10`; decisão de Bill registrada em 2026-10-29 | Nota atualizada com perfis distintos: Positronic `mounts=[]`; Percival sob default amplo do broker `R-10`. Inventário read-only de 2026-10-31; valores de contato não reproduzidos. |
| A-009 | F-009 / P3 | Implementado no código deste checkout: rejeitar `NOMINATIM_URL` terminada em `/search` na validação comum de configuração | Política fail-fast | Qualificado: container com URL `/search` encerra com exit 1 e mensagem nomeada; candidato limpo inicia com configuração válida e expõe 37 tools; validação comum ocorre antes do transporte/tools. |
| A-010 | F-010 / P3 | Implementado no código deste checkout: validar presença, formato, conversão e finitude da bounding box de Nominatim | Fixtures de schema | Qualificado: fixture de bbox incompleta retorna `upstream_error`, sem `KeyError`; fixture válida usada no caminho normal; suíte completa passou. |
| A-011 | F-011 / P3 | Fazer scan Trivy do candidato limpo (`R-11`); reconciliar exceções antigas no tracker F3 canônico; documentar migração best-effort do cache, sem mudança de código/schema agora | Trivy disponível para execução autônoma; Bill (owner único) assina VEX; `R-05`/`R-07` | Fechado localmente: scan ligado ao image ID em `pblabs-mcp-index/servers/osm/security-scan-312964c-3e6cc7dd.json`; 0 vulnerabilidades, nenhuma exceção OSM existente no índice a reconciliar, nenhum VEX necessário. Nota de cache consta na integração. |
| A-012 | F-012 / P3 | Tratar SIGTERM/SIGINT com encerramento observável da aplicação, fechamento do cliente HTTP e log | S2-C01/S2-NB A-012 para compatibilidade; o init do launcher encaminha sinais, mas não comprova o lifecycle da aplicação | Qualificado localmente: HTTP SIGTERM→exit 143 e SIGINT→exit 130, ambos com log de shutdown completo; teste confirma drain limitado, cancelamento sem tarefas órfãs; verificação focada confirma fechamento do cliente HTTP. |
| A-013 | F-013 / P3 | Fazer inventário somente leitura dos runtimes no escopo; repin apenas onde necessário, numa única operação | Inventário read-only concluído; update Percival executado pela UI no candidato limpo durante janela autorizada; `R-08`. Bill autorizou remoção do pin anterior após ser informado de que isso elimina rollback local. | Positronic `osm`: image ID `sha256:805b81ae60cb6726dc9d0590641abb0432557f96ed28ca5a617d7408a81f738e`, label `b39d027`, bridge, `mounts=[]`, ativo. Percival `osm`: image ID `sha256:3e6cc7ddf291ec5f06aa86bd21baab7ef7a6648d9f48968b7dae421cceadc8bc`, label revision `312964c9e8b0da41dc3e8ed3efca6cfd33362fb6`, container ativo, init e mounts efetivos do broker preservados. UI reportou MCP connected/37 tools; inventário confirmou pin e container. Imagem anterior `sha256:67f8ada639897af9ca4ca8f02e38932376f73f454db76028a3920f076011cfeb` removida a pedido; rollback local não foi testado e deixou de estar disponível, conforme decisão explícita do owner. |

### 3.1. Metadados operacionais locais

O draft OSM PBLabs 0.2 está em `pblabs-mcp-index/servers/osm/pblabs.app.yaml`.
O schema e os drafts foram validados por `scripts/catalog.py --check` (catálogo
intencionalmente sem entradas). O escopo desta campanha termina no draft e na
validação local.

Para cada CVE encontrado no scan do candidato, `R-07` exige um VEX associado ao
image ID e assinado por Bill; CVEs da imagem base seguem a postura por herança.
O scan do candidato está registrado em arquivo por image ID, sem CVEs; nenhum
VEX foi necessário.

Esse complemento não aumenta as 13 ações originais. F-002 contém hipótese de
causa: teste diferencial de upstream vazio/falhando deve confirmar o fluxo, sem
assumir causalidade só pela mensagem. Bill decide o hardening do perfil OSM;
eventuais mudanças no runtime são aplicadas por Bill usando a interface adequada,
dentro do escopo solicitado.

## 4. Lotes e dependências

1. **OS-1:** A-001/A-002/A-003, que afetam as conclusões do agente e a fronteira
   de rede; A-009/A-010 podem acompanhar o mesmo caminho de validação.
2. **OS-2:** A-005/A-007/A-008/A-011/A-012, compatibilidade e cache/lifecycle.
3. **OS-3:** A-004/A-006, candidato e artefatos de build; receber inventário
   read-only dos runtimes e executar A-013 somente onde o repin for necessário,
   em uma operação dentro do escopo solicitado por Bill.

Riscos: novas classes de erro/schema quebram consumidor, redirects seguros podem
recusar upstream antes tolerado, e a migração best-effort do cache legado pode
descartar entradas incompatíveis. Registrar o comportamento observado sem exigir
migração de schema nesta ação. `R-03` remove a exigência de estimar esforço, custo
ou prazo.
Piloto e replicação não são execução deste plano documental.

## 5. Qualificação proporcional

- [x] Executar os testes/checks relevantes às mudanças realizadas; usar a suíte
  completa para mudanças amplas ou quando uma regressão transversal for plausível.
- [x] Para mudanças de build/metadados, validar o candidato e os metadados
  afetados. Para mudanças de transporte/runtime, validar handshake e chamada
  segura no transporte alterado. Não repetir a mesma validação em interfaces
  diferentes sem discrepância concreta.
- [x] Usar fixtures para os caminhos de vazio, falha, schema incompleto, chave
  ausente e redirect que forem tocados; não gerar tráfego público em failure
  injection.
- [x] Fazer o inventário somente leitura dos runtimes incluídos no escopo de
  A-013. O repin necessário no runtime Percival permanece condicionado ao pedido
  específico de Bill; verificações de catálogo, provider real ou
  piloto ficam fora deste plano, salvo quando uma entrega depender delas.

Registrar o resultado concisamente junto à ação correspondente. Ausência de
evidência de runtime/catalog não bloqueia aceites locais que não dependam dela;
reportar apenas o que foi efetivamente verificado.

## 6. Penúltima etapa — documentar execução neste plano

- [x] Manter um registro curto das ações relevantes: data, SHA quando aplicável,
  mudança, evidência suficiente e pendência concreta. Não registrar comandos ou
  artefatos redundantes.
- [x] Atualizar o coordenador IaC apenas se a sincronização fizer parte do escopo
  desta execução; preservar a coleta original e identificar limites dos mocks.

| Data / owner | Ações / achados | SHA inicial → final | Mudanças / evidências locais | Resultado / V-* / pendências |
|---|---|---|---|---|
| 2026-10-27 / bill (owner), Positronic (execução local) | A-001 parcial, A-003 parcial, A-005 local, A-006 parcial, A-007 local, A-009 local, A-010 parcial; A-002/A-004/A-008/A-011/A-012/A-013 pendentes | `4a71108f3980c033df1a7f9c331402e688ed213a` → SHA de trabalho não commitado | A-001 decidido e comportamento/docs ajustados; A-003 valida `Location` antes de seguir; A-005 deriva versão do pacote e injeta no serverInfo, verificado pelo protocolo MCP (`serverInfo.version=0.5.0`); A-006 wrapper passa VERSION/GIT_SHA/SOURCE_DATE_EPOCH; A-007 captura nome por valor; A-009 falha no boot com URL `/search` (container `exit 1`, mensagem nomeada); A-010 trata bbox ausente/malformado. `./.venv/bin/python -m pytest -v`: 77 passed; compileall, `bash -n` e diff-check aprovados. Build local `scripts/docker-build.sh stage2-candidate`; smoke: non-root, env guard, MCP 37 tools, HTTP auth/health/shutdown aprovados. Imagem local `sha256:bb4d27903912928e51e0129d8202adef5135ff4e8b899268643091d507a11f63`, version `0.5.0`, revision label `unknown` (worktree sujo), created `2026-10-28T00:24:13Z`. `uv` CLI indisponível; executáveis `.venv` usados. | Parcial. A-002 precisa diferenciar falha, 429/5xx/timeout de vazio em todos os payloads. A-003 ainda precisa fixture provando zero requests ao destino bloqueado. A-004 precisa comparação real de builds limpos. A-006 requer candidato de SHA limpo para fechar o vínculo. A-008 a nota de integração não existe no worktree e as exclusões foram preservadas; A-011 tracker local de exceções não existe, remoção depende de reconciliação do owner de segurança; A-012 graceful shutdown pendente. A-013 depende de gestores e operação própria autorizada. S2-C01 continua pendente; formato/schema foi decidido em `R-06`, mas materialização e validação continuam pendentes; `R-03` remove a exigência de estimar esforço, custo ou prazo. Retorno externo pendente. |
| 2026-10-29 / Bill Kopp (owner e decisor único) | Decisões registradas para A-003, S2-C01, A-004, A-008, A-011 e A-013; execução e provas continuam pendentes | Atualização documental; sem alteração de código ou runtime | Owner: Bill Kopp, Positronic Bean Labs; `bill.kopp.dev@gmail.com`; `labs.positronicbean.com` em desenvolvimento. Redirects sem seguimento automático; semântica de erro/lifecycle definida; critério de build reproduzível fixado; nota OSM versionada sem restaurar exclusões; scan+tracker e cache best-effort para A-011; inventário read-only seguido de repin condicional para A-013. | Decisões não equivalem a aceite de execução. Pendentes: fixtures, builds limpos, scan no candidato limpo, atualização do tracker e nota do cache, revisão dos runtimes por leitura e autorização explícita de Bill para eventual repin numa única janela. |
| 2026-10-30 / Bill Kopp (owner, executor, decisor e assinante único) | Simplificação do processo e do escopo de verificação | Política aplicada ao plano | Positronic Bean Labs; `bill.kopp.dev@gmail.com`; `labs.positronicbean.com`. Uma solicitação explícita de Bill autoriza a operação descrita; interfaces de gestão não são aprovadores. Verificações devem ser focadas, sem duplicar aceites, revisões cruzadas ou artefatos para a mesma decisão. | Esta atualização substitui exigências anteriores de aprovação/retorno repetido. Preservam-se verificações técnicas relevantes e evidências necessárias às entregas; sincronização externa só bloqueia quando fizer parte do escopo ou for dependência concreta. |
| 2026-10-31 / Bill Kopp (owner); Positronic (revisão documental; fotografia anterior, supersedida pelo registro 11:21Z abaixo) | Reconciliar nota de integração, inventário read-only e status do candidato com o estado documentado | `b39d027be449d73f90900ddd25465f575a949ba7` → worktree com alterações locais | `docs/integrations/percival-osm.md` registrava UID/GID `10001:10001`, mounts vazios e inventário de 2026-10-30: runtime `osm` na revisão 4, imagem `sha256:67f8ada639897af9ca4ca8f02e38932376f73f454db76028a3920f076011cfeb`, rede `bridge`, configuração revisão 1. O contato efetivo diferia do contato do projeto. Nota também documentava migração best-effort de cache legado. | Fotografia histórica, substituída pela atualização do inventário de ambos os gestores e pelas evidências de build, teste e scan registradas abaixo. |
| 2026-10-31T12:01Z / Bill Kopp (owner); Positronic (execução local e inventário read-only) | Qualificação das ações locais, scan e inventário dos dois gestores | `312964c9e8b0da41dc3e8ed3efca6cfd33362fb6`; worktree limpo no build | `./.venv/bin/python -m pytest -v`: 88 passed. Buildx `--no-cache`, linux/amd64, mesmo builder/bases/args e sem attestations default: duas execuções produziram image ID `sha256:3e6cc7ddf291ec5f06aa86bd21baab7ef7a6648d9f48968b7dae421cceadc8bc` e os mesmos seis layer digests. OCI labels: version `0.5.0`, revision SHA completo acima. Smoke passou: non-root, guard de env, MCP initialize/tools/list (37 tools), HTTP auth/health, SIGTERM exit 143. Startup com `NOMINATIM_URL` em `/search` saiu 1 com erro nomeado; SIGINT em container HTTP autenticado saiu 130 com shutdown completo. Fixtures e verificações focadas confirmam erros upstream em `navigate`/`directions`, cancelamento sem tarefa órfã e fechamento do cliente HTTP. Trivy 0.76.1, DB v2 reportada em 2026-10-30T13:06:28Z: 0 vulnerabilidades no candidato exato. `uv` do projeto não está no PATH; suíte executada pelo `.venv` OSM. `pblabs-mcp-index/servers/osm/security-scan-312964c-3e6cc7dd.json` associa scan/image ID; `scripts/catalog.py --check` validou o draft PBLabs 0.2. | A-001–A-012 qualificados localmente. Positronic `osm` ativo/global rev 5/config rev 3, mounts vazios; o contato foi atualizado e `discover` passou. Percival `osm` permanece ativo na imagem antiga com worktree dirty, revisão `311a49d` e código divergente. Bill autorizou candidato e janela 08:30–08:45 America/Sao_Paulo, mas a janela expirou sem mutação: `uv run` falhou porque o `.venv` existente aponta para Python ausente e o gerenciador não pôde remover `.venv/CACHEDIR.TAG` (`Permission denied`); não foi usado endpoint sem autenticação nem a interface do gestor Positronic. Alterações locais anteriores do índice foram preservadas; somente o novo relatório foi criado. |
| 2026-10-31T12:17Z / Bill Kopp (owner); Positronic (verificação read-only e limpeza autorizada) | Confirmar update Percival e eliminar imagem anterior após confirmar ausência de referências | Candidate SHA `312964c9e8b0da41dc3e8ed3efca6cfd33362fb6`; Percival pin `sha256:67f8ada6…` → `sha256:3e6cc7dd…` | Inventário do Percival: container ativo em `sha256:3e6cc7dd…`, revisão `312964c`, config pointer atualizado; UI mostrou connected e 37 tools. Positronic continua em `sha256:805b81…`. Imagem anterior `sha256:67f8ada639897af9ca4ca8f02e38932376f73f454db76028a3920f076011cfeb` não tinha refs de container/config e foi removida com autorização explícita; ~54.4 MB exclusivos liberados. | A-013 concluído quanto ao inventário e pin. Rollback para o ID antigo não foi testado e não está mais disponível; Bill escolheu a remoção após ser informado desse efeito. A-001–A-012 mantêm as evidências anteriores. |

### 6.1. Harmonização com IaC — 2026-10-31

- A convenção de ownership `R-12` do coordenador IaC consolida Bill como
  owner/decisor final, sem aprovações duplicadas; não substitui os critérios
  técnicos nem autoriza mutações externas não solicitadas.
- `R-10` mantém o default amplo restrito ao broker Percival. O perfil OSM deve
  continuar declarando `mounts=[]` se não houver bind, ou mounts estreitos
  justificados; a arquitetura C02 Percival e o smoke DinD Percival+Notes não
  comprovam a arquitetura ou o perfil OSM.
- `pblabs-mcp-stdio/v1` foi demonstrado em Notes e Weather apenas no subconjunto
  stdio comum. Como OSM também tem modo HTTP, essa evidência não substitui as
  provas específicas de HTTP, autenticação, health, tools ou upstream previstas
  neste plano; tampouco fecha o `V-PILOT` (não executado para OSM).
- A ação A-011 do plano IaC, sobre provenance do bundle, pertence ao bootstrap
  Percival, não ao OSM. O scan e eventual VEX devem permanecer ligados ao
  candidato OSM exato, com SHA/image ID e DB registrados; cada CVE exige VEX
  assinado pelo owner para a promoção correspondente. Aprovações de outro
  candidato não se transferem.

## 7. Sincronização com o plano coordenador

Atualizar o [stage-2 geral](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md)
se essa sincronização estiver no escopo e o checkout IaC estiver disponível.
Registrar um resumo de status e dependências; não bloquear a conclusão local por
retorno, aceite ou aprovação duplicada de outro participante.
