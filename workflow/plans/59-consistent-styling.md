# Present every page consistently

Implement [PLT-4](../specs/product/platform.md#plt-4-present-every-page-consistently) with one inline presentation in the shared page layout, without new assets, dependencies or visible text.

- [x] implementer: Add the shared inline presentation and `<main>` wrapper to `src/deskmate/templates/deskmate/base.html`, covering readable width, typography, links, lists, forms, buttons, tables and a narrow-window rule. Keep every existing page's text, headings, links, labels, captions and routes unchanged, and make `src/deskmate/tests/test_styling.py` pass.
- [x] test-writer: Add `src/deskmate/tests/test_styling.py` for PLT-4.1, PLT-4.4, PLT-4.5 and PLT-4.6, and update the visible-text checks in `src/deskmate/tests/pages.py`, `src/deskmate/tests/test_home.py` and `src/deskmate/tests/test_production_settings.py` so inline CSS is not counted as page text. Run the focused tests and the verify command.
- [x] reviewer: Review the inline presentation and test changes for unchanged content, resource use and text line breaks.
