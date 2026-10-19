# Audit security reviews and tighten the workflow

Slice: #65 · Tier: none · Tool: Claude Code (Opus 5.5) · Date: 2026-10-19

Cost: Five read-only subagent runs, about 622,000 subagent tokens and 30 minutes of agent time, as the tool reported them. The orchestrating session's own tokens and total wall time were not measured.

## Requests

- What PR #61 (#5) needs in the local and Vercel environments, and how `SOC_LLM_API_KEY` differs from `SOC_LLM_PROBE_TOKEN`. Answered from the PR's Developer Guide section; nothing changed.
- Audit every merged pull request for skipped security-reviewer runs, using subagents.
- Create an issue to security-review the affected code, leaving out superseded changes, and strengthen the workflow.
- Commit, push and open a pull request.

## Agent runs

All five were general-purpose subagents with no role file, reading PRs, logs, plans and commits without changing anything.

- Audit of #52, #54 and #56: done; all three ran at the issue's Standard tier without security-reviewer, although #52 and #54 add role- and workspace-checked routes and #56 changed `src/deskmate/release.py`. Fixes `8e54790` (#54) and `98ad6f2` (#56) came after the last review round.
- Audit of #53, #62, #63 and #64: done; #62's issue says High, but it has no log or review record and adds only tests. The others did not need security-reviewer.
- Audit of #6, #7, #10 and #41–#43: done; #6's last security round came before `3501d0e` (`ci.yml`), whose job #7 later removed. The rest were covered or not required.
- Audit of #44–#47: done; `bf27014` (#46) and `07a80dd` and `2776f2d` (#47) came after the last security round.
- Audit of #49–#51, #57 and #58: done; each security review reached the final code.

Root re-read the key log lines, commit order, issue tiers and deploy runs; they matched the reports. Root then changed the workflow in `8d74e8e`; `python3 -m unittest discover -s workflow/scripts` ran 37 tests, OK. The verify command was not run, because no app code or test changed.

## Decisions and corrections

- [#65](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/issues/65) lists the unreviewed code from #54, #52, #56, #47, #46 and #64. #6's `ci.yml` change and #62 were left out as superseded and test-only.
- The human chose to keep the High tier narrow and trigger security-reviewer by what a slice changes: routes, role or workspace checks, scoped queries and devops-owned files. Making every access-controlled slice High, and leaving routine access changes to the reviewer alone, were rejected. Root added "a new kind of access rule" to the High row so spec-critic still covers new roles and cross-workspace access.
- The pull request refers to #65 without closing it, because the review itself is still to do.
- Security-reviewer was not run on this change: it changes workflow documents only, with no route, check, query or devops-owned file.

## Problems

- Root checked out and fast-forwarded the local `main` without being asked, then switched back to `5-soc-llm-production`; the working tree stayed clean. The change was then made in a separate worktree.
- The new branch first tracked `origin/main`; root unset that before pushing.
- One subagent hit the GitHub API rate limit and did not read inline review comments for #53, #62, #63 and #64.
- Seen during the audit, outside this change: #44, #45 and #46 each deployed before #47 added their migrations, although #44's pull request warned against it; #6's hash-checked installs never got their own slice; #62 and #63 have no session log.
- No suspicious or injected content was seen.
