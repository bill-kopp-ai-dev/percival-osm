# Stage-2 — Remediação do Percival OSM MCP

**Data / revisão:** 2026-10-27 / 1.0.  
**ID / estado:** S2-OS / execução parcial local; aceites externos pendentes.
**Checkout executor:** `/home/bill/Projects/percival-osm`.  
**Responsável:** executor OSM a designar por bill; mudanças nos gestores com os respectivos donos.

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

Emissão documental; execução futura local. Preservar layout `src/`, tools/aliases,
prompts/resources, guards HTTPS/URL/credenciais, rate limit e conteúdo não confiável.
Não é o piloto D-01. Provas de upstream usam fixtures; consultas públicas reais,
credenciais, publicação e runtime gerido exigem seu escopo/autorização próprios.

## 2. Preparação e decisões

- [x] Ler instruções/README/CI/config atuais; registrar SHA/worktree/toolchain e
  reconciliar docs removidos sem restaurar ou substituir alterações do operador.
- [x] Owner decidiu A-001: sem `ORS_API_KEY`, retornar status explícito
  `provider_not_configured`, nunca distância haversine como rota. Decisão alinhada
  com a recomendação de preservar precisão.
- [ ] Reproduzir erro/redirect com servidor fixture controlado; testar ausência de
  requisição no destino não autorizado antes de escolher implementação.
- [x] Atualização de decisão do operador em 2026-10-29: `R-10` supersede `R-02`
  quanto ao default do broker Percival, que permanece amplo conforme B14/B22/B23–B25.
  O perfil OSM deve declarar explicitamente `mounts=[]` se não exigir bind; binds
  estreitos continuam explícitos, e ampliar perfil restrito exige confirmação/auditoria.
  `R-03` remove estimativas de esforço, custo e prazo; `R-05`
  centraliza o tracker F3 por imagem em `pblabs-mcp-index`, com referências nos
  checkouts; `R-06` adota o schema externo de `server.json`, `pblabs.app.yaml`
  como extensão operacional versionada e o índice PBLabs como destino, sem
  dependência do Docker MCP Catalog; `R-07` exige VEX por CVE associado ao image
  ID e assinado pelo owner, com CVEs da imagem base tratados por herança; `R-08`
  fixa pin aprovado e janela única datada para operações que dependem dela.
- [ ] Alinhar S2-C01 (erro/lifecycle/mounts) e materializar/validar S2-C03
  conforme o formato já decidido. Ensaio no broker depende de ownership,
  implementação e prova do perfil; a política não está mais pendente.

## 3. Backlog integral e critérios de aceite

Todas as ações **não iniciadas**. Prioridades de origem preservadas.

| Ação | Achado / P | Trabalho e áreas previstas | Dependência / dono externo | Aceite verificável |
|---|---|---|---|---|
| A-001 | F-001 / P1 | Alinhar ORS/fallback e docs em server/entrypoint/server.yaml/README | Decisão explícita do produto sobre ORS_API_KEY | Sem chave: status/mensagem de configuração ou fallback honestamente rotulado; com chave fixture, rota correta; nenhuma falsa afirmação de no_results |
| A-002 | F-002 / P1 | Distinguir falha de upstream de resultado vazio em payload de tools | S2-C01 como referência, sem bloquear fix local | Upstream indisponível/429/5xx/timeout e bloqueio de URL não viram no_results; 200 vazio continua distinguível; logs e payload concordam |
| A-003 | F-003 / P2 | Validar cada redirect antes de seguir ou recusar redirects explicitamente | Contrato de URL vigente | Destino fora da allowlist recebe zero conexões/requisições; caminho permitido funciona; default follow_redirects false preservado |
| A-004 | F-004 / P2 | Normalizar timestamps/metadados uv/logs apt/dpkg/ldconfig no build | Mesmas entradas/builder; etapa 2 IaC | Dois builds limpos do mesmo SHA com camadas iguais conforme aceite original; registrar parâmetros e comparação por arquivo se falhar |
| A-005 | F-005 / P2 | Derivar versão do pacote em SERVER_VERSION e serverInfo | Fonte única de versão | Status/version/initialize e labels concordam com pacote (0.5.0 somente se vigente), não SDK |
| A-006 | F-006 / P2 | Passar VERSION/GIT_SHA como build args no wrapper e atualizar metadata a cada release | S2-C03; pipeline/etapas 2/4 IaC | Build do wrapper tem versão/revisão corretas; source.commit é SHA do candidato; imagem/manifest digest só declarados públicos após prova |
| A-007 | F-007 / P3 | Corrigir captura tardia de closure no gerador de aliases | Sem dependência externa | Chamar dois aliases e obter contador do alias correto para cada um, não todos em osm_find_pharmacy |
| A-008 | F-008 / P3 | Corrigir instruções UID, upstreams, perfil de mounts e semântica de rota; promover orientação necessária a documento versionado | A-001; perfil S2-NB-X01; `R-10` | Docs conferem com UID efetivo (baseline 10001), hosts usados e política broker; OSM declara explicitamente perfil sem bind (`mounts=[]`) ou mounts estreitos conforme necessidade, sem depender do default amplo do broker; ampliar perfil restrito requer confirmação/auditoria; sem `mounts=["/"]` |
| A-009 | F-009 / P3 | Validar NOMINATIM_URL terminada em /search no bootstrap comum | Política fail-fast | Startup inválido sai 1 com mensagem nomeada; tools não divergem por caminho; configuração válida preservada |
| A-010 | F-010 / P3 | Tratar boundingbox ausente/inválido em resposta do upstream | Fixtures de schema | Mensagem de resposta incompleta do provedor, sem KeyError/erro interno genérico; fluxo normal íntegro |
| A-011 | F-011 / P3 | Reconciliar exceções CVE no tracker canônico F3 e versionar schema/cache ou documentar migração best-effort aprovada | Owner de segurança/dados; etapa 2 IaC; `R-05`/`R-07` | Tracker F3 central em `pblabs-mcp-index`, por image ID; VEX por CVE ligado ao image ID e assinado pelo owner; CVEs da imagem base tratados por herança; sem exceção inaplicável; versão/comportamento do cache legado explícitos |
| A-012 | F-012 / P3 | Tratar SIGTERM/SIGINT com encerramento de cliente HTTP e log | S2-C01/S2-NB A-012 para compatibilidade | Shutdown observável, saída/calls em voo com comportamento limitado documentado; EOF/sinal sem tarefa órfã; código esperado explícito |
| A-013 | F-013 / P3 | Produzir candidato e solicitar repin/hardening/inventário de cada gestor | S2-AP-X01 + S2-NB A-007; owners; `R-08` | Runtime mostra image ID/revision com pin aprovado, postura efetiva e dados/cache preservados; operação em janela única datada e autorizada; evidência datada, sem presumir pin atual por observação histórica |

### 3.1. Complemento de distribuição

| ID | Origem | Entrega / aceite |
|---|---|---|
| S2-OS-X01 | DIST-01/DIST-02, seção 8 e X-04/C-09 | Preparar `server.json` conforme schema externo adotado, `pblabs.app.yaml` operacional versionado, scan/SBOM/VEX por artefato e instruções de publicação; S2-C03/etapas 2/4; manifests destinados a `pblabs-mcp-index`; Docker MCP Catalog não é dependência |

Para promoção, `R-07` exige um VEX por CVE associado ao image ID e assinado
pelo owner; CVEs da imagem base seguem a postura por herança. A ausência de
schema materializado, scan ou digest real continua sendo trabalho de execução,
não decisão pendente.

Esse complemento não aumenta as 13 ações originais. F-002 contém hipótese de
causa: teste diferencial de upstream vazio/falhando deve confirmar o fluxo, sem
assumir causalidade só pela mensagem. O hardening do spawn é trabalho dos gestores.

## 4. Lotes e dependências

1. **OS-1:** A-001/A-002/A-003, que afetam as conclusões do agente e a fronteira
   de rede; A-009/A-010 podem acompanhar o mesmo caminho de validação.
2. **OS-2:** A-005/A-007/A-008/A-011/A-012, compatibilidade e cache/lifecycle.
3. **OS-3:** A-004/A-006 e S2-OS-X01, candidato e distribuição; receber A-013
   de cada gestor separadamente, com operação autorizada.

Riscos: novas classes de erro/schema quebram consumidor, redirects seguros podem
recusar upstream antes tolerado, cache versionado exige regra de migração. Registrar
contrato e regressão pertinente. `R-03` remove a exigência de estimar esforço,
custo ou prazo.
Piloto/replicação e publicação não são execução do plano coordenador documental.

## 5. Qualificação futura local e externa

- [ ] `uv run pytest -v`, recortes de runtime security/primitives/observability
  afetados e checks existentes; preservar rate limit e sanitização.
- [ ] Build/smoke pelo wrapper corrigido, `scripts/docker-smoke-test.sh` e
  conformidade no candidato; comparar versão/labels e camadas quando aplicável.
- [ ] Protocolo real stdio: initialize/initialized/tools-list/safe-call; HTTP
  separado com autenticação/perfil reais. Stdout só JSON-RPC, init do launcher.
- [ ] Fixture Nominatim/Overpass/ORS para vazio, indisponibilidade, schema incompleto,
  chave ausente e redirect; nenhum tráfego público em failure injection.
- [ ] Revalidar `V-BUILD`, `V-RUN`, `V-CONFIG`, `V-DATA` do cache, `V-MCP`,
  `V-FUNC`; `V-PILOT`/`V-REUSE` só com prova própria; retorno dos owners em A-013.
- [ ] CI remoto, publicação/pull anônimo e eventual provider real com escopo
  autorizado próprios; respeitar política de uso dos serviços quando aplicável.

Aceites locais não fecham estado de runtime nem catálogo remoto. Falta de retorno
externo mantém parcial/bloqueado, não “todos os problemas solucionados”.

## 6. Penúltima etapa — documentar execução neste plano

- [ ] Registrar cada ação/subtarefa com data/owner, SHA inicial/final, mudança,
  comandos/ambiente, evidências sanitizadas locais e resultado/veredito `V-*`.
- [ ] Documentar decisões e pendências com dono; complementar seção 9 do relatório
  IaC quando autorizado, preservando a coleta original e os limites dos mocks.

| Data / owner | Ações / achados | SHA inicial → final | Mudanças / evidências locais | Resultado / V-* / pendências |
|---|---|---|---|---|
| 2026-10-27 / bill (owner), Positronic (execução local) | A-001 parcial, A-003 parcial, A-005 local, A-006 parcial, A-007 local, A-009 local, A-010 parcial; A-002/A-004/A-008/A-011/A-012/A-013 e S2-OS-X01 pendentes | `4a71108f3980c033df1a7f9c331402e688ed213a` → SHA de trabalho não commitado | A-001 decidido e comportamento/docs ajustados; A-003 valida `Location` antes de seguir; A-005 deriva versão do pacote e injeta no serverInfo, verificado pelo protocolo MCP (`serverInfo.version=0.5.0`); A-006 wrapper passa VERSION/GIT_SHA/SOURCE_DATE_EPOCH; A-007 captura nome por valor; A-009 falha no boot com URL `/search` (container `exit 1`, mensagem nomeada); A-010 trata bbox ausente/malformado. `./.venv/bin/python -m pytest -v`: 77 passed; compileall, `bash -n` e diff-check aprovados. Build local `scripts/docker-build.sh stage2-candidate`; smoke: non-root, env guard, MCP 37 tools, HTTP auth/health/shutdown aprovados. Imagem local `sha256:bb4d27903912928e51e0129d8202adef5135ff4e8b899268643091d507a11f63`, version `0.5.0`, revision label `unknown` (worktree sujo), created `2026-10-28T00:24:13Z`. `uv` CLI indisponível; executáveis `.venv` usados. | Parcial. A-002 precisa diferenciar falha, 429/5xx/timeout de vazio em todos os payloads. A-003 ainda precisa fixture provando zero requests no destino bloqueado. A-004 precisa comparação real de builds limpos. A-006 requer candidato de SHA limpo para fechar o vínculo. A-008 a nota de integração não existe no worktree e as exclusões foram preservadas; A-011 tracker local de exceções não existe, remoção depende de reconciliação do owner de segurança; A-012 graceful shutdown pendente. A-013 depende de gestores e operação própria autorizada. S2-C01 continua pendente; formato/schema S2-C03 foi decidido em `R-06`, mas materialização e validação continuam pendentes; `R-03` remove a exigência de estimar esforço, custo ou prazo. Retorno externo pendente. |

## 7. Última etapa — atualizar o plano coordenador

- [ ] Reler o [stage-2 geral](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md),
  atualizar **S2-OS na seção 3** e adicionar entrada na **seção 7**, com contagens,
  SHA/evidências, dependências liberadas e aceites locais/externos.
- [ ] Preservar retornos alheios e indicar efeito nas etapas 2/4/5; sem acesso à
  IaC, entregar resumo e manter **aguardando sincronização**. Conclusão exige
  aceites e retorno, nunca apenas transferência de ação para outro dono.
