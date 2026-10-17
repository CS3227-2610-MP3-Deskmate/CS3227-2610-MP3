"""A fast salted password hasher for the tests, which can report what it hashes.

The `fast_hashing` fixture configures it, so that making accounts is quick. A
test that needs to know each password hashed and the hash made, such as one
looking for them where they must not appear, receives them inside
`reporting_hashes_to`.
"""

from contextlib import contextmanager

from django.contrib.auth.hashers import MD5PasswordHasher

# RecordingPasswordHasher's dotted path, as PASSWORD_HASHERS names it.
RECORDING_HASHER = "deskmate.tests.hashing.RecordingPasswordHasher"

# The functions that RecordingPasswordHasher calls with what it hashes.
_receivers = []


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
