Goal: Deliver [PLT-7](../specs/product/platform.md#plt-7-publish-the-product-website) within the confirmed 250–450-line total diff; follow the [site design](../specs/TECHNICAL-SPEC.md#product-website) and [publication controls](../specs/SECURITY-SPEC.md#product-website-publication).

- [ ] **Orchestrator using [maintain-docs](../skills/maintain-docs.md)**: Add `docs/index.md` and `docs/_config.yml`; update `README.md` and `docs/DeveloperGuide.md` only where the site needs them.
  - Use Cayman, kramdown and the default layout at the specified project path; introduce only built features and link the existing guides/source on GitHub, omitting absent reflections.
  - Credit the reused theme/build tools in Developer Guide acknowledgements and link technical setup prerequisites; leave User Guide text unchanged because app behaviour is unchanged.
  - Make the theme/content and guide-link tests in `src/deskmate/tests/test_product_website.py` pass (PLT-7.1–7.2); check changed links and content against built behaviour.

- [ ] **devops**: Add `.github/workflows/pages.yml` only; make the remaining product-website source checks pass (PLT-7.3–7.6), preserving existing app CI.
  - Build PRs and successful same-repository main-push CI commits from clean checkouts with read-only access; pin source actions to SHAs and the official Jekyll builder to an exact version plus immutable digest.
  - Keep `build` and `deploy` separate; publish only their checked-commit site artifact after successful CI/build, using the protected production environment and deployment-only Pages/OIDC grants, with no stored secrets.
  - Serialize publication separately from Vercel without cancelling an active job; immediately recheck current main before deployment and skip an outdated commit.
  - Run the pinned site build and report unavailable rendering checks; the orchestrator runs `ruff check . && ruff format --check . && pytest` unchanged and checks title, theme paths and navigation where runnable.

Hosted settings and publication checks remain operator prerequisites; this plan authorizes no settings changes or push. Stop if the reserved workflow, documentation or total diff budget cannot hold.
