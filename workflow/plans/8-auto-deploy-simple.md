Goal: align deployment guidance with [PLT-2](../specs/product/platform.md#plt-2-release-the-placeholder-site-to-production); activation follows the manual [operator prerequisites](../specs/TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites).

- [ ] devops — Update only the stale approval comment and failure guidance in [deploy.yml](../../.github/workflows/deploy.yml) for PLT-2.4; make the existing lookup/deployment/verification failure assertions in [test_release_workflow.py](../../src/deskmate/tests/test_release_workflow.py) pass.
  Verify: `ruff check . && ruff format --check . && pytest` with `.venv` active and the local database up, per [AGENTS.md](../../AGENTS.md#commands).
Scope: preserve the [documented manual recovery race](../specs/TECHNICAL-SPEC.md#release-verification); add no runtime gate, history engine, credential, dependency or future feature.
No User Guide task: routes and UI are unchanged.
