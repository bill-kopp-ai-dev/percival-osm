# Issue: migrar o endpoint legado do OpenRouteService

- **Status:** concluída — implementação e critérios de aceite verificados em 2026-11-17
- **Prioridade sugerida:** P1 — compatibilidade das rotas com endpoint descontinuado
- **Identificada em:** 2026-11-04, revisão do runtime `osm` após falha de rota
- **Verificada em:** 2026-11-16, auditoria documental sobre o estado real do código
- **Owner / decisão:** Bill Kopp

## Problema

O cliente OpenRouteService do servidor `osm` usa por padrão
`https://api.openrouteservice.org`. Esse hostname foi descontinuado em favor de
`api.heigit.org`; o provedor anunciou a desativação do hostname antigo entre
2 e 6 de novembro de 2026. O caminho de Directions foi movido para
`https://api.heigit.org/openrouteservice/v2/directions/...`.

Se o hostname antigo for desligado, ferramentas de rota que estejam
configuradas com `ORS_API_KEY` continuarão tentando uma URL obsoleta. A ausência
de `ORS_API_KEY` é um bloqueio separado, detectado antes de qualquer chamada ao
upstream, e não deve ser corrigida nem mascarada por esta issue.

## Evidência e escopo

- `src/percival_osm_mcp/server.py` usa `https://api.openrouteservice.org` como
  valor fallback de `ors_instance` (linha 1703).
- O schema aceita `ORS_INSTANCE` e `ORS_URL`, então uma instalação pode
  substituir o endpoint explicitamente.
- A allowlist padrão `OSM_UPSTREAM_ALLOWED_HOSTS` (linha 151) e a configuração
  Compose ainda incluem `api.openrouteservice.org`; os fixtures e a integração
  também codificam esse hostname.
- A documentação do projeto lista o endpoint legado.
- O aviso oficial do OpenRouteService diz que `api.openrouteservice.org` foi
  descontinuado em favor de `api.heigit.org`, mapeia Directions para
  `api.heigit.org/openrouteservice/v2/directions` e agenda o desligamento do
  endpoint antigo para 2–6 de novembro de 2026:
  - https://ask.openrouteservice.org/t/deprecating-api-openrouteservice-org-in-favour-of-api-heigit-org/7912
  - https://ask.openrouteservice.org/t/reducing-the-quota-of-deprecated-api-api-openrouteservice-org/8013

O caminho atual `/v2/directions/{profile}` do cliente deve ser preservado; a
migração requer ajustar a base URL para incluir o prefixo `/openrouteservice`,
conforme o novo endpoint documentado pelo provedor.

## Critérios de aceite

- Atualizar o fallback do cliente ORS para
  `https://api.heigit.org/openrouteservice`.
- Atualizar a allowlist padrão para aceitar `api.heigit.org`; remover o hostname
  antigo do default se não houver outro uso legítimo, mantendo overrides
  explícitos para instâncias próprias ou compatíveis.
- Confirmar que `ORS_INSTANCE` e `ORS_URL` continuam aceitando URLs de instâncias
  próprias e passam pela validação/allowlist existente.
- Adicionar testes focados que verifiquem a URL final de Directions no novo host,
  incluindo o prefixo `/openrouteservice`, e que rejeitem hosts fora da
  allowlist. Os testes não devem exigir chave ORS nem chamar a internet.
- Atualizar README, perfil de integração, exemplos Compose e fixtures que
  descrevam ou restrinjam o hostname de produção.
- Preservar autenticação por `ORS_API_KEY`; não introduzir fallback sem chave,
  rota aproximada ou credencial em logs.
- `provider_not_configured` continua sendo a resposta correta quando a chave
  não estiver definida. Com a chave disponível, a chamada de Directions deve
  alcançar o endpoint novo e tratar erros upstream conforme o contrato atual.

## Limites

- Esta issue migra o endpoint ORS; não solicita nem configura uma chave API.
- Não altera Nominatim, Overpass, `USER_AGENT`, `FROM_HEADER` ou limites de uso
  OSM.
- Não muda nem implanta containers geridos; construção, pin e implantação de
  nova imagem continuam sob autorização operacional própria.
- Manter compatibilidade com `ORS_INSTANCE`/`ORS_URL` para deployments
  self-hosted. Não forçar todos os usuários a usar o serviço público HeiGIT.

## Verificação de auditoria — 2026-11-16

- **A issue permanece aberta e nenhuma migração foi feita.** O código, a
  allowlist padrão, a configuração de exemplo, o Compose, o README, a nota de
  integração e os fixtures de teste continuam apontando para
  `api.openrouteservice.org`.
- **A janela de desligamento anunciada já passou.** O provedor anunciou o
  desligamento para 2–6 de novembro de 2026 e a data da auditoria é 2026-11-16.
  O impacto deixou de ser uma indisponibilidade futura: qualquer instalação com
  `ORS_API_KEY` definida deve ser tratada como apontando para um endpoint
  possivelmente já fora do ar. Esta issue não foi verificada contra o endpoint
  em si — não houve chamada de rede ao provedor durante a auditoria —, portanto
  o estado real do hostname legado não está confirmado aqui.
- Inventário atual das referências ao hostname legado:
  - `src/percival_osm_mcp/server.py:1703` — fallback de `ors_instance`;
  - `src/percival_osm_mcp/server.py:151` — default de
    `OSM_UPSTREAM_ALLOWED_HOSTS`;
  - `.env.example:48` — exemplo de `ORS_INSTANCE`;
  - `.env.example:81` e `docker-compose.yml:78` — allowlist padrão;
  - `README.md:210` — allowlist padrão;
  - `docs/integrations/percival-osm.md:18` — lista de upstreams da integração;
  - `tests/test_s1_runtime_hardening.py:22`,
    `tests/test_s3_observability.py:31`, `tests/test_s4_new_tools.py:32` e
    `tests/test_s5_primitives.py:269,306` — fixtures de settings.
- A construção de URL confere com o plano de migração: a biblioteca
  `openrouteservice` monta `{base_url}/v2/directions/{profile}/{format}`, logo
  `base_url=https://api.heigit.org/openrouteservice` produz exatamente
   `https://api.heigit.org/openrouteservice/v2/directions/{profile}/json`.
- `provider_not_configured` continua sendo a resposta correta enquanto
  `ORS_API_KEY` não estiver definida; a ausência de chave é detectada antes de
  chamar ORS e não deve ser mascarada por esta issue. Os handlers atuais ainda
  geocodificam os extremos no Nominatim antes dessa verificação; F1 do plano
  abaixo propõe antecipá-la para evitar essas consultas desnecessárias.

## Encaminhamento — 2026-11-16

- Implementação proposta em [F1 do plano de atualização MCP](../../plans/closed/2026-11-16-mcp-api-refresh-and-reliability.md).
- Corrigida a indicação de formato da auditoria: `ors_directions` usa o default
  `format='json'` do SDK 2.3.3, compatível com o parsing atual de `routes[]`.
  A migração de base URL não exige mudar para o envelope GeoJSON.
- O anúncio oficial de migração e o cronograma foram consultados novamente em
  2026-11-16; a disponibilidade do hostname legado continua sem teste direto.
- Na revisão de 2026-11-16, a issue permanecia aberta até implementação e
  verificação. A implementação e a verificação subsequentes estão registradas
  abaixo.

## Implementação parcial e verificação — 2026-11-17

- Fallback atualizado para `https://api.heigit.org/openrouteservice`, removendo
  barras finais redundantes sem descartar prefixo de instância; allowlist padrão
  e fixtures agora usam `api.heigit.org`. `ORS_INSTANCE` e o alias `ORS_URL`
  continuam aceitos e passam pela mesma validação de HTTPS/allowlist.
- Compose encaminha `ORS_INSTANCE` com fallback para `ORS_URL`; exemplos,
  README, nota de integração e brief do projeto foram alinhados.
- `tests/test_f1_ors_migration.py` captura o POST do SDK 2.3.3 sem rede e verifica
  o path de Directions JSON, coordenadas `[lon, lat]`, header `Authorization`,
  host bloqueado, prefixo customizado, alias e chunking compatível com Python 3.11.
  `tests/test_s4_new_tools.py -k missing_ors_provider` confirma ausência de
  geocodificação sem chave. A suíte focal de F1 e Docker passou: **32 passed**;
  `docker compose config --quiet` passou.
- Import/startup foi verificado em Python 3.12.15, a versão minor do Dockerfile.
  Não há interpretador Python 3.11 instalado neste ambiente; isso permanece como
  pendência para concluir a fase F1 e fechar esta issue. Nenhuma requisição
  autenticada ao serviço ORS real foi feita; a evidência do endpoint é de captura
  determinística.

## Conclusão — 2026-11-17

- F1 foi concluída, incluindo a verificação posterior da suíte completa em
  Python 3.11.14 e 3.12.15; o complemento de evidência está no plano referenciado
  acima. A captura HTTP determinística confirmou a URL de Directions no novo
  host, e os testes cobriram prefixo/override, allowlist e ausência de chave antes
  da geocodificação.
- Os critérios da issue foram atendidos. Não houve chamada autenticada ao ORS
  real; isso não é requisito para o aceite local e não se afirma disponibilidade
  do serviço externo.
- Issue movida para `docs/issues/closed/`.
