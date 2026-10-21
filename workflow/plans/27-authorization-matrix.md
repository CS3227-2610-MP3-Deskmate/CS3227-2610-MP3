# Authorization matrix

Goal: check every registered route against every role and workspace (ACC-1.5, RQ-1.6, RQ-2.5, RQ-3.6, KB-1.6, KB-2.4, ACC-4.5).

- [x] test-writer: add `src/deskmate/tests/test_authorization_matrix.py`; walk the registered routes, map each to the role the route table gives it, and check a signed-out visitor, a Requester and a Support Officer against it.
- [x] test-writer: check that every registered route has an access decision, so a new route cannot be added without one.
- [x] test-writer: check each role cannot read another workspace's ticket, article or resolution, while the owner's own officer can.

No implementation task: the merged product already provides the behaviour under test.
