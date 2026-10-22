Goal: Implement [RQ-5.3](../specs/product/tickets.md#rq-5-suggest-articles-while-writing-a-ticket) using the [confirmed matching contract](../specs/ai/find-a-fix.md#output-and-source-matching) within the [Find a fix controls](../specs/SECURITY-SPEC.md#find-a-fix).

- [x] **implementer**: Update `src/deskmate/tickets/views.py` to replace phrase-substring matching with deterministic retained whole-word matching; estimate 50–80 changed application lines, with a confirmed maximum of 100 and the default 400-line application cap.
  Reuse a shared complete-input casefold/Unicode `str.isalnum()` tokenizer for phrases and independent saved title/body sources, applying exactly the linked contract's phrase-word filtering and set union.
  Preserve whole-reply empty-string rejection before filtering, skip article reads for an empty retained set, and retain the current workspace-scoped keyset paging, ascending stored identity and earliest-three stop.
  Make `src/deskmate/tests/test_find_a_fix.py` pass, especially `test_find_a_fix_reported_printer_draft_matches_saved_demo_article`, `test_find_a_fix_retained_whole_words_match_title_or_body` and the filtering, Unicode, source-boundary and deduplication regressions.
  Retain that module's workspace isolation, ordering, paged-read, third-match stop, failure, privacy and adversarial coverage through the full verification command below.
  Keep the prompt, schema, gateway, admission, audit and response rendering unchanged; add no ranking, stemming, fuzzy matching, synonyms, dependency or other capability.
- [ ] **implementer**: After the application task, update `docs/UserGuide.md` to describe the built whole-word overlap behavior and best-effort relevance using the exact UI text, linking to the contract for detailed rules.
  Read the changed section back against `src/deskmate/tickets/views.py` and `src/deskmate/tickets/templates/tickets/form.html`; retain the application task's test targets and full CI verification, and add no prose tests.

Verification: the orchestrator may commit and push provisionally and update existing draft PR #97 to use the existing PostgreSQL CI running unchanged `ruff check . && ruff format --check . && pytest`.
Application verification: [CI run 39709409258](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39709409258) at `52cfb619becc45f5d82639a7e3ed05c662b13f3d` passed the full verification command on PostgreSQL, as verified by the orchestrator from the job logs.
Run no local database tests and change no configuration, credentials or services; local PostgreSQL rejects the committed test credentials.
Keep both task boxes unchecked until successful full CI verifies their respective changes; record completion only after green CI, in a later plan-only commit if needed.
