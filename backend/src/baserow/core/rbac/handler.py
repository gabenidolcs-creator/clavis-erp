"""``RbacHandler`` — the handler spine for RBAC role assignments.

All role-assignment mutations and effective-role lookups go through this handler (never
direct ORM in API views), consistent with the project's handler-spine convention.
"""

from typing import List, Optional

from baserow.core.rbac import roles
from baserow.core.rbac.models import RoleAssignment


class RbacHandler:
    def assign_role(
        self,
        user,
        workspace,
        role: str,
        application=None,
    ) -> RoleAssignment:
        """Assign (or update) a fixed-tier role to ``user`` at the given scope.

        :param user: The subject user receiving the role.
        :param workspace: The workspace the assignment belongs to.
        :param role: One of the fixed tiers (see ``roles``).
        :param application: Optional database/application for database-scoped
            assignment. When ``None`` the assignment is workspace-scoped.
        :raises ValueError: if ``role`` is not a known fixed tier.
        :return: The created/updated ``RoleAssignment``.
        """

        if not roles.is_valid_role(role):
            raise ValueError(f"Unknown role: {role!r}")

        # Defense-in-depth (the handler is the shared REST/WS/CLI spine): a
        # database-scoped assignment must target an application inside the workspace,
        # otherwise the scope is incoherent and `get_effective_role` could never match.
        if (
            application is not None
            and getattr(application, "workspace_id", None) != workspace.id
        ):
            raise ValueError(
                "application must belong to the workspace it is scoped under"
            )

        assignment, _ = RoleAssignment.objects.update_or_create(
            user=user,
            workspace=workspace,
            application=application,
            defaults={"role": role},
        )
        return assignment

    def get_role_assignment(
        self, user, workspace, application=None
    ) -> Optional[RoleAssignment]:
        """Return the assignment for the exact scope, or ``None``."""

        return RoleAssignment.objects.filter(
            user=user, workspace=workspace, application=application
        ).first()

    def get_effective_role(self, user, workspace, application=None) -> Optional[str]:
        """Resolve the effective role for ``user`` at the given scope.

        Most-specific scope wins: a database-scoped assignment (matching
        ``application``) overrides the workspace-scoped assignment. Returns ``None``
        when the user has no assignment in scope (callers must then defer to the legacy
        permission managers — this is what preserves pre-1.2 behavior).
        """

        if application is not None:
            specific = self.get_role_assignment(user, workspace, application)
            if specific is not None:
                return specific.role

        workspace_scoped = self.get_role_assignment(user, workspace, None)
        return workspace_scoped.role if workspace_scoped is not None else None

    def list_role_assignments(
        self, workspace, application=None
    ) -> List[RoleAssignment]:
        """List role assignments in a workspace, optionally for one application scope."""

        queryset = RoleAssignment.objects.filter(workspace=workspace)
        if application is not None:
            queryset = queryset.filter(application=application)
        return list(queryset.select_related("user", "workspace", "application"))

    def remove_role_assignment(self, user, workspace, application=None) -> None:
        """Remove a role assignment at the given scope (no-op if absent)."""

        RoleAssignment.objects.filter(
            user=user, workspace=workspace, application=application
        ).delete()

    # ------------------------------------------------------------------
    # Interface-only page grant CRUD (Story 6.3)
    # ------------------------------------------------------------------

    def grant_page_access(self, user, workspace, page):
        """Idempotently grant an interface-only collaborator access to a page."""
        from .models import InterfaceCollaboratorPageGrant

        grant, _ = InterfaceCollaboratorPageGrant.objects.get_or_create(
            user=user,
            page=page,
            defaults={"workspace": workspace},
        )
        return grant

    def revoke_page_access(self, user, page) -> None:
        """Remove a page grant (no-op if absent)."""
        from .models import InterfaceCollaboratorPageGrant

        InterfaceCollaboratorPageGrant.objects.filter(user=user, page=page).delete()

    def list_granted_pages(self, user, workspace):
        """Return all page grants for an interface-only collaborator in a workspace."""
        from .models import InterfaceCollaboratorPageGrant

        return list(
            InterfaceCollaboratorPageGrant.objects.filter(
                user=user,
                workspace=workspace,
            ).select_related("page")
        )
