"""The migfix_alpha fixture model, described by its migrations."""

from django.db import models


class Card(models.Model):
    """A card on a board."""

    board = models.ForeignKey("migfix_beta.Board", on_delete=models.CASCADE)
    title = models.CharField(max_length=40)
