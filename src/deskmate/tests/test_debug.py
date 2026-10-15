"""PLT-1.6: only DJANGO_DEBUG=true turns debug on when Deskmate starts.

Each case starts Deskmate in a new process, because pytest-django turns debug
off inside the test process whatever the settings say.
"""

import pytest

from deskmate.tests.environment import valid_environment
from deskmate.tests.helpers import internal_details, run_probe

UNMATCHED_PATH = "/admin"

NOT_EXACTLY_TRUE = [
    pytest.param(None, id="unset"),
    pytest.param("", id="empty"),
    pytest.param("True", id="capitalised"),
    pytest.param("1", id="one"),
    pytest.param("yes", id="yes"),
    pytest.param(" true ", id="true-with-spaces"),
]


@pytest.mark.ac("PLT-1.6")
@pytest.mark.parametrize("value", NOT_EXACTLY_TRUE)
def test_debug_value_not_exactly_true_turns_debug_off(value):
    environment = valid_environment({"DJANGO_DEBUG": value})
    _, result = run_probe(UNMATCHED_PATH, environment)
    assert result["debug"] is False
    assert result["status"] == 404
    secret_key = {"the secret key": environment["DJANGO_SECRET_KEY"]}
    assert internal_details(result["body"], secret_key) == []


@pytest.mark.ac("PLT-1.6")
def test_debug_value_true_turns_debug_on():
    _, result = run_probe(UNMATCHED_PATH, valid_environment({"DJANGO_DEBUG": "true"}))
    assert result["debug"] is True
