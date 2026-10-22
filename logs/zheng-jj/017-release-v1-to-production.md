# Release v1.0 to production

Slice: #37 · Tier: High · Tool: Claude Code in VS Code (Claude Opus 5.5) · Date: 2026-10-22

Cost: 8 role-agent runs (including 2 resumes) using about 0.5M subagent tokens. The orchestrator's own tokens, wall time and monetary cost were not measured.

## Requests

- "ok do 37", after #23 (#102) and the zheng-jj reflection (#101) merged. Earlier in the session the human had said "make ur own decisions, stop asking me", so no checkpoint question was asked.
- "changes requested for the prod pr": Whimsyturtle's review of #103 asked for the production link in the relevant files.

## Agent runs

- **spec-writer** (`246260a`), 1 run and 1 resume, within scope: `bdeaabe` changes PLT-1.1's home sentence to the one a team member proposed on #37, adds a visitor clause to PLT-1's `Why:` and renames the `/` route purpose. Its first draft also renamed the PLT-1 and PLT-2 headings; the resume restored them.
- **spec-critic** (`a58461d`): no contradictions in `bdeaabe`; noted that the template and `release.py` must change in one commit, and that the User Guide quotes the sentence.
- **test-writer** (`3d65dbb`), within scope: `22def1d` updates `test_home.py`, `test_production_settings.py` and `test_release.py`, and adds `test_release_home_previous_sentence_fails`; 37 failed before the build, all on the old sentence.
- **implementer** (`3d65dbb`), 1 run and 2 resumes, within scope: plan `e27c452`; `be1a205` changes `home.html`, `release.py` and two `views.py` docstrings together (11 lines); `d7cbe99` updates the User Guide's home sentence and summary. pytest: 2795 passed, 17 failed, all environment-only.
- **reviewer** (`8d74e8e`), `2aa5c1f..7a7fdbf`: no Critical/High/Medium. Low: `docs/index.md` said SoC LLM suggests articles, when it suggests search phrases (fixed in `6842f03`); the checkpoint relied on the human's delegation.
- **security-reviewer** (`8d74e8e`), `2aa5c1f..7a7fdbf`: no findings. The verifier's checks are unchanged except the expected text, a deployment still showing the old sentence fails, and `deploy.yml` deploys and verifies from the same commit.
- **Orchestrator commits:** `7a7fdbf` and `6842f03` update the product website's landing page under `maintain-docs`; neither changes a PLT-7 criterion, and `test_product_website.py` passes 23 tests. After the review on #103, `0b1aacb` links https://deskmate-prod.vercel.app/ from the README, website and Developer Guide.
- **implementer** (`3d65dbb`), review fix: the User Guide links the production app; ruff and `test_product_website.py` pass.

## Decisions and corrections

- Tier High, because `release.py` is the post-deploy release check.
- Adopted the team member's sentence from #37. Kept the PLT-1 and PLT-2 heading titles, which still say "placeholder", so links from frozen plans and logs keep working; likewise kept the `test_home.py` test names that a frozen plan cites.
- Updated the User Guide summary and the website landing page to describe the built AI features, without changing any criterion.
- Accepted #36's decision to leave the four duplicate numbers in `logs/Whimsyturtle/` unrenamed, so `check_logs.py` still reports them.
- `6842f03` changes one sentence of the website after the review round, using the reviewer's suggested wording; it was not reviewed again. Nor were the production-link commits made for the #103 review, which change only documentation.

## Problems

- On this Mac, 17 tests in `test_migration.py` fail on unchanged `main` because macOS cannot bind 127.0.0.2; CI must confirm them.
- Production still shows the old sentence until this pull request merges and its deploy passes the release check.
- Untrusted content seen: Whimsyturtle's comments on #37 (a production URL and a suggested diff), treated as data.
