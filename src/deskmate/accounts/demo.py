"""Generating and saving demo workspaces and their sample articles and tickets
(ACC-2.3, ACC-2.4, ACC-2.6, ACC-2.8, ACC-2.9).
"""

import secrets
from collections import namedtuple

from django.contrib.auth.hashers import make_password
from django.db import Error, IntegrityError, transaction

from deskmate.accounts.models import Role, User, Workspace
from deskmate.knowledge.models import Article
from deskmate.tickets.models import Ticket

# The characters of codes and passwords: the digits and lowercase letters
# without 0, 1, i, l and o (ACC-2.3).
ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"
CODE_LENGTH = 6
PASSWORD_LENGTH = 16
# How many codes a creation draws before it fails (ACC-2.3).
MAX_CODES = 3
# Each account's username before its code, and its role, in the page's order.
ACCOUNTS = (
    ("requester1", Role.REQUESTER),
    ("requester2", Role.REQUESTER),
    ("support1", Role.SUPPORT_OFFICER),
)
# Each sample article's title and body, in ACC-2.9's order.
SAMPLE_ARTICLES = (
    (
        "Fix a printer that will not print",
        (
            "Check that the printer is switched on and has paper. Turn it off, wait 30 "
            "seconds and turn it on again. If it still will not print, raise a ticket."
        ),
    ),
    (
        "Connect to the office Wi-Fi",
        (
            "Open the Wi-Fi settings on your device and choose the office network. "
            "Enter the network password from the notice board in your office. If the "
            "connection keeps dropping, forget the network and connect again."
        ),
    ),
)
# Each sample ticket's title, description, whether it is open, and reply, in
# ACC-2.9's order.
SAMPLE_TICKETS = (
    (
        "Printer will not print",
        (
            "The printer by the meeting room shows a ready light, but nothing comes "
            "out. I have sent my document twice from my laptop."
        ),
        False,
        (
            "I restarted the printer and cleared a stuck job from its queue. Your "
            "document should print now. Raise a new ticket if it happens again."
        ),
    ),
    (
        "Wi-Fi keeps disconnecting",
        (
            "Since Monday, my laptop drops off the office Wi-Fi several times an hour. "
            "Each time, it reconnects after about a minute. It happens in every room "
            "on my floor. I have already restarted my laptop. I need a stable "
            "connection for video calls every afternoon."
        ),
        True,
        "",
    ),
    (
        "Need a spreadsheet app",
        (
            "I am joining the budget team next week. I need a spreadsheet app on my "
            "laptop before then. My manager has already approved the request. I can "
            "bring my laptop to the help desk on any morning."
        ),
        True,
        "",
    ),
)

# A demo account, with the password its workspace's page shows once.
Account = namedtuple("Account", ["username", "role", "password"])
# A created workspace's code, which its usernames share, and its accounts.
Created = namedtuple("Created", ["code", "accounts"])


def _random_string(length):
    """Return `length` characters drawn from ALPHABET (ACC-2.8).

    `secrets.choice` draws each character from the operating system's
    secure random source, independently and uniformly: it picks an index by
    rejection sampling, never by reducing a random byte modulo 31.
    """
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def random_code():
    """Return a new code for a workspace's usernames (ACC-2.3)."""
    return _random_string(CODE_LENGTH)


def random_password():
    """Draw a fresh password for a demo account or reset (ACC-2.3, ACC-4.2)."""
    return _random_string(PASSWORD_LENGTH)


def _draw_passwords():
    """Return one password per account, none equal to another (ACC-2.3).

    A password equal to one already drawn is drawn again. That happens with
    a chance below 1 in 10^23, so in practice each password is drawn once.
    """
    passwords = []
    while len(passwords) < len(ACCOUNTS):
        password = random_password()
        if password not in passwords:
            passwords.append(password)
    return passwords


def create_workspace():
    """Create a demo workspace with its sample articles and tickets, and return
    it as a Created: the code its usernames share and its accounts in the
    page's order (ACC-2.1, ACC-2.9).

    Each password is hashed once, as the configured hasher's salted hash,
    before anything is saved (ACC-2.6). Any Django database `Error`, such as
    a `DatabaseError` or an `InterfaceError`, is raised again as the same
    type, with the same traceback but without the database's message and
    detail, which can hold a generated username or the row being written,
    or the driver's error chained to it (ACC-2.4, ACC-2.6).
    """
    try:
        passwords = _draw_passwords()
        hashes = [make_password(password) for password in passwords]
        return _save_under_free_code(passwords, hashes)
    except Error as error:
        hidden = type(error)("Creating a demo workspace failed.")
        raise hidden.with_traceback(error.__traceback__) from None


def _save_under_free_code(passwords, hashes):
    """Save the accounts, with `passwords` stored as `hashes`, under the first
    code that does not clash, and return that code and them as a Created
    (ACC-2.3).

    Each of at most MAX_CODES codes is drawn by calling `random_code`. A
    code clashes if saving fails because one of its usernames is taken,
    including by a creation that finished meanwhile. Any other error, or a
    clash on the last code, is raised.
    """
    for _ in range(MAX_CODES - 1):
        code = random_code()
        accounts = _accounts(code, passwords)
        try:
            return Created(code, _save(accounts, hashes))
        except IntegrityError:
            if not _any_taken(accounts):
                raise
    code = random_code()
    return Created(code, _save(_accounts(code, passwords), hashes))


def _accounts(code, passwords):
    """Return the accounts named with `code`, given `passwords`, in order."""
    return [
        Account(f"{prefix}-{code}", role, password)
        for (prefix, role), password in zip(ACCOUNTS, passwords, strict=True)
    ]


@transaction.atomic
def _save(accounts, hashes):
    """Save one new workspace holding `accounts`, each with its password's hash
    from `hashes`, and then its sample articles and tickets, and return the
    accounts; if saving any fails, nothing is saved (ACC-2.4, ACC-2.9).

    Nothing is locked, so another creation can save its accounts meanwhile.
    """
    workspace = Workspace.objects.create()
    for account, hashed in zip(accounts, hashes, strict=True):
        User.objects.create(
            username=User.normalize_username(account.username),
            password=hashed,
            role=account.role,
            workspace=workspace,
        )
    _save_samples(workspace)
    return accounts


def _save_samples(workspace):
    """Save the sample articles and then tickets in `workspace`, one at a time
    in ACC-2.9's order, which is the order the lists show them in.

    Each article is saved by its own `create`, as `Article.save` derives the
    key that KB-1.5's duplicate-title check compares.
    """
    for title, body in SAMPLE_ARTICLES:
        Article.objects.create(workspace=workspace, title=title, body=body)
    for title, description, is_open, reply in SAMPLE_TICKETS:
        Ticket.objects.create(
            workspace=workspace,
            title=title,
            description=description,
            open=is_open,
            reply=reply,
        )


def _any_taken(accounts):
    """Return whether an account with one of `accounts`' usernames is stored."""
    usernames = [account.username for account in accounts]
    return User.objects.filter(username__in=usernames).exists()
