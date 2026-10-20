Goal: Implement [PLT-6.1–6.8](../specs/product/platform.md#plt-6-record-internal-ai-call-audit-metadata) through the [internal audit boundary](../specs/TECHNICAL-SPEC.md#internal-ai-call-audit-boundary), within the confirmed application estimate and total diff budget.

- [x] **implementer**: Add `src/deskmate/models.py`, `src/deskmate/llm_audit.py` and generated `src/deskmate/migrations/{__init__,0001_initial}.py`; make `src/deskmate/tests/test_llm_audit.py` (PLT-6.1–6.8) pass and preserve the full regression suite.
  - Reuse Django model, HMAC, durable-transaction, transaction-local timeout and suppressed-error conventions; generate and inspect the single atomic migration, keeping recording isolated from existing routes.
  - Run `ruff check . && ruff format --check . && pytest` through existing [GitHub CI](../../.github/workflows/ci.yml), per human direction; tick this task only after CI passes for the implementation commit.
