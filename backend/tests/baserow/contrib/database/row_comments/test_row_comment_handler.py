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


# ─── Story 6.2: Subscription & Notification Tests ──────────────────────────

@pytest.mark.django_db
def test_subscribe_viewer_succeeds(data_fixture):
    owner, viewer, workspace, table = _setup(data_fixture, VIEWER)
    sub = RowCommentHandler.subscribe(viewer, table.id, row_id=1)
    assert sub.user_id == viewer.id
    assert sub.row_id == 1
    assert sub.table_id == table.id


@pytest.mark.django_db
def test_subscribe_idempotent(data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    sub1 = RowCommentHandler.subscribe(commenter, table.id, row_id=1)
    sub2 = RowCommentHandler.subscribe(commenter, table.id, row_id=1)
    assert sub1.id == sub2.id


@pytest.mark.django_db
def test_unsubscribe_removes_subscription(data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    RowCommentHandler.subscribe(commenter, table.id, row_id=1)
    assert RowCommentHandler.is_subscribed(commenter, table.id, row_id=1)
    RowCommentHandler.unsubscribe(commenter, table.id, row_id=1)
    assert not RowCommentHandler.is_subscribed(commenter, table.id, row_id=1)


@pytest.mark.django_db
def test_unsubscribe_no_op_when_not_subscribed(data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    # Should not raise
    RowCommentHandler.unsubscribe(commenter, table.id, row_id=1)
    assert not RowCommentHandler.is_subscribed(commenter, table.id, row_id=1)


@pytest.mark.django_db
def test_is_subscribed_false_by_default(data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    assert not RowCommentHandler.is_subscribed(commenter, table.id, row_id=1)


@pytest.mark.django_db
def test_create_comment_auto_subscribes_commenter(data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    RowCommentHandler.create_comment(commenter, table.id, row_id=1, message=SIMPLE_MESSAGE)
    assert RowCommentHandler.is_subscribed(commenter, table.id, row_id=1)


@pytest.mark.django_db
def test_create_comment_auto_subscribes_mentioned_users(data_fixture):
    from baserow.contrib.database.row_comments.models import RowCommentSubscription
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    mentioned = data_fixture.create_user()
    data_fixture.create_user_workspace(workspace=workspace, user=mentioned, permissions="MEMBER")
    from baserow.core.rbac.handler import RbacHandler as RH
    RH().assign_role(mentioned, workspace, EDITOR)

    mention_msg = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "mention", "attrs": {"id": mentioned.id}}],
            }
        ],
    }
    RowCommentHandler.create_comment(commenter, table.id, row_id=1, message=mention_msg)
    assert RowCommentHandler.is_subscribed(mentioned, table.id, row_id=1)


@pytest.mark.django_db
def test_notify_subscribers_sends_to_subscribers_not_sender(data_fixture):
    from unittest.mock import patch
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    subscriber = data_fixture.create_user()
    data_fixture.create_user_workspace(workspace=workspace, user=subscriber, permissions="MEMBER")
    from baserow.core.rbac.handler import RbacHandler as RH
    RH().assign_role(subscriber, workspace, EDITOR)

    RowCommentHandler.subscribe(subscriber, table.id, row_id=1)
    comment = RowCommentHandler.create_comment(commenter, table.id, row_id=1, message=SIMPLE_MESSAGE)

    from baserow.core.notifications.models import NotificationRecipient
    # subscriber should have a row_comment_created notification
    notif = NotificationRecipient.objects.filter(
        recipient=subscriber,
        notification__notification_type="row_comment_created",
    ).first()
    assert notif is not None
    # commenter should NOT have it (sender excluded)
    assert not NotificationRecipient.objects.filter(
        recipient=commenter,
        notification__notification_type="row_comment_created",
    ).exists()


@pytest.mark.django_db
def test_notify_subscribers_skips_access_denied_users(data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)

    # Create outsider user and manually insert subscription (simulating stale sub)
    outsider = data_fixture.create_user()
    from baserow.contrib.database.row_comments.models import RowCommentSubscription
    RowCommentSubscription.objects.create(table=table, row_id=1, user=outsider)

    comment = RowCommentHandler.create_comment(commenter, table.id, row_id=1, message=SIMPLE_MESSAGE)

    from baserow.core.notifications.models import NotificationRecipient
    assert not NotificationRecipient.objects.filter(
        recipient=outsider,
        notification__notification_type="row_comment_created",
    ).exists()


@pytest.mark.django_db
def test_mentioned_user_gets_mention_not_created_notification(data_fixture):
    """When @mentioned, user should get row_comment_mention, NOT row_comment_created."""
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    mentioned = data_fixture.create_user()
    data_fixture.create_user_workspace(workspace=workspace, user=mentioned, permissions="MEMBER")
    from baserow.core.rbac.handler import RbacHandler as RH
    RH().assign_role(mentioned, workspace, EDITOR)

    # Pre-subscribe mentioned user
    RowCommentHandler.subscribe(mentioned, table.id, row_id=1)

    mention_msg = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "mention", "attrs": {"id": mentioned.id}}],
            }
        ],
    }
    RowCommentHandler.create_comment(commenter, table.id, row_id=1, message=mention_msg)

    from baserow.core.notifications.models import NotificationRecipient
    # Should have mention notification
    assert NotificationRecipient.objects.filter(
        recipient=mentioned,
        notification__notification_type="row_comment_mention",
    ).exists()
    # Should NOT have created notification (excluded from subscribers because @mentioned)
    assert not NotificationRecipient.objects.filter(
        recipient=mentioned,
        notification__notification_type="row_comment_created",
    ).exists()
