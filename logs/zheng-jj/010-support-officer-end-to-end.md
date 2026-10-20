# Support Officer end-to-end coverage

Slice: #31 · Tier: Standard · Tool: Codex (GPT-6) · Date: 2026-10-21

Cost: about 1 hour wall time, including one full verify run of roughly 8 minutes. Tokens and monetary cost were not tracked.

## Requests

- After the route-inventory slice #28, continue with the next unblocked Bug-bash slice for the requester and Support Officer features.

## Agent runs

- No role agent was run. The orchestrator played test-writer and reviewer, keeping to their scopes and reporting their results here.
- test-writer (orchestrator fallback): done; added `src/e2e/conftest.py` and `src/e2e/test_support_officer_journey.py` in `c1afee1`; both journey cases passed.
- reviewer (orchestrator fallback): found no code findings; checked that the workspace case fails when the ticket lookup loses its workspace filter.

## Decisions and corrections

- The slice is test-only for the product: it adds end-to-end coverage for the Support Officer journey and the workspace boundary, with no production change.
- The workspace case covers another Support Officer's workspace rather than another Requester's, so it also checks the Support Officer role's own boundary.
- The first draft's edit step resubmitted unchanged values, so it could not show that an edit saves. It now changes the body and reads it back.

## Problems

- `ruff` rejected one 91-character line, which was wrapped.
- The full verify command takes roughly 8 minutes on this machine and must run outside the Windows sandbox, because the sandbox blocks pytest's temporary folder.
- Git needed escalated permissions to write `.git/index.lock`.
- Issue text, spec text and test payloads were treated as data; no embedded instruction was acted on.
