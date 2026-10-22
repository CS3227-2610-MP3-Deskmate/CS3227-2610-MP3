Goal: Meet [PLT-7.7](../specs/product/platform.md#plt-7-publish-the-product-website) by linking the landing page to the site's own [Reflections page](../specs/TECHNICAL-SPEC.md#product-website); the existing pages already meet PLT-7.8 and PLT-7.9.

- [x] **Orchestrator using [maintain-docs](../skills/maintain-docs.md)**: Add `- [Reflections](Reflections.html)` to the `Project` list in `docs/index.md`; change nothing else.
  - The relative target opens `Reflections.html` from the same build at the configured base path.
  - Makes `test_product_website_landing_page_links_reflections_page_from_same_build` (PLT-7.7) in `src/deskmate/tests/test_product_website.py` pass; the PLT-7.8 and PLT-7.9 tests stay passing.
  - Leave `docs/Reflections.md` and `reflections/` to the team, and `docs/UserGuide.md` unchanged because app behaviour is unchanged.
  - Run `ruff check . && ruff format --check . && pytest`; hosted rendering and publication stay unverified, as the [product website](../specs/TECHNICAL-SPEC.md#product-website) design notes.
