"""Story 6.3 — API endpoint tests for InterfaceCollaboratorPageGrantsView."""

import pytest
from django.shortcuts import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.models import InterfaceCollaboratorPageGrant
from baserow.core.rbac.roles import INTERFACE_ONLY


def _setup(data_fixture):
    admin, token = data_fixture.create_user_and_token()
    workspace = data_fixture.create_workspace(user=admin)
    member = data_fixture.create_user()
    data_fixture.create_user_workspace(workspace=workspace, user=member, permissions="MEMBER")
    RbacHandler().assign_role(member, workspace, INTERFACE_ONLY)
    builder = data_fixture.create_builder_application(user=admin, workspace=workspace)
    page = data_fixture.create_builder_page(user=admin, builder=builder)
    return admin, token, workspace, builder, member, page


def _url(workspace_id, target_user_id):
    return reverse(
        "api:rbac:interface_page_grants",
        kwargs={"workspace_id": workspace_id, "target_user_id": target_user_id},
    )


@pytest.mark.django_db
def test_list_page_grants_requires_auth(api_client, data_fixture):
    admin, token, workspace, builder, member, page = _setup(data_fixture)
    url = _url(workspace.id, member.id)
    response = api_client.get(url, HTTP_AUTHORIZATION="JWT wrong")
    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_admin_lists_empty_page_grants(api_client, data_fixture):
    admin, token, workspace, builder, member, page = _setup(data_fixture)
    url = _url(workspace.id, member.id)
    response = api_client.get(url, HTTP_AUTHORIZATION=f"JWT {token}")
    assert response.status_code == HTTP_200_OK
    assert response.json() == []


@pytest.mark.django_db
def test_admin_lists_page_grants(api_client, data_fixture):
    admin, token, workspace, builder, member, page = _setup(data_fixture)
    RbacHandler().grant_page_access(member, workspace, page)

    url = _url(workspace.id, member.id)
    response = api_client.get(url, HTTP_AUTHORIZATION=f"JWT {token}")
    assert response.status_code == HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["page_id"] == page.id
    assert data[0]["user_id"] == member.id
    assert data[0]["workspace_id"] == workspace.id


@pytest.mark.django_db
def test_non_admin_cannot_list_page_grants(api_client, data_fixture):
    admin, token, workspace, builder, member, page = _setup(data_fixture)
    member_token = data_fixture.generate_token(member)

    url = _url(workspace.id, member.id)
    response = api_client.get(url, HTTP_AUTHORIZATION=f"JWT {member_token}")
    assert response.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_list_page_grants_workspace_not_found(api_client, data_fixture):
    admin, token, workspace, builder, member, page = _setup(data_fixture)
    url = _url(99999, member.id)
    response = api_client.get(url, HTTP_AUTHORIZATION=f"JWT {token}")
    assert response.status_code == HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_grant_page_access(api_client, data_fixture):
    admin, token, workspace, builder, member, page = _setup(data_fixture)
    url = _url(workspace.id, member.id)
    response = api_client.post(
        url,
        {"page_id": page.id},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == HTTP_200_OK
    data = response.json()
    assert data["page_id"] == page.id
    assert data["user_id"] == member.id
    assert InterfaceCollaboratorPageGrant.objects.filter(user=member, page=page).exists()


@pytest.mark.django_db
def test_grant_page_access_idempotent(api_client, data_fixture):
    admin, token, workspace, builder, member, page = _setup(data_fixture)
    url = _url(workspace.id, member.id)
    api_client.post(url, {"page_id": page.id}, format="json", HTTP_AUTHORIZATION=f"JWT {token}")
    response = api_client.post(url, {"page_id": page.id}, format="json", HTTP_AUTHORIZATION=f"JWT {token}")
    assert response.status_code == HTTP_200_OK
    assert InterfaceCollaboratorPageGrant.objects.filter(user=member, page=page).count() == 1


@pytest.mark.django_db
def test_grant_page_access_page_not_found(api_client, data_fixture):
    admin, token, workspace, builder, member, page = _setup(data_fixture)
    url = _url(workspace.id, member.id)
    response = api_client.post(url, {"page_id": 99999}, format="json", HTTP_AUTHORIZATION=f"JWT {token}")
    assert response.status_code == HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_grant_page_access_page_in_different_workspace(api_client, data_fixture):
    admin, token, workspace, builder, member, page = _setup(data_fixture)
    other_owner = data_fixture.create_user()
    other_ws = data_fixture.create_workspace(user=other_owner)
    other_builder = data_fixture.create_builder_application(user=other_owner, workspace=other_ws)
    other_page = data_fixture.create_builder_page(user=other_owner, builder=other_builder)

    url = _url(workspace.id, member.id)
    response = api_client.post(url, {"page_id": other_page.id}, format="json", HTTP_AUTHORIZATION=f"JWT {token}")
    assert response.status_code == HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_non_admin_cannot_grant_page_access(api_client, data_fixture):
    admin, token, workspace, builder, member, page = _setup(data_fixture)
    member_token = data_fixture.generate_token(member)
    url = _url(workspace.id, member.id)
    response = api_client.post(url, {"page_id": page.id}, format="json", HTTP_AUTHORIZATION=f"JWT {member_token}")
    assert response.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_revoke_page_access(api_client, data_fixture):
    admin, token, workspace, builder, member, page = _setup(data_fixture)
    RbacHandler().grant_page_access(member, workspace, page)

    url = _url(workspace.id, member.id)
    response = api_client.delete(url, {"page_id": page.id}, format="json", HTTP_AUTHORIZATION=f"JWT {token}")
    assert response.status_code == HTTP_204_NO_CONTENT
    assert not InterfaceCollaboratorPageGrant.objects.filter(user=member, page=page).exists()


@pytest.mark.django_db
def test_revoke_page_access_nonexistent_grant_is_noop(api_client, data_fixture):
    admin, token, workspace, builder, member, page = _setup(data_fixture)
    url = _url(workspace.id, member.id)
    response = api_client.delete(url, {"page_id": page.id}, format="json", HTTP_AUTHORIZATION=f"JWT {token}")
    assert response.status_code == HTTP_204_NO_CONTENT


@pytest.mark.django_db
def test_non_admin_cannot_revoke_page_access(api_client, data_fixture):
    admin, token, workspace, builder, member, page = _setup(data_fixture)
    RbacHandler().grant_page_access(member, workspace, page)
    member_token = data_fixture.generate_token(member)
    url = _url(workspace.id, member.id)
    response = api_client.delete(url, {"page_id": page.id}, format="json", HTTP_AUTHORIZATION=f"JWT {member_token}")
    assert response.status_code == HTTP_400_BAD_REQUEST
