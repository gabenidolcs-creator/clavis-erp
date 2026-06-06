"""Story 1.4 — handler to read and set a Field's edit-restriction rule.

Lives in the ``database`` app (next to ``Field``/``FieldPermission``). The mutating
method routes through ``CoreHandler.check_permissions`` with the admin-only
``UpdateFieldPermissionOperationType`` so only the Admin tier may change the threshold —
the same single-enforcement-path principle the rest of Story 1.4 follows.
"""

from typing import Optional

from django.contrib.auth.models import AbstractUser

from baserow.contrib.database.fields.models import Field, FieldPermission
from baserow.contrib.database.fields.operations import (
    UpdateFieldPermissionOperationType,
)
from baserow.core.handler import CoreHandler
from baserow.core.rbac.roles import is_valid_role


class FieldPermissionHandler:
    @classmethod
    def get_field_permission(cls, field: Field) -> Optional[FieldPermission]:
        """Return the field's edit-restriction rule, or ``None`` if unrestricted."""

        return FieldPermission.objects.filter(field=field).first()

    @classmethod
    def set_field_permission(
        cls,
        user: AbstractUser,
        field: Field,
        editable_by_role: Optional[str],
    ) -> Optional[FieldPermission]:
        """Set (or clear) the minimum-edit-role threshold for ``field``.

        Only an Admin may call this; the permission check is delegated to the central
        chain via the admin-only ``update_permission`` operation.

        :param editable_by_role: a fixed-tier role string (the minimum role allowed to
            edit the field). Pass ``None`` to clear the restriction (delete the rule),
            restoring the unrestricted default.
        :raises FieldEditProhibitedError: if ``user`` is not an Admin (mapped to 403).
        :raises ValueError: if ``editable_by_role`` is not a known fixed tier.
        """

        workspace = field.table.database.workspace
        CoreHandler().check_permissions(
            user,
            UpdateFieldPermissionOperationType.type,
            workspace=workspace,
            context=field,
        )

        if editable_by_role is None:
            FieldPermission.objects.filter(field=field).delete()
            return None

        if not is_valid_role(editable_by_role):
            raise ValueError(f"Unknown role: {editable_by_role!r}")

        permission, _ = FieldPermission.objects.update_or_create(
            field=field, defaults={"editable_by_role": editable_by_role}
        )
        return permission
