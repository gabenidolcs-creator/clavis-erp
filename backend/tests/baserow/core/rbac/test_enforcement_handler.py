"""Story 1.3 — handler-level enforcement with real Row/Field/View contexts.

Exercises the full `CoreHandler().check_permissions(...)` path through the production
`PERMISSION_MANAGERS` chain (rbac sits between member and basic), with real model
contexts so `_ensure_context_matches_operation` passes. Verifies that Viewer/Commenter
mutations raise `RoleProhibitedError` while reads still succeed.
"""

import pytest

from baserow.core.exceptions import RoleProhibitedError
from baserow.core.handler import CoreHandler
from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.roles import ADMIN, COMMENTER, EDITOR, VIEWER


def _member_with_role(data_fixture, role):
    """Create an admin owner + a separate MEMBER user assigned ``role`` in the same
    workspace, plus a database/table/field/view owned by the admin."""

    owner = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=owner)
    member = data_fixture.create_user()
    data_fixture.create_user_workspace(
        workspace=workspace, user=member, permissions="MEMBER"
    )
    RbacHandler().assign_role(member, workspace, role)

    database = data_fixture.create_database_application(user=owner, workspace=workspace)
    table = data_fixture.create_database_table(user=owner, database=database)
    field = data_fixture.create_text_field(user=owner, table=table)
    view = data_fixture.create_grid_view(user=owner, table=table)
    return member, workspace, table, field, view


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_role_denied_field_create(data_fixture, role):
    member, workspace, table, field, view = _member_with_role(data_fixture, role)

    with pytest.raises(RoleProhibitedError):
        CoreHandler().check_permissions(
            member,
            "database.table.create_field",
            workspace=workspace,
            context=table,
        )


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_role_denied_field_update(data_fixture, role):
    member, workspace, table, field, view = _member_with_role(data_fixture, role)

    with pytest.raises(RoleProhibitedError):
        CoreHandler().check_permissions(
            member,
            "database.table.field.update",
            workspace=workspace,
            context=field,
        )


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_role_denied_view_create_and_update(data_fixture, role):
    member, workspace, table, field, view = _member_with_role(data_fixture, role)

    with pytest.raises(RoleProhibitedError):
        CoreHandler().check_permissions(
            member, "database.table.create_view", workspace=workspace, context=table
        )
    with pytest.raises(RoleProhibitedError):
        CoreHandler().check_permissions(
            member, "database.table.view.update", workspace=workspace, context=view
        )


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_role_denied_row_create(data_fixture, role):
    member, workspace, table, field, view = _member_with_role(data_fixture, role)

    with pytest.raises(RoleProhibitedError):
        CoreHandler().check_permissions(
            member, "database.table.create_row", workspace=workspace, context=table
        )


@pytest.mark.django_db
@pytest.mark.parametrize("role", [VIEWER, COMMENTER])
def test_reads_still_succeed(data_fixture, role):
    """Read access (the other half of both ACs) must be preserved — the manager defers
    and the legacy basic manager grants the underlying MEMBER."""

    member, workspace, table, field, view = _member_with_role(data_fixture, role)

    assert CoreHandler().check_permissions(
        member, "database.table.list_fields", workspace=workspace, context=table
    )
    assert CoreHandler().check_permissions(
        member, "database.table.list_views", workspace=workspace, context=table
    )


@pytest.mark.django_db
def test_commenter_create_comment_allowed_viewer_denied(data_fixture):
    """Comment policy resolved at the handler level (no comment endpoint in free core)."""

    commenter, c_ws, c_table, _, c_view = _member_with_role(data_fixture, COMMENTER)
    viewer, v_ws, v_table, _, v_view = _member_with_role(data_fixture, VIEWER)

    # Commenter: defers → basic grants the MEMBER → allowed.
    assert CoreHandler().check_permissions(
        commenter,
        "database.table.view.create_comment",
        workspace=c_ws,
        context=c_view,
    )
    # Viewer: prohibited.
    with pytest.raises(RoleProhibitedError):
        CoreHandler().check_permissions(
            viewer,
            "database.table.view.create_comment",
            workspace=v_ws,
            context=v_view,
        )


@pytest.mark.django_db
@pytest.mark.parametrize("role", [EDITOR, ADMIN])
def test_editor_and_admin_can_mutate(data_fixture, role):
    """No regression: Editor (former MEMBER) and Admin keep write capability."""

    member, workspace, table, field, view = _member_with_role(data_fixture, role)

    assert CoreHandler().check_permissions(
        member, "database.table.create_field", workspace=workspace, context=table
    )
    assert CoreHandler().check_permissions(
        member, "database.table.create_view", workspace=workspace, context=table
    )
