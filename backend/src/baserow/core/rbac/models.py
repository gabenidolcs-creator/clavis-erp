"""RBAC ``RoleAssignment`` model.

A ``RoleAssignment`` layers a fixed-tier role (Viewer / Commenter / Editor / Admin) on
top of the legacy ``WorkspaceUser.permissions`` (ADMIN/MEMBER) field — it does NOT
replace it. An assignment is scoped to a **workspace** (``application`` null) or, more
specifically, to a **database/application** within a workspace (``application`` set).
The most specific scope wins (see ``RbacHandler.get_effective_role``).

Foreign keys use string references (``"core.Workspace"`` etc.) so this module imports
nothing from ``core.models`` — that keeps it free of the circular import that would
otherwise occur when ``core.models`` registers this model with the ``core`` app.
"""

from django.conf import settings
from django.db import models

from baserow.core.mixins import CreatedAndUpdatedOnMixin

from .roles import ROLE_CHOICES


class RoleAssignment(CreatedAndUpdatedOnMixin, models.Model):
    """A fixed-tier role granted to a user at workspace or database scope."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rbac_role_assignments",
        help_text="The user (subject) the role is granted to.",
    )
    workspace = models.ForeignKey(
        "core.Workspace",
        on_delete=models.CASCADE,
        related_name="rbac_role_assignments",
        help_text="The workspace the assignment belongs to.",
    )
    application = models.ForeignKey(
        "core.Application",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="rbac_role_assignments",
        help_text=(
            "When set, the assignment is scoped to this database/application and "
            "overrides the workspace-scoped assignment for that database. When null, "
            "the assignment is workspace-scoped."
        ),
    )
    role = models.CharField(
        max_length=32,
        choices=ROLE_CHOICES,
        help_text="The fixed role tier (Viewer / Commenter / Editor / Admin).",
    )

    class Meta:
        app_label = "core"
        # One assignment per (user, scope). NULL application == workspace scope.
        constraints = [
            models.UniqueConstraint(
                fields=["user", "workspace"],
                condition=models.Q(application__isnull=True),
                name="unique_workspace_scoped_role_assignment",
            ),
            models.UniqueConstraint(
                fields=["user", "workspace", "application"],
                condition=models.Q(application__isnull=False),
                name="unique_database_scoped_role_assignment",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "workspace"]),
        ]

    def __str__(self):
        scope = (
            f"application={self.application_id}"
            if self.application_id
            else f"workspace={self.workspace_id}"
        )
        return f"<RoleAssignment user={self.user_id} role={self.role} {scope}>"
