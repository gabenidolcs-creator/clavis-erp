from typing import List

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from baserow.contrib.database.row_comments.exceptions import (
    RowCommentDoesNotExist,
    RowCommentMentionAccessError,
    RowCommentNotOwnedByUser,
)
from baserow.contrib.database.row_comments.models import RowComment
from baserow.contrib.database.row_comments.operations import (
    RowCommentCreateOperationType,
    RowCommentDeleteOperationType,
    RowCommentListOperationType,
    RowCommentUpdateOperationType,
)
from baserow.contrib.database.row_comments.signals import (
    row_comment_created,
    row_comment_deleted,
    row_comment_updated,
)
from baserow.contrib.database.table.handler import TableHandler
from baserow.core.exceptions import PermissionDenied, UserNotInWorkspace
from baserow.core.handler import CoreHandler
from baserow.core.rbac.roles import ADMIN, role_at_least

User = get_user_model()


def _extract_mention_user_ids(message: dict) -> List[int]:
    """Walk a tiptap document and collect mention attrs.id values."""
    user_ids = []
    _walk_tiptap(message, user_ids)
    return user_ids


def _walk_tiptap(node: dict, user_ids: list):
    if not isinstance(node, dict):
        return
    if node.get("type") == "mention":
        uid = node.get("attrs", {}).get("id")
        if uid is not None:
            try:
                user_ids.append(int(uid))
            except (TypeError, ValueError):
                pass
    for child in node.get("content", []):
        _walk_tiptap(child, user_ids)


class RowCommentHandler:
    @staticmethod
    def get_comments(user, table_id: int, row_id: int) -> QuerySet:
        table = TableHandler().get_table(table_id)
        CoreHandler().check_permissions(
            user,
            RowCommentListOperationType.type,
            workspace=table.database.workspace,
            context=table,
        )
        return RowComment.objects.filter(
            table=table, row_id=row_id, deleted_on__isnull=True
        ).select_related("user")

    @staticmethod
    def create_comment(user, table_id: int, row_id: int, message: dict) -> RowComment:
        table = TableHandler().get_table(table_id)
        workspace = table.database.workspace
        CoreHandler().check_permissions(
            user,
            RowCommentCreateOperationType.type,
            workspace=workspace,
            context=table,
        )

        # Validate @mentions — each mentioned user must have Row access.
        mention_user_ids = _extract_mention_user_ids(message)
        mentioned_users = []
        if mention_user_ids:
            users_map = {
                u.id: u
                for u in User.objects.filter(id__in=mention_user_ids).select_related(
                    "profile"
                )
            }
            for uid in mention_user_ids:
                mentioned_user = users_map.get(uid)
                if mentioned_user is None:
                    continue
                try:
                    CoreHandler().check_permissions(
                        mentioned_user,
                        RowCommentListOperationType.type,
                        workspace=workspace,
                        context=table,
                    )
                except (PermissionDenied, UserNotInWorkspace):
                    raise RowCommentMentionAccessError(user_id=uid)
                mentioned_users.append(mentioned_user)

        with transaction.atomic():
            comment = RowComment.objects.create(
                table=table,
                row_id=row_id,
                user=user,
                message=message,
            )

        # Create notifications for valid @mentions.
        if mentioned_users:
            from baserow.core.notifications.handler import NotificationHandler

            NotificationHandler.create_direct_notification_for_users(
                notification_type="row_comment_mention",
                recipients=mentioned_users,
                sender=user,
                data={
                    "table_id": table.id,
                    "database_id": table.database.id,
                    "row_id": row_id,
                    "comment_id": comment.id,
                    "comment_preview": _comment_preview(message),
                },
                workspace=workspace,
            )

        row_comment_created.send(
            sender=RowCommentHandler,
            comment=comment,
            user=user,
            table=table,
        )
        return comment

    @staticmethod
    def update_comment(user, comment_id: int, message: dict) -> RowComment:
        try:
            comment = RowComment.objects.select_related(
                "table__database__workspace"
            ).get(id=comment_id, deleted_on__isnull=True)
        except RowComment.DoesNotExist:
            raise RowCommentDoesNotExist()

        table = comment.table
        workspace = table.database.workspace

        CoreHandler().check_permissions(
            user,
            RowCommentUpdateOperationType.type,
            workspace=workspace,
            context=table,
        )

        user_role = _get_user_role(user, workspace)
        if comment.user_id != user.id and not role_at_least(user_role, ADMIN):
            raise RowCommentNotOwnedByUser()

        comment.message = message
        comment.save(update_fields=["message", "updated_on"])

        row_comment_updated.send(
            sender=RowCommentHandler,
            comment=comment,
            user=user,
            table=table,
        )
        return comment

    @staticmethod
    def delete_comment(user, comment_id: int) -> None:
        try:
            comment = RowComment.objects.select_related(
                "table__database__workspace"
            ).get(id=comment_id, deleted_on__isnull=True)
        except RowComment.DoesNotExist:
            raise RowCommentDoesNotExist()

        table = comment.table
        workspace = table.database.workspace

        CoreHandler().check_permissions(
            user,
            RowCommentDeleteOperationType.type,
            workspace=workspace,
            context=table,
        )

        user_role = _get_user_role(user, workspace)
        if comment.user_id != user.id and not role_at_least(user_role, ADMIN):
            raise RowCommentNotOwnedByUser()

        comment.deleted_on = timezone.now()
        comment.save(update_fields=["deleted_on"])

        row_comment_deleted.send(
            sender=RowCommentHandler,
            comment=comment,
            user=user,
            table=table,
        )


def _comment_preview(message: dict) -> str:
    """Extract plain text from tiptap doc for notification preview (max 200 chars)."""
    parts = []
    _collect_text(message, parts)
    return "".join(parts)[:200]


def _collect_text(node: dict, parts: list):
    if not isinstance(node, dict):
        return
    if node.get("type") == "text":
        parts.append(node.get("text", ""))
    for child in node.get("content", []):
        _collect_text(child, parts)


def _get_user_role(user, workspace):
    from baserow.core.rbac.handler import RbacHandler

    return RbacHandler().get_effective_role(user, workspace)
