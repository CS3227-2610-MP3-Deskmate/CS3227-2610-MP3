# Reconsider the production hosting proposal

Slice: #2 · Tool: Codex (GPT-6) · Date: 2026-10-16

Cost: nine role-agent runs. Wall time was not measured from the start; token usage and monetary cost were unavailable. Hosting estimates are proposed operating costs, not spending incurred in this session.

## Requests

- Run `/slice 2` using the repository's slice workflow.
- Use the High tier. No hosting resources were set up; the human asked for a platform proposal.
- Compare free providers carefully, including Vercel; correct the proposal to development and production only; explain deployment approval and stale releases.
- Explain why application hosting and database hosting are separate, compare Supabase, then use Neon and identify what the human should check next.

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

## Decisions and corrections

- The human selected High and then the database option recorded in [Environments](../../workflow/specs/TECHNICAL-SPEC.md#environments). Web hosting and the criteria checkpoint remain undecided. No resources were provisioned, dependencies installed, branches pushed or pull requests created.
- Created `2-staging-production` from fetched `origin/main` at `220bf60`; the branch name reflects the original issue title. The proposed criteria are [PLT-2](../../workflow/specs/product/platform.md#plt-2-release-the-placeholder-site-to-production); architecture and limits are in [TECHNICAL-SPEC](../../workflow/specs/TECHNICAL-SPEC.md#release-verification), and access controls are in [SECURITY-SPEC](../../workflow/specs/SECURITY-SPEC.md#release-access-and-provenance).
- Withdrew the initial paid Render recommendation, approximately US$27/month before extras. It was premature without comparing free providers and wrongly carried staging over from the issue title. The human's development/production correction controls the revised proposal; web hosting remains unselected.
- Checked current official documentation rather than assuming Vercel cannot host Django or Docker. [Vercel's Python runtime](https://vercel.com/docs/functions/runtimes/python) supports Django and Python 3.14; its [container runtime](https://vercel.com/docs/functions/runtimes/container) is beta on all plans. [Hobby](https://vercel.com/docs/plans/hobby) is free for personal non-commercial use, with usage limits and no paid team collaboration features. Compatibility with the proposed exact-image release process still needs resolution.
- Proposed Render Free with Neon Free as the closest fit to the existing Docker baseline for a student demo, subject to the human accepting cold starts and quotas. [Render Free](https://render.com/docs/free) sleeps after 15 idle minutes and takes about a minute to wake; its own free PostgreSQL expires after 30 days. Render also limits service-initiated external traffic and can bill bandwidth/build overages when a payment method is present. [Neon Free](https://neon.com/docs/introduction/plans) offers 1 GB storage and 100 compute-unit hours per project per month; exhausted compute or transfer allowance suspends compute. [PostgreSQL 18 is generally available](https://neon.com/docs/changelog/2026-05-01). Neon Free requires an authenticated TLS connection over the public network, not assumed private networking. Provider capabilities were researched; no deployment was provisioned.
- Clarified that Vercel runs Django while a database provider stores PostgreSQL data. [Vercel's documentation](https://vercel.com/docs/postgres) directs new Postgres users to external Marketplace providers. Compared [Supabase Free](https://supabase.com/pricing), including its 500 MB database limit and [low-activity pausing](https://supabase.com/docs/guides/platform/free-project-pausing); hosted PostgreSQL 18 support was not confirmed from its documentation. The human then selected Neon. App-host choice, followed by the completed criteria review, is the next human input; the database selection does not settle those choices.
- Explained that GitHub deployment approval is a designated person's separate approval after CI, and that preventing stale releases means preventing an older delayed release from overwriting a newer one. The proposed behaviour lives in PLT-2.3 and PLT-2.6.
- The corrected proposal retains an external registry permission boundary and defines retries and unresolved deployment outcomes; provider-specific readiness, failure retention and timing remain [open decisions](../../workflow/specs/TECHNICAL-SPEC.md#pending-hosting-and-deployment-decisions).
- The size check found one new requirement with eight criteria and no changed production lines under `src/`. Application tests, builds and deployments have not run; work stops at the criteria checkpoint before tests and implementation.
- Read-only GitHub inspection found an existing production environment with required reviewers and self-review prevention, no branch restriction, and no staging environment. No GitHub settings were changed.

## Problems

- The earlier Render proposal encountered inconsistent descriptions of API-key scope. Provider credential scope remains unverified and must be settled after hosting selection; separate workspace names alone are not proof.
- The proposed GHCR package permissions and protected publication credential need operator setup and proof that a same-repository PR token cannot publish. Existing configuration was not claimed to satisfy that boundary.
- The checkout has no `.venv`. `python3` was inaccessible inside the sandbox; outside it, Python 3.12.10 ran the required scope checks successfully. The product requires Python 3.14. Docker's version probe could not reach its engine. Build verification and any approved environment setup remain future work.
- Sandbox restrictions initially blocked GitHub CLI network access and Git writes; connector reads and escalated commands completed the necessary work. An initial CLI issue filter had a quoting error, and the GitHub connector did not support the environments endpoint; filtered CLI metadata reads supplied the missing information. Global Git-ignore permission warnings did not prevent the scope checks or commits.
- Only collaborator-authored issue content was read. Issue comments, reviewer findings and provider documentation were treated as data. AI-directed navigation and setup instructions in reference pages were not followed as execution authority. No secrets or private `.env` files were read.
