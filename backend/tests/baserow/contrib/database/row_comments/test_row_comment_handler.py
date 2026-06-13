"""Story 6.1 — RowCommentHandler unit tests.

Tests the handler through the production PERMISSION_MANAGERS chain using real model
contexts, mirroring the pattern established in test_enforcement_handler.py.
"""

import pytest

from baserow.contrib.database.row_comments.exceptions import (
    RowCommentMentionAccessError,
    RowCommentNotOwnedByUser,
)
from baserow.contrib.database.row_comments.handler import RowCommentHandler
from baserow.core.exceptions import RoleProhibitedError
from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.roles import ADMIN, COMMENTER, EDITOR, VIEWER


def _setup(data_fixture, actor_role):
    """Owner + a workspace member with ``actor_role``."""
    owner = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=owner)
    actor = data_fixture.create_user()
    data_fixture.create_user_workspace(
        workspace=workspace, user=actor, permissions="MEMBER"
    )
    RbacHandler().assign_role(actor, workspace, actor_role)
    database = data_fixture.create_database_application(user=owner, workspace=workspace)
    table = data_fixture.create_database_table(user=owner, database=database)
    return owner, actor, workspace, table


SIMPLE_MESSAGE = {
    "type": "doc",
    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "hello"}]}],
}


@pytest.mark.django_db
def test_create_comment_commenter_succeeds(data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    comment = RowCommentHandler.create_comment(
        commenter, table.id, row_id=1, message=SIMPLE_MESSAGE
    )
    assert comment.id is not None
    assert comment.user_id == commenter.id
    assert comment.row_id == 1
    assert comment.table_id == table.id


@pytest.mark.django_db
def test_create_comment_viewer_raises_permission_denied(data_fixture):
    owner, viewer, workspace, table = _setup(data_fixture, VIEWER)
    with pytest.raises(RoleProhibitedError):
        RowCommentHandler.create_comment(
            viewer, table.id, row_id=1, message=SIMPLE_MESSAGE
        )


@pytest.mark.django_db
def test_mention_member_without_row_access_raises_error(data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)

    # Create a user NOT in the workspace — no row access.
    outsider = data_fixture.create_user()

    mention_message = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "mention", "attrs": {"id": outsider.id}},
                ],
            }
        ],
    }
    with pytest.raises(RowCommentMentionAccessError):
        RowCommentHandler.create_comment(
            commenter, table.id, row_id=1, message=mention_message
        )


@pytest.mark.django_db
def test_mention_member_with_row_access_creates_notification(data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)

    # Create a second member WITH workspace access.
    mentionee = data_fixture.create_user()
    data_fixture.create_user_workspace(
        workspace=workspace, user=mentionee, permissions="MEMBER"
    )
    RbacHandler().assign_role(mentionee, workspace, VIEWER)

    mention_message = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {"type": "mention", "attrs": {"id": mentionee.id}},
                ],
            }
        ],
    }

    from baserow.core.notifications.models import NotificationRecipient

    before_count = NotificationRecipient.objects.count()
    RowCommentHandler.create_comment(
        commenter, table.id, row_id=1, message=mention_message
    )
    assert NotificationRecipient.objects.count() == before_count + 1


@pytest.mark.django_db
def test_update_own_comment_succeeds(data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    comment = RowCommentHandler.create_comment(
        commenter, table.id, row_id=1, message=SIMPLE_MESSAGE
    )

    updated_message = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "updated"}]}
        ],
    }
    updated = RowCommentHandler.update_comment(
        commenter, comment.id, message=updated_message
    )
    assert updated.message == updated_message


@pytest.mark.django_db
def test_update_other_comment_as_editor_raises(data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    comment = RowCommentHandler.create_comment(
        commenter, table.id, row_id=1, message=SIMPLE_MESSAGE
    )

    editor = data_fixture.create_user()
    data_fixture.create_user_workspace(
        workspace=workspace, user=editor, permissions="MEMBER"
    )
    RbacHandler().assign_role(editor, workspace, EDITOR)

    new_message = {"type": "doc"}
    with pytest.raises(RowCommentNotOwnedByUser):
        RowCommentHandler.update_comment(editor, comment.id, message=new_message)


@pytest.mark.django_db
def test_update_other_comment_as_admin_succeeds(data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    comment = RowCommentHandler.create_comment(
        commenter, table.id, row_id=1, message=SIMPLE_MESSAGE
    )

    admin = data_fixture.create_user()
    data_fixture.create_user_workspace(
        workspace=workspace, user=admin, permissions="MEMBER"
    )
    RbacHandler().assign_role(admin, workspace, ADMIN)

    new_message = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "admin edit"}]}
        ],
    }
    updated = RowCommentHandler.update_comment(admin, comment.id, message=new_message)
    assert updated.message == new_message


@pytest.mark.django_db
def test_delete_own_comment_soft_deleted(data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    comment = RowCommentHandler.create_comment(
        commenter, table.id, row_id=1, message=SIMPLE_MESSAGE
    )

    RowCommentHandler.delete_comment(commenter, comment.id)

    comment.refresh_from_db()
    assert comment.deleted_on is not None

    # Verify it's excluded from listings.
    comments = RowCommentHandler.get_comments(commenter, table.id, row_id=1)
    assert comment not in list(comments)


@pytest.mark.django_db
def test_delete_other_comment_as_admin_succeeds(data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    comment = RowCommentHandler.create_comment(
        commenter, table.id, row_id=1, message=SIMPLE_MESSAGE
    )

    admin = data_fixture.create_user()
    data_fixture.create_user_workspace(
        workspace=workspace, user=admin, permissions="MEMBER"
    )
    RbacHandler().assign_role(admin, workspace, ADMIN)

    RowCommentHandler.delete_comment(admin, comment.id)
    comment.refresh_from_db()
    assert comment.deleted_on is not None


@pytest.mark.django_db
def test_comment_payload_contains_no_field_values(data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    comment = RowCommentHandler.create_comment(
        commenter, table.id, row_id=1, message=SIMPLE_MESSAGE
    )

    from baserow.contrib.database.row_comments.api.serializers import (
        RowCommentSerializer,
    )

    data = RowCommentSerializer(comment).data
    # Verify only expected keys present, no row field values.
    assert set(data.keys()) == {"id", "author", "message", "created_on", "updated_on"}
    assert "fields" not in data
