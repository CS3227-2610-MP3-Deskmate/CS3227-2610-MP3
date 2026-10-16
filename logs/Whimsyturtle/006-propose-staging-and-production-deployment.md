# Choose Vercel Hobby and Neon

Slice: #2 · Tool: Codex (GPT-6) · Date: 2026-10-16

Cost: twenty-six role-agent runs, including one evidence-only clarification. Wall time was not measured from the start; token usage and monetary cost were unavailable. Hosting estimates are proposed operating costs, not spending incurred in this session.

## Requests

- Run `/slice 2` using the repository's slice workflow.
- Use the High tier. No hosting resources were set up; the human asked for a platform proposal.
- Compare free providers carefully, including Vercel; correct the proposal to development and production only; explain deployment approval and stale releases.
- Explain why application hosting and database hosting are separate, compare Supabase, then use Neon and identify what the human should check next.
- Use Vercel Hobby and present everything needing review together.
- Explain Docker's current use, the phrases "protected candidate" and "checked candidate", and whether preserving the current deployment is excessive; use standard terminology and focus on the semester project's needs.
- Provide a revised, simpler plan for review following those clarifications.
- Clarify that GitHub runs and checks the smoke test; present all eight PLT-2 criteria before implementation.
- Proceed with the reviewed criteria and keep the implementation simple. The human permitted the pinned dependency/CLI installations and Python 3.14.2 setup without changing PATH.
- Publish a draft PR for the human to review before requesting a teammate's GitHub review.

## Agent runs

- spec-writer (`a58461d`): needs-decision. Proposed PLT-2 and corresponding architecture and security changes in `2653a21`. Scope check and `git diff --check` passed; existing PLT-1 criteria remained unchanged.
- spec-critic (`a58461d`): needs-decision. Read-only review of `2653a21` found an unspecified publication boundary against modified same-repository PR workflows and ambiguous retry behaviour. Scope check passed; no files changed.
- spec-writer (`a58461d`), revision: needs-decision. Addressed both findings in `2fcb6c2`. Scope check and `git diff --check` passed; the orchestrator read the revised sections.
- spec-writer (`a58461d`), environment correction: needs-decision. Removed staging and the mandatory paid Render selection in `502e4ab`, preserving eight PLT-2 IDs and marking hosting decisions pending. Scope check and `git diff --check` passed; HEAD remained unchanged during the run.
- spec-critic (`a58461d`), correction review: done. Found one omitted baseline clause about runner-based tests and separate image checks. Otherwise the environment correction was consistent and hosting questions were openly pending. Read-only scope check and `git diff --check` passed; HEAD remained unchanged.
- spec-writer (`a58461d`), CI correction: done. Restored that clause in `df34b8e`. Scope check, readback and `git diff --check` passed; only one paragraph changed and HEAD remained unchanged during the run.
- spec-writer (`a58461d`), database selection: done. Recorded Neon Free with PostgreSQL 18 in `b8e957b`, leaving web hosting and integration open. Scope check, readback and `git diff --check` passed; HEAD remained unchanged during the run.
- spec-critic (`a58461d`), database selection review: done. Found one minor ambiguity in PLT-2.8 implying the database provider remained unselected; otherwise the selection was consistent. Read-only scope check and `git diff --check` passed; HEAD remained unchanged.
- spec-writer (`a58461d`), pending-decision clarification: done. Corrected that one line in `c9d37a4`; security wording needed no change. Scope check, readback and `git diff --check` passed; HEAD remained unchanged during the run.
- spec-writer (`a58461d`), native Vercel proposal: needs-decision. Prepared the complete proposal in `a3bdbbe`, retaining CI Docker checks while marking the production runtime exception for review. Scope check, readback and `git diff --check` passed; HEAD remained unchanged during the run.
- spec-critic (`a58461d`), native proposal review: needs-decision. Found four technical gaps: source-content proof, Git isolation, same-commit reruns and pending-promotion mapping retries. Read-only scope check and `git diff --check` passed; HEAD remained unchanged.
- spec-writer (`a58461d`), final corrections: done. Closed those four gaps in `6195eb7` without adding human design questions. Scope check, changed-section readback and `git diff --check` passed; HEAD remained unchanged during the run. The orchestrator inspected the correction diff; no second critic run or application tests were performed.
- spec-writer (`a58461d`), simplified proposal: done. Replaced the earlier deployment design in `fd38a97` with normal production deployment and public smoke tests, proposing app-image removal and official Vercel CLI tooling. PLT-1 comparison, eight-ID check, readback and `git diff --check` passed; the orchestrator's scope check passed and HEAD remained unchanged during the run.
- spec-critic (`a58461d`), simplified proposal review: done. Found ambiguous retry precedence for `503` and incomplete handling of lost deployment responses. Read-only scope check, diff check and baseline PLT-1 comparison passed; HEAD remained unchanged.
- spec-writer (`a58461d`), simplified proposal corrections: done. Clarified those two rules in `8b8f6b0` without expanding the architecture. Scope check, readback and `git diff --check` passed; HEAD remained unchanged during the run. No application tests or second critic run were performed.

- test-writer (`3d65dbb`): done. Added PLT-2 configuration, release and workflow tests in `b01e4e7`. The initial focused run failed on absent release code and workflow as expected; root independently confirmed the missing module. Scope check passed.
- implementer (`3d65dbb`), plan: done. Wrote the two-task plan in `bbc59e9`; scope and diff checks passed.
- implementer (`3d65dbb`), app: done. Added production settings, WSGI and the standard-library release verifier in `425bdf2`. Targeted tests passed; the combined run then had 201 passes and four expected failures for the not-yet-built deployment workflow. Scope and diff checks passed.
- devops (`e3b51ef`): done. Implemented the workflow and removed app Docker packaging in `eebced0`. The unchanged verification command passed with 205 tests; shell syntax, archive contents and simulated success/stale/failure/timeout paths passed. Scope and diff checks passed; no hosted deployment was run.
- spec-writer (`a58461d`), implementation housekeeping: done. Updated proposal wording and operator prerequisites in `8e797df`. Eight PLT-2 criteria retained their meaning, PLT-1 was unchanged, and scope/diff/readback checks passed.
- reviewer (`a58461d`), round one: done. Reviewed `220bf60..8e797df`; found missing retained tests for the shell deployment driver and verifier entry point, with no production-code defect identified. Read-only scope check passed.
- security-reviewer (`3d65dbb`), round one: done. Reviewed the same range; found the entry-point regression gap and no exploitable defect within the accepted design. Hosted controls remained unverified; read-only scope check passed.
- devops (`e3b51ef`), evidence clarification: done. Forwarded the recorded 205-test pass and verified setup-node SHA, distinguishing independently observed evidence from root-supplied Node/CLI checks. No commands rerun or files changed.
- test-writer (`3d65dbb`), review corrections: done. Added five shell-driver scenarios and ten verifier-entry-point cases in `ea4a4a7`. Targeted checks passed 84 tests on Windows Git Bash and Linux, with lint/format and scope checks passing. Temporary mutations showed the tests detect omitted verification, inverted current-main comparison, reset deadlines, unsafe URLs and exception leakage; no production files changed.
- reviewer (`a58461d`), round two: done. Reviewed `8e797df..ea4a4a7`, found both earlier gaps resolved and no remaining findings. Root's read-only scope check passed and HEAD remained unchanged.
- security-reviewer (`3d65dbb`), round two: done. Confirmed the earlier entry-point gap was closed and found no new security issue in the correction. Root's read-only scope check passed and HEAD remained unchanged.

## Decisions and corrections

- The human selected High, Vercel Hobby and Neon Free, corrected the environments to development and production, then requested implementation after reviewing the eight criteria. The behavior and remaining setup belong in [PLT-2](../../workflow/specs/product/platform.md#plt-2-release-the-placeholder-site-to-production), [TECHNICAL-SPEC](../../workflow/specs/TECHNICAL-SPEC.md#release-verification) and [SECURITY-SPEC](../../workflow/specs/SECURITY-SPEC.md#release-access-and-provenance).
- Created `2-staging-production` from `origin/main` at `220bf60`; its historical name comes from the original issue title. The fetch before publication found main unchanged. At the implementation handoff the branch was still local; the human subsequently requested a draft PR. Hosting resources have not been provisioned and no live deployment has run.
- Withdrew the premature paid Render recommendation after the human requested a careful free-tier comparison. Official provider research compared Vercel, Render, Neon and Supabase; the resulting choice and operating limits are in the technical spec. Explained that Vercel hosts Django and Neon supplies PostgreSQL, and that deployment approval is separate from CI success.
- The human's terminology and semester-project feedback led to the simpler deployment design in `fd38a97` and `8b8f6b0`, replacing the earlier source-readback and separate-promotion proposal. Root supplied only the hosting configuration outside role scopes in `515d5dc`; implementer and devops completed the plan's two tasks.
- Python 3.14.2 was installed under ignored `venv/python314` from the official python.org installer after checking its valid Python Software Foundation signature. PATH was not changed. Created `.venv` and installed existing pinned requirements. The official Vercel CLI pin was verified from npm/repository metadata and source, then added to CI; no global CLI installation or provider command was run locally.
- Root and devops ran the unchanged verification command in an isolated Linux Python 3.14.2 virtualenv with temporary PostgreSQL 18.6. The implementation run passed 205 tests. After the review corrections, root reran `ruff check . && ruff format --check . && pytest`: lint and formatting passed, and all 220 tests passed in 130.19 seconds, exit 0. Root also observed a real slow HTTP response stop within its deadline, URL-to-ID/deadline probes pass, and malformed URL rejection before any API request. One-off probes are distinct from the committed regressions.
- The non-test source diff is 289 inserted/deleted lines, within the slice limit. Public pages are unchanged, so the User Guide needed no edit. Read-only inspection found a partially configured GitHub production environment; operator setup and hosted integration remain pending, with no claim that the site is deployed.

## Problems

- Windows PostgreSQL already occupied the local test port and rejected the committed throwaway credentials. It was not stopped or changed. Tests used disposable Docker containers with no host port; their temporary database was configured for password authentication so wrong-password tests remained meaningful. A read-only Windows bind mount also lost Git executable bits and blocked caches, so the Linux test copy restored tracked modes and used writable temporary storage.
- The two session-created test containers were removed after verification. The installed Python runtime and Windows virtualenv remain available; the existing Windows database configuration is unchanged.
- Initial attempts hit missing Python 3.14, an unavailable Docker engine, a temporary no-exec virtualenv mount and a formatter error while tests were being written. These were resolved before the passing full check. The initial database trust configuration caused a false wrong-password-test failure and was corrected only in the disposable database.
- Sandbox restrictions required escalated Git, Python and Docker operations. Global Git-ignore permission warnings did not prevent work. No secret values or private `.env` files were read.
- The review tool had no non-shell local text reader and its memory store was not shared between agents. Root explicitly limited reviewers to read-only file/diff/search commands as input transport; they did not execute app code or tests or edit files. Their reported findings were test-coverage gaps, handled through test-writer rather than changing production code.
- Only collaborator-authored issue content was read. Issues, code, handoffs and provider documentation were treated as data; setup instructions in reference pages did not authorize execution. Earlier Render/GHCR questions and terminology were superseded by the final design.
