# Relatório técnico — APIs do OpenStreetMap, autenticação e políticas de uso

**Data da revisão:** 12 de novembro de 2026  
**Idioma:** português (Brasil)  
**Escopo:** documentação oficial do OpenStreetMap (OSM), suas APIs e serviços associados, autenticação OAuth 2.0, limites operacionais, licenciamento e recomendações de integração.

> **Conclusão principal:** não existe uma chave API universal do OpenStreetMap que seja exigida para consultar os dados cartográficos públicos. Consultas públicas pontuais podem ser feitas sem credenciais, mas edições no banco de dados do OSM e operações restritas exigem autorização **OAuth 2.0**. Outros serviços do ecossistema — Nominatim, Overpass e tiles — têm **políticas independentes**. O acesso sem chave não significa tráfego ilimitado ou garantia de disponibilidade.

---

## 1. Objetivos e metodologia

Este relatório responde às seguintes questões:

1. O que é a API indicada em <https://wiki.openstreetmap.org/wiki/API>?
2. Quando é necessário obter credenciais e quais credenciais são essas?
3. Como registrar uma aplicação e obter um token OAuth 2.0?
4. Quais serviços são apropriados para geocodificação, busca de objetos geográficos, visualização de mapas e roteamento?
5. Quais limites técnicos, operacionais e de licença devem ser observados antes de utilizar esses serviços em produção?

**Metodologia:** leitura da documentação do OSM Wiki, das políticas oficiais de operação da OpenStreetMap Foundation (OSMF), da documentação do Nominatim e de referências técnicas sobre Overpass, roteamento e licenciamento. Os exemplos abaixo ilustram a documentação; **não constituem testes de carga ou garantia de disponibilidade dos endpoints**. Políticas e instâncias públicas podem mudar após a data desta revisão.

## 2. Resumo executivo

O OpenStreetMap é, antes de tudo, uma **base aberta de dados geográficos** produzida por colaboradores. Essa base é utilizada por diferentes APIs e mecanismos independentes; não se trata de uma plataforma única, com uma só API Key que habilita todos os recursos.

### 2.1 Matriz de decisão

| Necessidade | Serviço/ferramenta | Credencial para acesso público básico? | Observação essencial |
| --- | --- | --- | --- |
| Ler elementos específicos (`node`, `way`, `relation`) | OSM Editing API v0.6 | Não, para leituras públicas | API concebida principalmente para edição; não indicada para leituras em volume. |
| Criar/alterar/remover elementos no mapa | OSM Editing API v0.6 | **Sim: OAuth 2.0** | Necessário usuário autenticado e escopo adequado, normalmente `write_api`. |
| Ler dados privados do usuário | OSM API v0.6 | **Sim: OAuth 2.0** | Permissões dependem do recurso; nem toda leitura é pública. |
| Consultar objetos por tipo, tag e área | Overpass API | Geralmente não | Instâncias independentes; cotas e disponibilidade próprias. |
| Geocodificar endereços ou fazer busca pontual | Nominatim público | Não | Política muito restritiva, especialmente para alto volume, autocomplete e aplicações de IA. |
| Exibir mapa raster no navegador | Tiles OSM + Leaflet | Não para o servidor público | Exige atribuição, identificação, cache e uso moderado. |
| Consumir tiles vetoriais públicos | Serviço de tiles vetoriais OSM | Não há chave universal exigida pela política | Regras específicas; verificar versão de tiles e compatibilidade com o estilo. |
| Calcular rotas | Motor separado (ex.: OSRM) | Depende do operador | Não é funcionalidade genérica da Editing API do OSM. |
| Aplicação comercial em escala | Serviço próprio ou fornecedor especializado | **Depende do fornecedor** | Provedores podem exigir chave, cobrança, contrato e SLA; isso não é uma “chave do OSM”. |

**Resposta objetiva:** se o objetivo é pesquisar endereços, explorar POIs ou visualizar mapas em um protótipo de baixo tráfego, normalmente é possível começar **sem chave**. Se o objetivo é **editar o OpenStreetMap** ou acessar informações restritas, será preciso registrar uma aplicação e implementar OAuth 2.0.

## 3. O que a documentação oficial chama de “API”

A página <https://wiki.openstreetmap.org/wiki/API> descreve a **Editing API**, interface REST para buscar e salvar geodados brutos na base de dados do OpenStreetMap. A documentação deixa explícito que quem deseja apenas inserir um mapa em um site **não deve confundir essa API com um serviço de mapas incorporáveis**. A versão em uso é a **API v0.6** [1][2].

### 3.1 Modelo de dados

- **Node:** ponto com latitude e longitude, que pode representar um objeto isolado ou compor uma geometria.
- **Way:** sequência ordenada de nodes; pode representar vias e contornos de áreas.
- **Relation:** estrutura que reúne nodes, ways e/ou outras relations, com papéis definidos.
- **Tags:** pares chave–valor, como `amenity=pharmacy`, `highway=residential` e `name=...`.

A edição da base utiliza **changesets**, permitindo agrupar alterações. Consultas analíticas, buscas espaciais amplas e renderização costumam exigir outras ferramentas.

### 3.2 Base URLs e respostas

- API de produção: `https://api.openstreetmap.org/api/0.6/`
- Ambiente de desenvolvimento: `https://master.apis.dev.openstreetmap.org/api/0.6/`
- Respostas: tradicionalmente XML; determinados endpoints oferecem JSON. Nem todos os recursos têm formato JSON equivalente.

**Exemplo de consulta pública sem chave:**

```bash
curl --fail-with-body \
  -A 'ExemploOSM/1.0 (contato: contato@example.org)' \
  'https://api.openstreetmap.org/api/0.6/node/1.json'
```

O exemplo usa um identificador de node apenas para demonstrar a sintaxe; ele não comprova que o objeto possua os atributos de interesse de uma aplicação. Para obter muitos objetos em uma área, prefira Overpass ou extratos de dados, e não requisições massivas à Editing API.

### 3.3 Quando a autenticação é exigida

Segundo a documentação da API v0.6 [2]:

- **GET público:** não exige autenticação, salvo exceções, como detalhes privados de usuário.
- **Operações que alteram os dados:** exigem usuário autenticado e autorizado via OAuth 2.0.
- **Acesso a recursos protegidos:** exige escopos específicos, concedidos por usuário.

Desde **1º de julho de 2024**, a autenticação suportada pela API principal é **OAuth 2.0**; HTTP Basic e OAuth 1.0a deixaram de ser aceitos [4].

## 4. Como obter credenciais OAuth 2.0

### 4.1 Pré-requisitos

1. Criar uma conta gratuita em <https://www.openstreetmap.org/>.
2. Entrar na conta.
3. Registrar uma aplicação cliente em <https://www.openstreetmap.org/oauth2/applications/new>.
4. Definir nome, URIs de redirecionamento, tipo de cliente e permissões autorizáveis.
5. Guardar com segurança os identificadores e segredos fornecidos, quando aplicável.

O registro de um **cliente OAuth** não equivale a receber automaticamente acesso irrestrito aos serviços OSM. O cliente precisa obter a **autorização explícita do usuário** para escopos protegidos [3].

### 4.2 Campos de registro

| Campo | Significado | Boa prática |
| --- | --- | --- |
| Nome | Nome mostrado na autorização | Identificar claramente o software. |
| Redirect URI | URL para retorno do navegador após autorização | Em produção, HTTPS. Para testes locais, `http://127.0.0.1` é permitido. |
| Confidential application | Indica se é possível guardar um `Client Secret` | Marcar somente quando houver backend seguro. SPA e apps móveis não são clientes confidenciais. |
| Scopes/permissões | Define o conjunto de operações que a aplicação poderá solicitar | Princípio do menor privilégio. |

O **Client ID** identifica o cliente; o **Client Secret** autentica um cliente confidencial; o **Authorization Code** é temporário; o **Access Token** autoriza chamadas da API. São conceitos distintos.

> **Atenção:** conforme a documentação do OSM, o `Client Secret` pode não ser exibido novamente. Nunca colocá-lo em JavaScript enviado ao navegador, aplicações móveis distribuídas, commits ou logs.

### 4.3 Escopos relevantes

| Escopo | Finalidade |
| --- | --- |
| `openid` | Login/identidade com OpenStreetMap. |
| `write_api` | Alterar o mapa. |
| `read_prefs` | Ler preferências de usuário. |
| `write_prefs` | Alterar preferências de usuário. |
| `write_notes` | Modificar notas do mapa. |
| `read_gpx` | Ler trilhas GPS privadas autorizadas. |
| `write_gpx` | Enviar trilhas GPS. |
| `write_changeset_comments` | Comentar changesets; também incluído em `write_api`. |

Outros escopos existem, mas não devem ser requisitados sem justificativa. A lista e os nomes atuais estão documentados em [3].

### 4.4 Fluxo OAuth 2.0 recomendado

O OSM documenta **Authorization Code** e **Authorization Code com PKCE** [3]. Para clientes públicos (desktop, mobile e SPA), recomenda-se **PKCE**. Para backend confidencial, manter o segredo exclusivamente no servidor, e usar PKCE quando compatível com a biblioteca.

**Sequência típica:**

1. Aplicação inicia autenticação, gerando `state` e, com PKCE, `code_verifier` e `code_challenge`.
2. Navegador abre a URL de autorização do OSM com `client_id`, `redirect_uri`, `response_type=code`, `scope`, `state` e parâmetros PKCE.
3. Usuário faz login no OSM e aprova a solicitação.
4. OSM redireciona o navegador para a URI registrada com um `code`.
5. Aplicação valida o `state` e troca o `code` por `access_token` em um POST no endpoint de token.
6. Aplicação envia `Authorization: Bearer <TOKEN>` nas chamadas protegidas.

**Endpoints OAuth em produção:**

```text
Authorization: https://www.openstreetmap.org/oauth2/authorize
Token:         https://www.openstreetmap.org/oauth2/token
Metadata:      https://www.openstreetmap.org/.well-known/oauth-authorization-server
```

**Endpoints OAuth de desenvolvimento:**

```text
Authorization: https://master.apis.dev.openstreetmap.org/oauth2/authorize
Token:         https://master.apis.dev.openstreetmap.org/oauth2/token
```

**Exemplo de uso de um token já obtido:**

```bash
# Não inclua o token em comandos versionados, logs ou documentação pública.
export OSM_ACCESS_TOKEN='SEU_TOKEN_OAUTH_2'

curl --fail-with-body \
  -H "Authorization: Bearer ${OSM_ACCESS_TOKEN}" \
  -A 'ExemploOSM/1.0 (contato: contato@example.org)' \
  'https://api.openstreetmap.org/api/0.6/user/details.json'
```

Este comando **não gera** o token: ele demonstra como utilizar um token válido após completar o fluxo de autorização. Não basta enviar um `Client ID` como se fosse uma API Key.

**Ciclo de vida:** a documentação informa que os tokens OSM atualmente não expiram automaticamente em condições normais [3]; ainda assim, podem ser revogados. O código deve tratar revogação, `401` e renovação de autorização, sem presumir validade eterna.

### 4.5 Recomendações para edição

- Desenvolver e testar alterações no **ambiente de desenvolvimento** do OSM antes de enviar modificações ao banco real.
- Criar uma conta separada no ambiente de desenvolvimento: ele não compartilha contas ou dados com produção.
- Não executar rotinas automáticas de escrita sem revisar as políticas comunitárias aplicáveis a edições automatizadas.
- Usar escopos mínimos e não permitir que agentes autônomos publiquem edições sem validação apropriada.

## 5. Serviços de leitura e pesquisa sem chave universal

### 5.1 Nominatim: geocodificação e busca textual

**Função:** transformar texto em lugares/coordenadas (*forward geocoding*) e coordenadas em endereços (*reverse geocoding*). O projeto Nominatim pode ser instalado separadamente ou contratado de terceiros.

- Endpoint público de busca: `https://nominatim.openstreetmap.org/search`
- Documentação: <https://nominatim.org/release-docs/latest/api/Search/>
- Política da instância pública: <https://operations.osmfoundation.org/policies/nominatim/>

**Exemplo de busca pontual:**

```bash
curl --fail-with-body -G \
  -A 'MinhaAplicacao/1.0 (contato: contato@example.org)' \
  'https://nominatim.openstreetmap.org/search' \
  --data-urlencode 'q=Ribeirão Preto, São Paulo, Brasil' \
  --data-urlencode 'format=jsonv2' \
  --data-urlencode 'limit=3'
```

**Regras relevantes da instância pública (verificar política integral [5]):**

- Limite **absoluto de 1 requisição por segundo por aplicação**, somando os acessos dos usuários; isso **não é uma cota garantida** ou autorização para operar continuamente nesse ritmo.
- Enviar um `User-Agent` ou `Referer` que identifique a aplicação; o identificador genérico do cliente HTTP não é suficiente.
- Manter cache dos resultados e atribuição ao OSM.
- Permitir a substituição do serviço sem uma atualização do aplicativo, preferencialmente por uma camada de proxy/configuração.
- Para tarefas menores de geocodificação em lote, observar também execução em um único processo/máquina e as condições da política; scripts com execução superior a um dia ou periódica são limitados a **4 requisições por minuto**.
- **Proibido:** autocomplete implementado mediante chamadas ao Nominatim público, consultas sistemáticas para coletar todos os objetos de uma região, raspagem da página de detalhes para uso automatizado e revenda de geocodificação.
- Não enviar dados pessoais ou confidenciais nos parâmetros de pesquisa.

#### Atenção especial a LLMs e geradores de aplicações

A política oficial do Nominatim contém uma seção **“Usage in LLMs”** [5]:

- Modelos de linguagem podem sugerir esse serviço apenas apresentando claramente a política e as restrições.
- A API pública **não pode ser embutida ou oferecida como serviço genérico** de busca/geocodificação por plataformas *no-code*, *low-code* ou *vibe coding*.
- O uso é condicionado a uma escolha deliberada e consciente do desenvolvedor responsável pela conformidade.

**Implicação arquitetural:** para uma ferramenta genérica de geolocalização consumida por muitos agentes, usuários ou aplicações, **não se deve assumir que o Nominatim público seja um backend permitido**. Avaliar um Nominatim próprio ou um serviço comercial com termos apropriados.

### 5.2 Overpass API: busca por tags, objetos e regiões

**Função:** consultas espaciais e semânticas sobre dados OSM. Exemplo: encontrar farmácias, escolas, pontos de ônibus e vias dentro de uma área. Diferentemente da Editing API, é orientada a leitura [6].

- Uma instância pública importante: `https://overpass-api.de/api/interpreter`
- Documentação: <https://wiki.openstreetmap.org/wiki/Overpass_API>
- Linguagem de consulta: <https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL>
- Interface visual: <https://overpass-turbo.eu/>

**Exemplo: farmácias numa pequena bounding box:**

```bash
curl --fail-with-body -G \
  -A 'MinhaAplicacao/1.0 (contato: contato@example.org)' \
  'https://overpass-api.de/api/interpreter' \
  --data-urlencode 'data=[out:json][timeout:25];nwr["amenity"="pharmacy"](51.50,-0.15,51.52,-0.10);out center;'
```

A *bounding box* do exemplo fica em Londres e usa a ordem **sul, oeste, norte, leste**. O seletor `nwr` reúne nodes, ways e relations; `out center` inclui um ponto central para objetos sem coordenada única, mas o centro não deve ser interpretado como entrada ou localização exata do estabelecimento.

**Restrições e cuidados:**

- As políticas são específicas da instância escolhida; não existe uma cota universal para toda a rede Overpass.
- A documentação da instância principal apresenta referências orientativas de **até 10.000 consultas/dia e 1 GB/dia para uso pontual**, com tempo de processamento agregado restrito; **não são quotas asseguradas para aplicações recorrentes**.
- Para aplicações que consultam continuamente, a orientação é muito mais conservadora (aproximadamente **menos de 100 consultas/dia e menos de 10 MB/dia**, segundo a página consultada, para o caso da instância principal).
- A página recomenda **instâncias próprias ou pagas para uso comercial** e indica sobrecarga dos servidores públicos.
- Evitar paralelismo, cachear resultados, identificar o aplicativo e respeitar respostas de limitação de tráfego.

**Recomendação:** Overpass é excelente para exploração, consultas ad hoc e protótipos pequenos. Não usar como banco de dados geoespacial principal de uma aplicação comercial de alto tráfego [6].

### 5.3 Tiles raster: mostrar o mapa

Serviço público de tiles raster:

```text
https://tile.openstreetmap.org/{z}/{x}/{y}.png
```

É possível consumi-lo com bibliotecas como **Leaflet**. A biblioteca não é um serviço de hospedagem de tiles; a infraestrutura que disponibiliza os tiles tem regras próprias.

**Exemplo JavaScript (pressupõe Leaflet já instalado e o elemento HTML `#map`):**

```javascript
const map = L.map('map').setView([-21.18, -47.81], 12);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);
```

**Política obrigatória da OSMF [7]:**

- Exibir atribuição visível aos colaboradores do OSM.
- Não fazer download em massa, scraping, prefetch para uso offline ou cache-busting.
- Identificar o aplicativo adequadamente; em contexto web, permitir um `Referer` válido.
- Respeitar `Cache-Control`, `Expires` e `ETag`; se o mecanismo não interpreta os cabeçalhos, reter tiles em cache por pelo menos **7 dias**.
- Utilizar HTTPS; permitir troca futura do provedor.
- Não há SLA, capacidade garantida ou compromisso de atendimento a tráfego comercial.

**Observação:** em navegadores, o controle de `User-Agent` é do navegador, e o `Referer` é relevante. Em clientes nativos/servidores, a identificação do aplicativo via `User-Agent` é indispensável.

### 5.4 Tiles vetoriais

A OSMF mantém política própria para `vector.openstreetmap.org`, com URLs baseadas na versão do conjunto de tiles e retorno `.mvt` ou metadados TileJSON [8]. Os tiles vetoriais são diferentes dos tiles PNG e exigem estilo/renderizador compatível.

A documentação apresenta o formato:

```text
https://vector.openstreetmap.org/$VERSION/{zoom}/{x}/{y}.mvt
https://vector.openstreetmap.org/$VERSION/tilejson.json
```

Não fixar uma `$VERSION` arbitrária sem verificar os recursos e exemplos oficiais vigentes. A política também exige atribuição, identificação e cache, e não oferece SLA. Em projetos MapLibre, avaliar um provedor de tiles vetoriais com estilo compatível ou a hospedagem de um stack próprio.

### 5.5 Roteamento: serviço separado

O OSM fornece dados de vias, mas **não há um endpoint universal de roteamento na Editing API v0.6**. Para cálculo de caminhos, distância de percurso e instruções, são utilizados mecanismos como **OSRM**, GraphHopper ou Valhalla — próprios ou de fornecedores.

- Documentação de roteamento no ecossistema OSM: <https://wiki.openstreetmap.org/wiki/Routing>
- API OSRM: <https://project-osrm.org/docs/v5.24.0/api/>

Em um deployment próprio de OSRM, o formato típico é `.../route/v1/driving/{longitude},{latitude};{longitude},{latitude}`. O uso de servidores públicos de demonstração, quando disponíveis, deve seguir os termos dos respectivos operadores e não ser tratado como infraestrutura de produção.

### 5.6 Dados em lote: Planet OSM e extratos

Para baixas frequências de atualização e análises que exigem muitos objetos, a política da OSMF aponta **Planet OSM** e **extratos regionais** como alternativas à exploração massiva das APIs públicas [9][10].

Opções típicas:

- `planet.openstreetmap.org` para o conjunto global (grande volume e custos de processamento relevantes);
- extratos regionais, por exemplo de distribuidores como Geofabrik;
- processamento com ferramentas OSM e carga em banco geoespacial próprio, como PostgreSQL/PostGIS.

Este caminho evita milhares de requisições repetitivas e pode oferecer melhor previsibilidade para consultas de produção.

## 6. Licenciamento, atribuição e uso comercial

Os dados OSM são distribuídos sob a **Open Database License (ODbL)**. Isso permite copiar, adaptar e utilizar comercialmente os dados, condicionado às obrigações de atribuição e, quando aplicável, compartilhamento da base derivada sob a licença pertinente [11][12].

### 6.1 Atribuição

A forma usual de atribuição em mapas é:

```text
© OpenStreetMap contributors
```

Idealmente, com link para <https://www.openstreetmap.org/copyright>. Os detalhes variam conforme o meio (mapa interativo, imagem estática, geocodificação, base distribuída, aplicação de roteamento e outros) [12]. Não ocultar o crédito em interfaces.

### 6.2 Separação entre licença de dados e hospedagem

Há duas questões distintas:

1. **Licença:** o que é permitido fazer com os dados e quais obrigações de atribuição/compartilhamento se aplicam.
2. **Serviço:** se você pode usar determinado servidor público, em qual volume, e sob quais restrições técnicas.

A abertura do banco de dados **não cria direito a utilizar ilimitadamente a infraestrutura mantida por voluntários e doações**. Aplicações comerciais são possíveis, mas precisam de uma arquitetura compatível com as políticas operacionais.

**Nota:** esta seção é um resumo técnico, não um parecer jurídico sobre obras derivadas, bases derivadas ou obrigações de compartilhamento. Para redistribuição de bases enriquecidas, revisar integralmente a ODbL.

## 7. Arquiteturas recomendadas

### 7.1 Prova de conceito individual

```text
[Aplicação de teste]
        |
        +--> [Nominatim público]  (busca pontual, limites rígidos)
        +--> [Overpass público]   (consultas ocasionais)
        +--> [OSM raster tiles]   (mapa com atribuição/cache)
```

**Vantagens:** baixo custo inicial, configuração simples, sem credenciais OSM para operações públicas.  
**Desvantagens:** baixa previsibilidade de capacidade, serviços sem SLA, dependência de políticas mutáveis.

### 7.2 Aplicação comercial ou múltiplos usuários

```text
[Frontend / Agente]
       |
       v
[Backend geoespacial / gateway]
       |--- Autenticação e autorização da aplicação
       |--- Validação e normalização das entradas
       |--- Rate limiting / filas / cache
       |--- Logs, métricas e controle de custos
       |--- Abstração para troca de fornecedores
       |
       +--> [Geocodificação: provedor contratado / Nominatim próprio]
       +--> [POIs: base PostGIS / Overpass contratado ou próprio]
       +--> [Tiles: fornecedor contratado / hospedagem própria]
       +--> [Rotas: OSRM/Valhalla/GraphHopper próprio ou contratado]
       +--> [OSM OAuth: somente caso exista edição ou login OSM]
```

**Vantagens:** controle de segurança, custos, cache, auditoria, disponibilidade e governança das chamadas.  
**Desvantagens:** desenvolvimento e manutenção adicionais, possíveis custos de infraestrutura e de licenciamento dos fornecedores de serviços.

### 7.3 Recomendações específicas para agentes de IA e MCP

Se os recursos geográficos forem disponibilizados como ferramentas de agentes ou servidores MCP:

1. **Separar ferramentas por finalidade:** `geocode_address`, `reverse_geocode`, `search_osm_features`, `get_route` e `render_map` não precisam usar o mesmo backend.
2. **Tratar entradas de agentes como não confiáveis:** validar coordenadas, bounding boxes, tipos de tags, limites de resultado, timeout e tamanho das respostas.
3. **Impor controles no servidor:** limites por usuário/agente, cotas agregadas, cache, circuit breaker e backoff para `429`/`503`.
4. **Não embutir Nominatim público como backend genérico** de geocodificação de um produto de agentes; consultar expressamente sua política de uso em LLMs [5].
5. **Não dar escopo `write_api` por padrão:** separar leitura e edição e exigir aprovação humana para publicar mudanças no mapa.
6. **Não transmitir endereços privados, coordenadas sensíveis ou dados de clientes** inadvertidamente aos serviços públicos.
7. **Preservar atribuição e procedência** nas interfaces, resultados e dados armazenados quando aplicável.
8. **Permitir substituição de provedor por configuração**, pois um endpoint público pode restringir acesso ou alterar política.

## 8. Segurança, confiabilidade e erros comuns

| Risco/situação | Resposta recomendada |
| --- | --- |
| `401 Unauthorized` em endpoint protegido | Verificar token, escopo, revogação e fluxo OAuth. |
| `403 Forbidden` | Verificar permissões, escopos e bloqueios/restrições do serviço. |
| `429 Too Many Requests` | Reduzir volume, aplicar backoff e respeitar política específica. |
| `5xx`, timeout ou instabilidade | Retry limitado com atraso, circuit breaker, cache e fallback permitido. |
| Resultados ausentes ou incompletos | Verificar cobertura e tags OSM; não presumir completude cadastral. |
| Coordenadas trocadas | Conferir ordem: Overpass bbox usa sul/oeste/norte/leste; OSRM usa longitude,latitude. |
| Endereços em logs | Sanitizar parâmetros e impedir exposição de dados confidenciais. |
| Endpoint público embutido rigidamente | Centralizar a URL em configuração e permitir troca sem deploy disruptivo. |
| Chaves de terceiros expostas | Manter secrets em backend/cofre de segredos, usar quotas e rotação. |
| Edição automatizada acidental | Isolar ambiente de teste, restringir scopes e validar changesets. |

**Boas práticas gerais de API:** timeouts explícitos, limites de resposta, métricas, monitoramento de bloqueios, identificação do cliente, cache de respostas e tratamento de falhas com mensagens inteligíveis ao usuário. A política de cada serviço prevalece sobre recomendações genéricas.

## 9. Plano de implementação sugerido

**Fase 1 — Definir funcionalidades**

- [ ] Confirmar se haverá mapa visual, geocodificação, POIs, rotas ou edição.
- [ ] Estimar usuários, consultas por dia, pico de tráfego e regiões geográficas.
- [ ] Classificar dados pessoais e necessidade de armazenamento.

**Fase 2 — Prototipar de forma compatível**

- [ ] Testar consultas públicas ocasionais sem credenciais, com `User-Agent` apropriado.
- [ ] Usar bounding boxes pequenas e campos de resposta limitados.
- [ ] Implementar atribuição OSM e cache desde o início.
- [ ] Documentar políticas de Nominatim, Overpass e tiles para a equipe.

**Fase 3 — Resolver autenticação apenas se necessária**

- [ ] Caso exista login OSM ou edição, criar aplicação OAuth 2.0.
- [ ] Configurar URI de redirecionamento e scopes mínimos.
- [ ] Implementar Authorization Code com PKCE, estado CSRF e armazenamento seguro.
- [ ] Usar ambiente de desenvolvimento para testar escrita.

**Fase 4 — Preparar produção**

- [ ] Decidir entre infraestrutura própria e fornecedores especializados.
- [ ] Centralizar endpoints e credenciais em configuração.
- [ ] Incluir rate limits agregados, cache, métricas e fallback.
- [ ] Revisar obrigações da ODbL e atribuição.
- [ ] Validar termos de serviço, limites contratuais e SLA quando aplicável.

## 10. Perguntas frequentes

**Preciso criar conta OSM para exibir um mapa?**  
Não. Para mostrar tiles públicos seguindo a política de uso, não é exigido login OSM.

**Existe uma página para gerar “minha chave API do OpenStreetMap”?**  
Não existe uma chave universal equivalente às de determinados provedores comerciais. O registro em <https://www.openstreetmap.org/oauth2/applications/new> cria um cliente **OAuth 2.0** para as funcionalidades autenticadas do OSM.

**Posso usar o OpenStreetMap gratuitamente em um produto comercial?**  
Os dados são abertos sob a ODbL e podem sustentar soluções comerciais. Porém os **servidores públicos** têm políticas, capacidades e restrições próprias; produção comercial recorrente pode exigir serviço contratado ou infraestrutura própria.

**Nominatim e Overpass exigem OAuth?**  
Em suas instâncias públicas comuns de leitura, normalmente não. Isso não elimina limites, bloqueios, regras especiais ou autenticação imposta por fornecedores privados.

**Uma API Key de um provedor de mapas é igual ao token OAuth do OSM?**  
Não. A primeira é uma credencial definida pelo fornecedor; o token OAuth OSM representa autorização para operações protegidas na plataforma OSM.

**A Editing API serve como serviço de busca de estabelecimentos ou roteamento?**  
Não é a ferramenta adequada. Para buscar objetos por tags use Overpass; para geocodificação, Nominatim ou equivalente; para rotas, um motor de roteamento.

## 11. Conclusão técnica

A pergunta “preciso de uma chave API para usar OpenStreetMap?” só pode ser respondida corretamente **depois de identificar o serviço e a finalidade da integração**.

- **Não** para consultas públicas ocasionais, Overpass público, Nominatim público e tiles públicos, respeitadas as políticas individuais.
- **Sim, OAuth 2.0**, quando a aplicação precisa editar o mapa, autenticar usuários pelo OSM ou acessar recursos protegidos.
- **Possivelmente chave de fornecedor**, quando se escolhe uma empresa de geocodificação, roteamento ou hospedagem de tiles; é uma chave daquele serviço, não da base OSM.

**Recomendação final:** começar com uma arquitetura modular e de baixo tráfego para validar o caso de uso. Antes do lançamento, projetar uma camada própria de acesso a provedores e selecionar serviços com condições compatíveis com o tráfego e o modelo comercial. Em particular, não transformar endpoints comunitários públicos em backend genérico de uma plataforma de agentes de IA.

---

## 12. Fontes consultadas

Fontes prioritariamente oficiais; acessadas ou verificadas em **12/11/2026**.

1. **OpenStreetMap Wiki — API (página inicial):** <https://wiki.openstreetmap.org/wiki/API>
2. **OpenStreetMap Wiki — API v0.6:** <https://wiki.openstreetmap.org/wiki/API_v0.6>
3. **OpenStreetMap Wiki — OAuth (incluindo registro de aplicações, scopes e endpoints):** <https://wiki.openstreetmap.org/wiki/OAuth>
4. **OpenStreetMap Wiki — Atualização de autenticação de 2024:** <https://wiki.openstreetmap.org/wiki/2024_authentication_update>
5. **OpenStreetMap Foundation — Nominatim Usage Policy:** <https://operations.osmfoundation.org/policies/nominatim/>
6. **OpenStreetMap Wiki — Overpass API (instâncias e políticas):** <https://wiki.openstreetmap.org/wiki/Overpass_API>
7. **OpenStreetMap Foundation — Tile Usage Policy (raster):** <https://operations.osmfoundation.org/policies/tiles/>
8. **OpenStreetMap Foundation — Vector Tile Usage Policy:** <https://operations.osmfoundation.org/policies/vector/>
9. **OpenStreetMap Foundation — Editing API Usage Policy:** <https://operations.osmfoundation.org/policies/api/>
10. **OpenStreetMap Wiki — Downloading data:** <https://wiki.openstreetmap.org/wiki/Downloading_data>
11. **OpenStreetMap — Copyright and License:** <https://www.openstreetmap.org/copyright>
12. **OpenStreetMap Foundation — Attribution Guidelines:** <https://osmfoundation.org/wiki/Licence/Attribution_Guidelines>
13. **Nominatim — Search API Reference:** <https://nominatim.org/release-docs/latest/api/Search/>
14. **OpenStreetMap Wiki — Overpass QL:** <https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL>
15. **OpenStreetMap Wiki — Routing:** <https://wiki.openstreetmap.org/wiki/Routing>
16. **OSRM — HTTP API:** <https://project-osrm.org/docs/v5.24.0/api/>

**Nota sobre atualizações:** limites e políticas citados são específicos dos operadores e da data da consulta. Antes de colocar uma integração em produção, consultar novamente os documentos oficiais aplicáveis.
