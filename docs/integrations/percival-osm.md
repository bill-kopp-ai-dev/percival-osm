# Percival OSM — perfil de integração

**Revisado:** 2026-10-31
**Owner:** Bill Kopp, Positronic Bean Labs

## Identidade e processo

- Imagem executada como UID/GID `10001:10001`, conforme `Dockerfile` e
  `docker-compose.yml`.
- Transporte padrão: MCP stdio; stdout permanece reservado ao JSON-RPC.
- `docker-compose.yml` é fixture local. O manager Positronic/Percival continua
  sendo o owner dos containers geridos.

## Upstreams e respostas

- Nominatim: `https://nominatim.openstreetmap.org/`.
- Overpass: `https://overpass-api.de/api/interpreter`.
- OpenRouteService: `https://api.openrouteservice.org`, quando configurado.
- O perfil local permite esses hosts pela allowlist; upstreams exigem HTTPS e
  redirects ficam desativados no cliente/configuração efetiva padrão.
- Sem `ORS_API_KEY`, navegação e direções respondem
  `provider_not_configured`; distância haversine não é apresentada como rota.
- Uma resposta válida vazia retorna `no_results`; indisponibilidade, timeout,
  HTTP 429/5xx ou resposta inutilizável retorna erro explícito.

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

Esta nota distingue os perfis dos dois gestores. No inventário read-only de
2026-10-31, a interface Positronic mostrou `osm` ativo/global, revisão `5`,
configuração `3` após atualização do contato, versão `0.5.0`, imagem local
`sha256:805b81ae60cb6726dc9d0590641abb0432557f96ed28ca5a617d7408a81f738e`,
rede `bridge` e `mounts: []`. A inspeção local dessa imagem encontrou o label OCI
de revisão `b39d027be449d73f90900ddd25465f575a949ba7`; é metadado declarado pela
imagem, não uma prova criptográfica da cadeia fonte→imagem. O perfil de mounts do
manager coincide com `mounts: []` desta nota.

Após o update pela UI Percival em 2026-10-31, o inventário read-only encontrou o
container `percival-mcp-osm` ativo na imagem local
`sha256:3e6cc7ddf291ec5f06aa86bd21baab7ef7a6648d9f48968b7dae421cceadc8bc`,
versão `0.5.0`, label de revisão `312964c9e8b0da41dc3e8ed3efca6cfd33362fb6` e
sem label de worktree dirty. A referência do gestor Percival aponta para o mesmo
image ID. O perfil amplo do broker permanece (`/` montado em `/host`, além de
mounts explícitos); é distinto do perfil do aplicativo Positronic `mounts: []` e
do default amplo do broker definido em `R-10`.

A imagem anterior Percival `sha256:67f8ada639897af9ca4ca8f02e38932376f73f454db76028a3920f076011cfeb`
(label de revisão `311a49d`, `worktree=dirty`) foi removida após autorização
explícita de Bill. Não há rollback local para esse ID.

Na configuração Positronic, `USER_AGENT` e `FROM_HEADER` foram atualizados para o
contato de owner do projeto pela interface suportada; a revisão de configuração
agora é `3`. `positronic mcp server discover osm` confirmou initialize e tools/list
com sucesso após a alteração.

O runtime Positronic continua na imagem `sha256:805b81ae60cb6726dc9d0590641abb0432557f96ed28ca5a617d7408a81f738e`,
label de revisão `b39d027`; entre essa revisão e o candidato não há diferenças em
código, Dockerfile, entrypoint ou lock de dependências. Nenhum update Positronic
foi solicitado.
