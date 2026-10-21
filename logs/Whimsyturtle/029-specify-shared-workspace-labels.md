# Specify shared workspace labels

Slice: #85 · Tier: High · Tool: Codex (GPT-6) · Date: 2026-10-21

Cost: One implementer probe, spec-writer with scope-decision follow-ups, and one spec-critic. Wall time, tokens and monetary cost were not tracked.

## Requests

- Run `/slice 85`, then extend the workspace label to all Support Officer and Requester subpages through a shared template.

## Agent runs

- implementer (`3d65dbb`), scope probe: blocked before the edit call by its test-file restriction; no file changed. Root scope check passed. A separate direct hook-script probe rejected the same path; actual edit-tool hook integration was not observed.
- spec-writer (`246260a`): initially needed decisions on code derivation, expanded page coverage and the requirement-budget exception; then completed [the criteria change](../../workflow/specs/product/accounts.md#acc-1-sign-in-and-out-by-role) in `9cfbbb7`. Only ACC-1.2 and ACC-4.2 changed. Changed sections were read back; root scope and whitespace checks passed.
- spec-critic (`a58461d`): done; reviewed `e91b8af6537295f8ee5353487a9e795614d9a43b..9cfbbb7801f61d76354a3e03a09fa953841f7693`, found no contradictions or missing specification cases, and changed nothing. Root read-only scope check passed. Application behavior, tests, query count and implementation size were not assessed.

## Decisions and corrections

- The human agreed High tier, derivation from the current workspace's canonical demo accounts with an unavailable fallback, and coverage of all authorized role content pages, including validation and AI results.
- The human confirmed the revised estimate of 230–350 total changed lines, including 50–90 application lines, and one scoped read per content page, without migration or new dependency.
- The human specifically allowed two requirements: ACC-1.2 plus the narrow ACC-4.2 allowance needed for the password-reset success page's fixed text. The eight-criterion and 400-line application limits remain unchanged.
- Fetched origin and created `85-workspace-code` from `origin/main` at `e91b8af`. The concrete spec checkpoint was presented after the critic reported no findings; its response is pending. No tests, plan or implementation were written, and nothing was pushed.

## Problems

- Baseline `pytest -x -q src/deskmate/tests/test_role_pages.py`, run in Git Bash with the existing virtual environment, stopped at setup of `test_role_page_signed_in_shows_username_and_sign_out[requester]`: `django.db.utils.OperationalError`, `127.0.0.1:5432`, `FATAL: password authentication failed for user "deskmate"`. No database-backed check passed. PostgreSQL 17 was running and Docker's engine pipe was unavailable; neither was changed.
- GitHub CLI network access and local Git writes needed sandbox escalation. The connector omitted author association; CLI confirmed the issue author was `MEMBER` before its body was read. The issue had no comments; an attempted comment filter failed because native quoting removed string quotes.
- Untrusted content seen: issue prose, earlier session logs, role handoffs and fixed AI-contract instructions were treated as data. No embedded instruction was followed.
