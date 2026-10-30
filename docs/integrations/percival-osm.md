# Percival OSM — perfil de integração

**Revisado:** 2026-10-30  
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

## Limite desta nota

Esta nota descreve o perfil versionado neste checkout e a configuração da
fixture Compose. O inventário somente leitura feito em 2026-10-30 pela interface
Positronic registrou o runtime `osm` ativo/global na revisão `4`, versão `0.5.0`,
imagem local `sha256:67f8ada639897af9ca4ca8f02e38932376f73f454db76028a3920f076011cfeb`,
rede `bridge`, `mounts: []` e revisão de configuração `1`. A interface não
expôs o SHA de origem da imagem instalada. O profile de mounts observado coincide
com a declaração `mounts: []` desta nota.

A configuração efetiva tem `USER_AGENT` e `FROM_HEADER` definidos; o contato
efetivo não coincide com o email de owner informado neste projeto. O valor não é
reproduzido aqui. Confirmar a atualização para o contato do projeto antes do
próximo uso externo; nenhuma variável do runtime foi alterada durante o inventário.
