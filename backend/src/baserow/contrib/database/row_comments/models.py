from django.contrib.auth import get_user_model
from django.db import models

from baserow.contrib.database.table.models import Table

User = get_user_model()


class RowComment(models.Model):
    """Free-core RowComment model. Uses db_table = "database_rowcomment".

    When baserow_premium is installed, the premium RowComment model shares this table
    with additional fields (trashed, mentions). The fields defined here are the minimum
    required by the free-core handler.
    """

    table = models.ForeignKey(
        Table,
        on_delete=models.CASCADE,
        related_name="+",
        help_text="The table the row this comment is for is found in.",
    )
    row_id = models.PositiveIntegerField(db_index=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
        help_text="The user who made the comment.",
    )
    message = models.JSONField(default=dict, help_text="Tiptap document JSON.")
    created_on = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted_on = models.DateTimeField(null=True, db_index=True)
    # Present in premium schema (TrashableModelMixin). Included here so INSERT works
    # when premium is installed; harmless when free-core only.
    trashed = models.BooleanField(default=False, db_index=True)

    class Meta:
        app_label = "database"
        db_table = "database_rowcomment"
        ordering = ["created_on"]
        indexes = [models.Index(fields=["table", "row_id"])]
