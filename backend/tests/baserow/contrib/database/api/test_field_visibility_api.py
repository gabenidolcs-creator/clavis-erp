"""Story 1.5 — every-surface read-redaction + inference-oracle guard + cache /
live-session invalidation, asserted end-to-end.

A field with ``readable_by_role=ADMIN`` is hidden from a below-threshold member across
REST row list/get (including a client ``include=`` that explicitly names it), search
(no hit-count inference oracle), and is rejected when that member tries to filter/sort
on it (HTTP 403 ``ERROR_FIELD_VISIBILITY_PROHIBITED``). An Admin sees and may
filter/sort on everything. A workspace with zero read rules behaves exactly as pre-1.5
(no regression), and the redaction comes from the one central
``FieldPermissionHandler.get_hidden_field_ids`` helper (single path / NFR-4).
"""

from unittest.mock import patch

from django.urls import reverse

import pytest
from rest_framework.status import HTTP_200_OK

from baserow.contrib.database.fields.field_permission_handler import (
    FieldPermissionHandler,
)
from baserow.contrib.database.fields.models import FieldPermission
from baserow.contrib.database.views.handler import ViewHandler
from baserow.core.exceptions import FieldVisibilityProhibitedError
from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.roles import ADMIN, EDITOR


def _scenario(data_fixture, member_role=EDITOR, hidden_role=ADMIN):
    """Owner (Admin) + a member; a table with a hidden field ``Salary`` (read
    threshold ``hidden_role``) and a visible field ``Notes``; one row."""

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
    hidden = data_fixture.create_text_field(table=table, name="Salary")
    visible = data_fixture.create_text_field(table=table, name="Notes")
    grid = data_fixture.create_grid_view(table=table)
    (row,) = data_fixture.create_rows(
        fields=[hidden, visible], rows=[["100000", "hello world"]]
    )
    if hidden_role is not None:
        FieldPermission.objects.create(field=hidden, readable_by_role=hidden_role)
    return {
        "owner": owner,
        "member": member,
        "workspace": workspace,
        "table": table,
        "hidden": hidden,
        "visible": visible,
        "grid": grid,
        "row": row,
    }


# --- AC #1: REST row read redaction -----------------------------------------


@pytest.mark.django_db
def test_row_list_omits_hidden_field_for_below_threshold(api_client, data_fixture):
    s = _scenario(data_fixture)
    jwt = data_fixture.generate_token(s["member"])

    response = api_client.get(
        reverse("api:database:rows:list", kwargs={"table_id": s["table"].id}),
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK
    row = response.json()["results"][0]
    assert f"field_{s['hidden'].id}" not in row
    assert f"field_{s['visible'].id}" in row


@pytest.mark.django_db
def test_row_list_returns_hidden_field_for_admin(api_client, data_fixture):
    s = _scenario(data_fixture)
    jwt = data_fixture.generate_token(s["owner"])

    response = api_client.get(
        reverse("api:database:rows:list", kwargs={"table_id": s["table"].id}),
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK
    row = response.json()["results"][0]
    assert f"field_{s['hidden'].id}" in row


@pytest.mark.django_db
def test_single_row_get_omits_hidden_field(api_client, data_fixture):
    s = _scenario(data_fixture)
    jwt = data_fixture.generate_token(s["member"])

    response = api_client.get(
        reverse(
            "api:database:rows:item",
            kwargs={"table_id": s["table"].id, "row_id": s["row"].id},
        ),
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK
    assert f"field_{s['hidden'].id}" not in response.json()


@pytest.mark.django_db
def test_redaction_beats_explicit_include(api_client, data_fixture):
    """The #1 silent-failure mode: a client that explicitly names the hidden field via
    ``include=`` must still NOT receive it — the permission boundary overrides client
    field-selection (AC #1)."""

    s = _scenario(data_fixture)
    jwt = data_fixture.generate_token(s["member"])

    response = api_client.get(
        reverse("api:database:rows:list", kwargs={"table_id": s["table"].id})
        + f"?include=field_{s['hidden'].id}",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK
    row = response.json()["results"][0]
    assert f"field_{s['hidden'].id}" not in row


@pytest.mark.django_db
def test_grid_view_omits_hidden_field_for_below_threshold(api_client, data_fixture):
    """Grid view list endpoint must redact hidden fields for below-threshold members
    (AC #1 — view-based surface parity with the generic rows endpoint)."""

    s = _scenario(data_fixture)
    jwt = data_fixture.generate_token(s["member"])

    response = api_client.get(
        reverse("api:database:views:grid:list", kwargs={"view_id": s["grid"].id}),
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK
    row = response.json()["results"][0]
    assert f"field_{s['hidden'].id}" not in row
    assert f"field_{s['visible'].id}" in row


@pytest.mark.django_db
def test_gallery_view_omits_hidden_field_for_below_threshold(api_client, data_fixture):
    """Gallery view list endpoint must redact hidden fields for below-threshold members
    (AC #1 — gallery surface parity)."""

    s = _scenario(data_fixture)
    gallery = data_fixture.create_gallery_view(table=s["table"])
    jwt = data_fixture.generate_token(s["member"])

    response = api_client.get(
        reverse(
            "api:database:views:gallery:list", kwargs={"view_id": gallery.id}
        ),
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK
    row = response.json()["results"][0]
    assert f"field_{s['hidden'].id}" not in row
    assert f"field_{s['visible'].id}" in row


# --- AC #1: search is not an inference oracle --------------------------------


@pytest.mark.django_db
def test_search_on_hidden_value_returns_no_hit_for_member(api_client, data_fixture):
    """A value living ONLY in the hidden field must not produce a hit for a
    below-threshold member — otherwise hit/no-hit leaks the value's existence."""

    s = _scenario(data_fixture)
    jwt = data_fixture.generate_token(s["member"])

    response = api_client.get(
        reverse("api:database:rows:list", kwargs={"table_id": s["table"].id})
        + "?search=100000",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK
    assert response.json()["count"] == 0


@pytest.mark.django_db
def test_search_on_hidden_value_returns_hit_for_admin(api_client, data_fixture):
    s = _scenario(data_fixture)
    jwt = data_fixture.generate_token(s["owner"])

    response = api_client.get(
        reverse("api:database:rows:list", kwargs={"table_id": s["table"].id})
        + "?search=100000",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK
    assert response.json()["count"] == 1


@pytest.mark.django_db
def test_search_on_visible_value_still_hits_for_member(api_client, data_fixture):
    """Redaction must not over-block: a visible field is still searchable."""

    s = _scenario(data_fixture)
    jwt = data_fixture.generate_token(s["member"])

    response = api_client.get(
        reverse("api:database:rows:list", kwargs={"table_id": s["table"].id})
        + "?search=hello",
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )

    assert response.status_code == HTTP_200_OK
    assert response.json()["count"] == 1


# --- AC #2: inference-oracle guard (filter / sort) ---------------------------


@pytest.mark.django_db
def test_member_cannot_create_filter_on_hidden_field(data_fixture):
    s = _scenario(data_fixture)

    with pytest.raises(FieldVisibilityProhibitedError):
        ViewHandler().create_filter(
            s["member"], s["grid"], s["hidden"], "equal", "100000"
        )


@pytest.mark.django_db
def test_member_cannot_create_sort_on_hidden_field(data_fixture):
    s = _scenario(data_fixture)

    with pytest.raises(FieldVisibilityProhibitedError):
        ViewHandler().create_sort(s["member"], s["grid"], s["hidden"], "ASC")


@pytest.mark.django_db
def test_member_cannot_update_filter_to_hidden_field(data_fixture):
    s = _scenario(data_fixture)
    # Start from a filter on the visible field (allowed), then try to repoint it.
    view_filter = ViewHandler().create_filter(
        s["owner"], s["grid"], s["visible"], "equal", "hello world"
    )

    with pytest.raises(FieldVisibilityProhibitedError):
        ViewHandler().update_filter(s["member"], view_filter, field=s["hidden"])


@pytest.mark.django_db
def test_member_cannot_update_sort_to_hidden_field(data_fixture):
    """Repointing an existing sort to a hidden field must also be blocked (AC #2 —
    update_sort parity with update_filter)."""

    s = _scenario(data_fixture)
    view_sort = ViewHandler().create_sort(s["owner"], s["grid"], s["visible"], "ASC")

    with pytest.raises(FieldVisibilityProhibitedError):
        ViewHandler().update_sort(s["member"], view_sort, field=s["hidden"])


@pytest.mark.django_db
def test_admin_can_filter_and_sort_on_hidden_field(data_fixture):
    s = _scenario(data_fixture)

    view_filter = ViewHandler().create_filter(
        s["owner"], s["grid"], s["hidden"], "equal", "100000"
    )
    view_sort = ViewHandler().create_sort(s["owner"], s["grid"], s["hidden"], "ASC")

    assert view_filter.field_id == s["hidden"].id
    assert view_sort.field_id == s["hidden"].id


@pytest.mark.django_db
def test_member_can_filter_on_visible_field(data_fixture):
    """The guard must not over-block: a non-hidden field filters fine for a member."""

    s = _scenario(data_fixture)

    view_filter = ViewHandler().create_filter(
        s["member"], s["grid"], s["visible"], "equal", "hello world"
    )

    assert view_filter.field_id == s["visible"].id


# --- AC #3: cache + live-session invalidation on change ----------------------


@pytest.mark.django_db
def test_set_read_threshold_invalidates_model_cache(data_fixture):
    s = _scenario(data_fixture, hidden_role=None)

    with patch(
        "baserow.contrib.database.table.cache.invalidate_table_in_model_cache"
    ) as mock_invalidate:
        FieldPermissionHandler.set_field_permission(
            s["owner"], s["hidden"], readable_by_role=ADMIN
        )

    mock_invalidate.assert_called_once_with(s["table"].id)


@pytest.mark.django_db
def test_set_read_threshold_redacts_same_session_without_reconnect(
    api_client, data_fixture
):
    """A previously-visible field stops being returned to the same member after the
    threshold is set — no reconnect / new token (AC #3)."""

    s = _scenario(data_fixture, hidden_role=None)
    jwt = data_fixture.generate_token(s["member"])
    url = reverse("api:database:rows:list", kwargs={"table_id": s["table"].id})

    before = api_client.get(url, HTTP_AUTHORIZATION=f"JWT {jwt}")
    assert f"field_{s['hidden'].id}" in before.json()["results"][0]

    FieldPermissionHandler.set_field_permission(
        s["owner"], s["hidden"], readable_by_role=ADMIN
    )

    after = api_client.get(url, HTTP_AUTHORIZATION=f"JWT {jwt}")
    assert f"field_{s['hidden'].id}" not in after.json()["results"][0]


# --- NFR-4 single path + no-regression --------------------------------------


@pytest.mark.django_db
def test_central_redactor_is_the_single_hiding_source(data_fixture):
    """The helper every surface consumes returns exactly the hidden ids; an Admin sees
    nothing hidden. This is THE redactor — surfaces union its output, none hides ad hoc."""

    s = _scenario(data_fixture)

    member_hidden = FieldPermissionHandler.get_hidden_field_ids(
        s["member"], s["table"]
    )
    admin_hidden = FieldPermissionHandler.get_hidden_field_ids(s["owner"], s["table"])

    assert member_hidden == {s["hidden"].id}
    assert admin_hidden == set()


@pytest.mark.django_db
def test_no_read_rules_no_redaction_anywhere(api_client, data_fixture):
    """Zero ``readable_by_role`` rows → behaves exactly as pre-1.5: every field returned,
    helper returns an empty set, and filtering on any field is allowed."""

    s = _scenario(data_fixture, hidden_role=None)
    jwt = data_fixture.generate_token(s["member"])

    response = api_client.get(
        reverse("api:database:rows:list", kwargs={"table_id": s["table"].id}),
        HTTP_AUTHORIZATION=f"JWT {jwt}",
    )
    row = response.json()["results"][0]
    assert f"field_{s['hidden'].id}" in row
    assert f"field_{s['visible'].id}" in row

    assert FieldPermissionHandler.get_hidden_field_ids(s["member"], s["table"]) == set()

    # Filtering on the (now-unrestricted) field is allowed for the member.
    view_filter = ViewHandler().create_filter(
        s["member"], s["grid"], s["hidden"], "equal", "100000"
    )
    assert view_filter.field_id == s["hidden"].id


# --- AC #3: WebSocket broadcast redaction ------------------------------------


@pytest.mark.django_db
def test_ws_broadcast_excludes_hidden_field_ids(data_fixture):
    """_visibility_restricted_field_ids returns restricted field IDs for WS broadcast
    redaction, and None (fast path) when no rules exist (AC #3 / NFR-4)."""

    from baserow.contrib.database.ws.rows.signals import (
        _visibility_restricted_field_ids,
    )

    s = _scenario(data_fixture)

    restricted = _visibility_restricted_field_ids(s["table"])
    assert restricted == [s["hidden"].id]

    FieldPermission.objects.filter(field=s["hidden"]).delete()
    restricted_after = _visibility_restricted_field_ids(s["table"])
    assert restricted_after is None


# --- AC #2: inference-oracle guard — group-by surface (M1 review fix) --------


@pytest.mark.django_db
def test_member_cannot_create_group_by_on_hidden_field(data_fixture):
    """create_group_by on a hidden field must be blocked — same guard as create_sort/
    create_filter (AC #2 parity for the group-by surface)."""

    s = _scenario(data_fixture)

    with pytest.raises(FieldVisibilityProhibitedError):
        ViewHandler().create_group_by(s["member"], s["grid"], s["hidden"], "ASC", 100)


@pytest.mark.django_db
def test_member_cannot_update_group_by_to_hidden_field(data_fixture):
    """Repointing an existing group-by to a hidden field must also be blocked (AC #2)."""

    s = _scenario(data_fixture)
    view_group_by = ViewHandler().create_group_by(
        s["owner"], s["grid"], s["visible"], "ASC", 100
    )

    with pytest.raises(FieldVisibilityProhibitedError):
        ViewHandler().update_group_by(s["member"], view_group_by, field=s["hidden"])


@pytest.mark.django_db
def test_admin_can_group_by_on_hidden_field(data_fixture):
    """Admin at/above threshold must not be blocked by the group-by guard."""

    s = _scenario(data_fixture)

    view_group_by = ViewHandler().create_group_by(
        s["owner"], s["grid"], s["hidden"], "ASC", 100
    )
    assert view_group_by.field_id == s["hidden"].id
