"""Story 6.1 — RowComment API endpoint tests."""

import pytest

from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.roles import ADMIN, COMMENTER, EDITOR, VIEWER


def _setup(data_fixture, actor_role):
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


SIMPLE_MSG = {
    "type": "doc",
    "content": [{"type": "paragraph", "content": [{"type": "text", "text": "hi"}]}],
}


@pytest.mark.django_db
def test_list_comments_authenticated(api_client, data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    api_client.force_authenticate(user=commenter)
    url = f"/api/database/rows/table/{table.id}/1/comments/"
    response = api_client.get(url)
    assert response.status_code == 200
    assert "results" in response.data


@pytest.mark.django_db
def test_create_comment_commenter_201(api_client, data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    api_client.force_authenticate(user=commenter)
    url = f"/api/database/rows/table/{table.id}/1/comments/"
    response = api_client.post(url, {"message": SIMPLE_MSG}, format="json")
    assert response.status_code == 201
    assert response.data["message"] == SIMPLE_MSG


@pytest.mark.django_db
def test_create_comment_viewer_403(api_client, data_fixture):
    owner, viewer, workspace, table = _setup(data_fixture, VIEWER)
    api_client.force_authenticate(user=viewer)
    url = f"/api/database/rows/table/{table.id}/1/comments/"
    response = api_client.post(url, {"message": SIMPLE_MSG}, format="json")
    assert response.status_code == 403


@pytest.mark.django_db
def test_patch_own_comment_200(api_client, data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    api_client.force_authenticate(user=commenter)
    url = f"/api/database/rows/table/{table.id}/1/comments/"
    create_resp = api_client.post(url, {"message": SIMPLE_MSG}, format="json")
    comment_id = create_resp.data["id"]

    new_msg = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "updated"}]}
        ],
    }
    patch_url = f"/api/database/rows/table/{table.id}/1/comments/{comment_id}/"
    response = api_client.patch(patch_url, {"message": new_msg}, format="json")
    assert response.status_code == 200
    assert response.data["message"] == new_msg


@pytest.mark.django_db
def test_patch_other_comment_editor_403(api_client, data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    api_client.force_authenticate(user=commenter)
    url = f"/api/database/rows/table/{table.id}/1/comments/"
    create_resp = api_client.post(url, {"message": SIMPLE_MSG}, format="json")
    comment_id = create_resp.data["id"]

    editor = data_fixture.create_user()
    data_fixture.create_user_workspace(
        workspace=workspace, user=editor, permissions="MEMBER"
    )
    RbacHandler().assign_role(editor, workspace, EDITOR)
    api_client.force_authenticate(user=editor)

    new_msg = {"type": "doc"}
    patch_url = f"/api/database/rows/table/{table.id}/1/comments/{comment_id}/"
    response = api_client.patch(patch_url, {"message": new_msg}, format="json")
    assert response.status_code == 403


@pytest.mark.django_db
def test_delete_own_comment_204(api_client, data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    api_client.force_authenticate(user=commenter)
    url = f"/api/database/rows/table/{table.id}/1/comments/"
    create_resp = api_client.post(url, {"message": SIMPLE_MSG}, format="json")
    comment_id = create_resp.data["id"]

    delete_url = f"/api/database/rows/table/{table.id}/1/comments/{comment_id}/"
    response = api_client.delete(delete_url)
    assert response.status_code == 204


@pytest.mark.django_db
def test_delete_any_comment_as_admin_204(api_client, data_fixture):
    owner, commenter, workspace, table = _setup(data_fixture, COMMENTER)
    api_client.force_authenticate(user=commenter)
    url = f"/api/database/rows/table/{table.id}/1/comments/"
    create_resp = api_client.post(url, {"message": SIMPLE_MSG}, format="json")
    comment_id = create_resp.data["id"]

    admin = data_fixture.create_user()
    data_fixture.create_user_workspace(
        workspace=workspace, user=admin, permissions="MEMBER"
    )
    RbacHandler().assign_role(admin, workspace, ADMIN)
    api_client.force_authenticate(user=admin)

    delete_url = f"/api/database/rows/table/{table.id}/1/comments/{comment_id}/"
    response = api_client.delete(delete_url)
    assert response.status_code == 204


# ─── Story 6.2: Subscription API Tests ─────────────────────────────────────

@pytest.mark.django_db
def test_get_subscription_status_not_subscribed(api_client, data_fixture):
    owner, viewer, workspace, table = _setup(data_fixture, VIEWER)
    api_client.force_authenticate(user=viewer)
    url = f"/api/database/rows/table/{table.id}/1/comments/subscriptions/"
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data["subscribed"] is False


@pytest.mark.django_db
def test_post_subscribe_returns_200_with_subscribed_true(api_client, data_fixture):
    owner, viewer, workspace, table = _setup(data_fixture, VIEWER)
    api_client.force_authenticate(user=viewer)
    url = f"/api/database/rows/table/{table.id}/1/comments/subscriptions/"
    response = api_client.post(url)
    assert response.status_code == 200
    assert response.data["subscribed"] is True


@pytest.mark.django_db
def test_post_subscribe_then_get_returns_subscribed_true(api_client, data_fixture):
    owner, viewer, workspace, table = _setup(data_fixture, VIEWER)
    api_client.force_authenticate(user=viewer)
    url = f"/api/database/rows/table/{table.id}/1/comments/subscriptions/"
    api_client.post(url)
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data["subscribed"] is True


@pytest.mark.django_db
def test_post_subscribe_idempotent(api_client, data_fixture):
    owner, viewer, workspace, table = _setup(data_fixture, VIEWER)
    api_client.force_authenticate(user=viewer)
    url = f"/api/database/rows/table/{table.id}/1/comments/subscriptions/"
    api_client.post(url)
    response = api_client.post(url)
    assert response.status_code == 200
    assert response.data["subscribed"] is True


@pytest.mark.django_db
def test_delete_unsubscribe_returns_204(api_client, data_fixture):
    owner, viewer, workspace, table = _setup(data_fixture, VIEWER)
    api_client.force_authenticate(user=viewer)
    url = f"/api/database/rows/table/{table.id}/1/comments/subscriptions/"
    api_client.post(url)
    response = api_client.delete(url)
    assert response.status_code == 204


@pytest.mark.django_db
def test_delete_unsubscribe_when_not_subscribed_is_noop(api_client, data_fixture):
    owner, viewer, workspace, table = _setup(data_fixture, VIEWER)
    api_client.force_authenticate(user=viewer)
    url = f"/api/database/rows/table/{table.id}/1/comments/subscriptions/"
    response = api_client.delete(url)
    assert response.status_code == 204


@pytest.mark.django_db
def test_subscription_unauthenticated_returns_401(api_client, data_fixture):
    owner, viewer, workspace, table = _setup(data_fixture, VIEWER)
    url = f"/api/database/rows/table/{table.id}/1/comments/subscriptions/"
    response = api_client.get(url)
    assert response.status_code == 401
