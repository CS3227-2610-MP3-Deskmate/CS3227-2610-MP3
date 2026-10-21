# Requester end-to-end coverage

Goal: prove the Requester's merged journey works across roles and workspaces.

- [x] test-writer: add `src/e2e/conftest.py` and `src/e2e/test_requester_journey.py`; cover ACC-1.1, ACC-1.2, ACC-2.2, ACC-2.9, RQ-1.1, RQ-1.2, RQ-1.3, RQ-1.7, KB-2.1, KB-2.2 and KB-2.3 through the real pages and forms.
- [x] test-writer: extend the journey with the RQ-5 `Suggest articles` flow, covering RQ-5.1 to RQ-5.4 through the real form and the fake gateway provider. Depends on #80, so this branch is stacked on it.

No implementation task: the merged product already provides the behaviour under test.
