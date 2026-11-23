# Percival OSM — perfil de integração

**Revisado:** 2026-11-17
**Owner:** Bill Kopp, Positronic Bean Labs

## Identidade e processo

- Imagem executada como UID/GID `10001:10001`, conforme `Dockerfile` e
  `docker-compose.yml`.
- Transporte padrão: MCP stdio; stdout permanece reservado ao JSON-RPC.
- `docker-compose.yml` é fixture local. O manager Positronic/Percival continua
  sendo o owner dos containers geridos.

## Upstreams e respostas

- Backend escolhido por Bill para uso individual: definir explicitamente
  `NOMINATIM_URL=https://nominatim.openstreetmap.org/` no manager ao integrar
  uma versão com F4. A seleção em código não altera a configuração do runtime.
- O limite de 1 req/s sem burst é por aplicação, não por processo. Para dois
  managers ou réplicas compartilharem o serviço público, usar um único gateway
  que imponha o orçamento agregado, ou escolher outro backend. Um limiter local
  por processo não coordena gestores.
- Aplicam-se a [política pública](https://operations.osmfoundation.org/policies/nominatim/),
  inclusive suas restrições para LLMs, proibição de autocomplete e coleta
  sistemática, identificação e atribuição. Não enviar dados pessoais ou
  confidenciais; não há garantia de disponibilidade.
- Overpass: `https://overpass-api.de/api/interpreter`.
- OpenRouteService: `https://api.heigit.org/openrouteservice`, quando configurado.
- O perfil local permite esses hosts pela allowlist; upstreams exigem HTTPS e
  redirects ficam desativados no cliente/configuração efetiva padrão.
- `ORS_INSTANCE` (alias de compatibilidade: `ORS_URL`) substitui a base URL; o
  prefixo do serviço deve ser preservado. Compose encaminha ambos os nomes para
  a configuração canônica `ORS_INSTANCE`.
- Sem `ORS_API_KEY`, navegação e direções respondem
  `provider_not_configured`; distância haversine não é apresentada como rota.
- Uma resposta válida vazia retorna `no_results`; indisponibilidade, timeout,
  HTTP 429/5xx ou resposta inutilizável retorna erro explícito.
- `osm_get_health` inclui `tool_outcomes[tool][outcome]` para categorias
  enumeradas (`ok`, `no_results`, `upstream_error`, `exception`, `cancelled`,
  entre outras). `tool_errors` conta apenas exceções Python propagadas; outcomes
  e security counters são em memória por processo, não histórico durável.
- Logs vão a stderr e omitem entradas de busca/coordenadas, URLs, credenciais,
  detalhes de exceção e tracebacks upstream. A policy entregue ao agente está
  empacotada no resource `osm://security/nanobot-policy`.
- Saídas incluem procedência/atribuição OSM; `straight_line_estimate` é apenas
  estimativa e não distância viária.

## Mounts e cache

- Perfil do servidor MCP gerido: declarar `mounts: []`; o servidor não precisa
  de bind mount do host.
- A fixture Compose monta apenas o volume nomeado `percival-cache` em `/cache`.
  Esse volume não é um bind mount nem define o perfil do manager.
- UID/GID `10001:10001` tem escrita no cache; o path permitido é `/cache` na
  fixture Compose.
- A leitura de caches antigos em formato de dicionário puro é best-effort: o
  servidor os converte para o envelope atual ao carregar. JSON inválido ou
  formato não reconhecido inicia com cache vazio; compatibilidade de cada valor
  armazenado entre versões não é garantida.

## Limite desta nota

Esta nota distingue os perfis dos dois gestores. Os identificadores de imagem
(digest), de label de revisão e de container gerenciado foram omitidos desta
cópia pública; o registro operacional completo permanece no repositório
privado do operador.

No inventário read-only de 2026-10-31, a interface Positronic mostrou `osm`
ativo/global, revisão `5`, configuração `3` após atualização do contato, versão
`0.5.0`, uma imagem local (ID de imagem omitido), rede `bridge` e `mounts: []`.
A inspeção local dessa imagem encontrou um label OCI de revisão (omitido); é
metadado declarado pela imagem, não uma prova criptográfica da cadeia
fonte→imagem. O perfil de mounts do manager coincide com `mounts: []` desta
nota.

Após o update pela UI Percival em 2026-10-31, o inventário read-only encontrou
o container gerenciado do servidor MCP ativo na imagem local (ID de imagem
omitido), versão `0.5.0`, label de revisão (omitido) e sem label de worktree
dirty. A referência do gestor Percival aponta para o mesmo image ID. O perfil
amplo do broker permanece (`/` montado em `/host`, além de mounts explícitos);
é distinto do perfil do aplicativo Positronic `mounts: []` e do default amplo
do broker definido no registro de decisões do gestor, mantido no repositório
privado do operador.

A imagem anterior do gestor Percival (ID de imagem omitido; label de revisão
omitido, `worktree=dirty`) foi removida após autorização explícita de Bill. Não
há rollback local para esse ID.

Na configuração Positronic, `USER_AGENT` e `FROM_HEADER` foram atualizados para o
contato de owner do projeto pela interface suportada; a revisão de configuração
agora é `3`. `positronic mcp server discover osm` confirmou initialize e tools/list
com sucesso após a alteração.

O runtime Positronic continua na imagem ativa (ID de imagem omitido), com label
de revisão (omitido); entre essa revisão e o candidato não há diferenças em
código, Dockerfile, entrypoint ou lock de dependências. Nenhum update Positronic
foi solicitado.
