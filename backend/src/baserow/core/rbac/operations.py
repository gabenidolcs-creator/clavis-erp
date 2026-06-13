"""Operation types for managing RBAC role assignments.

These operate on a workspace context. They are admin-only: the
``BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS`` list is extended (in lockstep) so
that only workspace admins may assign or list role assignments. Registered via
``operation_type_registry`` in ``core/apps.py`` ``ready()``.
"""

from abc import ABC

from baserow.core.registries import OperationType


class RbacWorkspaceOperationType(OperationType, ABC):
    context_scope_name = "workspace"


class AssignRoleWorkspaceOperationType(RbacWorkspaceOperationType):
    type = "workspace.assign_role"


class ReadRoleAssignmentsWorkspaceOperationType(RbacWorkspaceOperationType):
    type = "workspace.read_role_assignments"


class GrantPageAccessOperationType(RbacWorkspaceOperationType):
    type = "workspace.interface_only.grant_page_access"


class RevokePageAccessOperationType(RbacWorkspaceOperationType):
    type = "workspace.interface_only.revoke_page_access"


class ListPageGrantsOperationType(RbacWorkspaceOperationType):
    type = "workspace.interface_only.list_page_grants"
