# 4-demo-workspace

Goal: A signed-out visitor presses **Create demo workspace** on the sign-in page and gets a new workspace with two Requesters and one Support Officer, whose generated passwords are shown once, meeting ACC-2.1–2.8 in about 120 changed lines under `src/`, not counting tests and migrations, with no model change, migration or dependency.

- [x] **implementer**: Create demo workspaces from the sign-in page (ACC-2.1–2.8). Makes `test_demo_workspace.py`, `test_demo_requests.py`, `test_demo_failures.py` and `test_demo_passwords.py` pass, and keeps every other test passing.
  - New `accounts/demo.py`, which owns generating and saving a demo workspace, with docstrings for the module and each function:
    - Constants: the 31 characters, the lengths 6 and 16, `MAX_CODES = 3`, and each account's username prefix and `Role`, in the page's order. `Account` is a named tuple of username, role and password.
    - `_random_string(length)` joins `secrets.choice(ALPHABET)` once per character, so each character is uniform and independent, from the operating system's secure source, with no modulo (ACC-2.8). `random_code()` returns one of length 6. The tests replace it, so creation calls it by its module-level name for each code and draws codes no other way.
    - `create_workspace()` draws the three passwords once, then, for each of at most 3 codes, passes the accounts to `_save`. That is a `transaction.atomic` function that creates one `Workspace` and calls `User.objects.create_user` for each account, so the configured hasher hashes each password, and a failure leaves nothing. Nothing locks a table, so another creation can save meanwhile. It returns the accounts in the page's order.
    - On `IntegrityError`, the code clashed only if one of its usernames now exists (`User.objects.filter(username__in=...).exists()`), which is how ACC-2.3 defines a clash. It then draws the next code, unless it was the third. Any other error, such as the not-null failure, is raised at once.
    - Every `DatabaseError` leaving `create_workspace`, including one from the clash check, is raised again as `type(error)("Creating a demo workspace failed.").with_traceback(error.__traceback__) from None`. The log then keeps Django's exception type and the original traceback, without the database's message, its detail or the chained psycopg error (ACC-2.4, ACC-2.6).
    - The passwords are not compared with each other, because two of three 16-character passwords coincide with a chance below 1 in 10^23. A docstring says so.
  - `accounts/views.py`: `demo_workspace`, decorated with `require_POST`, so other methods get 405 after the CSRF check. A signed-in user is redirected through `ROLE_PAGES`, as in `sign_in` (ACC-2.7). Otherwise it calls `create_workspace()` and renders the page with 200. There is no redirect and nothing goes in the session, and no request data is read (ACC-2.5). The module docstring adds ACC-2.
  - `src/deskmate/urls.py`: `demo-workspace/`, named `demo-workspace`.
  - Templates, which extend `deskmate/base.html` and use the exact texts of ACC-2.1:
    - `accounts/sign_in.html`: after the sign-in form, the invitation in a `<p>`, then a `post` form to `{% url 'demo-workspace' %}`. It holds only `{% csrf_token %}` and an unnamed `<button type="submit">`.
    - New `accounts/demo_workspace.html`: the copy-now line in a `<p>`, then one table. Its first row is `<th scope="col">` cells `Username`, `Role` and `Password`, then one row of `<td>` cells per account, with the role as `account.role.label`. Last, a `<p>` with the `Sign in` link to `{% url 'sign-in' %}`. No other text.
  - Nothing else changes. The existing middleware already adds `no-store` and `X-Frame-Options: DENY` to every response. CSRF failures already get `forbidden.html` through `csrf_failure`. The `LOGGING` setting already writes the 500's error to standard error.
- [ ] **implementer**: Update `docs/UserGuide.md` in the pages' exact words. Replace "only sign in and out" in the intro and "Accounts cannot yet be created in Deskmate.", and describe:
  - the invitation and the **Create demo workspace** button on `/sign-in/`;
  - the **Demo workspace created** page, with `Copy these passwords now. They will not be shown again.`, its **Username**, **Role** and **Password** table for two Requesters and one Support Officer, and its **Sign in** link;
  - that pressing the button again, or reloading and resending the form, makes another workspace;
  - that creating a workspace signs no one in.

  No tests.

Once this lands, the Developer Guide's step 6 can say "press **Create demo workspace**" instead of creating accounts in the shell. That is a `maintain-docs` change for the orchestrator, not a task here.
