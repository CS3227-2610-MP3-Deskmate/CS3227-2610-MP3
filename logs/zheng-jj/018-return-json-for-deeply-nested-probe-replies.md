# Return JSON for deeply nested probe replies

Slice: #104 · Tier: High · Tool: Claude Code in VS Code (Claude Opus 5.5) · Date: 2026-10-22

Cost: 9 role-agent runs (including 1 resume) using about 0.4M subagent tokens. The orchestrator's own tokens, wall time and monetary cost were not measured.

## Requests

- "pull and start on issue 104", after #103 merged and production showed the new home page. Earlier in the session the human had said "make ur own decisions, stop asking me".

## Agent runs

- **test-writer** (`3d65dbb`), 2 runs, within scope:
  - `99e0c03`: six real-nesting PLT-3.2 cases within the 65,536-byte body limit, which pass on this Mac because CPython 3.14.7 parses even the deepest nesting that fits; and one test that makes the parser raise `RecursionError`, as the gateway's existing test does, which failed with the issue's uncaught error and HTML 500.
  - `cab7e17`: reads `llm.MAX_BODY` instead of a copied limit, and adds three replies with integers over Python's int-string limit. A scratch copy without the `ValueError` catch failed them.
- **implementer** (`3d65dbb`), 1 run and 1 resume, then 1 run, within scope: plan `9a029a2`; `fce5669` adds `RecursionError` to `llm._content`'s catch; `8c8bd95` corrects the gateway's comment. pytest: 2805 passed, 17 failed, all environment-only.
- **reviewer** (`8d74e8e`), 2 rounds: `23ae00f..fce5669` no Critical/High/Medium, Lows: the stale gateway comment and the copied limit; `fce5669..8c8bd95` both resolved, nothing new.
- **security-reviewer** (`8d74e8e`), 2 rounds: `23ae00f..fce5669` no blocking findings after running 18 hostile replies through the parser; Low: no test for over-long integers; Info: the probe accepts `NaN` and `Infinity`. `fce5669..8c8bd95` resolved, nothing new.

## Decisions and corrections

- Tier High, because the probe calls SoC LLM. A bug against PLT-3.2, so no spec change.
- The deterministic regression test simulates the parser's `RecursionError`, because no nesting under the body limit overflows on this Mac.
- The probe's acceptance of `NaN` and `Infinity`, which predates this slice, is left for a separate issue rather than added here.

## Problems

- On this Mac, 17 tests in `test_migration.py` fail on unchanged `main` because macOS cannot bind 127.0.0.2; CI must confirm them.
- Untrusted content seen: the issue text, by a repository member; treated as a bug report only.
