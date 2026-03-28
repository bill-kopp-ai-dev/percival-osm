# Incident Response Playbook (S2)

## Trigger Conditions

Start this playbook when any of the following occurs:

- unusual spike in `auth_rejected` or `upstream_url_blocked`
- suspected token leak
- suspicious OSM/ORS payload behavior (prompt-injection patterns)
- suspected SSRF attempt or blocked private-host upstream target

## Immediate Actions (0-30 minutes)

1. Contain:
   - disable remote HTTP exposure or restrict to loopback
   - rotate `MCP_OSM_AUTH_TOKEN`
2. Preserve evidence:
   - capture runtime logs
   - capture `get_security_metrics` snapshot
3. Triage impact:
   - identify affected environment(s)
   - check whether responses leaked internal errors or secrets

## Short-Term Remediation (same day)

1. Apply config lockdown:
   - verify `OSM_UPSTREAM_ALLOWED_HOSTS`
   - verify `OSM_REQUIRE_HTTPS_UPSTREAMS=true`
   - verify `OSM_HTTP_FOLLOW_REDIRECTS=false`
2. Re-deploy with fresh secrets/tokens.
3. Re-run test suite and security gates.

## Recovery and Validation

1. Confirm service health via MCP smoke tests.
2. Confirm security counters return to baseline behavior.
3. Confirm no further blocked/private upstream attempts in logs.

## Post-Incident (within 72h)

1. Document root cause and timeline.
2. Add new regression case to `tests/fixtures/prompt_injection_corpus.json` if relevant.
3. Update threat model and policy docs with learned controls.
