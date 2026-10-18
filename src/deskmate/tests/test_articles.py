"""KB-1: workspace article authoring, validation and access boundaries."""

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from html import escape
from threading import Barrier
from urllib.parse import unquote, urlsplit

import pytest
from django.apps import apps
from django.db import DatabaseError, OperationalError, connection, connections

from deskmate.accounts.models import User, Workspace
from deskmate.tests.pages import ORIGIN, Page
from deskmate.tests.signing_in import (
    FORM_EXPIRED,
    NOT_FOR_YOUR_ROLE,
    REQUESTER,
    SUPPORT_OFFICER,
    VISITORS,
    assert_forbidden,
    assert_method_not_allowed,
    assert_redirects,
    assert_server_error,
    browser_as,
    csrf_token,
    methods_not_listed,
    send,
    sign_in_as,
)

pytestmark = pytest.mark.django_db
LIST = "/support/articles/"
NEW = f"{LIST}new/"
MISSING = f"{LIST}999999999/edit/"
ROUTES = (LIST, NEW, MISSING)
EDIT = re.compile(r"/support/articles/[0-9]+/edit/")
TITLE_ERROR = "Enter a valid title (1 to 200 characters)."
BODY_ERROR = "Enter a valid body (1 to 10000 characters)."
DUPLICATE = "An article with this title already exists."


@pytest.fixture
def author(make_account):
    """A signed-in officer and their stored account."""
    return sign_in_as(make_account, SUPPORT_OFFICER)


@pytest.fixture
def records():
    """Find the Article record specified by the technical data model."""
    matches = [m for m in apps.get_models() if m._meta.object_name == "Article"]
    assert len(matches) == 1, "The specified Article record is missing."
    return matches[0].objects


def form_at(browser, path=NEW):
    """Open the authoring form as a browser does."""
    response = browser.get(path)
    assert response.status_code == 200, f"GET {path}: {response.status_code}"
    return Page(response).form_with_button("Save article")


def create(browser, title="Guide", body="Steps", **changes):
    """Save an article and return its edit location."""
    response = form_at(browser).submit(
        browser, {"Title": title, "Body": body}, changes=changes
    )
    assert response.status_code == 302
    assert EDIT.fullmatch(response.url)
    return response.url


def values(browser, path):
    """Read the values shown in the edit form."""
    form = form_at(browser, path)
    return tuple(form.field(label).value for label in ("Title", "Body"))


def article_links(browser):
    """Read the ordered article titles and edit paths from the list."""
    response = browser.get(LIST)
    assert response.status_code == 200
    return [
        (text, urlsplit(url).path)
        for text, url in Page(response).links
        if EDIT.fullmatch(urlsplit(url).path)
    ]


@pytest.mark.ac("KB-1.1", "KB-1.2", "KB-1.3", "PLT-2.8")
def test_articles_navigation_creation_and_reopening(author, records):
    browser, account = author
    assert ("Knowledge base", f"{ORIGIN}{LIST}") in Page(
        browser.get("/support/", secure=True)
    ).links
    page = Page(browser.get(LIST, secure=True))
    assert page.title == "Knowledge base" and page.h1s == ["Knowledge base"]
    assert "No articles yet." in page.text
    assert ("New article", f"{ORIGIN}{NEW}") in page.links
    assert ("Support Officer", f"{ORIGIN}/support/") in page.links
    page = Page(browser.get(NEW, secure=True))
    assert page.title == "New article" and page.h1s == ["New article"]
    form = page.form_with_button("Save article")
    assert form.field("Title").tag == "input"
    assert form.field("Body").tag == "textarea"
    assert [form.field(label).value for label in ("Title", "Body")] == ["", ""]
    assert ("Knowledge base", f"{ORIGIN}{LIST}") in page.links
    first = create(browser, "Zulu", "First steps")
    second = create(browser, "Alpha", "Second steps")
    assert article_links(browser) == [("Zulu", first), ("Alpha", second)]
    assert values(browser, first) == ("Zulu", "First steps")
    page = Page(browser.get(first, secure=True))
    assert page.title == "Edit article" and page.h1s == ["Edit article"]
    assert ("Knowledge base", f"{ORIGIN}{LIST}") in page.links
    assert (
        records.count() == 2
        and records.filter(workspace=account.workspace).count() == 2
    )


@pytest.mark.ac("KB-1.3", "KB-1.5")
def test_articles_shared_officer_edit_and_stale_save_replace_both_fields(
    author, make_account, records
):
    browser, _ = author
    path = create(browser)
    other, _ = sign_in_as(make_account, SUPPORT_OFFICER)
    stale = form_at(browser, path)
    response = form_at(other, path).submit(other, {"Title": "New", "Body": "Other"})
    assert_redirects(response, path)
    assert values(browser, path) == ("New", "Other")
    assert_redirects(stale.submit(browser, {"Title": "Guide", "Body": "Stale"}), path)
    assert values(other, path) == ("Guide", "Stale")
    assert records.count() == 1


@pytest.mark.ac("KB-1.2", "KB-1.4")
@pytest.mark.parametrize(
    ("title", "body"),
    [
        ("x", "x"),
        ("x" * 199, "x" * 9999),
        ("x" * 200, "x" * 10000),
        ("\u3000Stra\u00dfe\t", "\u00a0Line 1\r\nLine 2\rLine 3\u3000"),
        ("\U0001f422" * 200, "\U0001f422" * 10000),
    ],
    ids=[
        "minimum",
        "below-maximum",
        "maximum",
        "whitespace-and-crlf",
        "unicode-maximum",
    ],
)
def test_articles_valid_boundaries_and_normalisation(author, title, body):
    browser, _ = author
    path = create(browser, title, body)
    assert values(browser, path) == (
        title.strip(),
        body.replace("\r\n", "\n").replace("\r", "\n").strip(),
    )


@pytest.mark.ac("KB-1.4")
@pytest.mark.parametrize("editing", [False, True])
@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("Title", None),
        ("Title", ""),
        ("Title", " \u3000\t"),
        ("Title", "x" * 201),
        ("Title", "a\rb"),
        ("Title", "a\nb"),
        ("Title", "a\r\nb"),
        ("Title", "a\x00b"),
        ("Body", None),
        ("Body", ""),
        ("Body", " \u3000\t"),
        ("Body", "x" * 10001),
        ("Body", "a\x00b"),
    ],
    ids=lambda value: (
        f"{len(value)}-chars"
        if isinstance(value, str) and len(value) > 24
        else repr(value)
    ),
)
def test_articles_invalid_field_retains_input_and_preserves_data(
    author, records, editing, field, invalid
):
    browser, _ = author
    path = create(browser) if editing else NEW
    form = form_at(browser, path)
    typed = {"Title": " Raw title ", "Body": " Raw\r\nbody "}
    changes = {form.field(field).name: invalid}
    response = form.submit(browser, typed, changes=changes)
    assert response.status_code == 200
    page = Page(response)
    assert (TITLE_ERROR in page.text) == (field == "Title")
    assert (BODY_ERROR in page.text) == (field == "Body")
    retained = page.form_with_button("Save article")
    typed[field] = invalid or ""
    for label, value in typed.items():
        value = (
            value.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "\ufffd")
        )
        assert retained.field(label).value == (
            value.replace("\n", " ") if label == "Title" else value
        )
    assert records.count() == int(editing)
    if editing:
        assert values(browser, path) == ("Guide", "Steps")


@pytest.mark.ac("KB-1.4")
def test_articles_both_invalid_fields_show_only_their_errors(author, records):
    browser, _ = author
    response = form_at(browser).submit(browser, {"Title": "", "Body": ""})
    assert response.status_code == 200
    assert Page(response).text.count(TITLE_ERROR) == 1
    assert Page(response).text.count(BODY_ERROR) == 1
    assert records.count() == 0


@pytest.mark.ac("KB-1.5")
@pytest.mark.parametrize(
    ("saved", "duplicate"),
    [
        ("Guide", "Guide"),
        ("Guide", " \u3000gUIDE\t"),
        ("Stra\u00dfe", "STRASSE"),
    ],
)
@pytest.mark.parametrize("editing", [False, True])
def test_articles_duplicate_creation_resend_and_rename_are_rejected(
    author, records, saved, duplicate, editing
):
    browser, _ = author
    original = create(browser, saved)
    path = create(browser, "Other", "Original") if editing else NEW
    response = form_at(browser, path).submit(
        browser, {"Title": duplicate, "Body": "Changed"}
    )
    assert response.status_code == 200
    page = Page(response)
    assert page.text.count(DUPLICATE) == 1
    assert TITLE_ERROR not in page.text and BODY_ERROR not in page.text
    assert page.form_with_button("Save article").field("Title").value == duplicate
    assert values(browser, original) == (saved.strip(), "Steps")
    if editing:
        assert values(browser, path) == ("Other", "Original")
    assert records.count() == 1 + int(editing)


@pytest.mark.ac("KB-1.5")
def test_articles_self_exclusion_case_preservation_and_no_unicode_normalisation(author):
    browser, _ = author
    path = create(browser, "Guide")
    assert_redirects(
        form_at(browser, path).submit(browser, {"Title": "gUIDE", "Body": "Changed"}),
        path,
    )
    assert values(browser, path) == ("gUIDE", "Changed")
    create(browser, "\u00e9")
    create(browser, "e\u0301")


@pytest.mark.ac("KB-1.6")
@pytest.mark.parametrize("visitor", [None, REQUESTER])
@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", p) for p in ROUTES] + [("POST", NEW), ("POST", MISSING)],
)
def test_articles_access_denied_before_lookup(
    make_account, records, visitor, method, path
):
    browser, _ = browser_as(make_account, visitor)
    response = send(browser, method, path, csrf_token(browser, visitor))
    if visitor is None:
        assert_redirects(response, "/sign-in/")
    else:
        assert_forbidden(response, NOT_FOR_YOUR_ROLE)
    assert "no-store" in response["Cache-Control"]
    assert response["X-Frame-Options"] == "DENY"
    assert records.count() == 0


METHOD_CASES = [
    (method, visitor, ROUTES[(i + j) % 3])
    for i, method in enumerate(methods_not_listed("GET", "POST"))
    for j, visitor in enumerate(VISITORS)
] + [("POST", v, LIST) for v in VISITORS]


@pytest.mark.ac("KB-1.6")
@pytest.mark.parametrize(("method", "visitor", "path"), METHOD_CASES)
def test_articles_unsupported_methods_have_empty_405(
    make_account, records, method, visitor, path
):
    browser, _ = browser_as(make_account, visitor)
    assert_method_not_allowed(send(browser, method, path, csrf_token(browser, visitor)))
    assert records.count() == 0


@pytest.mark.ac("KB-1.6")
@pytest.mark.parametrize("path", [NEW, MISSING])
@pytest.mark.parametrize("fault", ["missing", "wrong", "origin"])
def test_articles_csrf_and_origin_rejection_change_nothing(
    author, records, path, fault
):
    browser, _ = author
    token = csrf_token(browser, SUPPORT_OFFICER)
    headers = {"Origin": "https://evil.example"} if fault == "origin" else None
    token = None if fault == "missing" else "wrong" if fault == "wrong" else token
    assert_forbidden(send(browser, "POST", path, token, headers=headers), FORM_EXPIRED)
    assert records.count() == 0


@pytest.mark.ac("KB-1.6")
@pytest.mark.parametrize("state", ["expired", "deleted", "role-changed"])
def test_articles_current_session_and_stored_role_control_access(clock, author, state):
    browser, account = author
    if state == "expired":
        clock.set_elapsed(timedelta(hours=8))
    elif state == "deleted":
        account.delete()
    else:
        User.objects.filter(pk=account.pk).update(role=REQUESTER)
    response = browser.get(LIST)
    if state == "role-changed":
        assert_forbidden(response, NOT_FOR_YOUR_ROLE)
    else:
        assert_redirects(response, "/sign-in/")


@pytest.mark.ac("KB-1.5", "KB-1.7")
def test_articles_workspace_isolation_and_forged_fields(author, make_account, records):
    browser, account = author
    own = create(browser, "Shared title", "Own body")
    other, outsider = sign_in_as(make_account, SUPPORT_OFFICER)
    foreign = Workspace.objects.create()
    User.objects.filter(pk=outsider.pk).update(workspace=foreign)
    their = create(other, "Shared title", "Foreign body")
    assert article_links(browser) == [("Shared title", own)]
    assert article_links(other) == [("Shared title", their)]
    for path in (their, MISSING):
        get = browser.get(path)
        post = send(browser, "POST", path, csrf_token(browser, SUPPORT_OFFICER))
        assert get.status_code == post.status_code == 404
        assert get.content == post.content == browser.get(MISSING).content
        assert b"Foreign body" not in get.content
    forged = {
        "workspace": foreign.pk,
        "workspace_id": foreign.pk,
        "role": REQUESTER,
        "id": records.get(title="Shared title", workspace=foreign).pk,
    }
    created = create(browser, "Own creation", workspace=foreign.pk, role=REQUESTER)
    response = form_at(browser, own).submit(
        browser, {"Title": "Changed", "Body": "Updated"}, changes=forged
    )
    assert_redirects(response, own)
    assert values(other, their) == ("Shared title", "Foreign body")
    assert records.get(title="Own creation").workspace_id == account.workspace_id
    assert records.count() == 3
    User.objects.filter(pk=account.pk).update(workspace=foreign)
    assert article_links(browser) == [("Shared title", their)]
    assert browser.get(created).status_code == 404


@pytest.mark.ac("KB-1.7")
@pytest.mark.parametrize("field", ["Title", "Body"])
@pytest.mark.parametrize(
    "encoded",
    [
        "%3Cscript%3Ealert%281%29%3C%2Fscript%3E",
        "%22%3E%3Cimg%20src%3Dx%20onerror%3Dalert%281%29%3E",
        "%3C%2Ftextarea%3E%3Cimg%20src%3Dx%20onerror%3Dalert%281%29%3E",
    ],
)
def test_articles_saved_and_reflected_markup_is_text(author, field, encoded):
    browser, _ = author
    payload = unquote(encoded)
    typed = {"Title": "Guide", "Body": "Steps", field: payload}
    path = create(browser, typed["Title"], typed["Body"])
    for response in (browser.get(path), browser.get(LIST)):
        html = response.content.decode()
        assert payload not in html
        if field == "Title" or response.request["PATH_INFO"] != LIST:
            assert escape(payload) in html
    assert values(browser, path) == (typed["Title"], typed["Body"])
    typed["Body" if field == "Title" else "Title"] = ""
    response = form_at(browser).submit(browser, typed)
    assert response.status_code == 200
    assert payload not in response.content.decode()
    assert Page(response).form_with_button("Save article").field(field).value == payload


@pytest.mark.ac("KB-1.5")
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("mode", ["create-create", "rename-rename", "create-rename"])
def test_articles_competing_saves_allow_one_duplicate_free_result(
    author, make_account, records, mode
):
    first, _ = author
    second, _ = sign_in_as(make_account, SUPPORT_OFFICER)
    paths = [
        create(first, "First", "First body") if mode == "rename-rename" else NEW,
        create(second, "Second", "Second body") if mode != "create-create" else NEW,
    ]
    forms = [form_at(browser, path) for browser, path in zip((first, second), paths)]
    table = connection.ops.quote_name(records.model._meta.db_table)
    barrier = Barrier(2, timeout=30)

    def compete(index):
        def together(execute, sql, params, many, context):
            if table in sql and sql.startswith(("INSERT", "UPDATE")):
                barrier.wait()
            return execute(sql, params, many, context)

        try:
            with connection.execute_wrapper(together):
                return forms[index].submit(
                    (first, second)[index],
                    {
                        "Title": "Target" if index == 0 else "TARGET",
                        "Body": f"Body {index}",
                    },
                )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(compete, (0, 1)))
    assert sorted(response.status_code for response in responses) == [200, 302]
    loser = next(response for response in responses if response.status_code == 200)
    assert DUPLICATE in Page(loser).text
    assert records.filter(title__in=["Target", "TARGET"]).count() == 1
    for index, response in enumerate(responses):
        if response.status_code == 200 and paths[index] != NEW:
            assert values((first, second)[index], paths[index]) == (
                "First" if index == 0 else "Second",
                "First body" if index == 0 else "Second body",
            )


@pytest.mark.ac("KB-1.8")
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("editing", [False, True])
@pytest.mark.parametrize("debug", [False, True])
def test_articles_rejected_write_rolls_back_both_fields(
    author, records, settings, editing, debug
):
    browser, _ = author
    path = create(browser) if editing else NEW
    form = form_at(browser, path)
    table = connection.ops.quote_name(records.model._meta.db_table)

    def fail(execute, sql, params, many, context):
        result = execute(sql, params, many, context)
        if table in sql and sql.startswith(("INSERT", "UPDATE")):
            raise DatabaseError("Synthetic rejected article write.")
        return result

    settings.DEBUG = debug
    browser.raise_request_exception = False
    with connection.execute_wrapper(fail):
        response = form.submit(browser, {"Title": "Changed", "Body": "Changed body"})
    assert response.status_code == 500
    if not debug:
        assert_server_error(response)
    assert records.count() == int(editing)
    if editing:
        assert values(browser, path) == ("Guide", "Steps")


@pytest.mark.ac("KB-1.8")
@pytest.mark.parametrize("path", ROUTES)
def test_articles_database_outage_returns_generic_error(author, database_outage, path):
    browser, _ = author
    browser.raise_request_exception = False
    with database_outage():
        assert_server_error(browser.get(path))


@pytest.mark.ac("KB-1.8")
@pytest.mark.django_db(transaction=True)
def test_articles_lost_commit_confirmation_has_no_success_redirect(
    author, records, monkeypatch
):
    browser, _ = author
    form = form_at(browser)
    commit = connection.commit

    def lose_confirmation():
        commit()
        raise OperationalError("Synthetic lost commit confirmation.")

    browser.raise_request_exception = False
    with monkeypatch.context() as patch:
        patch.setattr(connection, "commit", lose_confirmation)
        response = form.submit(browser, {"Title": "Committed", "Body": "Stored"})
    assert_server_error(response)
    assert records.count() == 1
    assert article_links(browser)[0][0] == "Committed"
