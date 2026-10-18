# Security spec

Threats to Deskmate and to how it is built, and the controls against them. Where a criterion implements a control, the control names it.

## Secrets and settings

Threat: a leaked secret key lets an attacker forge sessions and signed data, leaked database credentials expose every record, and debug pages show source code, settings and tracebacks to anyone.

- Secrets and personal data never go into code, logs or fixtures, and agents never read `.env` files: see [`AGENTS.md` "Safety"](../../AGENTS.md#safety).
- Configuration comes only from environment variables ([TECHNICAL-SPEC](TECHNICAL-SPEC.md#configuration)). Committed files, including `.env.example`, the compose file, the workflows and the tests' configuration, hold only the throwaway credentials of the local and CI databases, and never a secret key. Tests may hold fixed, non-secret placeholders for optional settings such as `SOC_LLM_*`, used only with a fake provider.
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
- The `403` and `429` pages show only fixed text and `405` responses have an empty body, so none of them shows internal details (ACC-1.2, ACC-1.4, ACC-1.5, ACC-1.8, ACC-2.5, ACC-3.2).
- The health check reveals only `ok` or `error` (PLT-1.2, PLT-1.3).
- Server errors go to standard error with their traceback (PLT-1.4), never to the visitor. Logs never include request bodies or cookies. For the database server's own logs, see [Demo workspaces](#demo-workspaces).
- No error reporting or logging captures or sends the local variables of a failing request, because they can hold [generated passwords](#demo-workspaces) and their hashes. Django's debug page shows them, but debug is on only in local development.

## Sign-in and access control

Threat: a visitor opens a role's pages without signing in or with the other role, learns which usernames exist, steals, fixes or reuses a session, makes a signed-in browser sign in or out without its user meaning to, frames a page to trick its user into clicking, reads a role's page from a browser cache after its user has left, or uses the sign-in redirect to send users to another site.

- The server decides access on every request from the signed-in user's stored account: a signed-out visitor is redirected to the sign-in page and the other role gets `403`. Nothing the client sends but the session cookie affects the decision (ACC-1.4, ACC-1.5).
- Passwords are stored only as Django's salted hashes ([data model](TECHNICAL-SPEC.md#data-model)) and are never logged, and a password a user types is never shown back. Generated passwords are shown once under [Demo workspaces](#demo-workspaces) or [Requester password resets](#requester-password-resets).
- A failed sign-in shows one message whatever was wrong, and an existing username with a wrong password gets the same response, apart from its CSRF token, as an unknown username with the same submission (ACC-1.3). Gap: response time is not checked.
- Sign-in always leads to the user's own role's page and ignores any `next` parameter, so it cannot redirect anywhere else (ACC-1.5).
- Every request by a method other than `GET`, `HEAD`, `OPTIONS` or `TRACE` needs a valid CSRF token before any other rule applies, and signing in and out accept only `POST` (ACC-1.2, ACC-1.8).
- With debug off, such a request is also refused if its `Origin` is anything but exactly `https://` or `http://` and a host in `DJANGO_ALLOWED_HOSTS`. No forwarded-scheme request header changes this (ACC-1.8).
- Gap: with debug off, a request that needs a CSRF token and whose `Origin` is `http://` and a host in `DJANGO_ALLOWED_HOSTS` may be accepted, so someone who can serve plain HTTP on that host and plant a CSRF cookie might force a sign-in (ACC-1.8).
- Sessions are stored on the server. Sign-in replaces the session ID and sign-out ends the session on the server. The session cookie is dropped when the browser closes, and the server ends the session 8 hours after sign-in, however active its user is (ACC-1.2, ACC-1.6).
- With debug off, the session and CSRF cookies are sent only over HTTPS and with `SameSite=Lax`, and page scripts cannot read the session cookie (ACC-1.6).
- No page may show the sign-in or role pages in a frame, and no browser or cache may store the role pages (ACC-1.8).
- Sign-in attempts are rate-limited, which slows online password guessing, and no username is locked out on its own: see [Rate limits](#rate-limits).

## Demo workspaces

Threat: anyone, without signing in, makes the app create workspaces and accounts and spend CPU hashing their passwords; another site makes a visitor's browser create one; a request chooses the usernames, passwords, roles or workspace it gets; someone guesses a generated password or learns other workspaces' usernames; or a generated password leaks through logs, stored records, an error page, a browser or proxy cache, a framed page or someone who sees the screen. Because anyone can hold accounts of both roles, signing in and roles protect one workspace's records from other workspaces' users, not the app from strangers.

- Creating a workspace needs a `POST` with a valid CSRF token and, with debug off, an allowed `Origin`, like every request that changes something (ACC-1.8, ACC-2.5).
- The request chooses nothing: extra form fields and query parameters are ignored, and each creation makes one new workspace with two Requesters and one Support Officer and adds no account to an existing workspace (ACC-2.1, ACC-2.5).
- Generated passwords are 16 characters, each drawn independently and uniformly from the operating system's cryptographically secure random source, so each has about 79 bits of entropy. Usernames carry a random code from the same source rather than a sequence, so they reveal neither how many workspaces exist nor other workspaces' usernames (ACC-2.3, ACC-2.8).
- A generated password is shown once, only in the response that creates it, which no browser or cache may store and no page may frame. It is stored only as Django's salted hash, never in a session, cookie or other record, and no route shows it again; resending the submission makes a different workspace (ACC-2.6).
- No generated username or password, and no password hash, appears in standard output, standard error or logs in either debug mode: when creation fails, the error written there keeps its type and traceback but leaves out any database message or detail that contains one, since such details can hold the row being written (ACC-2.4, ACC-2.6). Error reports capture no local variables either: see [Error pages, health check and logs](#error-pages-health-check-and-logs).
- Creation is all or nothing, including when a code clashes, and it signs no one in and leaves a signed-in user's session as it was (ACC-2.2–ACC-2.4, ACC-2.7).
- Creating workspaces is rate-limited, so repeated creation cannot hash passwords or add workspaces faster than the limits allow: see [Rate limits](#rate-limits).
- Gap: the page shows the passwords in plain view, and a browser that keeps pages in its back-forward cache may show the page again in the same tab after Back or Forward, so anyone who sees the screen, or uses that tab soon after, may read them.
- Gap: workspaces are never deleted, and neither are sessions that end without their user signing out, so the database's storage still grows, though no faster than the limits for everyone allow creations and sign-ins (ACC-3.1). Once it is full, writes that need more storage, such as the sessions that sign-in creates, fail for every user.
- Gap: when an insert fails, the database server may log the failing statement and its detail, such as `Key (username)=(…) already exists.` or `Failing row contains (…)`, so a generated username and password hash can reach the database provider's logs, which the app does not control.

## Requester password resets

Threat: a signed-out visitor or Requester resets an account, a Support Officer changes another workspace's account or another Support Officer's password, a forged request changes a password, an old Requester session remains usable, or a generated password leaks through a retained response or failure detail.

- Reset access reuses [Sign-in and access control](#sign-in-and-access-control) in the order in [Routes](TECHNICAL-SPEC.md#routes), before selecting a target. Only a stored Requester in the caller's current stored workspace can be updated; submitted workspace, role and password fields have no authority (ACC-4.3, ACC-4.5).
- Generation reuses the password convention in [Demo workspaces](#demo-workspaces). Plaintext appears only in the successful reset POST response, except that existing local Django exception pages with `DEBUG=True` may also show it in local variables under [Error pages, health check and logs](#error-pages-health-check-and-logs). Production `DEBUG=False` error responses expose no generated password. Plaintext is retained in no session, cookie or other record; only its salted password hash is stored (ACC-4.2, ACC-4.6).
- Every response from the reset route carries `Cache-Control: no-store` and `X-Frame-Options: DENY`, including errors and redirects. Usernames are untrusted text and are escaped (ACC-4.3, ACC-4.6).
- In either debug mode, nothing the app writes to standard output, standard error or its logs during a reset includes the target username, a generated password or a password hash. Database failures keep their exception type and traceback but omit database messages, row details and chained driver details containing these values; error reports capture no local variables, as [Error pages, health check and logs](#error-pages-health-check-and-logs) requires (ACC-4.6, ACC-4.7).
- Session invalidation uses Django's authentication session hash in the [data model](TECHNICAL-SPEC.md#data-model); it affects the target's prior sessions without ending the officer's or other accounts' sessions (ACC-4.4).
- Reset POSTs that pass method and stored-account access checks use a separate kind of the existing [Rate limits](#rate-limits) mechanism before username validation, target lookup, generation or hashing, including when the submitted username will be rejected (ACC-4.8).
- Gaps: the screen and browser back-forward cache exposures described in [Demo workspaces](#demo-workspaces) also apply to reset responses. The database provider can log a failing update's statement or row details outside the app's control. A lost response cannot reveal its generated password again, and overlapping resets can supersede a password before its response is read (ACC-4.4, ACC-4.7).

## Rate limits

Threat: anyone scripts sign-in attempts, workspace creations or, after obtaining a demo Support Officer account, password resets, reusing one page load's CSRF token, to make the server hash passwords with Django's deliberately slow default hasher until the [free-plan CPU allowance](TECHNICAL-SPEC.md#free-plan-operating-limits) runs out and the site pauses, to fill the database's storage, or to guess passwords; sends a made-up forwarded-address header to escape a limit or to get someone else refused; or uses a limit to lock a known user out.

- Sign-in attempts, creations and resets are limited per client address group and for everyone, over the 10 minutes before each attempt. Each kind has an independent allowance. A refused attempt hashes no password, creates or resets nothing and counts toward no limit (ACC-3.1–ACC-3.3, ACC-4.8).
- Relaxed (#19): the separate reset allowance increases the aggregate hashing bound in [Free-plan operating limits](TECHNICAL-SPEC.md#free-plan-operating-limits), while the existing sign-in and creation allowances remain unchanged. Stored-role access alone cannot bound reset hashing because anyone can create a demo Support Officer account (ACC-4.8).
- The limits for everyone depend on nothing the client sends, so however many addresses an attacker uses, they bound how fast the app hashes passwords ([free-plan limits](TECHNICAL-SPEC.md#free-plan-operating-limits)) and adds workspaces (ACC-3.1, ACC-4.8).
- The limits apply after the CSRF and `Origin` checks and before any password is checked or hashed ([Routes](TECHNICAL-SPEC.md#routes)), so a reused CSRF token gets a script no more than the limits allow.
- The client address is the last entry of `X-Forwarded-For`, which a proxy that adds or replaces that entry keeps out of the client's control, so entries a client puts before it change nothing. IPv6 addresses are grouped by their first 64 bits, so moving between the addresses of one network does not escape a limit, and every address that is not a valid IP address shares one group, so made-up values make no new groups (ACC-3.5).
- Counts are kept only in the database, and attempts that arrive together are counted one after another, so neither parallel requests nor separate server instances let more through (ACC-3.6, ACC-3.8, ACC-4.8).
- No limit is kept per username, so no one can lock out one user without locking out everyone; see the gap below.
- The limits' records keep no readable address or anything else the request sent, and are deleted once they are 10 minutes old and an attempt of their kind is counted, as the [data model](TECHNICAL-SPEC.md#data-model), ACC-3.6 and ACC-4.8 say.
- The limits fail closed: when the database does not answer or fails during the check, or an attempt waits more than 5 seconds to be checked, no password is hashed and nothing is created or reset (ACC-3.7, ACC-4.8).
- Gap: the limits per address group trust that Vercel's proxy adds or replaces the last entry of `X-Forwarded-For` with the client's own address, without a port; this has not been verified ([operator prerequisites](TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites)). If it does not, a client could escape those limits or get another address refused; the limits for everyone still hold.
- Gap: anyone with 3 address groups can use up the sign-in limit for everyone, and anyone with 2 the creation limit for everyone, and one IPv6 network, such as a `/56` with its 256 groups, provides that many times over. While such an attack is kept up, no one can sign in or create a workspace, and if it is large enough, users already signed in are affected too, as the gap on database connections below says (ACC-3.1, ACC-3.5). Visitors who share one public address, such as on a campus network, share its limits.
- Gap: after a refusal by a limit for everyone, `Retry-After` shows, to the second, when other visitors' attempts were counted, though no address, username or count (ACC-3.3).
- Gap: the limits bound how fast the app hashes, not how much it hashes in a month, so an attack kept up at the limits for everyone for days could still use up the CPU allowance; the cost of a hash in production has not been measured ([operator prerequisites](TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites)).
- Gap: refused requests, and requests to other routes, still run the app and may query the database, so a flood of them can use up the free plans' function invocations, CPU and database compute; nothing stops requests before they reach the app.
- Gap: every attempt holds a database connection for up to 5 seconds while it waits for the earlier attempts of its kind to be checked (ACC-3.7, ACC-3.8), so a large enough flood of attempts can use up the database's connection limit, whose value on Neon's plan has not been verified. Then every request that needs the database fails, including signed-in users' pages and `/health/`. Revisit once production has been measured.
- Gap: if an attempt stalls while it is being checked, such as on a server instance that is frozen or torn down without closing its database connection, every later attempt of its kind gets `500` after waiting 5 seconds (ACC-3.7), until PostgreSQL notices that the client is gone. Revisit once production has been measured.
- Gap: a password that ACC-2 did not generate, such as one an operator sets, is protected from guessing only by the limits' rate.

## Knowledge-base authoring

Threat: a Requester or signed-out visitor reaches an authoring page; a Support Officer guesses another workspace's article identifier or submits a different workspace; another site submits an unwanted save; or stored or reflected article text executes markup in an author's browser.

- Article routes reuse the stored-account access decision, session expiry, CSRF and Origin checks in [Sign-in and access control](#sign-in-and-access-control), with method and access checks before article lookup as [Routes](TECHNICAL-SPEC.md#routes) specifies (KB-1.6).
- The server takes the workspace only from the current stored account. Both reads and writes select articles within that workspace, and an unknown identifier and an identifier in another workspace give the same generic error; extra client-supplied fields cannot select a different workspace or article (KB-1.7).
- Article titles and bodies are untrusted plain text, including when a failed validation shows them again. They are escaped in lists and form values and never rendered as HTML or Markdown (KB-1.7).
- Article responses carry the existing `Cache-Control: no-store` and `X-Frame-Options: DENY` headers; rejected requests change no article (KB-1.6).
- Failed reads and saves reuse [Error pages, health check and logs](#error-pages-health-check-and-logs); a save writes the title/body pair together, with failure behavior in KB-1.8.
- Gap: database error messages can quote article titles or bodies in app logs under existing error handling; the database provider may also log SQL or row details.
- Gap: there is no article quota, rate limit or deletion, so a signed-in Support Officer can grow the shared database until its storage cap prevents further writes, and the unpaginated list grows with their workspace. No additional storage or request-control subsystem is included.

## Knowledge-base reading

Threat: a Requester reads another workspace's article by guessing its identifier or supplying a different workspace, or stored article text executes markup in a reader's browser.

- Requester article routes reuse the stored-account access decision, session expiry, CSRF and Origin checks in [Sign-in and access control](#sign-in-and-access-control), with method and access checks before article lookup as [Routes](TECHNICAL-SPEC.md#routes) specifies (KB-2.4).
- The server takes the workspace only from the current stored account, and both the list and each reading page select articles within that workspace; an unknown identifier and an identifier in another workspace give the same generic error (KB-2.3).
- Article titles and bodies are untrusted plain text. They are escaped in the list and the reading page and never rendered as HTML or Markdown (KB-2.2).
- Reading responses carry the existing `Cache-Control: no-store` and `X-Frame-Options: DENY` headers, and reading changes no article (KB-2.4).
- Failed reads reuse [Error pages, health check and logs](#error-pages-health-check-and-logs), with failure behavior in KB-2.5.
- Gap: as for authoring, database error messages can quote article titles or bodies in app logs under existing error handling; the database provider may also log SQL or row details.

## Tickets

Threat: a signed-out visitor or the other role reaches a ticket route, a Requester or Support Officer reads or changes another workspace's tickets by guessing an identifier or supplying a different workspace, another site submits an unwanted ticket or resolution, a Support Officer attempts a ticket change through a read-only route or replaces a resolution through a repeated or overlapping submission, or stored or reflected ticket text executes markup in a reader's browser.

- Both roles' ticket routes, including the separate Support Officer resolution route, reuse the stored-account access decision, session expiry, CSRF and Origin checks in [Sign-in and access control](#sign-in-and-access-control), with method and access checks before ticket lookup as [Routes](TECHNICAL-SPEC.md#routes) specifies (RQ-1.6, RQ-2.5, RQ-2.6, RQ-3.6).
- The server takes the workspace only from the current stored account on every request, and ticket reads, creation and resolution are scoped to that workspace; unknown, foreign-workspace and out-of-range identifiers share the generic error, and client-supplied role, workspace or identifier overrides have no authority (RQ-1.7, RQ-2.4, RQ-2.5, RQ-3.5, RQ-3.6).
- Ticket titles, descriptions and resolution replies are untrusted plain text. They are escaped in lists, pages and form values, including invalid replies shown again, and never rendered as HTML or Markdown or converted to links from their text (RQ-1.3, RQ-1.7, RQ-2.7, RQ-3.7).
- Ticket responses carry the existing `Cache-Control: no-store` and `X-Frame-Options: DENY` headers, including errors and redirects; rejected requests change no ticket. Both roles' list/detail routes remain read-only, and only the separate Support Officer resolution route may save a reply and close an open ticket (RQ-1.6, RQ-2.3, RQ-2.6, RQ-3.6, RQ-3.7).
- Resolution changes only the workspace-scoped ticket's reply and open value, atomically and only while it is open, as in the [data model](TECHNICAL-SPEC.md#data-model); repeated or overlapping submissions cannot replace a saved reply, and already closed tickets with no reply remain unchanged (RQ-3.2, RQ-3.4).
- Failed reads, creations and resolutions reuse [Error pages, health check and logs](#error-pages-health-check-and-logs), with failure behavior in RQ-1.8, RQ-2.8 and RQ-3.8.
- Gap: database error messages can quote ticket titles, descriptions or replies in app logs under existing error handling; the database provider may also log SQL or row details.
- Gap: there is no ticket quota, rate limit or deletion, so a signed-in Requester can grow the shared database until its storage cap prevents further writes, and the unpaginated list grows with their workspace.

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

The PLT-2 design trusts the protected job's committed deployment inputs and Vercel's build, without independent source-content readback, pre-live runtime checks or separate promotion. A runtime failure can reach users before the public smoke test detects it. GitHub concurrency does not guarantee exclusion after runner loss; recovery relies on the operator procedure in [PLT-2.4](product/platform.md#plt-2-release-the-placeholder-site-to-production). Hosted controls still require the [setup and integration checks](TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites); none are claimed configured or verified.

Threat: untrusted source obtains production credentials, unchecked source is deployed, an earlier provider operation replaces a newer deployment, a healthy old site conceals failure, a migration leaves live code against a schema it cannot use, or migration output leaks credentials or row data.

- Pull requests and CI validation use read-only repository permissions, throwaway databases and no stored secrets. There is no container publication, package-write grant or publisher credential. The repository's workflow token alone cannot deploy to the designated Vercel project (PLT-2.1, PLT-2.5).
- Only the protected GitHub `production` job receives the Vercel token, automatically after successful same-repository `main`-push CI. Main branch protection requires a pull request approved at its final revision (stale approvals dismissed) and passing CI, without bypass or force pushes. Its environment admits only `main`, excludes pull-request refs and tags, and requires no separate deployment or rerun approval; editable PR workflow permissions cannot grant these secrets (PLT-2.1, PLT-2.3, PLT-2.5).
- The Vercel project's Git integration must be unlinked. PR changes to deployment configuration must cause no provider build or exposure of production configuration. The protected job submits only committed inputs from a clean checkout of the exact CI-checked current-`main` commit; caller-selected repositories, project IDs, source refs and deployment IDs are not accepted. Owner/project and public hostname are fixed operator configuration (PLT-2.2, PLT-2.5).
- Verify and disclose actual Vercel token scope during setup, use the least scope available and require human acceptance of access beyond this project. Production database credentials and the Django key stay in provider production settings; the job does not fetch them or dump environment configuration. There is no deployment-protection bypass secret (PLT-2.7, PLT-2.8).
- Verify the returned deployment ID, fixed owner/project, production target, `READY` state and authenticated public-hostname mapping before public smoke checks. This detects a wrong deployment or healthy old site; it does not independently prove source content or artifact equivalence (PLT-2.2, PLT-2.3).
- Production schema and deployment-time data changes occur only through the committed migration entry point, which the Vercel production build runs from the committed build configuration before the new version goes live; explicitly specified runtime application writes remain permitted under their existing controls. Pull requests, CI validation and untrusted runs cannot migrate production, and production database credentials stay in provider production settings. Health checks only verify database connectivity. Submitted inputs exclude local configuration and Git history. Production secrets must not be embedded in source, artifacts or logs (PLT-2.5, PLT-2.8, PLT-2.9, PLT-2.14).
- Relaxed (#11): build-time migration adds these exposures. Committed Django code runs at build time with write access to the production database. Vercel build logs carry the migration entry point's output, limited by PLT-2.12. Any Vercel production build migrates, including a dashboard Redeploy or a use of the Vercel token outside the job, which bypasses the current-`main` check and the GitHub concurrency group; the migration lock still keeps a build of committed code from migrating alongside another run (PLT-2.14). Vercel also runs the build command, and so the migration entry point, in every preview build. In a preview build of committed code, the entry point fails without connecting to a database (PLT-2.8). A preview build of modified source, such as one submitted with the Vercel token outside the job, can drop that check, so it is stopped only by Vercel's Preview and Development environments having no `POSTGRES_*`, `DJANGO_*` or `SOC_LLM_*` variables ([operator prerequisites](TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites)). Build-log and source protection must be enabled, and the [provider facts](TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites) confirmed, before deployment enablement.
- Migration compatibility is a review control: because the version in production keeps serving while and after migrating, after a failed release and after a rollback, and the schema is never rolled back, a pull request's migrations may only add tables, add nullable columns, add columns with a database default, or add indexes. Any other change is split across releases: first code that no longer needs the old shape, then a later migration. Every committed migration is atomic (PLT-2.14). Nothing checks compatibility automatically; an incompatible migration that is merged is still applied, the running version can fail until a fix is live, and rollback restores code but not schema.
- Gap: migrations run with no database lock-wait timeout or statement timeout. A migration that needs an exclusive table lock waits behind live app queries on that table while new queries queue behind it, which can stall the site until the build or the deployment job times out; that is an unknown migration outcome under PLT-2.4. Revisit this gap before the first migration that alters a table the app uses under load.
- GitHub concurrency, the immediate current-`main` check and a new migrating deployment on each rerun follow [Release verification](TECHNICAL-SPEC.md#release-verification). Unknown provider or migration outcomes follow the manual procedure in [PLT-2.4](product/platform.md#plt-2-release-the-placeholder-site-to-production); the migration lock (PLT-2.14) prevents concurrent migration but does not order builds (PLT-2.6), no automatic recovery block acts before intervention, and neither automatic deployment or migration retries nor automatic rollback are allowed (PLT-2.4, PLT-2.6, PLT-2.10).
- Authenticated provider responses may contain secrets. Job logs contain only the identifiers and stage results listed in [Release verification](TECHNICAL-SPEC.md#release-verification), never full API responses, request headers, environment dumps or secret values. The migration entry point's output in the provider build log is limited to the lines in PLT-2.12 and never includes SQL, database error messages or row data. Integration verification must establish these controls before deployment enablement.

## SoC LLM production probe

Threat: a stranger spends the team's SoC LLM allowance, learns whether a key is configured, or uses the probe to reach the provider with attacker-chosen text; a response or failure leaks the key or the provider's error details; a slow provider holds a request until the platform's limit.

- The route is gated by an operator secret in `SOC_LLM_PROBE_TOKEN` of at least 32 printable ASCII characters with no CR or LF. Only one `Authorization` header whose value is exactly `Bearer <SOC_LLM_PROBE_TOKEN>`, compared with `hmac.compare_digest`, passes; anything else, including a duplicated header, returns the generic `404` of PLT-1.4 before the key is read, so it reveals nothing about whether a key is configured. A request to `/health/llm`, without the trailing slash, gets that same `404` and is not redirected (PLT-3.3, [AI contract](../ai/llm-health.md#operator-token)).
- The operator generates the token with a cryptographically secure random source and rotates it on any suspected leak. The token never appears in source, CI, fixtures, `.env.example`, logs or a recorded probe result (PLT-3.7).
- The request is fixed by the app: no user, ticket, article or workspace text reaches the provider, and no request field can choose the URL, model, prompt or key (PLT-3.4, [AI contract](../ai/llm-health.md#authorship-and-prompt-injection)).
- The key is read only by this route, sent only in the provider's `Authorization` header, and never appears in a response, log, standard output, standard error or database record (PLT-3.2, PLT-3.5).
- Provider status, headers, body, error text and answer are never shown to the client or logged; the client body is only `{"status": "ok"}` or `{"status": "error"}` (PLT-3.2, [AI contract](../ai/llm-health.md#output)).
- The provider's response is untrusted data. It is read only for the fixed shape check of the [AI contract](../ai/llm-health.md#output), and never used as an instruction or passed to a template, shell, database or log.
- The provider call has a 10-second total limit, no retry and no redirect, so it cannot hold a request to the platform's 60-second limit or be sent to another host (PLT-3.6).
- `SOC_LLM_API_KEY` and `SOC_LLM_PROBE_TOKEN` are optional app settings. They stay in provider production settings only: no real value appears in CI, source, fixtures, `.env.example` or logs. `.env.example` may list them only as empty placeholders, and tests use a fixed non-secret placeholder with a fake provider. No `SOC_LLM_*` variable targets Preview or Development, and where Vercel Hobby allows it both are marked Sensitive. A missing value disables only the probe, not the app (PLT-3.5).
- Gap: nothing limits how often the probe is called, so anyone who learns its token can spend the allowance; quotas and an audit log are out of scope for this slice (#21, #22).
