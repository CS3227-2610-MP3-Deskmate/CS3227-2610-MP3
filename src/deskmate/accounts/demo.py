"""Generating and saving demo workspaces (ACC-2.3, ACC-2.4, ACC-2.6, ACC-2.8)."""

import secrets
from collections import namedtuple

from django.db import DatabaseError, IntegrityError, transaction

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

    A `DatabaseError` is raised again as the same type, with the same
    traceback but without the database's message and detail, which can hold
    a generated username or the row being written, or the driver's error
    chained to it (ACC-2.4, ACC-2.6).
    """
    try:
        return _save_under_free_code(_draw_passwords())
    except DatabaseError as error:
        hidden = type(error)("Creating a demo workspace failed.")
        raise hidden.with_traceback(error.__traceback__) from None


def _save_under_free_code(passwords):
    """Save the accounts, with `passwords`, under the first code that does not
    clash, and return them (ACC-2.3).

    Each of at most MAX_CODES codes is drawn by calling `random_code`. A
    code clashes if saving fails because one of its usernames is taken,
    including by a creation that finished meanwhile. Any other error, or a
    clash on the last code, is raised.
    """
    for _ in range(MAX_CODES - 1):
        accounts = _accounts(random_code(), passwords)
        try:
            return _save(accounts)
        except IntegrityError:
            if not _any_taken(accounts):
                raise
    return _save(_accounts(random_code(), passwords))


def _accounts(code, passwords):
    """Return the accounts named with `code`, given `passwords`, in order."""
    return [
        Account(f"{prefix}-{code}", role, password)
        for (prefix, role), password in zip(ACCOUNTS, passwords, strict=True)
    ]


@transaction.atomic
def _save(accounts):
    """Save one new workspace holding `accounts`, and return them; if saving
    any fails, nothing is saved.

    `create_user` stores each password as the configured hasher's salted
    hash (ACC-2.6). Nothing is locked, so another creation can save its
    accounts meanwhile.
    """
    workspace = Workspace.objects.create()
    for account in accounts:
        User.objects.create_user(
            username=account.username,
            password=account.password,
            role=account.role,
            workspace=workspace,
        )
    return accounts


def _any_taken(accounts):
    """Return whether an account with one of `accounts`' usernames is stored."""
    usernames = [account.username for account in accounts]
    return User.objects.filter(username__in=usernames).exists()
