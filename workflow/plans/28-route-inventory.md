# Route inventory check

Goal: keep the registered routes and the [route table](../specs/TECHNICAL-SPEC.md#routes) from drifting apart (PLT-1.9).

- [x] **test-writer**: add `src/deskmate/tests/test_routes.py`; read the table's routes and methods, read the registered patterns and their method guards, and compare them. Assert that `/health/llm` without the trailing slash is the only registered path outside the table.

No implementation task: the merged product already matches the table.
