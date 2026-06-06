"""Story 1.3 — REST API assertions: Viewer/Commenter mutations return HTTP 403
(ERROR_ROLE_PROHIBITED), reads return 200, Editor is unaffected. Also proves the global
exception mapping (RoleProhibitedError → 403) wins over the PermissionException → 401
catch-all via MRO precedence (no regression of the legacy 401).
"""

from django.urls import reverse

import pytest
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
)

from baserow.api.errors import ERROR_PERMISSION_DENIED, ERROR_ROLE_PROHIBITED
from baserow.api.utils import apply_exception_mapping
from baserow.core.exceptions import PermissionDenied, RoleProhibitedError
from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.roles import COMMENTER, EDITOR, VIEWER


def _member(data_fixture, role):
    """Admin owner + a separate MEMBER user assigned ``role`` in the same workspace,
    with a database/table owned by the owner. Returns (member, jwt, table)."""

    owner = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=owner)
    member = data_fixture.create_user()
    data_fixture.create_user_workspace(
        workspace=workspace, user=member, permissions="MEMBER"
    )
    RbacHandler().assign_role(member, workspace, role)
    database = data_fixture.create_database_application(user=owner, workspace=workspace)
    table = data_fixture.create_database_table(user=owner, database=database)
    return member, data_fixture.generate_token(member), table


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_create_field_denied_403_for_read_scoped_roles(api_client, data_fixture, role):
    member, jwt, table = _member(data_fixture, role)

    response = api_client.post(
        reverse("api:database:fields:list", kwargs={"table_id": table.id}),
        {"name": "Blocked", "type": "text"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json()["error"] == "ERROR_ROLE_PROHIBITED"


@pytest.mark.django_db
def test_create_field_allowed_for_editor(api_client, data_fixture):
    member, jwt, table = _member(data_fixture, EDITOR)

    response = api_client.post(
        reverse("api:database:fields:list", kwargs={"table_id": table.id}),
        {"name": "Allowed", "type": "text"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    # Editor (former MEMBER) is not role-denied; the field is created.
    assert response.status_code == HTTP_200_OK
    assert response.json()["name"] == "Allowed"


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_list_fields_read_succeeds_for_read_scoped_roles(
    api_client, data_fixture, role
):
    member, jwt, table = _member(data_fixture, role)
    data_fixture.create_text_field(table=table, name="Existing")

    response = api_client.get(
        reverse("api:database:fields:list", kwargs={"table_id": table.id}),
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK


def test_exception_mapping_role_prohibited_wins_over_catch_all():
    """MRO precedence: with the global mapping in place, RoleProhibitedError resolves to
    403 while the generic PermissionException catch-all stays 401 (no regression)."""

    mapping = {
        # The decorator injects this catch-all into every view.
        PermissionDenied.__mro__[1]: ERROR_PERMISSION_DENIED,  # PermissionException
        # The api_exception_registry injects this globally (see core/apps.py).
        RoleProhibitedError: ERROR_ROLE_PROHIBITED,
    }

    role_status, role_error, _ = apply_exception_mapping(mapping, RoleProhibitedError())
    generic_status, generic_error, _ = apply_exception_mapping(
        mapping, PermissionDenied()
    )

    assert role_status == HTTP_403_FORBIDDEN
    assert role_error == "ERROR_ROLE_PROHIBITED"
    assert generic_status == HTTP_401_UNAUTHORIZED
    assert generic_error == "PERMISSION_DENIED"


# ---------------------------------------------------------------------------
# QA gap-fill (bmad-qa-generate-e2e-tests): Task 7 names "create field, update row,
# create view" at the REST layer plus a read endpoint (list rows / read row). The
# original file only exercised create_field + list_fields; the rows and views
# mutation/read endpoints are added below so every AC#1/#2 REST surface is covered.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_create_row_denied_403_for_read_scoped_roles(api_client, data_fixture, role):
    member, jwt, table = _member(data_fixture, role)
    data_fixture.create_text_field(table=table, name="Name")

    response = api_client.post(
        reverse("api:database:rows:list", kwargs={"table_id": table.id}),
        {},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json()["error"] == "ERROR_ROLE_PROHIBITED"


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_update_row_denied_403_for_read_scoped_roles(api_client, data_fixture, role):
    member, jwt, table = _member(data_fixture, role)
    field = data_fixture.create_text_field(table=table, name="Name")
    # Owner-created row (the read-scoped member must not be able to mutate it).
    row = table.get_model().objects.create()

    response = api_client.patch(
        reverse(
            "api:database:rows:item",
            kwargs={"table_id": table.id, "row_id": row.id},
        ),
        {f"field_{field.id}": "Blocked"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json()["error"] == "ERROR_ROLE_PROHIBITED"


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_create_view_denied_403_for_read_scoped_roles(api_client, data_fixture, role):
    member, jwt, table = _member(data_fixture, role)

    response = api_client.post(
        reverse("api:database:views:list", kwargs={"table_id": table.id}),
        {"name": "Blocked", "type": "grid"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json()["error"] == "ERROR_ROLE_PROHIBITED"


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_list_rows_read_succeeds_for_read_scoped_roles(api_client, data_fixture, role):
    """AC#1/#2: read Rows over REST still succeeds for Viewer/Commenter."""

    member, jwt, table = _member(data_fixture, role)
    data_fixture.create_text_field(table=table, name="Name")

    response = api_client.get(
        reverse("api:database:rows:list", kwargs={"table_id": table.id}),
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_read_single_row_succeeds_for_read_scoped_roles(api_client, data_fixture, role):
    """AC#1/#2: reading an individual row over REST still succeeds."""

    member, jwt, table = _member(data_fixture, role)
    data_fixture.create_text_field(table=table, name="Name")
    row = table.get_model().objects.create()

    response = api_client.get(
        reverse(
            "api:database:rows:item",
            kwargs={"table_id": table.id, "row_id": row.id},
        ),
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK


@pytest.mark.django_db
def test_create_view_allowed_for_editor(api_client, data_fixture):
    member, jwt, table = _member(data_fixture, EDITOR)

    response = api_client.post(
        reverse("api:database:views:list", kwargs={"table_id": table.id}),
        {"name": "Allowed", "type": "grid"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    # Editor (former MEMBER) is not role-denied; the view is created.
    assert response.status_code == HTTP_200_OK
    assert response.json()["name"] == "Allowed"


@pytest.mark.django_db
def test_create_row_allowed_for_editor(api_client, data_fixture):
    member, jwt, table = _member(data_fixture, EDITOR)
    data_fixture.create_text_field(table=table, name="Name")

    response = api_client.post(
        reverse("api:database:rows:list", kwargs={"table_id": table.id}),
        {},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    # Editor is not role-denied; the row is created.
    assert response.status_code == HTTP_200_OK


# ---------------------------------------------------------------------------
# Review gap-fill (Story 1.3 senior review): AC#1/#2 say "create/edit/delete a
# Row/Field/View". The create + update_row surfaces were covered above; the
# edit/delete surfaces for Field and View and the delete surface for Row are added
# here so every enumerated mutating verb is asserted at the REST 403 layer (not only
# at the manager/handler level).
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_delete_row_denied_403_for_read_scoped_roles(api_client, data_fixture, role):
    member, jwt, table = _member(data_fixture, role)
    data_fixture.create_text_field(table=table, name="Name")
    row = table.get_model().objects.create()

    response = api_client.delete(
        reverse(
            "api:database:rows:item",
            kwargs={"table_id": table.id, "row_id": row.id},
        ),
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json()["error"] == "ERROR_ROLE_PROHIBITED"


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_update_field_denied_403_for_read_scoped_roles(api_client, data_fixture, role):
    member, jwt, table = _member(data_fixture, role)
    field = data_fixture.create_text_field(table=table, name="Name")

    response = api_client.patch(
        reverse("api:database:fields:item", kwargs={"field_id": field.id}),
        {"name": "Renamed"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json()["error"] == "ERROR_ROLE_PROHIBITED"


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_delete_field_denied_403_for_read_scoped_roles(api_client, data_fixture, role):
    member, jwt, table = _member(data_fixture, role)
    field = data_fixture.create_text_field(table=table, name="Name")

    response = api_client.delete(
        reverse("api:database:fields:item", kwargs={"field_id": field.id}),
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json()["error"] == "ERROR_ROLE_PROHIBITED"


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_update_view_denied_403_for_read_scoped_roles(api_client, data_fixture, role):
    member, jwt, table = _member(data_fixture, role)
    view = data_fixture.create_grid_view(table=table, name="Grid")

    response = api_client.patch(
        reverse("api:database:views:item", kwargs={"view_id": view.id}),
        {"name": "Renamed"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json()["error"] == "ERROR_ROLE_PROHIBITED"


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_delete_view_denied_403_for_read_scoped_roles(api_client, data_fixture, role):
    member, jwt, table = _member(data_fixture, role)
    view = data_fixture.create_grid_view(table=table, name="Grid")

    response = api_client.delete(
        reverse("api:database:views:item", kwargs={"view_id": view.id}),
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json()["error"] == "ERROR_ROLE_PROHIBITED"
