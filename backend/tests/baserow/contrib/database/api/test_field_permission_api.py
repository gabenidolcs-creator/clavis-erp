"""Story 1.4 — REST API + handler integration assertions.

A below-threshold member writing a restricted field's value → HTTP 403
(ERROR_FIELD_EDIT_PROHIBITED), distinct from the legacy 401; the field-config update of a
restricted field → 403; writing a non-restricted field → 200; reading the row → 200; an
Admin succeeds on every path. The admin-set-rule endpoint is admin-only (non-admin → 403).
A workspace with zero rules behaves exactly as before (no regression).
"""

from django.urls import reverse

import pytest
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
)

from baserow.api.errors import ERROR_FIELD_EDIT_PROHIBITED, ERROR_PERMISSION_DENIED
from baserow.api.utils import apply_exception_mapping
from baserow.contrib.database.fields.field_permission_handler import (
    FieldPermissionHandler,
)
from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.fields.models import FieldPermission
from baserow.contrib.database.rows.handler import RowHandler
from baserow.core.exceptions import (
    FieldEditProhibitedError,
    PermissionDenied,
)
from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.roles import ADMIN, EDITOR


def _scenario(data_fixture, member_role=EDITOR):
    """Owner (Admin) + a member assigned ``member_role``; a table with two text fields
    and one row. Returns a dict of the actors/objects under test."""

    owner = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=owner)
    RbacHandler().assign_role(owner, workspace, ADMIN)
    member = data_fixture.create_user()
    data_fixture.create_user_workspace(
        workspace=workspace, user=member, permissions="MEMBER"
    )
    RbacHandler().assign_role(member, workspace, member_role)
    database = data_fixture.create_database_application(user=owner, workspace=workspace)
    table = data_fixture.create_database_table(user=owner, database=database)
    restricted = data_fixture.create_text_field(table=table, name="Salary")
    free = data_fixture.create_text_field(table=table, name="Notes")
    (row,) = data_fixture.create_rows(
        fields=[restricted, free], rows=[["100", "hello"]]
    )
    return {
        "owner": owner,
        "member": member,
        "workspace": workspace,
        "table": table,
        "restricted": restricted,
        "free": free,
        "row": row,
    }


@pytest.mark.django_db
def test_row_write_restricted_field_returns_403(api_client, data_fixture):
    s = _scenario(data_fixture)
    FieldPermission.objects.create(field=s["restricted"], editable_by_role=ADMIN)
    jwt = data_fixture.generate_token(s["member"])

    response = api_client.patch(
        reverse(
            "api:database:rows:item",
            kwargs={"table_id": s["table"].id, "row_id": s["row"].id},
        ),
        {f"field_{s['restricted'].id}": "200"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json()["error"] == "ERROR_FIELD_EDIT_PROHIBITED"


@pytest.mark.django_db
def test_row_write_unrestricted_field_succeeds(api_client, data_fixture):
    s = _scenario(data_fixture)
    FieldPermission.objects.create(field=s["restricted"], editable_by_role=ADMIN)
    jwt = data_fixture.generate_token(s["member"])

    response = api_client.patch(
        reverse(
            "api:database:rows:item",
            kwargs={"table_id": s["table"].id, "row_id": s["row"].id},
        ),
        {f"field_{s['free'].id}": "world"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK
    assert response.json()[f"field_{s['free'].id}"] == "world"


@pytest.mark.django_db
def test_row_read_restricted_field_succeeds(api_client, data_fixture):
    s = _scenario(data_fixture)
    FieldPermission.objects.create(field=s["restricted"], editable_by_role=ADMIN)
    jwt = data_fixture.generate_token(s["member"])

    response = api_client.get(
        reverse(
            "api:database:rows:item",
            kwargs={"table_id": s["table"].id, "row_id": s["row"].id},
        ),
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    # Restricted field is still readable — this story restricts edit only.
    assert response.status_code == HTTP_200_OK
    assert response.json()[f"field_{s['restricted'].id}"] == "100"


@pytest.mark.django_db
def test_row_write_restricted_field_admin_succeeds(api_client, data_fixture):
    s = _scenario(data_fixture)
    FieldPermission.objects.create(field=s["restricted"], editable_by_role=ADMIN)
    jwt = data_fixture.generate_token(s["owner"])

    response = api_client.patch(
        reverse(
            "api:database:rows:item",
            kwargs={"table_id": s["table"].id, "row_id": s["row"].id},
        ),
        {f"field_{s['restricted'].id}": "200"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK
    assert response.json()[f"field_{s['restricted'].id}"] == "200"


@pytest.mark.django_db
def test_field_config_update_restricted_returns_403(api_client, data_fixture):
    s = _scenario(data_fixture)
    FieldPermission.objects.create(field=s["restricted"], editable_by_role=ADMIN)
    jwt = data_fixture.generate_token(s["member"])

    response = api_client.patch(
        reverse("api:database:fields:item", kwargs={"field_id": s["restricted"].id}),
        {"name": "Renamed"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json()["error"] == "ERROR_FIELD_EDIT_PROHIBITED"


@pytest.mark.django_db
def test_no_rule_means_no_regression(api_client, data_fixture):
    # Zero FieldPermission rows: an Editor edits exactly as before.
    s = _scenario(data_fixture)
    jwt = data_fixture.generate_token(s["member"])

    response = api_client.patch(
        reverse(
            "api:database:rows:item",
            kwargs={"table_id": s["table"].id, "row_id": s["row"].id},
        ),
        {f"field_{s['restricted'].id}": "200"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK


# --- admin-set-rule endpoint -------------------------------------------------


@pytest.mark.django_db
def test_set_permission_non_admin_returns_403(api_client, data_fixture):
    s = _scenario(data_fixture)
    jwt = data_fixture.generate_token(s["member"])

    response = api_client.patch(
        reverse(
            "api:database:fields:permission",
            kwargs={"field_id": s["restricted"].id},
        ),
        {"editable_by_role": ADMIN},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json()["error"] == "ERROR_FIELD_EDIT_PROHIBITED"


@pytest.mark.django_db
def test_set_permission_admin_persists(api_client, data_fixture):
    s = _scenario(data_fixture)
    jwt = data_fixture.generate_token(s["owner"])
    url = reverse(
        "api:database:fields:permission", kwargs={"field_id": s["restricted"].id}
    )

    response = api_client.patch(
        url,
        {"editable_by_role": EDITOR},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK
    assert response.json()["editable_by_role"] == EDITOR
    # Persists per field & reloads.
    assert FieldPermission.objects.get(field=s["restricted"]).editable_by_role == EDITOR
    get_response = api_client.get(url, HTTP_AUTHORIZATION=f"JWT {jwt}")
    assert get_response.json()["editable_by_role"] == EDITOR


@pytest.mark.django_db
def test_set_permission_null_clears_rule(api_client, data_fixture):
    s = _scenario(data_fixture)
    FieldPermission.objects.create(field=s["restricted"], editable_by_role=ADMIN)
    jwt = data_fixture.generate_token(s["owner"])

    response = api_client.patch(
        reverse(
            "api:database:fields:permission",
            kwargs={"field_id": s["restricted"].id},
        ),
        {"editable_by_role": None},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK
    assert response.json()["editable_by_role"] is None
    assert not FieldPermission.objects.filter(field=s["restricted"]).exists()


# --- handler integration -----------------------------------------------------


@pytest.mark.django_db
def test_handler_set_permission_admin_only(data_fixture):
    s = _scenario(data_fixture)

    with pytest.raises(FieldEditProhibitedError):
        FieldPermissionHandler.set_field_permission(s["member"], s["restricted"], ADMIN)

    FieldPermissionHandler.set_field_permission(s["owner"], s["restricted"], ADMIN)
    assert (
        FieldPermissionHandler.get_field_permission(s["restricted"]).editable_by_role
        == ADMIN
    )


# --- QA gap-fill (bmad-qa-generate-e2e-tests) --------------------------------
# Task 4/7 name two assertions that had no test: (1) the legacy generic 401 catch-all is
# NOT regressed to 403 by the global FieldEditProhibitedError mapping (MRO precedence),
# and (2) the row/field HANDLER layer (not only REST) enforces the rule.


def test_exception_mapping_field_edit_prohibited_wins_over_catch_all():
    """MRO precedence: with the global mapping in place, ``FieldEditProhibitedError``
    resolves to 403 while the generic ``PermissionException`` catch-all stays 401 (no
    regression). Mirrors Story 1.3's ``RoleProhibitedError`` proof."""

    mapping = {
        # The decorator injects this catch-all into every view.
        PermissionDenied.__mro__[1]: ERROR_PERMISSION_DENIED,  # PermissionException
        # core/apps.py registers this globally via api_exception_registry.
        FieldEditProhibitedError: ERROR_FIELD_EDIT_PROHIBITED,
    }

    field_status, field_error, _ = apply_exception_mapping(
        mapping, FieldEditProhibitedError()
    )
    generic_status, generic_error, _ = apply_exception_mapping(
        mapping, PermissionDenied()
    )

    assert field_status == HTTP_403_FORBIDDEN
    assert field_error == "ERROR_FIELD_EDIT_PROHIBITED"
    # The legacy 401 catch-all is intact — the new subclass did not hijack it.
    assert generic_status == HTTP_401_UNAUTHORIZED
    assert generic_error == "PERMISSION_DENIED"


@pytest.mark.django_db
def test_handler_row_update_restricted_field_raises(data_fixture):
    """Handler layer (``RowHandler.update_rows``) — a below-threshold Editor writing a
    restricted field raises ``FieldEditProhibitedError``; writing a non-restricted field
    in the same row succeeds; reading is unaffected."""

    s = _scenario(data_fixture)
    FieldPermission.objects.create(field=s["restricted"], editable_by_role=ADMIN)
    handler = RowHandler()

    with pytest.raises(FieldEditProhibitedError):
        handler.update_rows(
            s["member"],
            s["table"],
            [{"id": s["row"].id, f"field_{s['restricted'].id}": "200"}],
        )

    # A non-restricted field in the same table still updates for the same member.
    handler.update_rows(
        s["member"],
        s["table"],
        [{"id": s["row"].id, f"field_{s['free'].id}": "world"}],
    )
    s["row"].refresh_from_db()
    assert getattr(s["row"], f"field_{s['free'].id}") == "world"


@pytest.mark.django_db
def test_handler_update_field_restricted_config_raises(data_fixture):
    """Handler layer (``FieldHandler.update_field``) — an Editor updating a restricted
    field's config raises; an Admin succeeds. The single-check path re-raises the
    manager exception, so this 403s without a handler-local check."""

    s = _scenario(data_fixture)
    FieldPermission.objects.create(field=s["restricted"], editable_by_role=ADMIN)
    handler = FieldHandler()

    with pytest.raises(FieldEditProhibitedError):
        handler.update_field(s["member"], s["restricted"], name="Renamed")

    updated = handler.update_field(s["owner"], s["restricted"], name="Renamed")
    assert updated.name == "Renamed"
