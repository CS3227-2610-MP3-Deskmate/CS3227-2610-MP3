"""Workspace articles and their case-insensitive title identity (KB-1)."""

from django.db import models

from deskmate.accounts.models import Workspace

TITLE_UNIQUE = "knowledge_article_workspace_title"


class Article(models.Model):
    """Plain-text guidance shared by the officers in one workspace."""

    workspace = models.ForeignKey(Workspace, on_delete=models.PROTECT)
    title = models.CharField(max_length=200)
    body = models.TextField()
    title_key = models.TextField(editable=False, db_collation="C")

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "title_key"], name=TITLE_UNIQUE
            )
        ]

    def save(self, *args, **kwargs):
        """Keep the comparison key with the title, including partial title saves."""
        self.title_key = self.title.strip().casefold()
        if (
            kwargs.get("update_fields") is not None
            and "title" in kwargs["update_fields"]
        ):
            kwargs["update_fields"] = {*kwargs["update_fields"], "title_key"}
        return super().save(*args, **kwargs)
