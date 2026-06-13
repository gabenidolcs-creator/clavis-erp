"""Story 6.3 — INTERFACE_ONLY role enforcement tests.

Covers:
- Database op denial (prefix-based)
- Page-grant allow/deny for builder ops
- Cascade deletes on page/workspace delete
- Handler CRUD for page grants
"""

import pytest

from baserow.core.exceptions import RoleProhibitedError
from baserow.core.rbac.enforcement import INTERFACE_ONLY_DENIED_DATABASE_OPS
from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.models import InterfaceCollaboratorPageGrant
from baserow.core.rbac.permission_manager import RbacPermissionManagerType
from baserow.core.rbac.roles import INTERFACE_ONLY


def _setup_interface_user(data_fixture):
    """Create owner + interface-only member in same workspace, plus a builder page."""
    owner = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=owner)
    member = data_fixture.create_user()
    data_fixture.create_user_workspace(
        workspace=workspace, user=member, permissions="MEMBER"
    )
    RbacHandler().assign_role(member, workspace, INTERFACE_ONLY)
    builder = data_fixture.create_builder_application(user=owner, workspace=workspace)
    page = data_fixture.create_builder_page(user=owner, builder=builder)
    return owner, member, workspace, builder, page


@pytest.mark.django_db
def test_interface_only_denied_database_op(data_fixture):
    """Any database.* operation returns RoleProhibitedError for interface-only user."""
    _, member, workspace, _, _ = _setup_interface_user(data_fixture)

    manager = RbacPermissionManagerType()
    from baserow.core.registries import PermissionCheck

    checks = [
        PermissionCheck(member, "database.table.list_rows", None),
        PermissionCheck(member, "database.table.create_row", None),
        PermissionCheck(member, "database.read", None),
        PermissionCheck(member, "database.table.list_fields", None),
    ]
    results = manager.check_multiple_permissions(checks, workspace=workspace)
    for check in checks:
        assert isinstance(results.get(check), RoleProhibitedError), (
            f"Expected RoleProhibitedError for {check.operation_name}"
        )


@pytest.mark.django_db
def test_interface_only_denied_all_ops_in_frozenset(data_fixture):
    """Every op in INTERFACE_ONLY_DENIED_DATABASE_OPS is denied."""
    _, member, workspace, _, _ = _setup_interface_user(data_fixture)

    manager = RbacPermissionManagerType()
    from baserow.core.registries import PermissionCheck

    checks = [
        PermissionCheck(member, op, None)
        for op in INTERFACE_ONLY_DENIED_DATABASE_OPS
    ]
    results = manager.check_multiple_permissions(checks, workspace=workspace)
    for check in checks:
        result = results.get(check)
        assert isinstance(result, RoleProhibitedError), (
            f"Expected denial for op {check.operation_name}, got {result!r}"
        )


@pytest.mark.django_db
def test_interface_only_allowed_on_granted_page(data_fixture):
    """Interface-only user with a page grant is allowed builder ops on that page."""
    owner, member, workspace, _, page = _setup_interface_user(data_fixture)

    RbacHandler().grant_page_access(member, workspace, page)

    manager = RbacPermissionManagerType()
    from baserow.core.registries import PermissionCheck

    check = PermissionCheck(member, "builder.page.read", page)
    results = manager.check_multiple_permissions([check], workspace=workspace)
    assert results.get(check) is True


@pytest.mark.django_db
def test_interface_only_denied_on_non_granted_page(data_fixture):
    """Interface-only user WITHOUT a page grant is denied builder ops on that page."""
    _, member, workspace, builder, page = _setup_interface_user(data_fixture)

    manager = RbacPermissionManagerType()
    from baserow.core.registries import PermissionCheck

    check = PermissionCheck(member, "builder.page.read", page)
    results = manager.check_multiple_permissions([check], workspace=workspace)
    assert isinstance(results.get(check), RoleProhibitedError)


@pytest.mark.django_db
def test_interface_only_denied_workspace_level_ops(data_fixture):
    """Interface-only user is denied workspace-level ops (no page context)."""
    _, member, workspace, _, _ = _setup_interface_user(data_fixture)

    manager = RbacPermissionManagerType()
    from baserow.core.registries import PermissionCheck

    check = PermissionCheck(member, "builder.page.list", None)
    results = manager.check_multiple_permissions([check], workspace=workspace)
    assert isinstance(results.get(check), RoleProhibitedError)


@pytest.mark.django_db
def test_grant_page_access_idempotent(data_fixture):
    """Calling grant_page_access twice creates exactly one DB row."""
    owner, member, workspace, _, page = _setup_interface_user(data_fixture)

    RbacHandler().grant_page_access(member, workspace, page)
    RbacHandler().grant_page_access(member, workspace, page)

    count = InterfaceCollaboratorPageGrant.objects.filter(
        user=member, page=page
    ).count()
    assert count == 1


@pytest.mark.django_db
def test_revoke_page_access(data_fixture):
    """Revoking a page grant removes it; subsequent check returns RoleProhibitedError."""
    owner, member, workspace, _, page = _setup_interface_user(data_fixture)

    RbacHandler().grant_page_access(member, workspace, page)
    assert InterfaceCollaboratorPageGrant.objects.filter(user=member, page=page).exists()

    RbacHandler().revoke_page_access(member, page)
    assert not InterfaceCollaboratorPageGrant.objects.filter(
        user=member, page=page
    ).exists()


@pytest.mark.django_db
def test_list_granted_pages(data_fixture):
    """list_granted_pages returns all grants for the user in the workspace."""
    owner, member, workspace, builder, page = _setup_interface_user(data_fixture)
    page2 = data_fixture.create_builder_page(user=owner, builder=builder)

    RbacHandler().grant_page_access(member, workspace, page)
    RbacHandler().grant_page_access(member, workspace, page2)

    grants = RbacHandler().list_granted_pages(member, workspace)
    granted_page_ids = {g.page_id for g in grants}
    assert page.id in granted_page_ids
    assert page2.id in granted_page_ids


@pytest.mark.django_db
def test_cascade_delete_on_page_delete(data_fixture):
    """Deleting a page cascades to InterfaceCollaboratorPageGrant."""
    owner, member, workspace, _, page = _setup_interface_user(data_fixture)
    RbacHandler().grant_page_access(member, workspace, page)

    page_id = page.id
    assert InterfaceCollaboratorPageGrant.objects.filter(page_id=page_id).exists()
    page.delete()
    assert not InterfaceCollaboratorPageGrant.objects.filter(page_id=page_id).exists()


@pytest.mark.django_db
def test_cascade_delete_on_workspace_delete(data_fixture):
    """Deleting the workspace cascades to InterfaceCollaboratorPageGrant."""
    owner, member, workspace, builder, page = _setup_interface_user(data_fixture)
    RbacHandler().grant_page_access(member, workspace, page)

    grant_id = InterfaceCollaboratorPageGrant.objects.get(user=member, page=page).id
    # Must remove child application before workspace (FK constraint).
    builder.delete()
    workspace.delete()
    assert not InterfaceCollaboratorPageGrant.objects.filter(id=grant_id).exists()


@pytest.mark.django_db
def test_get_page_id_from_context_page_object(data_fixture):
    """_get_page_id_from_context returns page.id for a Page object."""
    owner = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=owner)
    builder = data_fixture.create_builder_application(user=owner, workspace=workspace)
    page = data_fixture.create_builder_page(user=owner, builder=builder)

    result = RbacPermissionManagerType._get_page_id_from_context(page)
    assert result == page.id


@pytest.mark.django_db
def test_get_page_id_from_context_none():
    """_get_page_id_from_context returns None for None context."""
    result = RbacPermissionManagerType._get_page_id_from_context(None)
    assert result is None
