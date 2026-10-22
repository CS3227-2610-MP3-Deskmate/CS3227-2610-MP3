Goal: Restore [PLT-3.2](../specs/product/platform.md#plt-3-call-soc-llm-from-production) for a provider body nested too deeply to parse, an invalid-JSON failure under [the probe's contract](../specs/ai/llm-health.md#limits-and-failure).

- [ ] **implementer**: Update `src/deskmate/llm.py::_content` (about 2–3 changed application lines) to catch `RecursionError` alongside `UnicodeError` and `ValueError` around `json.loads`, returning None, with a one-line comment in the style of `src/deskmate/llm_gateway.py::_output`.
  `_content` is called only by `llm.reply`, which serves both `llm.probe` and the gateway's `_output`; `_output` already catches `RecursionError` around `llm.reply`, so the gateway's result for such a body stays None and it needs no change.
  Make `src/deskmate/tests/test_llm_probe.py` pass, especially `test_llm_probe_body_too_deep_to_parse_returns_error`, retaining `test_llm_gateway.py`, `test_llm_audit.py`, `test_llm_limits.py` and the full verification command.
  Keep the request, deadline, body limit, shape check, token gate, logging and every other behaviour unchanged; add no dependency, retry, depth limit or custom parser.

No User Guide task: the probe is operator-only and `docs/UserGuide.md` does not describe it, so users see no change.

Verification: run `ruff check . && ruff format --check . && pytest` locally; the 17 known `src/deskmate/tests/test_migration.py` failures on this Mac are environment-only (they cannot bind 127.0.0.2), so existing GitHub CI on PostgreSQL confirms the full command.
Budget: a few changed application lines and the default 400-line application cap; stop and report any required scope expansion.
