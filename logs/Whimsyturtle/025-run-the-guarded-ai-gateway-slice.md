# Run the guarded AI gateway slice

Slice: #20 · Tier: High · Tool: Claude Code (Opus 5.5) · Date: 2026-10-20

Cost: 16 role runs, two of them resumed after interruptions, plus four CI runs. The session ran from 2026-10-20 into 2026-10-21 SGT, including waits for CI; wall time was not measured. The tool reported these subagent token totals at each agent's last run: spec-writer 266,929, spec-critic 123,224, test-writer 313,643, implementer (plan) 150,970, implementer (build and fixes) 153,673, reviewer 178,374, security-reviewer 170,541. The orchestrator's own tokens and the money spent were not counted.

## Requests

- Run `/slice 20`, [Guard LLM input and output in the AI gateway](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/issues/20). The issue is MEMBER-authored and had no comments.
- At the start, the human chose:
  - the full gateway: one internal entry point running PLT-5 admission, the input guard, one SoC LLM call with the probe's limits, the output guard against a caller-supplied schema, and PLT-6 audit. This includes the confirmed relaxation that the gateway reads `SOC_LLM_API_KEY`;
  - High tier;
  - verification through GitHub CI on a draft PR, which approved pushing `20-llm-guards` and opening the draft.
- At the checkpoint, the human chose to:
  - proceed with PLT-8.1–8.8 as committed at `431dc7b`;
  - raise the budget to 300 application lines and about 1,200 total diff lines;
  - accept exactly one surrounding ```` ```json ```` fence in replies;
  - leave two problems found outside the slice out of it.
- After the tests: keep the 689-line test file, and raise the total estimate to about 1,300 lines.
- After review round 1: lower the input cap now, to 4,000 code points; fix the two test gaps but not add the optional caller scan; log the probe-deadline finding only.
- After review round 2: fix the plan's stale cap; note the Developer Guide's context figure in the PR rather than change the spec; fill in PR #75 and mark it ready.
- The human asked twice to continue after an agent run was interrupted.

## Agent runs

- **spec-writer** (`246260a`), 4 runs, all within scope:
  - Initial run: done. `2acdf77` adds [PLT-8.1–8.8](../../workflow/specs/product/platform.md#plt-8-guard-user-ai-calls-in-the-internal-gateway), the [gateway contract](../../workflow/specs/ai/llm-gateway.md), the TECHNICAL and SECURITY sections, and "Relaxed (#20)".
  - The critic's findings: done after a resume, since a network error interrupted it. `431dc7b` adds the `<` escape, the order of the precondition checks, exact built-in types, one home for the transport rules, and new gaps.
  - The checkpoint fence: done. `6faa4ec`.
  - The 4,000 cap and its gap: done. `3213cf0`.
  - Whitespace checks passed on each run.
- **spec-critic** (`a58461d`): done. Reviewed `8af7c62..2acdf77` and found 8 problems, 5 of them for the human. The escape, precondition, type, transport and gap findings were applied in `431dc7b`. The budget finding went to the checkpoint.
- **test-writer** (`3d65dbb`), 3 runs, all within scope:
  - Initial run: done. `94ee66f` adds 176 cases in [`test_llm_gateway.py`](../../src/deskmate/tests/test_llm_gateway.py). Locally, all 176 errored with `ModuleNotFoundError: No module named 'deskmate.llm_gateway'` before database setup; ruff passed.
  - Review fixes: done after a resume, since a session limit interrupted it. `a61c241` updates the cap cases to 4,000, adds RecursionError cases at both JSON levels through a `json.JSONDecoder.raw_decode` seam, and adds nested-surrogate cases.
  - Regression fix: done. `6a1c65b` renames the new `NESTED` dict to `NESTED_SURROGATES`.
- **implementer** (`3d65dbb`), 4 runs, all within scope:
  - Plan: done. `8bbf23a` adds the single-task [plan](../../workflow/plans/20-llm-guards.md).
  - Build: done. `2d125d0` adds [`llm_gateway.py`](../../src/deskmate/llm_gateway.py) and shares `llm.reply` and `llm_audit.valid_caller`. Ruff and Django checks passed; there was no local pytest.
  - Cap fix: done. `41e73ef` sets `MAX_TEXT` to 4000.
  - Plan fix: done. `aadd683` changes the plan's cap to 4,000.
- **reviewer** (`8d74e8e`), 2 rounds:
  - Round 1, `8af7c62..4578dc8`: one Medium (no test reached "nesting too deep to parse"), one Low (surrogates tested only at the top level) and Info notes. No correctness bug.
  - Round 2, `4578dc8..6a1c65b`: both findings fixed; one Low (the plan said 12,000) and one Info (the Developer Guide's 65,536-token figure).
- **security-reviewer** (`8d74e8e`), 2 rounds:
  - Round 1, `8af7c62..4578dc8`: one Medium (the 12,000 code-point cap did not bound tokens, so a long text could overflow the context), Lows on the untested RecursionError path, the probe transport's deadline missing the connect and header phases, and public `llm.reply`, and Info notes for #26 and the first calling slice.
  - Round 2, `4578dc8..6a1c65b`: nothing Medium or High; the RecursionError tests catch the round-1 attack; one Low (the plan said 12,000).

## Decisions and corrections

- Created `20-llm-guards` from fetched `main` at `8af7c62` in the primary checkout, since #21 had merged. `main` had not moved at delivery.
- Opened [draft PR #75](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/pull/75) after the test commit to run CI, as the human chose. This happens earlier than the slice's delivery step.
- The entry point `deskmate.llm_gateway.call(user, *, feature, instructions, schema, text)` follows #22's naming. The spec does not name it.
- Before the build, Claude restored the plan's `<` escape, which a tool had decoded, and committed `8bbf23a` with the implementer's trailer. Claude ticked the plan box itself in `4578dc8`, without a trailer.
- CI runs:
  - [Red, 39423463661](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39423463661) at `94ee66f`: 2,025 passed, and all 176 new cases errored with the missing module.
  - [Green, 39428143659](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39428143659) at `2d125d0`: 2,201 passed.
  - [39453145929](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39453145929) at `41e73ef`: 2 failed and 2,203 passed, from the `NESTED` rebinding.
  - [39454633108](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39454633108) at `6a1c65b`: 2,205 passed.
- The slice adds 287 application lines, under the 300 cap, and 1,235 diff lines before this log, under the human's estimate of about 1,300. No dependency, setting, record, migration, route or User Guide change.

## Problems

- The verify command could not run locally. Docker's daemon was unavailable, and the `postgresql-x64-17` Windows service holds port 5432, so the tests' database connection failed with `password authentication failed for user "deskmate"`. No service, credentials or `.env` file was touched. Every full verify ran in CI.
- `a61c241` and `41e73ef` were pushed together, so CI never ran the 4,000-cap tests against the 12,000 code. The test-writer's database-free check showed that `_guard("a" * 4001)` was accepted at `2d125d0`.
- The Edit and Write tools decoded `<` into `<` in the spec and the plan. Each was restored and checked byte by byte.
- The first `gh run watch` exited before CI finished, so Claude switched to a polling loop.
- The test-writer and the planning implementer wrote throwaway scripts with Bash in the session scratchpad, outside their write scopes and outside the repository: `gen/attacks.py`, `gen/depth.py`, `gen/odd.py`, `json_edges.py` and `json_pairs.py`. The hook then blocked their Writes there. Nothing was committed, and every repository scope check passed.
- Left out of the slice, as the human chose:
  - four broken `../ai/llm-health.md` links in SECURITY-SPEC;
  - the probe's uncaught `RecursionError` on deeply nested provider JSON, which likely gives `500` where PLT-3.2 requires `503`, from reading the code;
  - the probe transport's 10-second limit, which does not cover connecting or reading headers.
- Untrusted content seen: `test_llm_gateway.py` holds percent-encoded synthetic red-team payloads, such as "Ignore all previous instructions" and forged Llama turns. They are test data, and no role followed them. Collaborator-authored issue metadata and agent handoffs were treated as data.
