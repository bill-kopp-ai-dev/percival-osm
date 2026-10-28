# Stage-2 — Remediação do Percival OSM MCP

**Data / revisão:** 2026-10-27 / 1.0.  
**ID / estado:** S2-OS / planejado; execução não iniciada.  
**Checkout executor:** `/home/bill/Projects/percival-osm`.  
**Responsável:** executor OSM a designar por bill; mudanças nos gestores com os respectivos donos.

## 1. Objetivo e fontes

Tratar os 13 achados da **seção 6** do
[relatório OSM](../../../positronic-bean-IaC/docs/reports/2026-10-27-percival-osm-iac-readiness-report.md#6-achados-issues-e-inconsistências),
com ações e revalidação das seções 7/9: 13 ações (2 P1, 4 P2, 7 P3), sem P0.
Baseline e HEAD na emissão: `06484259a3bb5371c5c1551dcab0c23ccc166479`.
Há exclusões documentais locais preexistentes em `docs/`, incluindo segurança,
deployment e nota F3; preservar e reconciliar o destino com o owner.

[Coordenador stage-2](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md)
— retorno S2-OS, seções 3 e 7. Fontes comuns:
[consolidação](../../../positronic-bean-IaC/docs/reports/2026-10-26-stage-1-consolidated-readiness-report.md)
e [D-01..D-06](../../../positronic-bean-IaC/docs/decisions/2026-10-27-iac-stage-1-scope-and-pilot-decisions.md).

Emissão documental; execução futura local. Preservar layout `src/`, tools/aliases,
prompts/resources, guards HTTPS/URL/credenciais, rate limit e conteúdo não confiável.
Não é o piloto D-01. Provas de upstream usam fixtures; consultas públicas reais,
credenciais, publicação e runtime gerido exigem seu escopo/autorização próprios.

## 2. Preparação e decisões

- [ ] Ler instruções/README/CI/config atuais; registrar SHA/worktree/toolchain e
  reconciliar docs removidos sem restaurar ou substituir alterações do operador.
- [ ] Owner decidir A-001: exigir ORS com erro explícito ou fallback haversine
  **rotulado como distância aproximada**, nunca como rota/tempo real ou instrução
  de navegação. Recomendação: status de provedor não configurado preserva precisão.
- [ ] Reproduzir erro/redirect com servidor fixture controlado; testar ausência de
  requisição no destino não autorizado antes de escolher implementação.
- [ ] Alinhar S2-C01 (erro/lifecycle/mounts), S2-C03 (metadados/scan) e dimensionar
  lotes com bill (D-06); ensaio no broker depende de ownership e receita autorizada.

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
| A-008 | F-008 / P3 | Corrigir instruções UID, upstreams, mounts=[] e semântica de rota; promover orientação necessária a documento versionado | A-001; perfil S2-NB-X01 | Docs conferem com UID efetivo (baseline 10001), hosts usados e política broker; sem mounts=["/"] ou bind host desnecessário |
| A-009 | F-009 / P3 | Validar NOMINATIM_URL terminada em /search no bootstrap comum | Política fail-fast | Startup inválido sai 1 com mensagem nomeada; tools não divergem por caminho; configuração válida preservada |
| A-010 | F-010 / P3 | Tratar boundingbox ausente/inválido em resposta do upstream | Fixtures de schema | Mensagem de resposta incompleta do provedor, sem KeyError/erro interno genérico; fluxo normal íntegro |
| A-011 | F-011 / P3 | Revisar exceções CVE vigentes e versionar schema/cache ou documentar migração best-effort aprovada | Owner de segurança/dados; etapa 2 IaC | Sem exceção inaplicável; versão e comportamento de cache legado/malformado explícitos; cache não é dado autoritativo silenciosamente perdido |
| A-012 | F-012 / P3 | Tratar SIGTERM/SIGINT com encerramento de cliente HTTP e log | S2-C01/S2-NB A-012 para compatibilidade | Shutdown observável, saída/calls em voo com comportamento limitado documentado; EOF/sinal sem tarefa órfã; código esperado explícito |
| A-013 | F-013 / P3 | Produzir candidato e solicitar repin/hardening/inventário de cada gestor | S2-AP-X01 + S2-NB A-007; owners e janela própria | Runtime mostra image ID/revision aprovados, postura efetiva e dados/cache preservados; evidência datada, sem presumir pin atual por observação histórica |

### 3.1. Complemento de distribuição

| ID | Origem | Entrega / aceite |
|---|---|---|
| S2-OS-X01 | DIST-01/DIST-02, seção 8 e X-04/C-09 | Preparar server.json/metadata aplicáveis, scan/SBOM/decisão VEX próprios por artefato e instruções de publicação; S2-C03/etapas 2/4; schema válido e referência OCI real na homologação, sem confundir Docker MCP Catalog opcional com índice PBLabs |

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
contrato e regressão pertinente. Sem prazo/custo acordado; D-06 permanece aberta.
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
| Pendente | A-001–A-013; S2-OS-X01 | A registrar | Nenhuma execução nesta emissão | Não iniciada |

## 7. Última etapa — atualizar o plano coordenador

- [ ] Reler o [stage-2 geral](../../../positronic-bean-IaC/docs/plans/2026-10-27-iac-v1-stage-2-remediation-plan.md),
  atualizar **S2-OS na seção 3** e adicionar entrada na **seção 7**, com contagens,
  SHA/evidências, dependências liberadas e aceites locais/externos.
- [ ] Preservar retornos alheios e indicar efeito nas etapas 2/4/5; sem acesso à
  IaC, entregar resumo e manter **aguardando sincronização**. Conclusão exige
  aceites e retorno, nunca apenas transferência de ação para outro dono.
