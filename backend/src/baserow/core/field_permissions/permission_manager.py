"""``FieldPermissionManagerType`` — per-Field, per-Role edit restriction.

This manager is the single central enforcement point for Story 1.4 (architecture D7).
It consumes the **already-emitted** ``database.table.field.write_values`` and
``database.table.field.update`` operations and denies them when a field carries a
``FieldPermission`` rule whose ``editable_by_role`` threshold is above the actor's
effective role. It never adds a parallel, surface-specific check — every write surface
(row update, Application-Builder data source, field-config update) routes through these
operations and is therefore governed uniformly.

Contract (defer, don't deny — Story 1.3 lesson):
- **Deny** (return a ``FieldEditProhibitedError`` instance) only for the precise tuple
  *(restricted field × edit operation × effective role below the threshold)*.
- **Defer** (omit the check) for: fields with no rule, actors at/above the threshold,
  actors with no effective role in scope, and any operation not in
  ``FIELD_EDIT_OPERATIONS``. Reads, Editor/Admin edits, and unrelated ops all pass.

Read-redaction (``filter_queryset``) is intentionally NOT implemented here — that is
Story 1.5. This layer restricts *edit* only; a restricted field stays readable.

This is a clean-room (Bucket A) reimplementation: it shares only the public MIT registry
shape (a manager returning an exception to deny) and reuses Story 1.2's fixed-tier role
resolution. It does NOT replicate the enterprise field-permissions model, its role enum,
or its custom-subject allow/deny system.
"""

from baserow.core.exceptions import FieldEditProhibitedError
from baserow.core.rbac import roles
from baserow.core.registries import PermissionManagerType
from baserow.core.subjects import UserSubjectType

from .enforcement import FIELD_EDIT_OPERATIONS, UPDATE_FIELD_PERMISSION_OPERATION


class FieldPermissionManagerType(PermissionManagerType):
    type = "field_permissions"
    supported_actor_types = [UserSubjectType.type]

    def _field_ids_from_checks(self, checks):
        """Field ids of the checks that target a governed field operation.

        The ``write_values`` / ``field.update`` / ``update_permission`` operations are
        scoped to ``database_field`` — the check ``context`` *is* the ``Field``
        instance. Only those checks can be decided here; every other check defers.
        """

        field_ids = set()
        for check in checks:
            if not self._is_governed_operation(check.operation_name):
                continue
            field_id = getattr(check.context, "id", None)
            if field_id is not None:
                field_ids.add(field_id)
        return field_ids

    @staticmethod
    def _is_governed_operation(operation_name):
        return (
            operation_name in FIELD_EDIT_OPERATIONS
            or operation_name == UPDATE_FIELD_PERMISSION_OPERATION
        )

    def _load_rules(self, field_ids):
        """Batch-load ``{field_id: editable_by_role}`` for the restricted fields.

        One query for all checks — never per-check (the security-critical permission
        chain must not N+1; Story 1.2's ``_build_role_index`` lesson).
        """

        if not field_ids:
            return {}

        from baserow.contrib.database.fields.models import FieldPermission

        rows = FieldPermission.objects.filter(field_id__in=field_ids).values_list(
            "field_id", "editable_by_role"
        )
        return {field_id: role for field_id, role in rows}

    def _load_field_application_ids(self, field_ids):
        """Batch-load ``{field_id: database_id}`` so role resolution can use the
        database-scoped (most-specific) assignment. One query."""

        if not field_ids:
            return {}

        from baserow.contrib.database.fields.models import Field

        rows = Field.objects.filter(id__in=field_ids).values_list(
            "id", "table__database_id"
        )
        return {field_id: database_id for field_id, database_id in rows}

    def _build_role_index(self, checks, workspace):
        """Load every relevant role assignment in one query, keyed by
        ``(user_id, application_id)`` (``application_id`` is ``None`` for
        workspace-scoped assignments). Mirrors ``RbacPermissionManagerType``."""

        from baserow.core.rbac.models import RoleAssignment

        actor_ids = {getattr(check.actor, "id", None) for check in checks} - {None}
        if not actor_ids:
            return {}

        rows = RoleAssignment.objects.filter(
            workspace=workspace, user_id__in=actor_ids
        ).values_list("user_id", "application_id", "role")
        return {
            (user_id, application_id): role for user_id, application_id, role in rows
        }

    @staticmethod
    def _effective_role(role_index, actor_id, application_id):
        """Resolve the effective role (most-specific scope wins)."""

        if actor_id is None:
            return None
        if application_id is not None:
            specific = role_index.get((actor_id, application_id))
            if specific is not None:
                return specific
        return role_index.get((actor_id, None))

    def check_multiple_permissions(self, checks, workspace=None, include_trash=False):
        if workspace is None or not checks:
            return {}

        field_ids = self._field_ids_from_checks(checks)
        if not field_ids:
            return {}

        # Threshold rules for the edit ops; the admin-only update_permission op does NOT
        # depend on a rule existing, so we still resolve roles even when rules is empty.
        rules = self._load_rules(field_ids)
        field_application_ids = self._load_field_application_ids(field_ids)
        role_index = self._build_role_index(checks, workspace)
        result = {}

        for check in checks:
            operation = check.operation_name
            if not self._is_governed_operation(operation):
                continue

            field_id = getattr(check.context, "id", None)
            actor_id = getattr(check.actor, "id", None)
            application_id = field_application_ids.get(field_id)
            role = self._effective_role(role_index, actor_id, application_id)

            if operation == UPDATE_FIELD_PERMISSION_OPERATION:
                # Admin-only: managing the rule. Deny a non-admin role with a 403; grant
                # the Admin tier; defer when no role is in scope (legacy ADMIN-string
                # check in `basic` then decides — preserves pre-RBAC admins).
                if role is None:
                    continue
                if roles.role_at_least(role, roles.ADMIN):
                    result[check] = True
                else:
                    result[check] = FieldEditProhibitedError(check.actor)
                continue

            # FIELD_EDIT_OPERATIONS — threshold check against the field's rule.
            threshold = rules.get(field_id)
            if threshold is None:
                # Unrestricted field — defer (preserves pre-1.4 behavior).
                continue
            if role is None:
                # No assignment in scope — defer to the legacy chain. Never
                # deny-by-default here.
                continue
            if not roles.role_at_least(role, threshold):
                # Effective role below the field's minimum-edit threshold — deny.
                # Returning the exception INSTANCE = deny; the row handler / field
                # handler surface it as HTTP 403 (ERROR_FIELD_EDIT_PROHIBITED).
                result[check] = FieldEditProhibitedError(check.actor)

            # At/above threshold — defer so the legacy chain still decides the rest.

        return result

    def get_permissions_object(self, actor, workspace=None):
        """Data the frontend needs to render restricted fields read-only.

        Returns ``{"restricted_field_ids": [...]}`` — the ids of fields in this
        workspace the actor may NOT edit (effective role below the field's threshold).
        Returns ``None`` when nothing is restricted for this actor, so the frontend
        manager defers and existing behavior is unchanged.
        """

        if workspace is None:
            return None

        actor_id = getattr(actor, "id", None)
        if actor_id is None:
            return None

        from baserow.contrib.database.fields.models import FieldPermission

        rows = list(
            FieldPermission.objects.filter(
                field__table__database__workspace=workspace
            ).values_list("field_id", "field__table__database_id", "editable_by_role")
        )
        if not rows:
            return None

        role_index = self._build_role_index([_SimpleCheck(actor)], workspace)

        restricted_field_ids = []
        for field_id, application_id, threshold in rows:
            role = self._effective_role(role_index, actor_id, application_id)
            if role is None:
                continue
            if not roles.role_at_least(role, threshold):
                restricted_field_ids.append(field_id)

        if not restricted_field_ids:
            return None
        return {"restricted_field_ids": restricted_field_ids}


class _SimpleCheck:
    """Minimal actor carrier so ``_build_role_index`` can be reused by
    ``get_permissions_object`` (which has an actor but no check list)."""

    def __init__(self, actor):
        self.actor = actor
