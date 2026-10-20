"""Admission of user AI calls through shared durable counts (PLT-5)."""

from django.utils.crypto import salted_hmac

from deskmate.accounts.limits import check_group_and_count
from deskmate.accounts.models import Kind

_SALT = "deskmate.llm_limits"
_LIMITS = (10, 30)


def check_and_count(user):
    """Admit and count an AI attempt for the trusted caller's stored `user`.

    The caller resolves the authenticated Django User through trusted server
    code and calls outside another database transaction. This gate does not
    authenticate users. Only the stored primary key selects the user allowance.
    Returns None after admission commits, or a refusal delay in whole seconds,
    rounded up; database failures propagate. Admission remains counted however
    subsequent work ends. This gate performs no provider work or automatic retry.
    """
    group = salted_hmac(_SALT, str(user.pk), algorithm="sha256").hexdigest()
    return check_group_and_count(group, Kind.LLM_CALL, _LIMITS)
