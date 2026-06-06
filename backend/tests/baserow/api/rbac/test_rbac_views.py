from django.shortcuts import reverse

import pytest
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
)

from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.models import RoleAssignment
from baserow.core.rbac.roles import ADMIN, ALL_ROLES, EDITOR, VIEWER


@pytest.mark.django_db
def test_list_role_assignments_requires_auth(api_client, data_fixture):
    workspace = data_fixture.create_workspace()
    url = reverse(
        "api:rbac:workspace_role_assignments", kwargs={"workspace_id": workspace.id}
    )
    response = api_client.get(url, HTTP_AUTHORIZATION="JWT random")
    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_admin_lists_role_assignments(api_client, data_fixture):
    admin, token = data_fixture.create_user_and_token()
    member = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=admin, members=[member])
    RbacHandler().assign_role(member, workspace, EDITOR)

    url = reverse(
        "api:rbac:workspace_role_assignments", kwargs={"workspace_id": workspace.id}
    )
    response = api_client.get(url, HTTP_AUTHORIZATION=f"JWT {token}")
    response_json = response.json()

    assert response.status_code == HTTP_200_OK
    assert len(response_json) == 1
    assert response_json[0]["user_id"] == member.id
    assert response_json[0]["role"] == EDITOR
    assert response_json[0]["workspace_id"] == workspace.id


@pytest.mark.django_db
def test_non_admin_cannot_list_role_assignments(api_client, data_fixture):
    member, token = data_fixture.create_user_and_token()
    admin = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=admin, members=[member])

    url = reverse(
        "api:rbac:workspace_role_assignments", kwargs={"workspace_id": workspace.id}
    )
    response = api_client.get(url, HTTP_AUTHORIZATION=f"JWT {token}")

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_USER_INVALID_GROUP_PERMISSIONS"


@pytest.mark.django_db
def test_admin_assigns_role(api_client, data_fixture):
    admin, token = data_fixture.create_user_and_token()
    member = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=admin, members=[member])

    url = reverse(
        "api:rbac:workspace_role_assignments", kwargs={"workspace_id": workspace.id}
    )
    response = api_client.post(
        url,
        {"user_id": member.id, "role": VIEWER},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    response_json = response.json()

    assert response.status_code == HTTP_200_OK
    assert response_json["role"] == VIEWER
    assert response_json["user_id"] == member.id
    assert RoleAssignment.objects.filter(user=member, workspace=workspace).count() == 1


@pytest.mark.django_db
def test_non_admin_cannot_assign_role(api_client, data_fixture):
    member, token = data_fixture.create_user_and_token()
    admin = data_fixture.create_user()
    other = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=admin, members=[member, other])

    url = reverse(
        "api:rbac:workspace_role_assignments", kwargs={"workspace_id": workspace.id}
    )
    response = api_client.post(
        url,
        {"user_id": other.id, "role": VIEWER},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_USER_INVALID_GROUP_PERMISSIONS"
    assert RoleAssignment.objects.count() == 0


@pytest.mark.django_db
def test_assign_role_target_must_be_member(api_client, data_fixture):
    admin, token = data_fixture.create_user_and_token()
    outsider = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=admin)

    url = reverse(
        "api:rbac:workspace_role_assignments", kwargs={"workspace_id": workspace.id}
    )
    response = api_client.post(
        url,
        {"user_id": outsider.id, "role": VIEWER},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_USER_NOT_IN_GROUP"


@pytest.mark.django_db
def test_assign_role_rejects_invalid_role(api_client, data_fixture):
    admin, token = data_fixture.create_user_and_token()
    member = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=admin, members=[member])

    url = reverse(
        "api:rbac:workspace_role_assignments", kwargs={"workspace_id": workspace.id}
    )
    response = api_client.post(
        url,
        {"user_id": member.id, "role": "SUPERUSER"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_REQUEST_BODY_VALIDATION"


@pytest.mark.django_db
def test_assign_role_unknown_workspace(api_client, data_fixture):
    admin, token = data_fixture.create_user_and_token()
    member = data_fixture.create_user()

    url = reverse(
        "api:rbac:workspace_role_assignments", kwargs={"workspace_id": 999999}
    )
    response = api_client.post(
        url,
        {"user_id": member.id, "role": VIEWER},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json()["error"] == "ERROR_GROUP_DOES_NOT_EXIST"


# --- QA gap coverage (bmad-qa-generate-e2e-tests, story 1.2) ---


@pytest.mark.django_db
def test_assign_role_requires_auth(api_client, data_fixture):
    workspace = data_fixture.create_workspace()
    url = reverse(
        "api:rbac:workspace_role_assignments", kwargs={"workspace_id": workspace.id}
    )
    response = api_client.post(
        url,
        {"user_id": 1, "role": VIEWER},
        format="json",
        HTTP_AUTHORIZATION="JWT random",
    )
    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
@pytest.mark.parametrize("role", ALL_ROLES)
def test_admin_assigns_each_role_tier(api_client, data_fixture, role):
    admin, token = data_fixture.create_user_and_token()
    member = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=admin, members=[member])

    url = reverse(
        "api:rbac:workspace_role_assignments", kwargs={"workspace_id": workspace.id}
    )
    response = api_client.post(
        url,
        {"user_id": member.id, "role": role},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_200_OK
    assert response.json()["role"] == role


@pytest.mark.django_db
def test_admin_assigns_database_scoped_role(api_client, data_fixture):
    admin, token = data_fixture.create_user_and_token()
    member = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=admin, members=[member])
    database = data_fixture.create_database_application(workspace=workspace)

    url = reverse(
        "api:rbac:workspace_role_assignments", kwargs={"workspace_id": workspace.id}
    )
    response = api_client.post(
        url,
        {"user_id": member.id, "role": VIEWER, "application_id": database.id},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    response_json = response.json()

    assert response.status_code == HTTP_200_OK
    assert response_json["application_id"] == database.id
    assert response_json["role"] == VIEWER
    assert RbacHandler().get_effective_role(member, workspace, database) == VIEWER


@pytest.mark.django_db
def test_workspace_and_database_scope_coexist(api_client, data_fixture):
    admin, token = data_fixture.create_user_and_token()
    member = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=admin, members=[member])
    database = data_fixture.create_database_application(workspace=workspace)
    url = reverse(
        "api:rbac:workspace_role_assignments", kwargs={"workspace_id": workspace.id}
    )

    api_client.post(
        url,
        {"user_id": member.id, "role": EDITOR},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    api_client.post(
        url,
        {"user_id": member.id, "role": VIEWER, "application_id": database.id},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    # Both scopes persist; most-specific (database) wins for that application.
    assert RoleAssignment.objects.filter(user=member, workspace=workspace).count() == 2
    assert RbacHandler().get_effective_role(member, workspace) == EDITOR
    assert RbacHandler().get_effective_role(member, workspace, database) == VIEWER


@pytest.mark.django_db
def test_reassign_role_updates_existing_assignment(api_client, data_fixture):
    admin, token = data_fixture.create_user_and_token()
    member = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=admin, members=[member])
    url = reverse(
        "api:rbac:workspace_role_assignments", kwargs={"workspace_id": workspace.id}
    )

    api_client.post(
        url,
        {"user_id": member.id, "role": VIEWER},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    response = api_client.post(
        url,
        {"user_id": member.id, "role": ADMIN},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_200_OK
    # Upsert: same scope updates in place, no duplicate row.
    assert RoleAssignment.objects.filter(user=member, workspace=workspace).count() == 1
    assert RbacHandler().get_effective_role(member, workspace) == ADMIN


@pytest.mark.django_db
def test_assign_role_unknown_application(api_client, data_fixture):
    admin, token = data_fixture.create_user_and_token()
    member = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=admin, members=[member])

    url = reverse(
        "api:rbac:workspace_role_assignments", kwargs={"workspace_id": workspace.id}
    )
    response = api_client.post(
        url,
        {"user_id": member.id, "role": VIEWER, "application_id": 999999},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json()["error"] == "ERROR_APPLICATION_DOES_NOT_EXIST"


@pytest.mark.django_db
def test_assign_role_application_in_other_workspace(api_client, data_fixture):
    admin, token = data_fixture.create_user_and_token()
    member = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=admin, members=[member])
    other_workspace = data_fixture.create_workspace(user=admin)
    foreign_database = data_fixture.create_database_application(
        workspace=other_workspace
    )

    url = reverse(
        "api:rbac:workspace_role_assignments", kwargs={"workspace_id": workspace.id}
    )
    response = api_client.post(
        url,
        {"user_id": member.id, "role": VIEWER, "application_id": foreign_database.id},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json()["error"] == "ERROR_APPLICATION_DOES_NOT_EXIST"
    assert RoleAssignment.objects.count() == 0
