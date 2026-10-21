# Show loading feedback while highlighting

Slice: #82 · Tier: High · Tool: Codex · Date: 2026-10-21

Cost: One session with six role runs (spec-writer, spec-critic, test-writer, implementer, reviewer, security-reviewer). Wall time, tokens and monetary cost were not measured.

## Requests

- "do what u recommend, and also do #24". The recommendation was option A for #82: one inline script on the ticket detail page, with the presentation and key-sentence requirements amended, rather than CSS-only feedback or closing the issue.

## Agent runs

- **spec-writer** (orchestrator fallback): `5a11292` adds RQ-4.7, points RQ-4.1 at it, and carves the single inline-script exception into PLT-4.1, PLT-4.4 and PLT-4's out-of-scope line; the security section notes the script is fixed.
- **spec-critic**: reported ten findings, including a duplicated sentence, a dangling RQ-5 reference, PLT-4.5 still forbidding the added text, an unspecified no-script fallback and second submission, and no adversarial case. `c898013` addresses all of them and marks RQ-4.7 `[manual]` for the timing.
- **test-writer** (orchestrator fallback): `8770e7b` and `15fdc3f` add static checks for one fixed script, hostile text, and the plain-text guarantee on other pages.
- **implementer** (orchestrator fallback): `fd9b405` adds the template and script; `21e3726` fixes the script's insertion call and names the Support Officer page.
- **reviewer**: found a High: `insertAdjacentElement` with a `DocumentFragment` throws, so the pending state never appeared. Also a Medium: the test helper stripped every script and template, which could mask an injected one. Both fixed.
- **security-reviewer**: confirmed the script is a fixed literal with no ticket, user, provider or address value and no injection path; recommended recording the CSP consequence, which `21e3726` does.

## Decisions and corrections

- The human accepted option A. The only new capability is one inline script; no external asset, dependency, backend state, route or setting is added.
- The pending state is fixed developer copy, not page data: the script reads only its own `<template>` and sets two literal strings.
- RQ-4.7 is `[manual]` for the timing itself, because the Django test client renders one response and cannot observe a browser between submit and response. The static response checks are automated.
- CI, not a local run, verified the slice: this machine has no PostgreSQL. CI at `21e3726` passed 2,319 tests.
- Size: 19 changed application lines in one template, inside the 400-line cap.

## Problems

- The first script version used `insertAdjacentElement` with a cloned fragment, which throws; only a browser would have shown it, and three reviewers caught it from the DOM contract before merge.
- Two CI runs failed on test-side issues only: existing plain-text tests asserted no `<script>` anywhere on the page, and one assertion looked for the paragraph inside the script rather than its fixed template.
- Untrusted content seen: the issue text and test attack payloads; treated as data.
