"""Replace only an eligible Requester's password hash (ACC-4.2–ACC-4.7)."""

from django.contrib.auth.hashers import make_password
from django.db import Error, transaction

from deskmate.accounts.demo import random_password
from deskmate.accounts.models import Role, User


def reset_password(username, workspace_id):
    """Return the stored username and new password, or None for an ineligible target.

    The conditional update rechecks eligibility without changing any other field.
    Django's session hashes invalidate prior target sessions on their next request.
    Database failures keep their type and traceback but omit sensitive details.
    """
    try:
        eligible = User.objects.filter(role=Role.REQUESTER, workspace_id=workspace_id)
        target = eligible.filter(username=username).only("pk", "username").first()
        if target is None:
            return None
        password = random_password()
        hashed = make_password(password)
        with transaction.atomic():
            updated = eligible.filter(pk=target.pk).update(password=hashed)
        return (target.username, password) if updated else None
    except Error as error:
        hidden = type(error)("Resetting a Requester password failed.")
        raise hidden.with_traceback(error.__traceback__) from None
