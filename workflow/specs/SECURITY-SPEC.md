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
- The `403` pages show only fixed text and `405` responses have an empty body, so neither shows internal details (ACC-1.2, ACC-1.4, ACC-1.5, ACC-1.8, ACC-2.5).
- The health check reveals only `ok` or `error` (PLT-1.2, PLT-1.3).
- Server errors go to standard error with their traceback (PLT-1.4), never to the visitor. Logs never include request bodies or cookies.

## Sign-in and access control

Threat: a visitor opens a role's pages without signing in or with the other role, learns which usernames exist, steals, fixes or reuses a session, makes a signed-in browser sign in or out without its user meaning to, frames a page to trick its user into clicking, reads a role's page from a browser cache after its user has left, or uses the sign-in redirect to send users to another site.

- The server decides access on every request from the signed-in user's stored account: a signed-out visitor is redirected to the sign-in page and the other role gets `403`. Nothing the client sends but the session cookie affects the decision (ACC-1.4, ACC-1.5).
- Passwords are stored only as Django's salted hashes ([data model](TECHNICAL-SPEC.md#data-model)) and are never logged, and a password a user types is never shown back. A generated password is shown once, as [Demo workspaces](#demo-workspaces) says.
- A failed sign-in shows one message whatever was wrong, and an existing username with a wrong password gets the same response, apart from its CSRF token, as an unknown username with the same submission (ACC-1.3). Gap: response time is not checked.
- Sign-in always leads to the user's own role's page and ignores any `next` parameter, so it cannot redirect anywhere else (ACC-1.5).
- Every request by a method other than `GET`, `HEAD`, `OPTIONS` or `TRACE` needs a valid CSRF token before any other rule applies, and signing in and out accept only `POST` (ACC-1.2, ACC-1.8).
- With debug off, such a request is also refused if its `Origin` is anything but exactly `https://` or `http://` and a host in `DJANGO_ALLOWED_HOSTS`. No forwarded-scheme request header changes this (ACC-1.8).
- Gap: with debug off, a request that needs a CSRF token and whose `Origin` is `http://` and a host in `DJANGO_ALLOWED_HOSTS` may be accepted, so someone who can serve plain HTTP on that host and plant a CSRF cookie might force a sign-in (ACC-1.8).
- Sessions are stored on the server. Sign-in replaces the session ID and sign-out ends the session on the server. The session cookie is dropped when the browser closes, and the server ends the session 8 hours after sign-in, however active its user is (ACC-1.2, ACC-1.6).
- With debug off, the session and CSRF cookies are sent only over HTTPS and with `SameSite=Lax`, and page scripts cannot read the session cookie (ACC-1.6).
- No page may show the sign-in or role pages in a frame, and no browser or cache may store the role pages (ACC-1.8).
- Gap: sign-in attempts have no rate limit or lockout, so nothing slows online password guessing.

## Demo workspaces

Threat: anyone, without signing in, makes the app create workspaces and accounts and spend CPU hashing their passwords; another site makes a visitor's browser create one; a request chooses the usernames, passwords, roles or workspace it gets; someone guesses a generated password or learns other workspaces' usernames; or a generated password leaks through logs, stored records, an error page, a browser or proxy cache, a framed page or someone who sees the screen. Because anyone can hold accounts of both roles, signing in and roles protect one workspace's records from other workspaces' users, not the app from strangers.

- Creating a workspace needs a `POST` with a valid CSRF token and, with debug off, an allowed `Origin`, like every request that changes something (ACC-1.8, ACC-2.5).
- The request chooses nothing: extra form fields and query parameters are ignored, and each creation makes one new workspace with two Requesters and one Support Officer and adds no account to an existing workspace (ACC-2.1, ACC-2.5).
- Generated passwords are 16 characters, each drawn independently and uniformly from the operating system's cryptographically secure random source, so each has about 79 bits of entropy. Usernames carry a random code from the same source rather than a sequence, so they reveal neither how many workspaces exist nor other workspaces' usernames (ACC-2.3, ACC-2.8).
- A generated password is shown once, only in the response that creates it, which no browser or cache may store and no page may frame. It is stored only as Django's salted hash, never in a session, cookie or other record, and no route shows it again; resending the submission makes a different workspace (ACC-2.6).
- No generated username or password, and no password hash, appears in standard error or logs in either debug mode: when creation fails, the error written there keeps its type and traceback but leaves out any database message or detail that contains one, since such details can hold the row being written (ACC-2.4, ACC-2.6).
- Creation is all or nothing, including when a code clashes, and it signs no one in and leaves a signed-in user's session as it was (ACC-2.2–ACC-2.4, ACC-2.7).
- Gap: the page shows the passwords in plain view, and a browser that keeps pages in its back-forward cache may show the page again in the same tab after Back or Forward, so anyone who sees the screen, or uses that tab soon after, may read them.
- Gap: creating workspaces has no rate limit, and workspaces are never deleted. Each creation hashes three passwords with Django's deliberately slow default hasher, so repeated creation can use up the [free-plan CPU allowance](TECHNICAL-SPEC.md#free-plan-operating-limits), which can pause the site, and fill the database's storage, after which writes that need more storage, such as the sessions that sign-in creates, fail for every user.

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

Threat: untrusted source obtains production credentials, unchecked source is deployed, an earlier provider operation replaces a newer deployment, or a healthy old site conceals failure.

- Pull requests and CI validation use read-only repository permissions, throwaway databases and no stored secrets. There is no container publication, package-write grant or publisher credential. The repository's workflow token alone cannot deploy to the designated Vercel project (PLT-2.1, PLT-2.5).
- Only the protected GitHub `production` job receives the Vercel token, automatically after successful same-repository `main`-push CI. Main branch protection requires a pull request approved at its final revision (stale approvals dismissed) and passing CI, without bypass or force pushes. Its environment admits only `main`, excludes pull-request refs and tags, and requires no separate deployment or rerun approval; editable PR workflow permissions cannot grant these secrets (PLT-2.1, PLT-2.3, PLT-2.5).
- The Vercel project's Git integration must be unlinked. PR changes to deployment configuration must cause no provider build or exposure of production configuration. The protected job submits only committed inputs from a clean checkout of the exact CI-checked current-`main` commit; caller-selected repositories, project IDs, source refs and deployment IDs are not accepted. Owner/project and public hostname are fixed operator configuration (PLT-2.2, PLT-2.5).
- Verify and disclose actual Vercel token scope during setup, use the least scope available and require human acceptance of access beyond this project. Production database credentials and the Django key stay in provider production settings; the job does not fetch them or dump environment configuration. There is no deployment-protection bypass secret (PLT-2.7, PLT-2.8).
- Verify the returned deployment ID, fixed owner/project, production target, `READY` state and authenticated public-hostname mapping before public smoke checks. This detects a wrong deployment or healthy old site; it does not independently prove source content or artifact equivalence (PLT-2.2, PLT-2.3).
- Build, deployment and checks never run migrations or mutate production data; health checks only verify database connectivity. Submitted inputs exclude local configuration and Git history. Production secrets must not be embedded in source, artifacts or logs (PLT-2.8).
- GitHub concurrency, the immediate current-`main` check and new deployment on each rerun follow [Release verification](TECHNICAL-SPEC.md#release-verification). For unknown provider outcomes, operators manually pause deployments, cancel queued runs and reconcile Vercel before resuming; no automatic recovery block prevents an earlier in-flight provider operation from racing a later release before intervention. Neither automatic deployment retries nor automatic rollback are allowed (PLT-2.4, PLT-2.6).
- Authenticated provider responses may contain secrets. Logs contain only the identifiers and stage results listed in [Release verification](TECHNICAL-SPEC.md#release-verification), never full API responses, request headers, environment dumps or secret values. Integration verification must establish these controls before deployment enablement.
