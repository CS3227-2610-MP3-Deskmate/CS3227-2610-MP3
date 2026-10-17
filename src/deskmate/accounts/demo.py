"""Generating and saving demo workspaces (ACC-2.3, ACC-2.4, ACC-2.6, ACC-2.8)."""

import secrets
from collections import namedtuple

from django.contrib.auth.hashers import make_password
from django.db import Error, IntegrityError, transaction

from deskmate.accounts.models import Role, User, Workspace

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

# A demo account, with the password its workspace's page shows once.
Account = namedtuple("Account", ["username", "role", "password"])


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


def _draw_passwords():
    """Return one password per account, none equal to another (ACC-2.3).

    A password equal to one already drawn is drawn again. That happens with
    a chance below 1 in 10^23, so in practice each password is drawn once.
    """
    passwords = []
    while len(passwords) < len(ACCOUNTS):
        password = _random_string(PASSWORD_LENGTH)
        if password not in passwords:
            passwords.append(password)
    return passwords


def create_workspace():
    """Create a demo workspace, and return its accounts in the page's order.

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
    code that does not clash, and return them (ACC-2.3).

    Each of at most MAX_CODES codes is drawn by calling `random_code`. A
    code clashes if saving fails because one of its usernames is taken,
    including by a creation that finished meanwhile. Any other error, or a
    clash on the last code, is raised.
    """
    for _ in range(MAX_CODES - 1):
        accounts = _accounts(random_code(), passwords)
        try:
            return _save(accounts, hashes)
        except IntegrityError:
            if not _any_taken(accounts):
                raise
    return _save(_accounts(random_code(), passwords), hashes)


def _accounts(code, passwords):
    """Return the accounts named with `code`, given `passwords`, in order."""
    return [
        Account(f"{prefix}-{code}", role, password)
        for (prefix, role), password in zip(ACCOUNTS, passwords, strict=True)
    ]


@transaction.atomic
def _save(accounts, hashes):
    """Save one new workspace holding `accounts`, each with its password's hash
    from `hashes`, and return them; if saving any fails, nothing is saved.

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
    return accounts


def _any_taken(accounts):
    """Return whether an account with one of `accounts`' usernames is stored."""
    usernames = [account.username for account in accounts]
    return User.objects.filter(username__in=usernames).exists()
