"""Middleware that signs users out 8 hours after they signed in (ACC-1.6).

Signing in records the time in the session, and the session ends
SESSION_COOKIE_AGE seconds after it, however active its user is and however
often the session is saved.
"""

from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.utils import timezone
from django.utils.functional import SimpleLazyObject

# The session key that holds when its user signed in, as a POSIX timestamp.
_SIGNED_IN_AT = "deskmate_signed_in_at"


def record_sign_in(session):
    """Store the current time in `session` as the time its user signed in."""
    session[_SIGNED_IN_AT] = timezone.now().timestamp()


def _must_end(signed_in, signed_in_at):
    """Return whether a session must end, given whether and when it signed in.

    A signed-in session ends SESSION_COOKIE_AGE seconds after `signed_in_at`,
    or at once if that time is unknown.
    """
    if not signed_in:
        return False
    if signed_in_at is None:
        return True
    return timezone.now().timestamp() - signed_in_at >= settings.SESSION_COOKIE_AGE


def sign_in_limit(get_response):
    """End a request's session if `_must_end` says so, before its user is read.

    The check wraps the user that AuthenticationMiddleware gives the request,
    so it runs only when that user is first read. A request that never reads
    it, such as one for the home page, never loads its session, so it is
    still served while the database does not answer (PLT-1.1). Ending the
    session flushes it, as Django does when a session's hash fails to verify.
    """

    def middleware(request):
        user, auser = request.user, request.auser
        session = request.session

        def checked_user():
            if _must_end(SESSION_KEY in session, session.get(_SIGNED_IN_AT)):
                session.flush()
            # `user` is still lazy, so it reads the session after the check.
            return user

        async def checked_auser():
            signed_in = await session.ahas_key(SESSION_KEY)
            if _must_end(signed_in, await session.aget(_SIGNED_IN_AT)):
                await session.aflush()
            return await auser()

        request.user = SimpleLazyObject(checked_user)
        request.auser = checked_auser
        return get_response(request)

    return middleware
