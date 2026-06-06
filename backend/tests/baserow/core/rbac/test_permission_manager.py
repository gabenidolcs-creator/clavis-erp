from django.test.utils import override_settings

import pytest

from baserow.core.exceptions import RoleProhibitedError
from baserow.core.handler import CoreHandler
from baserow.core.operations import (
    ListApplicationsWorkspaceOperationType,
    UpdateWorkspaceOperationType,
)
from baserow.core.rbac.enforcement import (
    COMMENTER_DENIED_OPS,
    CREATE_COMMENT_OPERATION,
    VIEWER_DENIED_OPS,
)
from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.operations import AssignRoleWorkspaceOperationType
from baserow.core.rbac.permission_manager import RbacPermissionManagerType
from baserow.core.rbac.roles import ADMIN, COMMENTER, EDITOR, VIEWER
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


# ---------------------------------------------------------------------------
# Story 1.3 — deny side for Viewer / Commenter (manager-level unit tests).
# ---------------------------------------------------------------------------

# A representative read/subscribe op that MUST keep deferring for both read-scoped tiers
# (asserting the manager does not flip to deny-by-default).
READ_AND_SUBSCRIBE_OPS = [
    "database.table.read_row",
    "database.table.view.list_rows",
    "database.table.view.read_row",
    "database.table.list_fields",
    "database.table.list_views",
    "database.table.listen_to_all",
    "database.table.view.list_comments",
]


def _assign(data_fixture, role):
    user_workspace = data_fixture.create_user_workspace(permissions="MEMBER")
    user = user_workspace.user
    workspace = user_workspace.workspace
    RbacHandler().assign_role(user, workspace, role)
    return user, workspace


@pytest.mark.django_db
@pytest.mark.parametrize("operation", sorted(VIEWER_DENIED_OPS))
def test_viewer_denied_each_mutating_op(data_fixture, operation):
    """A Viewer gets a RoleProhibitedError (deny) for every denied op string."""

    user, workspace = _assign(data_fixture, VIEWER)
    manager = RbacPermissionManagerType()
    check = PermissionCheck(user, operation, workspace)

    result = manager.check_multiple_permissions([check], workspace=workspace)

    assert isinstance(result.get(check), RoleProhibitedError)


@pytest.mark.django_db
@pytest.mark.parametrize("operation", sorted(COMMENTER_DENIED_OPS))
def test_commenter_denied_each_mutating_op(data_fixture, operation):
    """A Commenter gets a RoleProhibitedError for every structural/comment-edit op."""

    user, workspace = _assign(data_fixture, COMMENTER)
    manager = RbacPermissionManagerType()
    check = PermissionCheck(user, operation, workspace)

    result = manager.check_multiple_permissions([check], workspace=workspace)

    assert isinstance(result.get(check), RoleProhibitedError)


@pytest.mark.django_db
def test_commenter_allowed_create_comment_but_viewer_denied(data_fixture):
    """The one capability that distinguishes the tiers: create_comment."""

    commenter, c_ws = _assign(data_fixture, COMMENTER)
    viewer, v_ws = _assign(data_fixture, VIEWER)
    manager = RbacPermissionManagerType()

    c_check = PermissionCheck(commenter, CREATE_COMMENT_OPERATION, c_ws)
    v_check = PermissionCheck(viewer, CREATE_COMMENT_OPERATION, v_ws)

    c_result = manager.check_multiple_permissions([c_check], workspace=c_ws)
    v_result = manager.check_multiple_permissions([v_check], workspace=v_ws)

    # Commenter: NOT in the result == defer (the chain then grants the read/comment) —
    # the manager never denies create_comment for a Commenter.
    assert c_check not in c_result
    # Viewer: denied.
    assert isinstance(v_result.get(v_check), RoleProhibitedError)


@pytest.mark.django_db
@pytest.mark.parametrize("operation", READ_AND_SUBSCRIBE_OPS)
def test_read_and_subscribe_ops_defer_for_both_tiers(data_fixture, operation):
    """Reads/subscribe must DEFER (absent from result), never deny — preserves read
    access for Viewer and Commenter (the 'read still succeeds' half of both ACs)."""

    for role in (VIEWER, COMMENTER):
        user, workspace = _assign(data_fixture, role)
        manager = RbacPermissionManagerType()
        check = PermissionCheck(user, operation, workspace)

        result = manager.check_multiple_permissions([check], workspace=workspace)

        assert check not in result, f"{operation} should defer for {role}, not deny"


@pytest.mark.django_db
def test_editor_and_admin_unchanged_by_13(data_fixture):
    """Editor/Admin must not be denied any of the 1.3 deny-set ops (behavior unchanged
    from 1.2: the manager grants admin-only ops to Admin and defers the rest)."""

    manager = RbacPermissionManagerType()
    for role in (EDITOR, ADMIN):
        user, workspace = _assign(data_fixture, role)
        checks = [
            PermissionCheck(user, op, workspace) for op in sorted(VIEWER_DENIED_OPS)
        ]
        result = manager.check_multiple_permissions(checks, workspace=workspace)
        for check in checks:
            # None of the mutating ops is RBAC-managed/admin-only, so Editor/Admin defer
            # (absent) — never a RoleProhibitedError.
            assert not isinstance(result.get(check), RoleProhibitedError)


@pytest.mark.django_db
def test_no_assignment_still_defers_on_mutation(data_fixture):
    """A user with no RoleAssignment is unaffected by 1.3 — the manager defers and the
    legacy chain grants the member (no regression of pre-1.2 behavior)."""

    user_workspace = data_fixture.create_user_workspace(permissions="MEMBER")
    user = user_workspace.user
    workspace = user_workspace.workspace

    manager = RbacPermissionManagerType()
    check = PermissionCheck(user, "database.table.create_row", workspace)

    result = manager.check_multiple_permissions([check], workspace=workspace)

    assert check not in result
