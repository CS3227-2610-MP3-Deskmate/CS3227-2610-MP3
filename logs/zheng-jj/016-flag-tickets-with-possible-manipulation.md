# Flag tickets with possible manipulation

Slice: #23 · Tier: High · Tool: Claude Code in VS Code (Claude Opus 5.5) · Date: 2026-10-22

Cost: 24 role-agent runs using about 1.8M subagent tokens. The orchestrator's own tokens, wall time and monetary cost were not measured.

## Requests

- "pull and check what issues are left open", twice, then "get started on 23".
- At the first question, chose a fixed pattern check with no AI call, and the marker on the Support Officer list and detail pages.
- At the checkpoint, chose to drop `"}` from sign 4 and to continue the slice; approved setting up the local `.venv`, `.env` and PostgreSQL container.
- After security review round 1, chose to document role cues after U+2028/U+2029 as a known miss.
- "pull and continue", then "finish 23"; approved pushing the branch and opening the pull request.
- After security review round 2, chose to put the list marker on its own line; then said "make ur own decisions, stop asking me".
- "pull, it should have been merged. then open both prs": this pull request and the separate reflection pull request for #35.

## Agent runs

- **spec-writer** (`246260a`), 5 runs, all within scope:
  - RQ-6 with 8 criteria plus PRODUCT, TECHNICAL and SECURITY-SPEC links: `974c209`.
  - The spec-critic's fixes, including escaping the raw invisible characters it had written: `7af8cdd`.
  - Sign 4 without `"}`: `f75fe3c`.
  - Review round 1: `<bdi>` around list titles and the U+2028/U+2029 known miss: `ec277a4`.
  - Review round 2: the list marker in its own paragraph: `388b4a8`.
  - Each run checked every spec example against the signs in a scratch script.
- **spec-critic** (`a58461d`): 7 findings on `974c209`; the blocker was raw invisible characters in the examples. Its scratch check confirmed every example's stated outcome.
- **test-writer** (`3d65dbb`), 3 runs, all within scope:
  - `159942c`: 99 tests in `test_manipulation_marker.py`, 73 failing on the missing marker; one assertion in `test_key_sentences.py` changed to allow only the fixed marker `<strong>`. Five deliberately wrong scratch versions were each caught.
  - `52fe55e`: `<bdi>` structure, separator misses and every sign branch; 130 failed only on the missing `<bdi>`.
  - `cae0a2a`: the marker's own `<p>`, three more bidi titles and four more sign-5 neighbours; 131 failed only on the inline marker.
- **implementer** (`3d65dbb`), 6 runs, all within scope:
  - Plan: `bb4d542`.
  - Task 1: `ecce4e9`, 74 changed application lines; `remove_guarded()` extracted from the gateway's `_guard` with unchanged behaviour.
  - Task 2, the User Guide: `f01713d`.
  - Review fixes: `fede406` (`<bdi>`), `948fbb6` (marker paragraph), `65f9566` (User Guide wording).
  - Integration fix: `3850ebf` narrowed #100's saved-text panel selector in `base.html` so the panel stays on the description, not the detail marker paragraph.
  - Each run reported `pytest` with only the 17 environment-only failures below.
- **reviewer** (`8d74e8e`), 4 rounds:
  - `20d2c3d..f01713d`: no Critical/High/Medium; Low: untested sign branches, and the public `remove_guarded()` to note in the pull request.
  - `f01713d..fede406`: no Critical/High/Medium; Low: `list.html` reuses `can_resolve_ticket` as the Support Officer switch; asked whether the human confirmed the `<bdi>` spec change.
  - `fede406..65f9566`: no Critical/High/Medium; Low: the plan still described the inline marker (fixed in `207488f`), and a test comment calls U+FF00 a lower neighbour.
  - `207488f..3850ebf`: no Critical/High/Medium; Low: browsers without `:has()` get no saved-text panel; this log and the plan predated the merge and fix (updated).
- **security-reviewer** (`8d74e8e`), 4 rounds:
  - `20d2c3d..f01713d`: no Critical/High/Medium; L1 bidi controls in a list title could reverse or move the marker; L2 U+2028/U+2029 role cues; L3 untested hidden-character ranges. No regex blow-up (about 1.3 ms per 10,000-code-point ticket).
  - `f01713d..fede406`: `<bdi>` alone did not contain a stray U+2069 plus an override, or an unclosed isolate after right-to-left text; shown in headless Chrome. L3 resolved apart from four neighbours.
  - `fede406..65f9566`: both resolved. New Low: stacked combining marks in a title could visually cover the marker, on either page and before this slice too.
  - `65f9566..3850ebf`: no Critical/High/Medium; ticket text cannot move the panel onto the marker. Lows: no `:has()` support fails safe with no panel; no test pins the panel selector, which the orchestrator left open because PLT-4 keeps selectors out of scope.
- **Orchestrator commits:** `e2a6b1e` merged `main` (#97, #98), resolving a conflict in SECURITY-SPEC's Find a fix gap by keeping both sides; `ce24354` merged `main` (#100) without conflict; `207488f` and a later plan commit recorded the review and integration fixes.

## Decisions and corrections

- Tier High, because the slice touches an AI feature's safety and `llm_gateway.py`.
- The human chose the fixed pattern check, its placement, dropping `"}`, the U+2028/U+2029 known miss and the marker's own line.
- The orchestrator treated as within scope: extracting `remove_guarded()`; wrapping only Support Officer list titles in `<bdi>`, so the Requester list stays unchanged; the extra 1rem below flagged list items from the shared paragraph margin.
- The `<bdi>` spec change (`ec277a4`) was described to the human but not put to them as a question; the reviewer flagged this.
- After the human delegated decisions, the orchestrator left the U+FF00 test comment and the combining-mark Low as open findings rather than start a fourth review round.
- The `:has()` selector in `3850ebf` was accepted: browsers older than about two years show no saved-text panel, which is #99's earlier look.
- Size: 80 changed application lines under `src/`, within the confirmed 80–120 estimate and the 400-line cap.

## Problems

- On this Mac, 17 tests in `test_migration.py` fail on unchanged `main` too, because macOS cannot bind 127.0.0.2. Every local verify run reported only those; GitHub CI must confirm them.
- spec-writer and implementer twice wrote raw invisible characters into files while editing; both caught and escaped them before handoff.
- Security review round 2 launched headless Chrome and then headless Firefox, beyond its read-only remit. Firefox started its staged updater; the reviewer stopped it and reported Firefox still at 158.0 with a valid signature and the update still pending. Round 3 was told not to launch applications.
- Untrusted content seen: escaped red-team payloads in the specs and tests; treated as data.
