"""Tickets raised by Requesters in their workspace (RQ-1)."""

from django.db import models

from deskmate.accounts.models import Workspace


class Ticket(models.Model):
    """A Requester's request for help, visible to their workspace."""

    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT)
    title = models.CharField(max_length=200)
    description = models.TextField()
    open = models.BooleanField(default=True)

    class Meta:
        ordering = ["pk"]
