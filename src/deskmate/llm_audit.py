"""Record explicit AI-call metadata without observing provider traffic (PLT-6)."""

from datetime import timedelta

from django.conf import settings
from django.db import DatabaseError, Error, connection, transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from deskmate.accounts.models import User
from deskmate.models import FEATURES, OUTCOMES, AICallAuditEvent


def record_call(user, *, feature, outcome):
    """Commit one reported event and prune expired events for a trusted caller.

    The caller authenticates and loads the stored User; this helper does not
    authenticate a request or verify the reported outcome. Invalid metadata
    raises before database access. Recording requires its own transaction and
    returns None only after commit. Database failures expose a fixed error,
    including an unknown outcome after a lost commit acknowledgement; recording
    never retries, calls a provider or emits metadata.
    """
    if (
        not isinstance(user, User)
        or user._state.adding
        or user.pk is None
        or not user.is_authenticated
        or type(feature) is not str
        or feature not in FEATURES
        or type(outcome) is not str
        or outcome not in OUTCOMES
    ):
        raise ValueError("LLM audit metadata is invalid.")

    try:
        if connection.in_atomic_block or not connection.get_autocommit():
            raise RuntimeError("LLM audit recording requires its own transaction.")
        with transaction.atomic(durable=True):
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('statement_timeout', %s, true),"
                    " set_config('lock_timeout', %s, true)",
                    ["5000ms", "5000ms"],
                )
            moment = timezone.now()
            AICallAuditEvent.objects.create(
                recorded_at=moment,
                user_hash=salted_hmac(
                    "deskmate.llm.audit",
                    str(user.pk),
                    secret=settings.SECRET_KEY,
                    algorithm="sha256",
                ).hexdigest(),
                feature=feature,
                outcome=outcome,
            )
            AICallAuditEvent.objects.filter(
                recorded_at__lte=moment - timedelta(days=30)
            ).delete()
    except Error:
        raise DatabaseError("LLM audit recording failed.") from None
