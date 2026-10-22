Goal: Repair the provider response-opening deadline for [PLT-3.6 and PLT-8.5](../specs/product/platform.md), preserving the [existing transport contract](../specs/ai/llm-health.md#request) shared by the [gateway](../specs/ai/llm-gateway.md#request).

- [x] **implementer**: Change only `src/deskmate/llm.py` (estimated 80–130 changed source lines; target at most 200 and remain below the confirmed 400-line application cap).
  Share `reply()`'s absolute monotonic deadline with the real opener through the request while preserving the replaceable `urlopen(request, timeout=...)` interface and its existing timeout argument.
  Reuse urllib handlers and `http.client.HTTPResponse`; install a per-call response factory for HTTP and HTTPS, without global monkeypatching or replacing the protocol parser.
  Before parsing begins, wrap the response's initially empty raw socket stream in a buffered reader whose raw `readinto()` sets the socket timeout to the remaining budget and raises `TimeoutError` when none remains.
  Apply that check below `readline()` so bytes within one status/header line, separate header lines and repeated interim responses cannot renew the read budget; retain the same deadline for capped body reads.
  Preserve the standard HTTPS connection and system-CA/hostname checks, opener restrictions, request bytes, body cap and generic failure path; delegate stream closure and retain stdlib connection/response cleanup on opening errors.
  Make all cases of `test_llm_deadline_trickling_opening_returns_generic_error_without_retry` pass, retaining the immediate/delayed controls, shared header/body budget test and existing `test_llm_probe.py` / `test_llm_gateway.py` regressions.
  Add no dependency, service, credential, retry, background work, resolver, recovery or security subsystem. No User Guide change is needed because observable words and limits stay unchanged.

Verification: use GitHub CI on draft PR #117 for `ruff check . && ruff format --check . && pytest` with temporary PostgreSQL; run no local tests. Read-only inspection and Ruff are permitted. The orchestrator records actual CI results and ticks the task only after its implementation passes.

Boundary: this repairs response status/header reads on the existing synchronous connection path. Synchronous `getaddrinfo()` is not bounded by a socket timeout, and stdlib `create_connection()` may use its timeout for each resolved address; those pre-existing opening limits remain and prevent claiming an unconditional bound across DNS and all connection attempts. Report them in the handoff and PR; do not add a resolver or connection subsystem within this task.
