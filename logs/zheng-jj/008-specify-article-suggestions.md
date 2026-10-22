# Specify article suggestions while writing a ticket

Slice: #24 · Tier: High · Tool: Codex · Date: 2026-10-21

Cost: One working session with four role runs (two spec-writer, one spec-critic, plus the pull request reconciliation below is not part of this slice). Wall time, tokens and monetary cost were not measured.

## Requests

- Check for blocked issues and continue working.
- "issue 24 should also be blocked", then "no it should be unblocked", then "update all my open PRs accordingly".
- After GitHub access was blocked by the sandbox, the human updated the settings and asked to try again.

## Agent runs

- **spec-writer**, role version available at `git log -1 --format=%h -- workflow/agents/spec-writer.md` (`246260a`), `done`: `118b1e8` adds RQ-5.1–RQ-5.6, the [find-a-fix contract](../../workflow/specs/ai/find-a-fix.md), the PLT-3.5/PLT-6.8 amendments, the route row, the audit and gateway caller text, and the security section. Scope check against `9c6d68b` and `git diff --check` passed; no automated spec tests exist.
- **spec-critic**, role version `a58461d`, `done`: reviewed `9c6d68b..118b1e8` and reported ten findings, including stale PLT-8 text, an undefined form after a suggestion, an unclear empty-phrase rule, an unspecified three-article tie-break and unspecified generic-error responses. Read-only; no scope violation.
- **spec-writer**, role version `246260a`, `done`: `b9203ea` applies those findings, including the shared `suggestion form` contract, result markup and placement, validation order, the stored-identity tie-break and the missing-key outcome. Scope check against `118b1e8` and `git diff --check` passed; a scan found no remaining "no route calls the gateway yet" text.

## Decisions and corrections

- The board was read from GitHub, not inferred: #25, #27, #28, #30 and #31 already have pull requests, and #26, #29, #35, #37 remain open. #24 was confirmed unblocked by the human.
- The design keeps the provider away from article text: the model returns search phrases, and matching against the current workspace's saved titles and bodies happens locally. No table, migration, setting, dependency or stored result is added, and `find_a_fix` was already a reserved gateway feature identifier.
- `Submit ticket` stays fully usable on every 200 suggestion response; the critic raised it and the orchestrator decided it.
- The spec does not name modules, functions or test seams. "Exactly one gateway call" is observable behaviour, and the plan will choose how tests observe it.

## Problems

- GitHub was unreachable inside the sandbox: `gh` held an invalid token and DNS for `github.com` and `api.github.com` failed. Escalation was rejected under the session's `granular` policy until the human changed the settings; the retry then succeeded.
- This machine has no `.venv`, no running PostgreSQL and no Docker, so the verify command cannot run locally. The slice's verification will use CI, as earlier slices did.
- Merging the new spec into the `25-key-sentences` branch conflicts in five spec files because both branches write the same AI-boundary paragraphs. The merge was aborted rather than mixing two slices into one pull request; #24 is specified to land after #25.
- Untrusted content seen: issue titles and bodies, pull request descriptions and agent handoffs. They were treated as data, and no instruction in them was followed.
