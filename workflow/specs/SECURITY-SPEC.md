# Security spec

Threats to Deskmate and to how it is built, and the controls against them. Where a criterion implements a control, the control names it.

## Secrets and settings

Threat: a leaked secret key lets an attacker forge sessions and signed data, leaked database credentials expose every record, and debug pages show source code, settings and tracebacks to anyone.

- Secrets and personal data never go into code, logs or fixtures, and agents never read `.env` files: see [`AGENTS.md` "Safety"](../../AGENTS.md#safety).
- Configuration comes only from environment variables ([TECHNICAL-SPEC](TECHNICAL-SPEC.md#configuration)). Committed files, including `.env.example`, the compose file, the workflows and the tests' configuration, hold only the throwaway credentials of the local and CI databases, and never a secret key.
- No secret key is written in code, including the tests: with debug on and `DJANGO_SECRET_KEY` unset or empty, the app makes a random key each time it starts, and the tests make their own key on each run.
- The app fails closed: with a required variable unset or invalid, including a weak secret key or no allowed hosts when debug is off, it refuses to start, and its error names the variable but never shows a value (PLT-1.7).
- Debug is off unless explicitly turned on (PLT-1.6), and it is turned on only in local development.
- With debug off, the app answers only to the hosts in `DJANGO_ALLOWED_HOSTS`; a `*` there switches that check off. Production configuration permits only the exact public hostname, without expansion from provider metadata or request headers (PLT-2.8); the underlying PLT-1 configuration syntax is unchanged.
- CI validation uses no stored secrets, and its databases are throwaway containers; release credentials are isolated as described in [Release access and provenance](#release-access-and-provenance).
- The local database accepts connections only from the developer's own machine.
- Production configuration uses a database, credentials and Django secret key separate from development and temporary CI values; production credentials are never supplied to CI validation (PLT-2.8).
- Production database access uses authenticated public-network TLS with system-CA and hostname verification, without plaintext fallback; local and CI plaintext is limited to loopback. The production-mode signal, direct endpoint, connection lifetime and timeout are specified in [Configuration](TECHNICAL-SPEC.md#configuration). No private network or disabled external database access is claimed (PLT-2.8).

## Error pages, health check and logs

Threat: an error response reveals internals that help an attacker, or reflects attacker input into a page.

- With debug off, errors show no internal details (PLT-1.4).
- The health check reveals only `ok` or `error` (PLT-1.2, PLT-1.3).
- Server errors go to standard error with their traceback (PLT-1.4), never to the visitor. Logs never include request bodies or cookies.

## Container image

Threat: a tampered base image, a secret baked into an image layer, or a compromised app taking over its container.

- Base images are official Docker images pinned to an exact version and digest, wherever they are used, including development and CI PostgreSQL.
- There is no app image; the [native-runtime architecture](TECHNICAL-SPEC.md#architecture) trusts Vercel's runtime isolation and patch management. App-image minimisation and non-root controls are inapplicable to this managed runtime.
- Django's development server never serves a deployed environment.

## CI and dependencies

Threat: a compromised action or package, or an agent's change to a workflow, runs attacker code with the repository's token, leaks secrets or lets failing code merge.

- Workflows get least-privilege permissions, SHA-pinned actions, secrets only where needed, no `pull_request_target`, and the verify command run unchanged: see [`devops.md`](../agents/devops.md), step 3.
- Python dependencies are exact pins of real PyPI packages ([`devops.md`](../agents/devops.md), step 2), added only with the human's approval ([`AGENTS.md` "Safety"](../../AGENTS.md#safety)). The official Vercel CLI has an exact version pin in the [deployment workflow](../../.github/workflows/deploy.yml).
- Only devops may write the workflows, the Dockerfile, the compose file and the requirements files, within the limits in [`workflow/README.md` "How scope is enforced"](../README.md#how-scope-is-enforced).
- Merging needs a reviewed pull request with passing checks: see [`workflow/README.md` "GitHub settings"](../README.md#github-settings-once).

## Release access and provenance

The PLT-2 design trusts the protected job's committed deployment inputs and Vercel's build, without independent source-content readback, pre-live runtime checks or separate promotion. A runtime failure can reach users before the public smoke test detects it. GitHub concurrency does not guarantee exclusion after runner loss; recovery relies on the operator procedure in [Release verification](TECHNICAL-SPEC.md#release-verification). Hosted controls still require the [setup and integration checks](TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites); none are claimed configured or verified.

Threat: untrusted source obtains production credentials, unchecked source is deployed, a stale run replaces a newer deployment, or a healthy old site conceals failure.

- Pull requests and CI validation use read-only repository permissions, throwaway databases and no stored secrets. There is no container publication, package-write grant or publisher credential. The repository's workflow token alone cannot deploy to the designated Vercel project (PLT-2.1, PLT-2.5).
- Production release relies on the reviewed-pull-request and passing-check requirements on `main`, requiring approval of the final source revision, dismissal of stale approvals after source changes, and no merge bypass, described in [GitHub settings](../README.md#github-settings-once). Only the protected GitHub `production` job receives the Vercel token. Its environment admits only `main`, excludes pull-request refs and tags, has no separate required deployment reviewer, and prohibits bypassing the remaining admission and recovery controls. Eligible successful push CI starts deployment automatically; editable PR workflow permissions cannot grant these secrets (PLT-2.1, PLT-2.3, PLT-2.5).
- The Vercel project's Git integration must be unlinked. PR changes to deployment configuration must cause no provider build or exposure of production configuration. The protected job submits only committed inputs from a clean checkout of the exact CI-checked current-`main` commit; caller-selected repositories, project IDs, source refs and deployment IDs are not accepted. Owner/project and public hostname are fixed operator configuration (PLT-2.2, PLT-2.5).
- Verify and disclose actual Vercel token scope during setup, use the least scope available and require human acceptance of access beyond this project. Production database credentials and the Django key stay in provider production settings; the job does not fetch them or dump environment configuration. There is no deployment-protection bypass secret (PLT-2.7, PLT-2.8).
- Verify the returned deployment ID, fixed owner/project, production target, `READY` state and authenticated public-hostname mapping before public smoke checks. This detects a wrong deployment or healthy old site; it does not independently prove source content or artifact equivalence (PLT-2.2, PLT-2.3).
- Build, deployment and checks never run migrations or mutate production data; health checks only verify database connectivity. Submitted inputs exclude local configuration and Git history. Production secrets must not be embedded in source, artifacts or logs (PLT-2.8).
- GitHub concurrency, the immediately-before-submission current-`main` check, fresh validation and deployment on explicitly requested reruns, and automatic blocking of later submissions while an earlier provider outcome is unsettled follow [Release verification](TECHNICAL-SPEC.md#release-verification). Missing reconciliation evidence fails closed. Only a repository administrator may acknowledge all affected attempts after confirming the outcome and that no earlier operation can complete later; that acknowledgement releases the block without waiving CI or current-main checks; lost responses require recovery even when a job exits normally as failed. Neither automatic deployment retries nor automatic rollback are allowed (PLT-2.4, PLT-2.6).
- Recovery acknowledgement must originate in authoritative administrator-controlled production configuration, with no inherited fallback and with read credentials isolated as specified in [Recovery admission](TECHNICAL-SPEC.md#recovery-admission).
- Authenticated provider responses may contain secrets. Logs contain only the identifiers and stage results listed in [Release verification](TECHNICAL-SPEC.md#release-verification), never full API responses, request headers, environment dumps or secret values. Integration verification must establish these controls before deployment enablement.
