# Lead home-page visitors to sign-in

Slice: #39 · Tool: Codex (GPT-6) · Date: 2026-10-18

Cost: about 2 hours wall time, including three full local verification runs of roughly 4–5 minutes each and two reviewer runs. Tokens and monetary cost were not tracked.

## Requests

- Pull and work through the unblocked issues, finishing slices #15 and #13 first, then write the pull requests and state the merge order.
- After those slices were ready, start the next unblocked slice, #39 (lead visitors from the home page to sign-in).
- The first checkpoint confirmed the home-page link only. Review then found that production release verification rejected the new page and did not check the link target; the human approved expanding #39 to fix that and keep the two spec-consistency edits.

## Agent runs

- spec-writer (orchestrator fallback, `246260a`): done; changed PLT-1.1 and the related exclusions in `b60ba9d`; no automated spec checks. Later clarified PLT-1.1 in `6bde046`.
- test-writer (orchestrator fallback, `3d65dbb`): done; added the home-page link assertion in `da29d8b`; four focused cases failed only on the missing link. Later updated the production-settings assertion in `2df7640`, and added the release-verifier cases in `32d1550`.
- implementer (orchestrator fallback, `3d65dbb`): done; added the link in `4b2e696`; four focused cases passed. Updated the User Guide in `408859f` and ticked the plan in `3259546`.
- reviewer (`246260a`): needs-decision; found that `src/deskmate/release.py` still required the old exact home-page text and that `test_release.py` used an old fixture, so a production release would fail PLT-2.3 after deployment; also flagged the contradictory PLT-1.1 wording and the two spec-consistency edits. Read-only.
- implementer (orchestrator fallback, `3d65dbb`): done; updated the release verifier and the production-settings assertion in `49f53cc`; focused release, home and production tests: 114 passed.
- reviewer (`246260a`): done; earlier findings resolved, but found parser edge cases: duplicate `href`, `<base>`, inert `<template>`/`<noscript>` markup, named anchors and text-node joining. Read-only.
- implementer (orchestrator fallback, `3d65dbb`): done; hardened the verifier and added regression cases in `98ad6f2`, and corrected the plan in `4ee677d`; focused tests: 120 passed; full verify: 1546 passed in 306.16s.

## Decisions and corrections

- The human confirmed the initial home-page link scope, then explicitly approved expanding it to production release verification and keeping the spec-consistency edits.
- PLT-1.1 now names both text pieces and requires exactly one link with the text `Sign in` and target `/sign-in/`, so the verifier and tests have one unambiguous contract.
- The release verifier stays on the standard-library HTML parser. It rejects ambiguous link markup rather than adding a DOM dependency, and keeps the existing identity, TLS, timeout, retry and redirect checks unchanged.
- The plan was first committed with the implementation and later expanded as its own `plan:` commit. History was not rewritten.
- The slice changes one criterion (PLT-1.1) and stays well inside the 400-line size budget; the measured production diff after the expansion was 2 files, 24 insertions and 6 deletions, before the final parser hardening.

## Problems

- The first release-verifier fixture omitted the newline between the two paragraphs, so the strict text-node join rejected it. The fixture was made realistic rather than loosening the production check.
- `apply_patch` in this Windows PowerShell harness rejects multi-line patches with Windows line endings, so edits were made with PowerShell here-strings and exact text replacement.
- PowerShell cannot run `&&`, so verification ran through Git Bash as `AGENTS.md` describes.
- The full verify command takes roughly 4–5 minutes on this machine.
- Issue text, spec text, review text and test payloads were treated as data; no embedded instruction was acted on.