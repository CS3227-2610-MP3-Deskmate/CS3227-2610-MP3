# 1-django-project

Goal: Deskmate runs as a Django project under `src/` that meets PLT-1.1–1.4, 1.6 and 1.7, with every dependency pinned, an app image, and CI that runs the verify command.

- [ ] **implementer**: Create the project package. Makes every test in `src/deskmate/tests/` pass (PLT-1.1–1.4, 1.6, 1.7). It is one task because every test fails until the settings, routes and views all exist.
  - `src/manage.py`, defaulting `DJANGO_SETTINGS_MODULE` to `deskmate.settings`, and `src/deskmate/__init__.py`.
  - `src/deskmate/settings.py`: when imported, reads each variable in the TECHNICAL-SPEC Configuration table, checks it against its row, collects the PLT-1.7 message for each invalid one, then raises `SystemExit` with all of them. Use `SystemExit` rather than `ImproperlyConfigured`, because `manage.py` catches that while it loads settings.
  - Same file: debug is on only if `DJANGO_DEBUG` is exactly `true`; with debug on and no key, make a random key on each start; PostgreSQL with `connect_timeout` 5; `INSTALLED_APPS = ["deskmate"]`, only `CommonMiddleware`, no context processors; `LOGGING` sends `django.request` errors, with their tracebacks, to standard error in both debug modes.
  - `src/deskmate/urls.py`, `src/deskmate/views.py`, `src/deskmate/templates/deskmate/home.html`: `home` renders the page; `health` runs `SELECT 1` and returns `{"status": "ok"}`, or `503` and `{"status": "error"}` on any database error. Both views use `require_GET`, so HEAD and other methods get 405. Django's default 404 and 500 responses stay as they are.
- [ ] **devops**: Pin the indirect dependencies at the versions in `.venv` (`pip freeze`): runtime ones in `requirements.txt`, test and lint ones in `requirements-dev.txt`. Keep the markers their packages declare: `tzdata` and `colorama` only for `sys_platform == "win32"`. No new tests.
- [ ] **devops**: Add `Dockerfile` and `.dockerignore` per SECURITY-SPEC "Container image":
  - an official `python:3.14.2-slim` base pinned to its digest; installs `requirements.txt` only;
  - copies `src/` without its tests or caches; runs as a non-root user;
  - its default command runs `python manage.py check` and exits, so no web server serves the image until #2.
  - No new tests; `docker build .` must succeed.
- [ ] **devops**: Add `.github/workflows/ci.yml` per TECHNICAL-SPEC "Environments" and `devops.md` step 3: runs on pull requests and on pushes to `main`, with `contents: read`, SHA-pinned actions and `ubuntu-24.04`.
  - Job `verify`: Python 3.14.2, a `.venv` installed from `requirements-dev.txt`, and a PostgreSQL service on port 5432 using `compose.yaml`'s image and digest and `.env.example`'s throwaway database values. It then runs the verify command unchanged, which runs every test.
  - Job `image`: `docker build .`, without pushing.
- [ ] **implementer**: Create `docs/UserGuide.md` (`README.md` already links to it): what a visitor sees at `/`, in the page's exact words, and nothing else. No tests.
