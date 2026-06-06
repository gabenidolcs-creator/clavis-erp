from django.test.utils import override_settings

import pytest

from baserow.core.handler import CoreHandler
from baserow.core.operations import (
    ListApplicationsWorkspaceOperationType,
    UpdateWorkspaceOperationType,
)
from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.operations import AssignRoleWorkspaceOperationType
from baserow.core.rbac.permission_manager import RbacPermissionManagerType
from baserow.core.rbac.roles import ADMIN, EDITOR
from baserow.core.types import PermissionCheck

# Mirror the production PERMISSION_MANAGERS relative order for the OSS-registered
# managers (config/settings/base.py): "rbac" sits after "member"/"token", before
# "basic". Enterprise-only managers ("write_field_values", "role") are absent in OSS and
# are intentionally omitted — they are not in the registry under OSS test settings.
RBAC_CHAIN = [
    "core",
    "setting_operation",
    "staff",
    "allow_if_template",
    "member",
    "token",
    "rbac",
    "basic",
]


@pytest.mark.django_db
@override_settings(PERMISSION_MANAGERS=RBAC_CHAIN)
def test_admin_retains_admin_only_capability(data_fixture):
    user_workspace = data_fixture.create_user_workspace(permissions="ADMIN")
    user = user_workspace.user
    workspace = user_workspace.workspace
    RbacHandler().assign_role(user, workspace, ADMIN)

    assert CoreHandler().check_permissions(
        user,
        UpdateWorkspaceOperationType.type,
        workspace=workspace,
        context=workspace,
    )


@pytest.mark.django_db
@override_settings(PERMISSION_MANAGERS=RBAC_CHAIN)
def test_editor_retains_member_capability(data_fixture):
    user_workspace = data_fixture.create_user_workspace(permissions="MEMBER")
    user = user_workspace.user
    workspace = user_workspace.workspace
    RbacHandler().assign_role(user, workspace, EDITOR)

    # Non-admin op still allowed (rbac defers, basic grants the member).
    assert CoreHandler().check_permissions(
        user,
        ListApplicationsWorkspaceOperationType.type,
        workspace=workspace,
        context=workspace,
    )


@pytest.mark.django_db
@override_settings(PERMISSION_MANAGERS=RBAC_CHAIN)
def test_editor_does_not_gain_admin_capability(data_fixture):
    """Editor must NOT escalate: the rbac manager defers admin-only ops for non-Admin
    roles, so the legacy basic manager (MEMBER) denies — preserving today's behavior."""

    user_workspace = data_fixture.create_user_workspace(permissions="MEMBER")
    user = user_workspace.user
    workspace = user_workspace.workspace
    RbacHandler().assign_role(user, workspace, EDITOR)

    assert (
        CoreHandler().check_permissions(
            user,
            UpdateWorkspaceOperationType.type,
            workspace=workspace,
            context=workspace,
            raise_permission_exceptions=False,
        )
        is False
    )


@pytest.mark.django_db
@override_settings(PERMISSION_MANAGERS=RBAC_CHAIN)
def test_legacy_admin_without_assignment_preserved(data_fixture):
    """A user with no RoleAssignment (role None) — rbac defers entirely and the legacy
    ADMIN string still authorizes admin-only ops."""

    user_workspace = data_fixture.create_user_workspace(permissions="ADMIN")

    assert CoreHandler().check_permissions(
        user_workspace.user,
        UpdateWorkspaceOperationType.type,
        workspace=user_workspace.workspace,
        context=user_workspace.workspace,
    )


@pytest.mark.django_db
@override_settings(PERMISSION_MANAGERS=RBAC_CHAIN)
def test_managed_operation_granted_to_admin(data_fixture):
    user_workspace = data_fixture.create_user_workspace(permissions="ADMIN")
    user = user_workspace.user
    workspace = user_workspace.workspace
    RbacHandler().assign_role(user, workspace, ADMIN)

    assert CoreHandler().check_permissions(
        user,
        AssignRoleWorkspaceOperationType.type,
        workspace=workspace,
        context=workspace,
    )


@pytest.mark.django_db
def test_manager_defers_when_no_assignment(data_fixture):
    """Directly: with no RoleAssignment the manager returns an empty result (defers on
    every check) so the chain decides."""

    user_workspace = data_fixture.create_user_workspace(permissions="MEMBER")
    user = user_workspace.user
    workspace = user_workspace.workspace

    manager = RbacPermissionManagerType()
    checks = [
        PermissionCheck(user, UpdateWorkspaceOperationType.type, workspace),
        PermissionCheck(user, ListApplicationsWorkspaceOperationType.type, workspace),
    ]

    result = manager.check_multiple_permissions(checks, workspace=workspace)

    assert result == {}


@pytest.mark.django_db
def test_manager_grants_only_admin_only_ops_to_admin(data_fixture):
    """Directly: Admin role grants admin-only ops (True) and defers non-admin ops."""

    user_workspace = data_fixture.create_user_workspace(permissions="ADMIN")
    user = user_workspace.user
    workspace = user_workspace.workspace
    RbacHandler().assign_role(user, workspace, ADMIN)

    manager = RbacPermissionManagerType()
    admin_check = PermissionCheck(user, UpdateWorkspaceOperationType.type, workspace)
    member_check = PermissionCheck(
        user, ListApplicationsWorkspaceOperationType.type, workspace
    )

    result = manager.check_multiple_permissions(
        [admin_check, member_check], workspace=workspace
    )

    assert result.get(admin_check) is True
    # Non-admin-only op is deferred (not present in the result), never denied.
    assert member_check not in result


@pytest.mark.django_db
def test_manager_batch_loads_assignments_no_n_plus_1(
    data_fixture, django_assert_num_queries
):
    """Many checks for the same actor must resolve in a single assignment query — the
    manager prefetches the role index instead of querying per check (N+1 guard)."""

    user_workspace = data_fixture.create_user_workspace(permissions="ADMIN")
    user = user_workspace.user
    workspace = user_workspace.workspace
    RbacHandler().assign_role(user, workspace, ADMIN)

    manager = RbacPermissionManagerType()
    checks = [
        PermissionCheck(user, UpdateWorkspaceOperationType.type, workspace)
        for _ in range(10)
    ] + [
        PermissionCheck(user, ListApplicationsWorkspaceOperationType.type, workspace)
        for _ in range(10)
    ]

    with django_assert_num_queries(1):
        manager.check_multiple_permissions(checks, workspace=workspace)
