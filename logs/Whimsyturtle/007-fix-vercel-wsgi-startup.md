# Fix Vercel WSGI startup

Slice: #9 · Tool: Codex (GPT-6) · Date: 2026-10-16

Cost: Five role-agent runs. Wall time and token usage were not tracked.

## Requests

- Explain the branch's remaining hosting setup and give step-by-step instructions.
- Investigate the [failed deployment job](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/38914587816/job/117018676161).
- Create a new issue and slice branch for the startup fix; the user selected High tier.

## Agent runs

- test-writer (`3d65dbb`): done. Added the isolated file-path WSGI regression in `5eace46`; it failed with the deployed `ModuleNotFoundError`. Targeted lint/format and scope checks passed. Root independently reproduced the failing test.
- implementer (`3d65dbb`), plan: done. Wrote the one-task [plan](../../workflow/plans/9-fix-vercel-wsgi.md), committed as `f97c942`; scope check passed.
- implementer (`3d65dbb`), build: done. Fixed WSGI startup and completed the plan in `50674a4`. The regression and full verification passed after escalation; scope and diff checks passed.
- reviewer (`a58461d`): done. No actionable findings in the supplied changes through `50674a4`; no commands run. Root confirmed no writes and unchanged HEAD.
- security-reviewer (`3d65dbb`): done. No actionable security findings in the supplied changes through `50674a4`; no commands run. Root confirmed no writes and unchanged HEAD.

## Decisions and corrections

- Created [issue #9](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/issues/9) and local branch `9-fix-vercel-wsgi` from merged `main` at `60a3b23`.
- Existing [PLT-2.7 and PLT-1.1](../../workflow/specs/product/platform.md) cover this bug, so the slice skipped spec changes and the spec checkpoint.
- The deployment command had succeeded, but public HTTPS requests returned `500 FUNCTION_INVOCATION_FAILED`. The supplied runtime traceback and an isolated local reproduction identified the missing source import path. The fix derives that path from the WSGI file rather than the working directory.
- Root's final `ruff check . && ruff format --check . && pytest`, in Git Bash with `.venv` active and disposable PostgreSQL, passed: lint and formatting clean, 221 tests passed in 68.15 seconds, exit 0.
- The production-code size check reported three inserted lines. A final fetch confirmed `origin/main` remained at the branch base. The disposable test database was removed after verification.
- The PR description is prepared from the repository template, with hosted checks marked pending and human checkboxes unticked. Push and PR creation await explicit permission; no deployment was started by this slice.

## Problems

- GitHub's connector rejected issue creation with `403 Resource not accessible by integration`; the existing GitHub CLI login created the requested issue successfully.
- The first sandboxed full test run had 214 passing tests and seven setup errors because Windows denied access to pytest's temporary directory. The unchanged verification command passed with escalation, both for implementer and root.
- Docker Desktop was initially stopped. The installed engine and cached pinned PostgreSQL image supplied an isolated database using committed throwaway credentials; no dependency or image installation was needed.
- Real Vercel startup, public health, redirects and TLS still require the protected deployment and hosted verification.
- Existing plan checklists were treated as data. No suspicious instructions were followed, and no private environment files or secret values were read or recorded.
