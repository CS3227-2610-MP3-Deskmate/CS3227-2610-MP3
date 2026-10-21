"""Create one next-numbered Requester in a canonical workspace (ACC-5.2–5.6)."""

from collections import namedtuple

from django.contrib.auth.hashers import make_password
from django.db import Error, transaction

from deskmate.accounts import demo, membership
from deskmate.accounts.models import Role, User, Workspace

QUOTA_REACHED = "This workspace already has 20 Requester accounts."
NONCANONICAL = "Requester accounts cannot be created for this workspace."
# Credentials exist only in the successful call's result, never in stored state.
Result = namedtuple("Result", ["username", "password", "error"], defaults=[None] * 3)


def create_requester(workspace_id):
    """Return new credentials or a fixed membership/quota rejection.

    Lock the existing workspace before checking membership, quota or hashing,
    so overlapping creations cannot exceed the quota or choose the same number.
    Commit insertion before the caller renders credentials. A global username
    collision rolls back without retry. Database failures keep their type and
    traceback but omit sensitive messages and chained driver details, as in demo
    creation and password resets.
    """
    try:
        with transaction.atomic():
            Workspace.objects.select_for_update().get(pk=workspace_id)
            current = membership.resolve(workspace_id)
            if current.requester_count >= membership.MAX_REQUESTERS:
                return Result(error=QUOTA_REACHED)
            if current.code is None:
                return Result(error=NONCANONICAL)
            username = f"requester{current.requester_count + 1}-{current.code}"
            password = demo.random_password()
            hashed = make_password(password)
            User.objects.create(
                username=username,
                password=hashed,
                role=Role.REQUESTER,
                workspace_id=workspace_id,
            )
        return Result(username=username, password=password)
    except Error as error:
        hidden = type(error)("Creating a Requester account failed.")
        raise hidden.with_traceback(error.__traceback__) from None
