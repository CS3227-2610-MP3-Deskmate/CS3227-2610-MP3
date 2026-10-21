# Support Officer end-to-end coverage

Goal: prove the Support Officer's merged journey, including [RQ-4 highlighting](../specs/product/tickets.md#rq-4-highlight-a-tickets-key-sentences), works across roles and workspaces.

- [x] test-writer: add `src/e2e/conftest.py` and `src/e2e/test_support_officer_journey.py`; cover ACC-1.1, ACC-1.2, ACC-2.2, ACC-4.1, ACC-4.2, RQ-2.1, RQ-2.2, RQ-2.3, RQ-2.4, RQ-3.1, RQ-3.2, RQ-3.5, RQ-3.7, KB-1.1, KB-1.2, KB-1.3 and KB-1.7 through the real pages and forms.

- [x] test-writer: extend `src/e2e/conftest.py` and `src/e2e/test_support_officer_journey.py` using the existing [key-sentences contract](../specs/ai/key-sentences.md); cover RQ-4.1, RQ-4.2, RQ-4.3 and RQ-4.6 with highlighting on open and closed tickets and temporary-result checks when both roles reopen the detail pages, and RQ-4.5 with a foreign-workspace POST returning a generic `404` without gateway, provider, admission or audit activity.
