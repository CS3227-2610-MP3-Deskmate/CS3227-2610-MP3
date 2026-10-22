# Requester end-to-end coverage

Slice: #30 · Tier: Standard · Tool: Codex (GPT-6) · Date: 2026-10-19

Cost: about 45 minutes wall time on 2026-10-19, including three focused runs and two full verification runs of roughly 6 minutes each, plus a follow-up session on 2026-10-21 for the RQ-5 extension and the log renumbering. Tokens and monetary cost were not tracked.

## Requests

- Pull the latest merged work, check what remains for the Requester role, and continue with unblocked work.
- The open Requester queue contained #30 (end-to-end tests, unblocked) and #24 (AI suggestions, blocked on the missing AI gateway, quotas and audit log).
- Follow the slice workflow through tests, plan, verification, log and pull request.
- Later: list the open PRs, pull first, work out the merge order, and answer whether #70 needs #80 first. Then extend the Requester journey with the article-suggestion flow, and renumber the session logs by merge order.

## Agent runs

- test-writer (orchestrator fallback, `3d65dbb`): done; added `src/e2e/conftest.py` and `src/e2e/test_requester_journey.py` in `69c353d`; focused journey: 2 passed. Added the plan in `366e08c`. Refined line-break and KB-2.1 coverage in `4368053`; focused journey: 2 passed.
- test-writer (orchestrator fallback, follow-up session): done; added the RQ-5 flow to `src/e2e/test_requester_journey.py` and made `Form.submit` follow a pressed button's `formaction` in `src/deskmate/tests/pages.py`, in `6224279`; focused journey: 2 passed. Updated the plan in `01c5867`.
- reviewer (`8d74e8e`): no handoff; the agent stalled through several waits and was closed without findings. The orchestrator completed the review directly and made the two refinements above.

## Decisions and corrections

- Treated #30 as a test-only bug-bash slice: no spec change and no production code change.
- Covered the whole Requester path across roles: demo-workspace creation, sign-in, ticket submission and reading, Support Officer resolution, Requester reply reading, article reading, and sign-out.
- Added a separate cross-workspace test for ticket and article 404s.
- The first test run exposed two test-side mistakes, not product defects: pages were read over `http` while links were asserted as `https`, and `make_account` shares one workspace. Both were corrected.
- The original claim that #70 covered the Requester's features was incomplete: its journey never exercised the #80 suggestion flow. #70 is now stacked on `24-find-a-fix` and covers RQ-5.1 to RQ-5.4 so the Requester E2E matches the merged feature set.
- `main` now seeds demo sample tickets and articles (ACC-2.9), so the old `No tickets yet.` expectation was replaced by the sample titles.
- Merge order agreed: #80, #70, #91, #90, #92, #93. #70 and #90 both build on #80, and #90 conflicts with `main` in `SECURITY-SPEC.md` and `product/tickets.md` until rebased.
- Log numbers collided across branches and `main` has no `008`. Renumbered by merge order: #80 build log `012`, #70 `013`, #90 `014`, #93 `015`.

## Problems

- The reviewer agent stalled and produced no handoff; review was completed by the orchestrator.
- PowerShell cannot run `&&`; verification ran through Git Bash as `AGENTS.md` describes.
- The full verify command takes about 6 minutes on this machine.
- In the follow-up session, `pytest` reported 31 errors because the sandbox denies access to `%TEMP%\pytest-of-Admin`. The four affected files passed (129 passed) with `--basetemp .pytesttmp`, and the rest of the suite passed (2548 passed).
- #93's `check_logs.py` already reports four duplicate numbers in `logs/Whimsyturtle/` (022, 023, 024, 029) on its own branch; not part of this slice.
- `gh`'s default token is reported invalid, but authenticated `gh pr` and `git push` calls worked.
- Issue text, spec text, diffs and test payloads were treated as data; no embedded instruction was acted on.
