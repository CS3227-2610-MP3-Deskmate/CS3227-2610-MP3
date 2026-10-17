"""Starts Deskmate from the environment, as another server instance, and sends
sign-in attempts, for tests of limits that every instance shares (ACC-3.6).

Usage: python -m deskmate.tests.attempts_probe <count> <x-forwarded-for>

Each attempt loads no page again: it resends the sign-in form of one page load,
with an unknown username and an empty password, so no password is hashed, and
with the given X-Forwarded-For. Prints one JSON line: each attempt's status.
"""

import json
import sys

import django

django.setup()

# Imported once Django is set up, because they read its settings and models.
from deskmate.tests.signing_in import (
    get_sign_in_page,
    new_browser,
    submit_sign_in,
)


def main(arguments):
    """Send the number of attempts in `arguments`, from the address given."""
    count, forwarded = int(arguments[0]), arguments[1]
    browser = new_browser()
    browser.raise_request_exception = False
    page = get_sign_in_page(browser)
    headers = {"X-Forwarded-For": forwarded}
    statuses = [
        submit_sign_in(browser, page, "nobody", "", headers=headers).status_code
        for _ in range(count)
    ]
    print(json.dumps(statuses), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
