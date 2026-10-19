# Security-review the merged code that skipped it

Slice: #65 · Tier: High · Tool: Claude Code (Opus 5.5) · Date: 2026-10-19

Cost: Six security-reviewer runs in parallel, about 881,000 subagent tokens and 57 minutes of agent time (about 14 minutes of wall time), as the tool reported them, and one verify run of about 6 minutes. The orchestrating session's own tokens and total wall time were not measured.

## Requests

- Run the `slice` skill for #65, adding to the existing pull request #66 instead of opening another.
- Show the findings and draft bug issues before filing any.

## Agent runs

Root merged `main` (`fea06e1`) into the branch as `da09039`; every row's files there are identical to `main`. The verify command passed at `da09039`: ruff clean and 1869 tests passed. Each run below is security-reviewer at role file `8d74e8e`, done, changing nothing; `check_scope.py security-reviewer --base da09039` passed after all six. Each reviewed its files in full as on `main`, not only the commits #65 lists, but did not inspect the commits in between. Root checked every finding's cited lines against the code, and P3 against the installed Django 6.1.2 source.

### #54: Requester tickets (RQ-1)

Range `3fc0a0c^..fea06e1` on `src/deskmate/tickets/` and `src/deskmate/urls.py`. No exploitable flaw: every Requester route checks the method, sign-in and stored role before reading a ticket, and every read and creation is scoped to the stored workspace.

- T1 Medium, missing test: nothing checks that forged `open`, `reply`, `id` or `pk` fields, or query-string overrides, are ignored on creation (`test_tickets.py:314-328`; the control is `forms.py:58-60`). RQ-1.2, RQ-1.7.
- T2 Medium, missing test: the role-denial and session tests send only GET, and the CSRF test sends no ticket fields, so nothing shows that a rejected POST carrying a valid ticket creates nothing (`test_tickets.py:212-280`). RQ-1.6.
- T3 Low, missing test: escaping of invalid values shown again by `redisplay()` (`forms.py:37-45`). RQ-1.7.
- T4 Low, missing test: `no-store` and `DENY` on the form, the redirect after creation, the invalid form and the 404, 405, 403 and 500 responses. RQ-1.6.
- T5 Low, missing test: a POST to the Requester ticket page expecting 405. RQ-1.3.
- T6 Low, hardening: the route guard defaults to the Requester role (`tickets/views.py:21`), so a Support Officer route wired without its role would admit Requesters. Nothing is broken today.
- T7 Low, missing test: creation's INSERT failing after the access checks pass. RQ-1.8.
- T8 Low, spec gap: sequential ticket numbers show how many tickets other workspaces created.
- T9 Info, spec gap: invisible and bidirectional Unicode in ticket text is kept and shown, untested.
- T10 Info: anyone can become a Requester through a demo workspace, and about 25,000 maximum-size tickets (arithmetic, not measured) could fill the free database, more easily than the SECURITY-SPEC Tickets gap suggests.
- Not security: a title both too long and holding a null character probably shows two errors (`forms.py:51-56`); not run.

### #52: Requester knowledge-base reading (KB-2)

Range `5c79ea5^..fea06e1` on `src/deskmate/knowledge/`, `src/deskmate/urls.py` and `role_page.html`. No exploitable flaw: the views check the method, sign-in and stored role before one lookup scoped by id and stored workspace (`knowledge/views.py:109-136`), and article text is escaped.

- K1 Low, missing test: identifier edge cases on the reading route: 2^63, 0, non-ASCII digits, and a Support Officer with the 5000-digit id. KB-2.3, KB-2.4.
- K2 Low, missing test: a bad `Origin` on the reading routes. KB-2.4.
- K3 Low, missing test: cache and framing headers on the 404, 405 and 500 responses. KB-2.4.
- K4 Low, missing test: attribute breakout, pre-escaped references, `<svg>`, bare URLs and `javascript:` in titles and bodies. KB-2.2.
- K5 Low, missing test: KB-2.4's clause on a Requester requesting a Support Officer route is tested only by a test marked KB-1.6 (`test_articles.py:272`). KB-2.4.
- K6 Info, spec gap: invisible and bidirectional Unicode in article text.
- K7 Info, spec gap: sequential article ids show other workspaces' activity.
- K8 Info, spec gap: no Content-Security-Policy or `nosniff`, so escaping is the only barrier to stored markup, app-wide.
- K9 Info: SECURITY-SPEC "Knowledge-base reading" lacks the unpaginated-list gap that "Knowledge-base authoring" records.
- Not security: `PRODUCT-SPEC.md` lines 7 and 18 and the intro of `knowledge-base.md` still describe the knowledge base as Support Officer-only, and KB-2.4 links to the authoring section for its controls.

### #56: the home-page link check

Range `49f53cc^..fea06e1` on `src/deskmate/release.py`.

- R1 Medium: the checker skips the contents of `template`, `noscript`, `script` and `style` with one shared counter and treats `<x/>` as closed (`release.py:135-143, 166-180`), so pages that browsers render differently pass: a declarative shadow root replacing the visible Sign in link, `<base>` inside `<noscript>`, `<style>` inside SVG, and self-closing or crossed wrappers. PLT-1.1, PLT-2.3.
- R2 Medium, wrong and missing tests: `test_release_home_ignores_inert_link_markup` (`test_release.py:127-143`) requires a page with a hidden extra link to pass, R1's and R3's attacks have no failing cases, and no test runs the page Django renders through `verify_release`. PLT-1.1, PLT-2.3.
- R3 Low, partly spec gap: no allowlist of tags, attributes or character set, so `onclick`, `ping`, `<area>`, scripts, refresh, forms, frames and another charset pass. PLT-1.1 for links; the rest is a spec gap.
- R4 Low: the hostname mapping is checked only before the public checks (`release.py:200-212`), so a domain that moves back to a healthy older deployment in between still passes. PLT-2.3.
- R5 Low, spec gap: `deploy.yml:122` runs `python src/deskmate/release.py`, which puts `src/deskmate/` first on the import path in the process holding `VERCEL_TOKEN`; nothing there shadows the standard library today.
- R6 Info: an `ssl.SSLError` that urllib does not wrap is retried until the deadline instead of failing at once (`release.py:83`).

### #47: the migration entry point and deploy workflow

Ranges `07a80dd^..fea06e1` on `src/deskmate/migrate.py` and `2776f2d^..fea06e1` on `.github/workflows/deploy.yml`. Both listed commits are sound.

- P1 Medium, spec gap: `npm install --global vercel@64.3.1` (`deploy.yml:52`) pins only the CLI, with no lockfile, and runs install scripts, so a compromised dependency runs in the job that holds `VERCEL_TOKEN`. SECURITY-SPEC "CI and dependencies" requires only the CLI's exact version.
- P2 Low: `RELEASE_JOB_DEADLINE` is 900 seconds from the first step and `timeout-minutes: 15` counts from job start (`deploy.yml:30, 39`), so GitHub's timeout always fires first and the `deployment: failed` line and recovery guidance depend on the exit trap surviving cancellation; untested. PLT-2.4.
- P3 Low: Django records a migration with deferred SQL in a separate statement after its schema change commits (Django 6.1.2 `executor.py:254-262`), so a connection lost in between leaves the change applied but unrecorded. PLT-2.14, PLT-2.4.
- P4 Low: any `SystemExit` during migration whose text matches the PLT-1.7 line, with any upper-case name, is echoed (`migrate.py:31, 126-131`), so an upper-case row value could reach the build log. PLT-2.12.
- P5 Low, missing test: nothing makes `_silence()` fail (`migrate.py:36-53, 120-125`). PLT-2.12.
- P6 Low: nothing enforces the docstring's rule that no file in `src/deskmate` shares a standard-library module's name (`migrate.py:18-20`). PLT-2.8, PLT-2.12.
- P7 Info, missing test: every entry-point test sets `PYTHONPATH=src`, so none runs it as the provider does. PLT-2.9, PLT-2.14.
- P8 Info: `workflow_run` jobs always run with the default branch's ref, so the `production` environment's main-only rule is not a separate barrier for Deploy. PLT-2.5.

### #46: the rate limits

Range `bf27014^..fea06e1` on `src/deskmate/accounts/limits.py`. ACC-3.8's manual check passes on all three points: each kind pins READ COMMITTED and takes its own transaction-scoped advisory lock (`limits.py:81-98`); every query and delete filters on its own kind, so neither kind waits for the other; and `timezone.now()` is read once, after the lock (`limits.py:101`). `bf27014` is correct and has a regression test.

- L1 Medium, spec gap: anyone with a demo Support Officer and 2 address groups can use up the reset limit for everyone, blocking resets in every workspace (`limits.py:21`); SECURITY-SPEC records this only for sign-in and creation. ACC-4.8.
- L2 Low: each kind's lock id is its position in `Kind` (`limits.py:97`), so inserting or reordering a member breaks serialisation between old and new instances during a deploy; nothing pins it. ACC-3.6, ACC-3.8.
- L3 Info, spec gap: after the app clock jumps forward and back, a kind whose limit for everyone is reached refuses every attempt for the length of the jump.
- L4 Info: a test that the clock is read after waiting is possible; the criterion is a manual check.

### #64: demo workspace codes and passwords

Range `e1fa2de^..fea06e1` on `src/deskmate/accounts/demo.py`. ACC-2.8's manual check passes: codes and passwords both come from `_random_string` (`demo.py:31-48`), one `secrets.choice` per character over the 31 distinct characters of `ALPHABET`, and `secrets.choice` uses rejection sampling, not a modulo. Showing the code on the page reveals only what the usernames already show.

- D1 Low, spec gap and missing test: `Watch.generated()` (`demo_workspaces.py:447-466`) looks only for whole usernames, so a change that logged the code alone, which gives away all three usernames, would pass. ACC-2.6.
- D2 Low, missing test: no request sends a `code` field or a chosen 6-character `workspace` value. ACC-2.5.
- D3 Low, spec gap: nothing automated guards ACC-2.8; `assert_generated` checks only length and alphabet. The spec chose a manual check.

## Decisions and corrections

- The human chose the High tier, run review-only: one security-reviewer per row of #65, no reviewer, because no criterion or code changes.
- Offered one issue per finding or 17 grouped issues, the human chose a single bug issue for the six Medium findings: #67 (R1, R2, P1, L1, T1, T2). The Low and Info findings stay in this log without issues, so #65's "each finding has its own bug issue" holds for the Medium findings only.
- The knowledge-base wording note under #52 stays in this log only.

## Problems

- The worktree has no `.venv`, so the reviewers took Django's behaviour from memory; the #56 reviewer read the local Python 3.14 standard library. Root checked P3 against Django's source.
- No suspicious or injected content was seen; the tests' escaped red-team payloads were read as data.
