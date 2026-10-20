"""Metadata explicitly reported by trusted AI callers (PLT-6)."""

from django.db import models

FEATURES = ("find_a_fix", "key_sentences")
OUTCOMES = ("success", "failure")


class AICallAuditEvent(models.Model):
    """One pseudonymous AI event, with no user or provider content."""

    recorded_at = models.DateTimeField(db_index=True)
    user_hash = models.CharField(max_length=64)
    feature = models.CharField(
        max_length=13, choices=[(value, value) for value in FEATURES]
    )
    outcome = models.CharField(
        max_length=7, choices=[(value, value) for value in OUTCOMES]
    )
