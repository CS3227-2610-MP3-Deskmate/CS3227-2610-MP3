# Developer Guide

## Development workflow

How we work, and what each file in `workflow/` is for, is in [`workflow/README.md`](../workflow/README.md).

### Why role scopes need a script

Claude Code and Codex can both make an agent read-only natively, so the critic and the reviewers get only read tools in Claude Code and `sandbox_mode = "read-only"` in Codex. Neither tool can limit which paths a writing agent may change (checked against both tools' documentation in October 2026):

- Claude Code's agent definitions have no path setting, and its path permission rules, such as `Edit(src/**)`, apply to the whole session rather than to one agent. The documented way to restrict one agent's paths is a pre-edit hook.
- Codex's sandbox lets an agent write anywhere in the workspace or nowhere. Hooks are its only per-agent control.

So [`check_scope.py`](../workflow/scripts/check_scope.py) reads each role's `writes` and `never_writes` lists and enforces them twice: as the pre-edit hook in both tools, and as a check the orchestrator runs after every role agent. This is what stops the implementer from weakening a test to make it pass. Its limits are listed under "How scope is enforced" in [`workflow/README.md`](../workflow/README.md).
