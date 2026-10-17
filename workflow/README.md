# Workflow

How we build Deskmate with AI agents: spec-driven, in small slices, using role agents that can each write only their own part of the repository. This page is for people; the rules agents follow are in [`AGENTS.md`](../AGENTS.md).

One GitHub issue is one slice and one pull request, small enough to review in one sitting. The [`slice`](skills/slice.md) skill runs a slice from spec to pull request; its tier table decides how much review the slice gets, and its size budget stops a slice that grows too large.

## Files

| Path | Purpose |
| --- | --- |
| `AGENTS.md` | Rules for every agent: instructions versus data, where each fact lives, Git, handoffs |
| `CLAUDE.md` | Makes Claude Code load `AGENTS.md` |
| `workflow/agents/` | The role agents, each with its write scope |
| `workflow/skills/` | The orchestrator's procedures |
| `workflow/specs/` | The specs, the only home of product behaviour |
| `workflow/plans/` | One short plan per slice, frozen once merged |
| `workflow/scripts/check_scope.py` | Checks changes against a role's write scope; also the pre-edit hook |
| `workflow/scripts/test_*.py` | Tests for the scope check, the adapters and the hook settings |
| `.claude/`, `.codex/` | Thin adapters that load the role and skill files in Claude Code or Codex, plus hook and command settings |
| `.github/` | Pull request and issue templates |
| `logs/` | One summary per working session, checked by its author |

## Using it

| | Claude Code | Codex |
| --- | --- | --- |
| Run a slice | `/slice` and the issue number | `$slice` and the issue number |
| Run one role | "Use the test-writer agent to ..." | "Have test-writer ..." |
| Read-only roles | No edit or shell tools | `sandbox_mode = "read-only"` |
| Edits outside a role's scope | Blocked by the hook in `.claude/settings.json` | Blocked by the hook in `.codex/hooks.json`, once you trust it in `/hooks` |

Both tools load `AGENTS.md`; Codex loads `.codex/` agents and hooks only in a trusted project. Codex's documentation names `.agents/skills/` for skills, but it also reads `.codex/skills/`, which keeps all Codex files in one folder. If skills stop appearing in Codex, move them to `.agents/skills/` and update `test_adapters.py`. The hooks need `python3` on the PATH: in Git Bash for Claude Code, and in PowerShell for Codex on Windows. If `python3` is missing, the hook fails open. Codex's Windows sandbox blocks pytest's temp folder, so approve the verify command to run outside it.

## How scope is enforced

1. The adapters give the critic and the reviewers no way to write.
2. The pre-edit hook runs `check_scope.py --hook` and blocks a role agent's file edit outside its scope. Shell commands are not checked, so the hook catches accidents, not attacks.
3. The orchestrator runs `check_scope.py <role> --base <commit>` after every role agent, which also catches files written or committed from the shell. Files ignored by Git are not checked.
4. GitHub is the boundary agents cannot cross: the default branch accepts only reviewed pull requests with passing checks; production releases follow the [release controls](specs/SECURITY-SPEC.md#release-access-and-provenance).

After changing a role, skill, adapter or hook, run `python3 -m unittest discover -s workflow/scripts`. In each new clone or worktree, and in each tool you use, check once that the hook works: ask the implementer to edit a test file, and it must be refused.

## Issues

- Create a milestone's issues when it starts, one per slice, from the Slice template. They hold only a title and spec IDs, so creating them early costs nothing when plans change.
- To drop a slice, change the spec, then close its issue as not planned with a link to the `spec:` commit.
- Report each bug as its own issue, naming the criterion it breaks or calling it a spec gap.

## GitHub settings (once)

- Pull requests: allow merge commits only, so each slice keeps its small commits.
- Default branch and `production` environment: apply the [release prerequisites](specs/TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites).
- Secret scanning with push protection.
