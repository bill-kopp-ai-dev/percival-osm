# Stage-2 — Remediação do Percival OSM MCP

**Data / revisão:** 2026-10-31 / 1.3 (emissão original: 2026-10-27 / 1.0).
**ID / estado:** S2-OS / execução parcial local; candidato corrente sem qualificação reproduzível; inventário read-only do runtime registrado, sem repin.
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
  serão rejeitados. A fixture de zero requisições ao destino bloqueado continua pendente.
- [x] Atualização de decisão do operador em 2026-10-29: `R-10` supersede `R-02`
  quanto ao default do broker Percival, que permanece amplo conforme B14/B22/B23–B25.
  O perfil OSM deve declarar explicitamente `mounts=[]` se não exigir bind; binds
  estreitos continuam explícitos; mudanças de perfil ficam limitadas ao escopo
  definido por Bill, sem auditoria ou aceite redundante.
  `R-03` remove estimativas de esforço, custo e prazo; `R-05`
  centraliza o tracker F3 por imagem em `pblabs-mcp-index`, com referências nos
  checkouts; `R-06` adota o schema externo de `server.json`, `pblabs.app.yaml`
  como extensão operacional versionada e o índice PBLabs como destino, sem
  dependência do Docker MCP Catalog; `R-07` exige VEX por CVE associado ao image
  ID e assinado pelo owner, com CVEs da imagem base tratados por herança; `R-08`
  fixa pin aprovado e janela única datada para operações que dependem dela.
- [x] Bill decidiu em 2026-10-29 os critérios de build reproduzível (A-004), a
  semântica de erros e lifecycle (S2-C01), a nota OSM versionada e o perfil de
  mounts (A-008), o tratamento mínimo de CVEs/cache legado (A-011) e a sequência
  de inventário read-only e repin condicional (A-013). Os registros detalhados
  constam na tabela de decisões abaixo; implementação e evidências continuam abertas.
- [x] `R-11` (2026-10-29): Trivy é o scanner padrão e está instalado; o agente
  pode executá-lo autonomamente para scans locais quando necessário, cobrindo
  todas as severidades, atualizando a DB e registrando scanner/DB, SHA e image ID.
  Preferir TAR do candidato limpo, sem Docker socket. Scan não assina VEX nem
  autoriza publicação/promoção.
- [ ] Registrar as decisões operacionais necessárias em S2-C01 e materializar
  S2-C03 conforme R-06. Mutação de runtime exige candidato limpo e pedido de Bill
  que identifique imagem, runtimes e janela; esse pedido basta como autorização.

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
| A-006 | F-006 / P2 | Passar VERSION/GIT_SHA como build args no wrapper e atualizar metadata a cada release | S2-C03; pipeline/etapas 2/4 IaC | Build do wrapper tem versão/revisão corretas; source.commit é SHA do candidato; imagem/manifest digest só declarados públicos após prova |
| A-007 | F-007 / P3 | Corrigido no código deste checkout: captura de nome/categoria por valor no gerador de aliases | Sem dependência externa | Qualificação pendente: chamar dois aliases e comprovar que cada chamada incrementa o contador do alias correto, não todos em `osm_find_pharmacy` |
| A-008 | F-008 / P3 | Criar nota OSM versionada com UID, upstreams, perfil de mounts e semântica de rota; não restaurar documentos excluídos | A-001; perfil OSM e `R-10`; decisão de Bill registrada em 2026-10-29 | Nota confere com UID efetivo (baseline 10001), hosts e perfil; declara `mounts=[]` se não houver bind ou documenta binds estreitos justificados; sem `mounts=["/"]`. Nota local atualizada; a evidência é do inventário de 2026-10-30 e não revela SHA de origem da imagem. |
| A-009 | F-009 / P3 | Implementado no código deste checkout: rejeitar `NOMINATIM_URL` terminada em `/search` na validação comum de configuração | Política fail-fast | Qualificação pendente: startup inválido sai 1 com mensagem nomeada; tools não divergem por caminho; configuração válida preservada |
| A-010 | F-010 / P3 | Implementado no código deste checkout: validar presença, formato, conversão e finitude da bounding box de Nominatim | Fixtures de schema | Qualificação pendente: mensagem de resposta incompleta do provedor, sem `KeyError`/erro interno genérico; fixture normal íntegra |
| A-011 | F-011 / P3 | Fazer scan Trivy do candidato limpo (`R-11`); reconciliar exceções antigas no tracker F3 canônico; documentar migração best-effort do cache, sem mudança de código/schema agora | Trivy disponível para execução autônoma; Bill (owner único) assina VEX; `R-05`/`R-07` | Resultado ligado ao image ID em `pblabs-mcp-index`, com versão/data da DB; exceções obsoletas marcadas como não aplicáveis; VEX assinado por Bill para cada CVE encontrado, com CVEs de imagem-base tratados por herança; nota curta documenta comportamento best-effort do cache legado |
| A-012 | F-012 / P3 | Tratar SIGTERM/SIGINT com encerramento observável da aplicação, fechamento do cliente HTTP e log | S2-C01/S2-NB A-012 para compatibilidade; o init do launcher encaminha sinais, mas não comprova o lifecycle da aplicação | Qualificação pendente: shutdown observável, saída/calls em voo com comportamento limitado documentado; EOF/sinal sem tarefa órfã; código esperado explícito. O smoke de container/init, isoladamente, não comprova drenagem/cancelamento nem fechamento do cliente HTTP |
| A-013 | F-013 / P3 | Fazer inventário somente leitura dos runtimes no escopo; repin apenas onde necessário, numa única operação | Inventário read-only pode preceder candidato; repin requer candidato de SHA limpo e pedido de Bill que identifique imagem, runtimes e janela; usar a interface própria; `R-08` | Identificar image ID/revision e postura efetiva; onde houver repin, registrar estado antes/depois e rollback uma vez. Inventário OSM de 2026-10-30 está registrado na nota de integração; SHA de origem não exposto, e nenhum repin foi realizado. |

### 3.1. Complemento de distribuição

| ID | Origem | Entrega / aceite |
|---|---|---|
| S2-OS-X01 | DIST-01/DIST-02, seção 8 e X-04/C-09 | Preparar `server.json` conforme schema externo adotado, `pblabs.app.yaml` operacional versionado, scan Trivy/SBOM e VEX para CVEs encontrados ligados ao image ID, além de instruções de publicação; S2-C03/etapas 2/4; manifests destinados a `pblabs-mcp-index`; Docker MCP Catalog não é dependência |

Para cada CVE encontrado no scan do candidato, `R-07` exige um VEX associado ao
image ID e assinado por Bill; CVEs da imagem base seguem a postura por herança.
A ausência de schema materializado, scan ou digest real continua sendo trabalho
de execução, não decisão pendente.

Esse complemento não aumenta as 13 ações originais. F-002 contém hipótese de
causa: teste diferencial de upstream vazio/falhando deve confirmar o fluxo, sem
assumir causalidade só pela mensagem. Bill decide o hardening do perfil OSM;
eventuais mudanças no runtime são aplicadas por Bill usando a interface adequada,
dentro do escopo solicitado.

## 4. Lotes e dependências

1. **OS-1:** A-001/A-002/A-003, que afetam as conclusões do agente e a fronteira
   de rede; A-009/A-010 podem acompanhar o mesmo caminho de validação.
2. **OS-2:** A-005/A-007/A-008/A-011/A-012, compatibilidade e cache/lifecycle.
3. **OS-3:** A-004/A-006 e S2-OS-X01, candidato e distribuição; receber inventário
   read-only dos runtimes e executar A-013 somente onde o repin for necessário,
   em uma operação dentro do escopo solicitado por Bill.

Riscos: novas classes de erro/schema quebram consumidor, redirects seguros podem
recusar upstream antes tolerado, e a migração best-effort do cache legado pode
descartar entradas incompatíveis. Registrar o comportamento observado sem exigir
migração de schema nesta ação. `R-03` remove a exigência de estimar esforço, custo
ou prazo.
Piloto/replicação e publicação não são execução do plano coordenador documental.

## 5. Qualificação proporcional

- [ ] Executar os testes/checks relevantes às mudanças realizadas; usar a suíte
  completa para mudanças amplas ou quando uma regressão transversal for plausível.
- [ ] Para mudanças de build/distribuição, validar o candidato e os metadados
  afetados. Para mudanças de transporte/runtime, validar handshake e chamada
  segura no transporte alterado. Não repetir a mesma validação em interfaces
  diferentes sem discrepância concreta.
- [ ] Usar fixtures para os caminhos de vazio, falha, schema incompleto, chave
  ausente e redirect que forem tocados; não gerar tráfego público em failure
  injection.
- [ ] Fazer inventário e eventual repin somente dos runtimes incluídos no escopo
  de A-013. Verificações de catálogo, publicação, provider real ou piloto ficam
  fora deste plano, salvo quando uma entrega deste plano depender delas.

Registrar o resultado concisamente junto à ação correspondente. Ausência de
evidência de runtime/catalog não bloqueia aceites locais que não dependam dela;
reportar apenas o que foi efetivamente verificado.

## 6. Penúltima etapa — documentar execução neste plano

- [ ] Manter um registro curto das ações relevantes: data, SHA quando aplicável,
  mudança, evidência suficiente e pendência concreta. Não registrar comandos ou
  artefatos redundantes.
- [ ] Atualizar o coordenador IaC apenas se a sincronização fizer parte do escopo
  desta execução; preservar a coleta original e identificar limites dos mocks.

| Data / owner | Ações / achados | SHA inicial → final | Mudanças / evidências locais | Resultado / V-* / pendências |
|---|---|---|---|---|
| 2026-10-27 / bill (owner), Positronic (execução local) | A-001 parcial, A-003 parcial, A-005 local, A-006 parcial, A-007 local, A-009 local, A-010 parcial; A-002/A-004/A-008/A-011/A-012/A-013 e S2-OS-X01 pendentes | `4a71108f3980c033df1a7f9c331402e688ed213a` → SHA de trabalho não commitado | A-001 decidido e comportamento/docs ajustados; A-003 valida `Location` antes de seguir; A-005 deriva versão do pacote e injeta no serverInfo, verificado pelo protocolo MCP (`serverInfo.version=0.5.0`); A-006 wrapper passa VERSION/GIT_SHA/SOURCE_DATE_EPOCH; A-007 captura nome por valor; A-009 falha no boot com URL `/search` (container `exit 1`, mensagem nomeada); A-010 trata bbox ausente/malformado. `./.venv/bin/python -m pytest -v`: 77 passed; compileall, `bash -n` e diff-check aprovados. Build local `scripts/docker-build.sh stage2-candidate`; smoke: non-root, env guard, MCP 37 tools, HTTP auth/health/shutdown aprovados. Imagem local `sha256:bb4d27903912928e51e0129d8202adef5135ff4e8b899268643091d507a11f63`, version `0.5.0`, revision label `unknown` (worktree sujo), created `2026-10-28T00:24:13Z`. `uv` CLI indisponível; executáveis `.venv` usados. | Parcial. A-002 precisa diferenciar falha, 429/5xx/timeout de vazio em todos os payloads. A-003 ainda precisa fixture provando zero requests no destino bloqueado. A-004 precisa comparação real de builds limpos. A-006 requer candidato de SHA limpo para fechar o vínculo. A-008 a nota de integração não existe no worktree e as exclusões foram preservadas; A-011 tracker local de exceções não existe, remoção depende de reconciliação do owner de segurança; A-012 graceful shutdown pendente. A-013 depende de gestores e operação própria autorizada. S2-C01 continua pendente; formato/schema S2-C03 foi decidido em `R-06`, mas materialização e validação continuam pendentes; `R-03` remove a exigência de estimar esforço, custo ou prazo. Retorno externo pendente. |
| 2026-10-29 / Bill Kopp (owner e decisor único) | Decisões registradas para A-003, S2-C01, A-004, A-008, A-011 e A-013; execução e provas continuam pendentes | Atualização documental; sem alteração de código ou runtime | Owner: Bill Kopp, Positronic Bean Labs; `bill.kopp.dev@gmail.com`; `labs.positronicbean.com` em desenvolvimento. Redirects sem seguimento automático; semântica de erro/lifecycle definida; critério de build reproduzível fixado; nota OSM versionada sem restaurar exclusões; scan+tracker e cache best-effort para A-011; inventário read-only seguido de repin condicional para A-013. | Decisões não equivalem a aceite de execução. Pendentes: fixtures, builds limpos, scan no candidato limpo, atualização do tracker e nota do cache, revisão dos runtimes por leitura e autorização explícita de Bill para eventual repin numa única janela. |
| 2026-10-30 / Bill Kopp (owner, executor, decisor e assinante único) | Simplificação do processo e do escopo de verificação | Política aplicada ao plano | Positronic Bean Labs; `bill.kopp.dev@gmail.com`; `labs.positronicbean.com`. Uma solicitação explícita de Bill autoriza a operação descrita; interfaces de gestão não são aprovadores. Verificações devem ser focadas, sem duplicar aceites, revisões cruzadas ou artefatos para a mesma decisão. | Esta atualização substitui exigências anteriores de aprovação/retorno repetido. Preservam-se verificações técnicas relevantes e evidências necessárias às entregas; sincronização externa só bloqueia quando fizer parte do escopo ou for dependência concreta. |
| 2026-10-31 / Bill Kopp (owner); Positronic (revisão documental) | Reconciliar nota de integração, inventário read-only e status do candidato com o estado documentado | `b39d027be449d73f90900ddd25465f575a949ba7` → worktree com alterações locais | `docs/integrations/percival-osm.md` registra UID/GID `10001:10001`, upstreams, semântica de rota, `mounts: []` e inventário de 2026-10-30: runtime `osm` ativo/global, revisão 4, versão 0.5.0, imagem local `sha256:67f8ada639897af9ca4ca8f02e38932376f73f454db76028a3920f076011cfeb`, rede `bridge`, configuração revisão 1. A interface não expôs SHA de origem; contato efetivo difere do contato do projeto e precisa ser atualizado antes de uso externo. Nota também documenta migração best-effort de cache legado. | A-008 tem a nota e o perfil de mounts documentados, mas não há cadeia fonte→imagem para qualificar o runtime; A-013 tem inventário read-only registrado, sem justificativa/evidência de repin e sem mutação. A-011 ainda requer scan do candidato limpo, reconciliação no tracker e registro da nota de cache no contexto de segurança. O smoke de shutdown foi alterado localmente, mas não há resultado novo registrado; A-012 continua pendente. Nenhum candidato corrente foi qualificado, nem houve publicação ou repin. |

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
