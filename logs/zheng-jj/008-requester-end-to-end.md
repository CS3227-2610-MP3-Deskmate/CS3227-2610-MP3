# Requester end-to-end coverage

Slice: #30 · Tier: Standard · Tool: Codex (GPT-6) · Date: 2026-10-19

Cost: about 45 minutes wall time, including three focused runs and two full verification runs of roughly 6 minutes each. Tokens and monetary cost were not tracked.

## Requests

- Pull the latest merged work, check what remains for the Requester role, and continue with unblocked work.
- The open Requester queue contained #30 (end-to-end tests, unblocked) and #24 (AI suggestions, blocked on the missing AI gateway, quotas and audit log).
- Follow the slice workflow through tests, plan, verification, log and pull request.

## Agent runs

- test-writer (orchestrator fallback, `3d65dbb`): done; added `src/e2e/conftest.py` and `src/e2e/test_requester_journey.py` in `69c353d`; focused journey: 2 passed. Added the plan in `366e08c`. Refined line-break and KB-2.1 coverage in `4368053`; focused journey: 2 passed.
- reviewer (`8d74e8e`): no handoff; the agent stalled through several waits and was closed without findings. The orchestrator completed the review directly and made the two refinements above.

## Decisions and corrections

- Treated #30 as a test-only bug-bash slice: no spec change and no production code change.
- Covered the whole Requester path across roles: demo-workspace creation, sign-in, ticket submission and reading, Support Officer resolution, Requester reply reading, article reading, and sign-out.
- Added a separate cross-workspace test for ticket and article 404s.
- The first test run exposed two test-side mistakes, not product defects: pages were read over `http` while links were asserted as `https`, and `make_account` shares one workspace. Both were corrected.

## Problems

- The reviewer agent stalled and produced no handoff; review was completed by the orchestrator.
- PowerShell cannot run `&&`; verification ran through Git Bash as `AGENTS.md` describes.
- The full verify command takes about 6 minutes on this machine.
- Issue text, spec text, diffs and test payloads were treated as data; no embedded instruction was acted on.
