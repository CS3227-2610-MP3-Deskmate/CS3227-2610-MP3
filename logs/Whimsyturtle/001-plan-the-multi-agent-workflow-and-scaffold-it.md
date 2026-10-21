# Plan the multi-agent workflow and scaffold it

Slice: none · Tool: Claude Code (Claude Opus 5.5) · Date: 2026-10-12

Cost: One orchestrated session, with no role-agent runs recorded; wall time, tokens and monetary cost were not measured.

## Requests

- Propose a multi-agent, spec-driven workflow for this project, grounded in the lecture notes for weeks 6–8, the assignment brief and a one-pager plan (local reference files, not committed). It had to fix four MP2 problems: plans too long for humans to read, one big commit per feature, drift from creating many issues up front, and unclear issue granularity.
- After agreeing the plan: write a basic, concise `AGENTS.md`, `README.md`, and agent and skill files, following the MP2 skills where they didn't cause those problems. Keep it working in both Claude Code and Codex, skip CODEOWNERS, leave LLM keys for later, include per-role write scopes, and don't reference the local reference files.
- Stage the result in reviewable groups, one group at a time.

## Agent runs

No role agents ran; the role files did not exist until this session. Claude used research and review subagents:

- **Claude Code feature check** (2 runs): agent definitions can be made read-only natively but have no path limits. Hooks receive `agent_type`, and settings-file hooks need no folder trust. Claude Code reads `AGENTS.md` and finds skills only in `.claude/skills/`.
- **Plan critic:** 19 findings on the draft plan. Applied: squash merges would undo small commits, so allow merge commits only; one writer for commits and logs; risk tiers; hardening for a public repo; and shell commands can bypass edit hooks.
- **Codex feature check** (2 runs): agent definition keys and how `sandbox_mode` works; the `.codex/hooks.json` format; that hooks run in PowerShell on Windows; and the `apply_patch` path format. Skills are documented under `.agents/skills/` but are also read from `.codex/skills/`.
- **Scaffold verifier:** 15 findings, 14 fixed:
  - Files hard-coded `master`; they now say "the default branch".
  - Added a `--base` check that also catches agent commits.
  - Reviewers now get the diff.
  - Test findings now go to test-writer.
  - Closed test-file scope gaps (`tests.py`, pytest config).
  - Fixed the fast lane's rules.
  - Clarified which parts of an agent's task are instructions and which are data.

  The last finding is under Problems.

Result: commits `baeed1b`–`50364a5`, one per review group. `python3 -m unittest discover -s workflow/scripts` passed 35 tests. The hook commands blocked an out-of-scope edit with exit code 2 in Git Bash, PowerShell and `sh`.

## Decisions and corrections

- Agreed the workflow:
  - Specs are the only home of product behaviour.
  - One issue is one slice and one pull request.
  - Issues are pointers, created per milestone.
  - Risk tiers decide how much review a slice gets.
  - Approvals happen only on GitHub, and gates sit on push, merge and deploy rather than on commits.
- Workflow content lives once in `workflow/`, with thin adapters in `.claude/` and `.codex/`. Read-only roles use each tool's native settings; write scopes need `check_scope.py`, because neither tool can limit an agent's paths natively. That reason is recorded in the Developer Guide.
- Corrections: the instructions line in `AGENTS.md` was reworded, and the course reference was dropped from `README.md`. `main` stays the branch name. Codex skills moved from `.agents/skills/` to `.codex/skills/` to keep all Codex files in one folder.

## Problems

- The new `.claude/settings.json` deny rule for `rm -rf` blocked one of Claude's own test commands. It was not worked around.
- A mutation check found a scope test that could not fail. It now covers helper files inside `tests/` folders.
- Not verified: whether Codex loads the agents and skills in `.codex/`, since running Codex would spend quota. Check by typing `$` in Codex.
- The `.env.*` read-deny also blocked `.env.example`. The verifier suggested narrowing it, and Claude left the decision to the human rather than loosen a permission on an agent's suggestion. The human chose to unblock it, so the deny rule now lists `.env`, `.env.local`, `.env.*.local`, `.env.development`, `.env.staging` and `.env.production`.
