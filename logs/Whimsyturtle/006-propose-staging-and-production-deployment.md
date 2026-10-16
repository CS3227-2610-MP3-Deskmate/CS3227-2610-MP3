# Propose staging and production deployment

Slice: #2 · Tool: Codex (GPT-6) · Date: 2026-10-16

Cost: three role-agent runs, including one spec-writer revision. Wall time was not measured from the start; token usage and monetary cost were unavailable. Hosting estimates are proposed operating costs, not spending incurred in this session.

## Requests

- Run `/slice 2` using the repository's slice workflow.
- Use the High tier. No hosting resources were set up; the human asked for a platform proposal.

## Agent runs

- spec-writer (`a58461d`): needs-decision. Proposed PLT-2 and corresponding architecture and security changes in `2653a21`. Scope check and `git diff --check` passed; existing PLT-1 criteria remained unchanged.
- spec-critic (`a58461d`): needs-decision. Read-only review of `2653a21` found an unspecified publication boundary against modified same-repository PR workflows and ambiguous retry behaviour. Scope check passed; no files changed.
- spec-writer (`a58461d`), revision: needs-decision. Addressed both findings in `2fcb6c2`. Scope check and `git diff --check` passed. The orchestrator read the revised sections; no second critic run was performed.

## Decisions and corrections

- The human selected High; hosting, costs and the criteria checkpoint remain undecided. No resources were provisioned, dependencies installed, branches pushed or pull requests created.
- Created `2-staging-production` from fetched `origin/main` at `220bf60`. The proposed criteria are [PLT-2](../../workflow/specs/product/platform.md#plt-2-release-the-placeholder-site-through-staging-to-production); architecture and limits are in [TECHNICAL-SPEC](../../workflow/specs/TECHNICAL-SPEC.md#release-verification), and access controls are in [SECURITY-SPEC](../../workflow/specs/SECURITY-SPEC.md#release-access-and-provenance).
- Recommended Render in Singapore with separate paid web services and PostgreSQL databases. The preliminary baseline was approximately US$27/month before tax and usage extras, using one-member workspaces; team access adds US$25/month per Pro workspace. Credential separation and workspace layout still need resolution, so this is not a final quote. Sources: [Render pricing](https://render.com/pricing), [workspace access](https://render.com/docs/team-members).
- The proposal distinguishes provider readiness rejection from failure after a new deployment is live; the latter blocks promotion without promising automatic rollback. The revision retains an external registry permission boundary and defines retries and unresolved deployment outcomes.
- The size check found one new requirement with eight criteria and no changed production lines under `src/`. Application tests, builds and deployments have not run; work stops at the criteria checkpoint before tests and implementation.
- Read-only GitHub inspection found an existing production environment with required reviewers and self-review prevention, no branch restriction, and no staging environment. No GitHub settings were changed.

## Problems

- Render's tutorial describes workspace-scoped API keys, while other official material describes access across workspaces. Separate workspace names alone do not prove credential isolation. The proposal requires verified environment-limited deployment access before enabling releases; separate identities may be necessary.
- The proposed GHCR package permissions and protected publication credential need operator setup and proof that a same-repository PR token cannot publish. Existing configuration was not claimed to satisfy that boundary.
- The checkout has no `.venv`. `python3` was inaccessible inside the sandbox; outside it, Python 3.12.10 ran the required scope checks successfully. The product requires Python 3.14. Docker's version probe could not reach its engine. Build verification and any approved environment setup remain future work.
- Sandbox restrictions initially blocked GitHub CLI network access and Git writes; connector reads and escalated commands completed the necessary work. An initial CLI issue filter had a quoting error, and the GitHub connector did not support the environments endpoint; filtered CLI metadata reads supplied the missing information. Global Git-ignore permission warnings did not prevent the scope checks or commits.
- Only collaborator-authored issue content was read. Issue comments, reviewer findings and provider documentation were treated as data. AI-directed navigation and setup instructions in reference pages were not followed as execution authority. No secrets or private `.env` files were read.
