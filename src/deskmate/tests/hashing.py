"""A fast salted password hasher for the tests, which can report what it hashes.

The `fast_hashing` fixture configures it, so that making accounts is quick. A
test that needs to know each password hashed and the hash made, such as one
looking for them where they must not appear, receives them inside
`reporting_hashes_to`. A test that needs to know whether any password was
hashed or checked, and by which thread, collects them in `recording_hashes`.
"""

import threading
from collections import namedtuple
from contextlib import contextmanager

from django.contrib.auth.hashers import MD5PasswordHasher

# RecordingPasswordHasher's dotted path, as PASSWORD_HASHERS names it.
RECORDING_HASHER = "deskmate.tests.hashing.RecordingPasswordHasher"

# The functions that RecordingPasswordHasher calls with what it hashes.
_receivers = []

# A password RecordingPasswordHasher hashed, the hash it made, and the name of
# the thread that asked for it.
Hashed = namedtuple("Hashed", ["password", "encoded", "thread"])


class RecordingPasswordHasher(MD5PasswordHasher):
    """Django's salted MD5 hasher, fast enough for tests, which also calls every
    active receiver with each password it hashes and the hash it makes."""

    def encode(self, password, salt):
        """Hash `password` with `salt`, and tell every active receiver."""
        encoded = super().encode(password, salt)
        for receive in _receivers:
            receive(password, encoded)
        return encoded


@contextmanager
def reporting_hashes_to(receive):
    """Inside it, RecordingPasswordHasher calls `receive(password, encoded)` for
    each password it hashes."""
    _receivers.append(receive)
    try:
        yield
    finally:
        _receivers.remove(receive)


@contextmanager
def recording_hashes():
    """Inside it, return a list that gets a Hashed for each password
    RecordingPasswordHasher hashes.

    Checking a password against a stored hash hashes it too, so the list also
    shows every password checked, whether or not it matched.
    """
    hashed = []

    def receive(password, encoded):
        hashed.append(Hashed(password, encoded, threading.current_thread().name))

    with reporting_hashes_to(receive):
        yield hashed
