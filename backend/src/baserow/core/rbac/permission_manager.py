"""``RbacPermissionManagerType`` — fixed-tier role checks in the permission chain.

This manager mirrors the *shape* of the free-core ``BasicPermissionManagerType`` (it is
NOT adapted from any premium/enterprise source). It is registered into the existing
``PERMISSION_MANAGERS`` chain after ``"member"`` and before ``"basic"``.

Story 1.2 contract — **defer, don't deny:**
- It NEVER denies anything a member can do today. It either *grants* (returns ``True``)
  or *defers* (omits the check) so the legacy ``basic``/``member`` managers still decide.
- For the existing admin-only operations it grants when the effective role is ``Admin``
  (== today's ADMIN capability) and defers otherwise — identical net behavior to before,
  because ``ADMIN → Admin`` and ``MEMBER → Editor`` after migration.
- The new role-management operations are also added to
  ``BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS`` (in lockstep), so a user with no
  ``RoleAssignment`` is still authorized correctly by the legacy ADMIN-string check.

Story 1.3 adds the **deny** side for the two read-scoped tiers: a Viewer/Commenter that
attempts a Row/Field/View mutation (or, for Viewer, a comment) gets a
``RoleProhibitedError`` value in the result (= deny → HTTP 403). Reads/subscribe and
unlisted ops still **defer** so read access is preserved (NOT deny-by-default). The deny
policy lives in ``enforcement.py`` as operation-``type`` strings. Editor/Admin behavior
is unchanged from 1.2.
"""

from baserow.core.exceptions import RoleProhibitedError
from baserow.core.registries import PermissionManagerType
from baserow.core.subjects import UserSubjectType

from . import roles
from .enforcement import COMMENTER_DENIED_OPS, VIEWER_DENIED_OPS
from .models import InterfaceCollaboratorPageGrant, RoleAssignment
from .operations import (
    AssignRoleWorkspaceOperationType,
    GrantPageAccessOperationType,
    ListPageGrantsOperationType,
    ReadRoleAssignmentsWorkspaceOperationType,
    RevokePageAccessOperationType,
)

# Operations owned by this manager (introduced by Story 1.2). They are also listed in
# BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS so legacy admins remain authorized.
RBAC_MANAGED_OPERATIONS = {
    AssignRoleWorkspaceOperationType.type,
    ReadRoleAssignmentsWorkspaceOperationType.type,
    GrantPageAccessOperationType.type,
    RevokePageAccessOperationType.type,
    ListPageGrantsOperationType.type,
}


class RbacPermissionManagerType(PermissionManagerType):
    type = "rbac"
    supported_actor_types = [UserSubjectType.type]

    @staticmethod
    def _get_page_id_from_context(context):
        """Extract page_id from builder contexts without importing builder models.

        Avoids a core → contrib/builder import cycle (layering violation).
        """
        if context is None:
            return None
        # Page itself — has .id but no .page FK
        if hasattr(context, "id") and type(context).__name__ == "Page":
            return context.id
        # Page itself via page_id attribute (some serialized forms)
        if hasattr(context, "page_id") and not hasattr(context, "page"):
            return context.page_id
        # DataSource, Element, WorkflowAction → have .page FK
        if hasattr(context, "page") and hasattr(context.page, "id"):
            return context.page.id
        if hasattr(context, "page_id"):
            return context.page_id
        return None

    def _application_from_context(self, context):
        """Return the Application context (for database-scoped roles), else ``None``.

        Only resolves database scope when the context object *is* an Application (or a
        subclass such as Database). Finer-grained context resolution (e.g. Table →
        Database) is intentionally out of scope for the 1.2 foundation.
        """

        if context is None:
            return None
        from baserow.core.models import Application

        return context if isinstance(context, Application) else None

    def _build_role_index(self, checks, workspace):
        """Load every relevant assignment in one query, keyed by ``(user_id, app_id)``.

        ``app_id`` is ``None`` for workspace-scoped assignments. Only the actors present
        in ``checks`` are fetched (the chain has already filtered to supported user
        actors via ``actor_is_supported``).
        """

        actor_ids = {getattr(check.actor, "id", None) for check in checks} - {None}
        if not actor_ids:
            return {}

        rows = RoleAssignment.objects.filter(
            workspace=workspace, user_id__in=actor_ids
        ).values_list("user_id", "application_id", "role")
        return {
            (user_id, application_id): role for user_id, application_id, role in rows
        }

    def _build_page_grant_index(self, interface_only_actor_ids, workspace):
        """Load all page grants for interface-only actors in one query.

        Returns a set of (user_id, page_id) tuples.
        """
        if not interface_only_actor_ids:
            return set()
        rows = InterfaceCollaboratorPageGrant.objects.filter(
            user_id__in=interface_only_actor_ids,
            workspace=workspace,
        ).values_list("user_id", "page_id")
        return set(rows)

    @staticmethod
    def _effective_role_from_index(role_index, actor, application):
        """Resolve the effective role from the prefetched index (most-specific wins)."""

        actor_id = getattr(actor, "id", None)
        if actor_id is None:
            return None
        if application is not None:
            specific = role_index.get((actor_id, application.pk))
            if specific is not None:
                return specific
        return role_index.get((actor_id, None))

    def check_multiple_permissions(self, checks, workspace=None, include_trash=False):
        if workspace is None or not checks:
            return {}

        # Imported lazily to avoid an import cycle at app load (core.permission_manager
        # imports the registry that this module is registered into).
        from baserow.core.permission_manager import BasicPermissionManagerType

        admin_only_operations = set(BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS)

        # Batch-load every assignment for the actors in this workspace in ONE query and
        # resolve effective roles in memory. Calling RbacHandler.get_effective_role per
        # check would issue 1-2 queries each — an N+1 on the security-critical permission
        # chain (the same path the recent permissions-endpoint perf work optimized).
        role_index = self._build_role_index(checks, workspace)

        # Pre-identify interface-only actors so we can batch-load page grants once.
        interface_only_actor_ids = {
            getattr(check.actor, "id", None)
            for check in checks
            if self._effective_role_from_index(
                role_index,
                check.actor,
                self._application_from_context(check.context),
            )
            == roles.INTERFACE_ONLY
        } - {None}
        page_grant_index = self._build_page_grant_index(
            interface_only_actor_ids, workspace
        )

        result = {}

        for check in checks:
            application = self._application_from_context(check.context)
            role = self._effective_role_from_index(role_index, check.actor, application)
            operation = check.operation_name

            if operation in RBAC_MANAGED_OPERATIONS:
                # Grant to Admin role; otherwise defer to `basic` (ADMIN-string check).
                if role == roles.ADMIN:
                    result[check] = True
                continue

            if role is None:
                # No assignment in scope — defer entirely to preserve pre-1.2 behavior.
                continue

            # Story 6.3: Interface-only collaborators are denied all database operations
            # (prefix-based, robust against new op additions) and all builder ops not on
            # a granted page. This block must appear before the Viewer/Commenter checks.
            if role == roles.INTERFACE_ONLY:
                if operation.startswith("database."):
                    result[check] = RoleProhibitedError(check.actor)
                    continue
                # For builder page/element/data-source ops, enforce page grant.
                page_id = self._get_page_id_from_context(check.context)
                actor_id = getattr(check.actor, "id", None)
                if page_id is not None:
                    if (actor_id, page_id) in page_grant_index:
                        result[check] = True
                    else:
                        result[check] = RoleProhibitedError(check.actor)
                else:
                    # Workspace-level ops (not page-scoped) → deny for interface-only.
                    result[check] = RoleProhibitedError(check.actor)
                continue

            # Story 1.3 deny side: read-scoped tiers are prohibited from the enumerated
            # mutating ops. Returning the exception INSTANCE = deny (the handler
            # re-raises it; the API maps RoleProhibitedError → 403). Unlisted ops (reads,
            # subscribe, unrelated workspace ops) fall through and DEFER below — never
            # deny-by-default for these roles, or read access breaks.
            if role == roles.VIEWER and operation in VIEWER_DENIED_OPS:
                result[check] = RoleProhibitedError(check.actor)
                continue
            if role == roles.COMMENTER and operation in COMMENTER_DENIED_OPS:
                result[check] = RoleProhibitedError(check.actor)
                continue

            if operation in admin_only_operations:
                # Grant admin-only ops to the Admin tier; defer everything else so the
                # legacy chain decides (this never tightens existing behavior).
                if roles.role_at_least(role, roles.ADMIN):
                    result[check] = True

            # Non-admin-only ops are left to `basic` (which grants members) — defer.

        return result

    def get_permissions_object(self, actor, workspace=None):
        # Story 1.2 does not change frontend permission behavior; the frontend manager
        # defers. Returning None keeps the existing client behavior intact.
        return None
