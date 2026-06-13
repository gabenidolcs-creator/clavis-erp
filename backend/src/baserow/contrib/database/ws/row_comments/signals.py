from django.db import transaction
from django.dispatch import receiver

from baserow.contrib.database.row_comments import signals as comment_signals
from baserow.contrib.database.row_comments.api.serializers import RowCommentSerializer
from baserow.ws.registries import page_registry


@receiver(comment_signals.row_comment_created)
def row_comment_created(sender, comment, user, table, **kwargs):
    table_page_type = page_registry.get("table")
    payload = {
        "type": "row_comment_created",
        "table_id": table.id,
        "row_id": comment.row_id,
        "comment": RowCommentSerializer(comment).data,
    }
    transaction.on_commit(
        lambda: table_page_type.broadcast(
            payload,
            getattr(user, "web_socket_id", None),
            table_id=table.id,
        )
    )


@receiver(comment_signals.row_comment_updated)
def row_comment_updated(sender, comment, user, table, **kwargs):
    table_page_type = page_registry.get("table")
    payload = {
        "type": "row_comment_updated",
        "table_id": table.id,
        "row_id": comment.row_id,
        "comment": RowCommentSerializer(comment).data,
    }
    transaction.on_commit(
        lambda: table_page_type.broadcast(
            payload,
            getattr(user, "web_socket_id", None),
            table_id=table.id,
        )
    )


@receiver(comment_signals.row_comment_deleted)
def row_comment_deleted(sender, comment, user, table, **kwargs):
    table_page_type = page_registry.get("table")
    payload = {
        "type": "row_comment_deleted",
        "table_id": table.id,
        "row_id": comment.row_id,
        "comment_id": comment.id,
    }
    transaction.on_commit(
        lambda: table_page_type.broadcast(
            payload,
            getattr(user, "web_socket_id", None),
            table_id=table.id,
        )
    )
