"""PLT-1.9: the registered routes are exactly the route table's rows."""

import re

import pytest
from django.urls import get_resolver

from deskmate.tests.helpers import REPO_ROOT

SPEC = REPO_ROOT / "workflow" / "specs" / "TECHNICAL-SPEC.md"
ROUTE_ROW = re.compile(
    r"^\|\s*`(?P<route>/[^`]*)`\s*\|\s*(?P<methods>[^|]+)\|\s*(?P<access>[^|]+)\|",
    re.MULTILINE,
)
PARAMETER = re.compile(r"<[^>]+>")
NAMED_GROUP = re.compile(r"\(\?P<[^>]+>.+?\)")

# The one registered path the route table deliberately leaves out (PLT-3.3).
NO_SLASH = "health-llm-no-slash"
NO_SLASH_ROUTE = "/health/llm"


def route_table():
    """Return the route and methods each row of the technical spec's table lists."""
    text = SPEC.read_text(encoding="utf-8")
    section = text.split("## Routes", 1)[1].split("\n## ", 1)[0]
    return [
        {
            "route": PARAMETER.sub("<id>", match["route"]),
            "methods": tuple(method.strip() for method in match["methods"].split(",")),
        }
        for match in ROUTE_ROW.finditer(section)
    ]


def pattern_route(pattern):
    """Return `pattern` as the path a visitor requests, with `<id>` for a parameter."""
    route = NAMED_GROUP.sub("<id>", str(pattern)).removeprefix("^")
    if route.endswith("$"):
        route = route[:-1]
    elif route.endswith("\\Z"):
        route = route[:-2]
    return "/" + route


def allowed_methods(view):
    """Return the methods `view`'s method guard allows, or None if it has none.

    Django keeps a view's allowed methods only in the `require_*` decorator's
    closure, so walk the wrapped views to find the first method list.
    """
    seen = set()
    while view is not None and id(view) not in seen:
        seen.add(id(view))
        for cell in view.__closure__ or ():
            try:
                value = cell.cell_contents
            except ValueError:
                continue
            if (
                isinstance(value, (list, tuple))
                and value
                and all(isinstance(method, str) for method in value)
            ):
                return tuple(value)
        view = getattr(view, "__wrapped__", None)
    return None


def registered_routes():
    """Return each registered route's path, name and allowed methods."""
    return [
        {
            "route": pattern_route(pattern.pattern),
            "name": pattern.name,
            "methods": allowed_methods(pattern.callback),
        }
        for pattern in get_resolver().url_patterns
    ]


@pytest.mark.ac("PLT-1.9")
def test_registered_routes_are_exactly_the_route_table_rows():
    table = route_table()
    registered = [route for route in registered_routes() if route["name"] != NO_SLASH]
    assert sorted(route["route"] for route in registered) == sorted(
        route["route"] for route in table
    )


@pytest.mark.ac("PLT-1.9")
def test_each_registered_route_allows_the_methods_its_row_lists():
    methods_by_route = {route["route"]: route["methods"] for route in route_table()}
    mismatches = []
    for route in registered_routes():
        if route["name"] == NO_SLASH:
            continue
        expected = methods_by_route.get(route["route"])
        if route["methods"] != expected:
            mismatches.append((route["route"], expected, route["methods"]))
    assert not mismatches, f"Routes whose methods differ from the table: {mismatches}"


@pytest.mark.ac("PLT-1.9")
def test_the_no_slash_probe_alias_is_the_only_registered_path_outside_the_table():
    table_routes = {route["route"] for route in route_table()}
    outside = [
        route for route in registered_routes() if route["route"] not in table_routes
    ]
    assert [route["name"] for route in outside] == [NO_SLASH]
    assert outside[0]["route"] == NO_SLASH_ROUTE
