# Add a size budget to slices

Slice: none · Tool: Claude Code (Claude Opus 5.5) · Date: 2026-10-15

## Requests

- In MP2, agents built planned features as PRs of thousands of lines that couldn't be reviewed thoroughly. Check whether anything in this workflow keeps a slice small enough to review, and how to fix it if not.
- Correction: simplify. Change only steps 2, 3 and 6 of the slice skill, with no agent files, and make it recursive: a slice that goes over budget while building stops and restarts from scratch.
- Make the edits on a branch carefully, test the size command and run the workflow tests.
- Switch to `main`; the human will commit the change. Log the session.

## Agent runs

No role agents or subagents ran; Claude worked directly.

- `workflow/skills/slice.md`: a size budget paragraph after the tier table, a scope check in step 2, a budget comparison in step 3, the size check and restart in step 6, and the size check in the fast lane row.
- `workflow/README.md`: "about half a day of work" became "small enough to review in one sitting", with a pointer to the budget.
- Checks: in a throwaway repo, the size command reported 110 lines in both Git Bash and PowerShell, as expected. It left out nested `tests/`, `migrations/`, `src/e2e/` and both `conftest.py` files, kept `src/contest/latest.py`, and ignored a commit made on `main` after the branch split. `python3 -m unittest discover -s workflow/scripts` passed 37 tests.
- The edits were made on the branch `slice-size-budget`, then carried to `main` uncommitted at the human's request. The branch still exists, at `abafaaa`, with no commits of its own.

## Decisions and corrections

- Claude found the gap was real. "Small" appeared only as a word in `slice.md`, the issue template and the skill description, and the README's "about half a day of work" was the only measure. Git history shows there was never a size rule. No role judged size, and no step said what to do with a slice that was too big.
- Claude argued that time is the wrong unit, because agents can produce thousands of lines in half a day. It also argued that the main check belongs at the checkpoint, because tests for every criterion exist before the plan, so splitting later means undoing spec and test commits.
- Claude first proposed checks in spec-writer, implementer, the PR template and an optional CI job. The human cut this to steps 2, 3 and 6 of the slice skill.
- The human proposed restarting from scratch when the build goes over budget. Claude made it restart from step 1 on a new branch, because clearing the old branch needs `reset --hard` or a branch deletion, which `AGENTS.md` leaves to the human. The old branch is left for the human.
- The human may raise the budget for one slice at the checkpoint, so a slice that is big by nature, such as the Django skeleton, does not restart forever.
- The budget is one requirement, at most 8 criteria and at most 400 changed lines under `src/`, not counting tests and migrations. These are starting values. Claude based the line count on the SmartBear/Cisco code review study and Google's code review guide, from its own knowledge; neither was checked in this session.
- Claude also made the two fixes it had offered as optional, the fast lane row and the README line, after the human approved the edits.

## Problems

- Claude's first attempt to test the size command in a throwaway repo was denied. A later run in a new scratchpad folder was allowed.
- The size command is untested on real Django code, because `src/` does not exist yet. Test files placed outside `tests/` folders would be counted, which makes the check stricter.
