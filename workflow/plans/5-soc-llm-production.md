# Call SoC LLM from production

Implement [PLT-3](../specs/product/platform.md#plt-3-call-soc-llm-from-production) with one fixed, operator-triggered SoC LLM call from the deployed app, using only the standard library.

- [x] test-writer: Add PLT-3.1-3.7 coverage in `src/deskmate/tests/test_llm_probe.py` using a fake provider and the existing `database_outage` fixture; cover the 403 -> 405 -> 404 -> 503/200 order, `/health/llm` without a slash, token cases, exact request body and headers, the 10-second total timeout, no retry, no logging and no database access. Make the tests fail for the expected reason, then run the verify command.
- [x] implementer: Add the probe client and view in `src/deskmate/llm.py` and `src/deskmate/views.py`, register `/health/llm/` in `src/deskmate/urls.py`, and use `hmac.compare_digest`, standard-library HTTP, system TLS, no redirects, no proxy, a 10-second total deadline and a 65,536-byte response cap. Make the tests pass, then run the verify command.
- [x] test-writer: Add `SOC_LLM_` to the test configuration discard rule in `src/deskmate/tests/environment.py`; use only fixed non-secret placeholders and a fake provider.
- [x] devops: Add empty `SOC_LLM_API_KEY=` and `SOC_LLM_PROBE_TOKEN=` placeholders to `.env.example`; do not add a dependency.
- [x] orchestrator: Update `docs/DeveloperGuide.md` with the operator setup and the manual PLT-3.7 check; record only the result, never the token or key.
- [x] reviewer and security-reviewer: Review the diff, including prompt injection, secret handling, route order and test isolation.
