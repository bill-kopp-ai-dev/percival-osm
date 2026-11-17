# ADR — Transporte assíncrono e prazo integral para chamadas upstream

- **Estado:** aceito
- **Data:** 2026-11-17
- **Decisor:** Bill Kopp

## Contexto

O prazo de execução do MCP precisa incluir fila, rate limit, retries, leitura e
cleanup. O caminho ORS síncrono via `asyncio.to_thread` não interrompe a chamada
HTTP ao cancelar o await. A leitura GET também bufferizava `response.content`
antes de aplicar o limite configurado.

## Decisão

- O caminho de produção ORS usa POST assíncrono com `httpx`, sem retry implícito;
  mantém endpoint, perfis, JSON, unidades e autorização no header. O SDK
  `openrouteservice` e seus caminhos síncronos foram removidos após migrar
  produção e testes.
- Cada tool upstream reserva parte do limite configurado para cleanup. O prazo
  de execução usa relógio monotônico do timeout estruturado do `asyncio`; o
  cleanup de tasks e clientes HTTP tem um único limite curto, sem drains
  sequenciais de 25 s e 2 s.
- Nominatim, Overpass e ORS leem os corpos por streaming, interrompendo a leitura
  assim que o limite de bytes é excedido. Redirects seguem desativados por
  padrão e URLs de cada salto continuam sujeitas à allowlist.
- Cancelamento propaga sem ser absorvido pelo limiter nem transformado em retry.

## Consequências

Chamadas canceladas deixam de manter worker thread ORS. Erros HTTP/transportes
ORS são convertidos para falha upstream controlada sem revelar chave, URL ou
corpo. A dependência do SDK foi retirada de `pyproject.toml` e `uv.lock`.

## Evidência inicial

Fixtures locais verificam perfil, coordenadas, unidades, segredo somente no
header, propagação de cancelamento, interrupção por tamanho e deadline/cleanup.
Os conjuntos focados de regressão passaram; resultado consolidado está no plano
e na issue de cache/cleanup fechada.
