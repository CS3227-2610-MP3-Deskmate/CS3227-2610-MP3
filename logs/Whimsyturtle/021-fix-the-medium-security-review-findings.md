# Fix the Medium security-review findings

Slice: #67 · Tool: Claude Code (Opus 5.5) · Date: 2026-10-19

Cost: 13 role-agent runs plus one resumed run, about 1,050,000 subagent tokens and 87 minutes of agent time, as the tool reported them, and four verify runs of about 6 minutes each. The orchestrating session's own tokens and total wall time were not measured.

## Requests

- Run the `slice` skill for #67, which lists six Medium findings from #65's review of the code on `main`: R1, R2, P1, L1, T1 and T2. That review's log is on #65's branch (`logs/Whimsyturtle/020-security-review-the-merged-code-that-skipped-it.md`) and is not yet on `main`.
- After review round 2: stop changing the slice and open no new issue for the remaining findings.

## Agent runs

Base `fea06e1`. `check_scope.py` passed after every run. Role file versions: spec-writer `246260a`, spec-critic `a58461d`, test-writer `3d65dbb`, implementer `3d65dbb`, reviewer `246260a`, security-reviewer `3d65dbb`.

- spec-writer, done: added the L1 and P1 gaps to SECURITY-SPEC (`3e7517d`).
- spec-critic, needs-decision: no relaxed control. Wording fixes, and TECHNICAL-SPEC line 10's exact-pins claim disagreed with the P1 gap. Root checked its npm questions against the registry: `vercel@64.3.1` has no shrinkwrap, depends on `luxon ^3.4.0`, and `esbuild@0.27.0` has a postinstall script.
- spec-writer, done: applied the critic's wording and qualified TECHNICAL-SPEC line 10 (`d348715`).
- test-writer, done: R1/R2 release cases, the real `/` page through `verify_release`, and T1/T2 ticket tests (`a500fc8`). It reversed `test_release_home_ignores_inert_link_markup` as confirmed. Before the fix, the 15 release cases failed with `DID NOT RAISE ReleaseError`; T1/T2 passed, because they cover working code.
- implementer, done: wrote the plan (`46fc40e`).
- implementer, done: the R1 fix in `src/deskmate/release.py` (`db8d9cf`). Verify passed: ruff clean, 1902 passed.
- reviewer and security-reviewer, round 1, needs-decision: CDATA, abrupt comments (`<!-->`) and `frameset` still passed the check, and no test pinned `script` or `noscript`. Root's probe of `_HomePage` on Python 3.14.2 confirmed each. It also showed that the security-reviewer's claim that comments agree was wrong.
- test-writer, done, then resumed once to add an empty-frameset case: comment, CDATA and frameset cases, plus cases pinning `script` and `noscript` (`ae7f638`).
- implementer, done: failed comments, CDATA declarations, `frameset` and `frame`, and corrected the `_HomePage` docstring (`9d989c0`). Verify passed: ruff clean, 1910 passed. Size: 60 insertions and 12 deletions under `src/` outside tests.
- reviewer and security-reviewer, round 2, needs-decision: round 1 resolved, nothing weakened. They found further parser/browser disagreements, listed under Problems.

## Decisions and corrections

- The human chose one High-tier slice over splitting #67.
- L1 and P1 were recorded as SECURITY-SPEC gaps, with no change to rate limits or the deploy workflow. The human chose this over a per-workspace reset allowance and a CLI lockfile.
- For R1, the human chose to reject markup the checker cannot read as a browser does, over a strict tag allowlist.
- The human chose to qualify TECHNICAL-SPEC line 10 rather than leave it overstated.
- After round 1, the human confirmed adding comments, CDATA declarations and framesets to the check.
- After round 2, the human chose to stop and open no new issue, after asking for an explanation of the findings.
- Root left the reviewer's Low note on `settings.DEBUG = False` in the T2 other-origin case unchanged, because ACC-1.8's Origin check applies with debug off.

## Problems

- Round 2's findings are unresolved and tracked nowhere else. Root's probe confirmed that the parser passes B, C and E's `noembed` case; browser behaviour comes from the WHATWG specs, not a browser.
  - A: the check ignores the `Content-Type` charset and uses the first of duplicate `Content-Type` headers.
  - B: an unclosed quote after ` = ` in a tag, and character references such as `&#1;`, which Python drops.
  - C: a `</p>` inside the link, which browsers split into two links.
  - D: `Refresh` and `Content-Disposition` headers.
  - E: `noembed`, `noframes` and other content that browsers hide.
  - Also no test pins `frame`, and the plan describes round 1 only.
- The scope hook blocked the test-writer and the implementer from writing throwaway files to the session scratchpad. Neither worked around it; the test-writer later used a throwaway test file inside its scope and deleted it.
- Another worktree's PostgreSQL container held port 5432, so the verify runs used it instead of this worktree's.
- No suspicious or injected content was seen. The escaped test payloads were read as data.
