# Call SoC LLM from production

Goal: Satisfy [PLT-3](../specs/product/platform.md#plt-3-call-soc-llm-from-production) by making one fixed, operator-triggered SoC LLM call from the deployed app, using only the standard library.

Status: blocked at the High-tier checkpoint. The spec at `0c24e82` adds an operator token and a second production credential. Do not implement or write tests until the human confirms the scope and the decisions below.

## Blocking decisions

- Scope: approve `GET /health/llm/` plus optional `SOC_LLM_API_KEY` and `SOC_LLM_PROBE_TOKEN`, or choose a smaller operator-only call.
- Missing values: keep both optional so the app starts and the probe returns `404`/`503`, or make a missing key stop production startup.
- `.env.example`: add empty `SOC_LLM_*` placeholders, or leave the names out.
- Token: 32+ printable ASCII, `hmac.compare_digest`, exact `Bearer <token>`, rotate on suspected leak.

## Proposed tasks after confirmation

- [ ] test-writer: Add PLT-3.1?PLT-3.7 tests using a fake provider and the existing `database_outage` fixture; cover the 403 -> 405 -> 404 -> 503/200 order, `/health/llm` without a slash, token cases, exact request body and headers, the 10-second timeout, no retry, no logging, and no database access.
- [ ] implementer: Add the probe client and view under `src/deskmate/`, register `/health/llm/` in `src/deskmate/urls.py`, and use `hmac.compare_digest`, standard-library HTTP, system TLS, no redirects, a 10-second total timeout and a 65,536-byte response cap.
- [ ] test-writer: Add `SOC_LLM_` to the test configuration discard rule in `src/deskmate/tests/environment.py`; use only fixed non-secret placeholders and a fake provider.
- [ ] devops: Add empty `SOC_LLM_API_KEY=` and `SOC_LLM_PROBE_TOKEN=` placeholders to `.env.example` if approved; do not add a dependency.
- [ ] implementer: Update `docs/DeveloperGuide.md` with the operator setup and the manual PLT-3.7 check; record only the result, never the token or key.
- [ ] reviewer and security-reviewer: Review the diff, including prompt-injection, secret handling, route order and test isolation.

## Handoff

- Spec draft: `0c24e82` on `5-soc-llm-production`.
- The spec-critic found ten issues. The first is the scope decision above. The rest are reflected in the reviewed spec text; apply any uncommitted revisions before tests.
- No implementation, tests or plan tasks have been started.
