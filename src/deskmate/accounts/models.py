"""Workspaces and the users who belong to them (TECHNICAL-SPEC "Data model")."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class Workspace(models.Model):
    """A group of users and the records they share; it holds only its identity."""


class Role(models.TextChoices):
    """What a user does in their workspace (PRODUCT-SPEC "Roles")."""

    REQUESTER = "requester", "Requester"
    SUPPORT_OFFICER = "support_officer", "Support Officer"


class User(AbstractUser):
    """A person who signs in, with one role in exactly one workspace.

    `AbstractUser` gives the unique username, its validation and NFKC
    normalisation, and the salted password hash.
    """

    role = models.CharField(max_length=32, choices=Role)
    workspace = models.ForeignKey(
        Workspace, on_delete=models.PROTECT, related_name="users"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(role__in=Role.values), name="accounts_user_role"
            )
        ]
