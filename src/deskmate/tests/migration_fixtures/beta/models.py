"""The migfix_beta fixture model, described by its migrations."""

from django.db import models


class Board(models.Model):
    """A board, which may pin one card."""

    name = models.CharField(max_length=40)
    pinned = models.ForeignKey(
        "migfix_alpha.Card", null=True, on_delete=models.SET_NULL, related_name="+"
    )
