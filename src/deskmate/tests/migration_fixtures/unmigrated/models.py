"""The migfix_unmigrated fixture model, which no migration creates."""

from django.db import models


class Tag(models.Model):
    """A tag, in an app that has no migrations package."""

    name = models.CharField(max_length=40)
