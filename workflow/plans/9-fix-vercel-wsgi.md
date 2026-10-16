Make file-path WSGI startup satisfy [PLT-2.7 and PLT-1.1](../specs/product/platform.md) with the existing `src/deskmate` layout.

- [x] **implementer**: Change `src/deskmate/wsgi.py` to derive the absolute `src` directory from `__file__` and add it to Python's import path before Django initializes; retain the existing settings and application entry point.
  Make `test_production_wsgi_loaded_by_path_without_src_import_path_serves_home` in `src/deskmate/tests/test_production_settings.py` pass, then run the unchanged [verify command](../../AGENTS.md#commands).
  Tick this task in `workflow/plans/9-fix-vercel-wsgi.md` after successful verification.
