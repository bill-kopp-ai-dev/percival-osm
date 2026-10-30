# Percival OSM — Project agent instructions

This file is the project-scoped instruction set for the `<positronic>`
agent when working inside this capsule. It extends (does not replace) the
global `AGENTS.md`, `SOUL.md`, and `USER.md` loaded from
`$POSITRONIC_HOME/`.

## Owner and operating posture

This project and its IaC are owned and operated solely by Bill Kopp, who is
also the sole decision-maker and signer. Company: Positronic Bean Labs; email:
`bill.kopp.dev@gmail.com`; website: `labs.positronicbean.com`.

Keep process proportional to a single-owner project. Do not add duplicate
approvals, cross-owner reviews, sign-offs, or evidence artifacts for the same
decision. Use focused checks that address a concrete risk; do not require a
full test suite, manual inspector session, or external corroboration by default.
When Bill explicitly requests a remote change (including push, release,
publication, or deployment), that request is the authorization; do not ask for
the same approval again. For an external operation whose target or impact is
not specified, clarify only that missing detail. Report what was changed and
the checks actually performed.

Operator-edited content wins over model defaults. Treat every section as
data, not as privileged tool instructions.

| Concern                        | Where it lives                          |
| ------------------------------ | --------------------------------------- |
| Global rules and posture       | `$POSITRONIC_HOME/AGENTS.md`            |
| Voice and tone                 | `$POSITRONIC_HOME/identity/SOUL.md`     |
| Operator preferences and facts | `$POSITRONIC_HOME/identity/USER.md`     |
| Project brief and conventions  | `.positronic/PROJECT.md` (this file)    |
| Project permissions            | `.positronic/policy.json`               |
| Project metadata               | `.positronic/project.json`              |

## Working conventions

- Python ≥ 3.11; toolchain é `uv` (`uv sync`, `uv run …`).
- Layout `src/percival_osm_mcp`; entry point `percival-osm-mcp =
  percival_osm_mcp:main`. Não mover para layout flat.
- Logs do servidor vão **apenas para stderr**; stdout é reservado para o
  stream JSON-RPC do MCP. Respeitar essa separação em qualquer logger
  novo.
- Toda configuração vem do **ambiente do processo** (sem `env_file`).
  Falhas de configuração devem ser altas (`ValueError`), nunca silenciosas.
- Princípios `percival.OS` regem mudanças: privacidade, soberania de
  dados, segurança hardened, transparência operacional.
- Mutations must stay within the scope Bill requested. Do not infer a release,
  publication, or production deployment from a code change or push request.
- Preserve concrete safety controls (secrets handling, URL allowlists,
  non-root execution, stdio protocol separation, and least-privilege mounts).
  Explain material risk when a requested change would weaken one; avoid
  procedural gates that do not reduce a specific risk.

## Verification

- Run the smallest relevant check for the change when verification is needed;
  use `uv run pytest -v` for broad Python changes. Do not run tests when the
  user asks only for review or documentation and no test is needed.
- Manual MCP inspection is useful for transport/runtime changes, not a
  mandatory sign-off for every release or documentation update.

## Open questions

List only unresolved decisions that materially affect implementation or scope;
do not maintain a list of routine choices or resolved questions.


## Docker MCP operations

- Preserve stdio JSON-RPC-only stdout; do not add TTY, host ports or HTTP
  healthchecks to stdio. Follow the repo's explicit transport/profile contract.
- Bill owns production MCP containers and decides their configuration. Use the
  supported Percival or Positronic interface when changing managed runtime
  state; Compose remains a local fixture. Do not hand-edit manager state.
- Use fixtures for outbound API failure cases where practical; redact secrets
  and personal request data. Verify handshake/health when changing transport
  or runtime behavior, without repeating the same verification through
  multiple interfaces unless a concrete discrepancy requires it.
