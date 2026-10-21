"""Resolve canonical workspace membership for labels and creation (ACC-1.2, ACC-5)."""

from collections import namedtuple

from deskmate.accounts import demo
from deskmate.accounts.models import Role, User

MAX_REQUESTERS = 20
Membership = namedtuple("Membership", ["code", "requester_count"])


def resolve(workspace_id):
    """Return the canonical code, or None, and the stored Requester count.

    Read only this workspace's stored accounts and let database errors propagate.
    Creation calls this while holding the workspace lock; labels only read.
    """
    members = list(
        User.objects.filter(workspace_id=workspace_id).values_list("username", "role")
    )
    count = sum(role == Role.REQUESTER for _, role in members)
    return Membership(_canonical_code(members, count), count)


def _canonical_code(members, count):
    """Recognize exactly support1 and contiguous requester1..N sharing one code."""
    if not 2 <= count <= MAX_REQUESTERS or len(members) != count + 1:
        return None
    code = members[0][0].rpartition("-")[2]
    if len(code) != demo.CODE_LENGTH or any(char not in demo.ALPHABET for char in code):
        return None
    expected = {(f"support1-{code}", Role.SUPPORT_OFFICER)}
    expected.update(
        (f"requester{number}-{code}", Role.REQUESTER) for number in range(1, count + 1)
    )
    return code if set(members) == expected else None
