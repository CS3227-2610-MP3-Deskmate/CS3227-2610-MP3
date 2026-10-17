"""The migfix_drift fixture model: `done` is in no migration."""

from django.db import models


class Note(models.Model):
    """A note, whose `done` field was added without a migration."""

    text = models.CharField(max_length=40)
    done = models.BooleanField(default=False)
