"""Story 1.4/1.5 — handler to read and set a Field's permission rule, and the central
read redactor.

Lives in the ``database`` app (next to ``Field``/``FieldPermission``). The mutating
method routes through ``CoreHandler.check_permissions`` with the admin-only
``UpdateFieldPermissionOperationType`` so only the Admin tier may change a threshold —
the same single-enforcement-path principle Story 1.4 follows.

Story 1.5 adds:
- ``get_hidden_field_ids(user, table)`` — the **single** central redactor. It routes the
  table's ``Field`` queryset through ``CoreHandler.filter_queryset`` with the read op, so
  the redaction decision lives entirely in ``FieldPermissionManagerType.filter_queryset``.
  Every read surface (REST row list/get, search, WebSocket row payloads) consumes this one
  helper — there is no per-surface ad-hoc hiding (architecture D7 / NFR-4).
- ``readable_by_role`` on the setter, plus cache + live-session invalidation on any
  threshold change so a visibility change takes effect without a reconnect.
"""

from typing import Optional, Set

from django.contrib.auth.models import AbstractUser

from baserow.contrib.database.fields.models import Field, FieldPermission
from baserow.contrib.database.fields.operations import (
    ReadFieldOperationType,
    UpdateFieldPermissionOperationType,
)
from baserow.core.handler import CoreHandler
from baserow.core.rbac.roles import is_valid_role

# Sentinel so the setter can distinguish "leave this threshold untouched" from
# "explicitly clear it to None". A bare None means *clear*; _UNSET means *don't change*.
_UNSET = object()


class FieldPermissionHandler:
    @classmethod
    def get_field_permission(cls, field: Field) -> Optional[FieldPermission]:
        """Return the field's permission rule, or ``None`` if unrestricted."""

        return FieldPermission.objects.filter(field=field).first()

    @classmethod
    def get_hidden_field_ids(cls, user: AbstractUser, table) -> Set[int]:
        """Return the ids of fields in ``table`` that ``user`` may NOT see (Story 1.5).

        This is the central redactor — the single computation every read surface consumes.
        It does NOT reimplement the visibility rule; it asks the permission chain to filter
        the table's ``Field`` queryset for the read operation and returns the complement
        (all field ids minus the ids that survived the filter). Because the only filtering
        manager for this op is ``FieldPermissionManagerType``, the surviving set is exactly
        the fields the actor may see, and the complement is what must be redacted.

        Returns an empty set when nothing is hidden (the common case), so callers can union
        it into ``exclude_field_ids`` / ``only_search_by_field_ids`` cheaply.
        """

        all_field_ids = set(
            Field.objects.filter(table=table).values_list("id", flat=True)
        )
        if not all_field_ids:
            return set()

        workspace = table.database.workspace
        visible_queryset = CoreHandler().filter_queryset(
            user,
            ReadFieldOperationType.type,
            Field.objects.filter(table=table),
            workspace=workspace,
        )
        visible_field_ids = set(visible_queryset.values_list("id", flat=True))
        return all_field_ids - visible_field_ids

    @classmethod
    def set_field_permission(
        cls,
        user: AbstractUser,
        field: Field,
        editable_by_role=_UNSET,
        readable_by_role=_UNSET,
    ) -> Optional[FieldPermission]:
        """Set (or clear) the edit and/or read thresholds for ``field``.

        Only an Admin may call this; the permission check is delegated to the central
        chain via the admin-only ``update_permission`` operation. The two thresholds share
        one rule row: passing ``_UNSET`` (the default) for one leaves it untouched, so a
        caller may change visibility without disturbing the edit restriction and vice
        versa. Passing an explicit ``None`` clears that threshold. When BOTH end up null
        the rule row is deleted (restoring the unrestricted default).

        Any change invalidates the table's model cache and re-evaluates live sessions
        (Story 1.5 AC #3) so a new visibility takes effect without a reconnect.

        :param editable_by_role: minimum role allowed to edit; ``None`` clears it,
            ``_UNSET`` leaves it unchanged.
        :param readable_by_role: minimum role allowed to see the field; ``None`` clears it
            (visible to all), ``_UNSET`` leaves it unchanged.
        :raises FieldEditProhibitedError: if ``user`` is not an Admin (mapped to 403).
        :raises ValueError: if a provided role is not a known fixed tier.
        """

        workspace = field.table.database.workspace
        CoreHandler().check_permissions(
            user,
            UpdateFieldPermissionOperationType.type,
            workspace=workspace,
            context=field,
        )

        existing = FieldPermission.objects.filter(field=field).first()
        current_edit = existing.editable_by_role if existing else None
        current_read = existing.readable_by_role if existing else None

        new_edit = current_edit if editable_by_role is _UNSET else editable_by_role
        new_read = current_read if readable_by_role is _UNSET else readable_by_role

        if new_edit is not None and not is_valid_role(new_edit):
            raise ValueError(f"Unknown role: {new_edit!r}")
        if new_read is not None and not is_valid_role(new_read):
            raise ValueError(f"Unknown role: {new_read!r}")

        if new_edit is None and new_read is None:
            deleted, _ = FieldPermission.objects.filter(field=field).delete()
            cls._invalidate_after_change(field)
            return None

        permission, _ = FieldPermission.objects.update_or_create(
            field=field,
            defaults={
                "editable_by_role": new_edit,
                "readable_by_role": new_read,
            },
        )
        cls._invalidate_after_change(field)
        return permission

    @classmethod
    def _invalidate_after_change(cls, field: Field) -> None:
        """Invalidate caches and re-evaluate live sessions after a threshold change.

        - Bumps the table's model-cache version (``invalidate_table_in_model_cache``) so
          the next row/field fetch recomputes redaction from fresh state.
        - Fires the ``permissions_updated`` signal (a public extension point).
        - Broadcasts to the table's permission channel group so currently-connected
          clients re-subscribe and re-fetch with the new visibility — no reconnect needed.
          (This is a re-evaluation, not a revocation: subscribe-time auth re-admits any
          still-authorized user; only the redacted payload changes.)
        """

        from baserow.contrib.database.table.cache import (
            invalidate_table_in_model_cache,
        )
        from baserow.core.signals import permissions_updated

        invalidate_table_in_model_cache(field.table_id)

        workspace = field.table.database.workspace
        permissions_updated.send(cls, workspace=workspace)

        cls._broadcast_live_session_reevaluation(field, workspace)

    @classmethod
    def _broadcast_live_session_reevaluation(cls, field: Field, workspace) -> None:
        """Tell clients on this table's permission channel group to re-evaluate.

        Reuses the free-core ``users_removed_from_permission_group`` channel message —
        the established live-session re-evaluation path. Only clients actually subscribed
        to the table's permission group receive it, and each acts only if its own user id
        is listed, so passing the workspace members is safe and self-targeting.
        """

        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        from baserow.contrib.database.ws.pages import TablePageType
        from baserow.ws.tasks import send_message_to_channel_group

        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        user_ids = list(workspace.users.values_list("id", flat=True))
        if not user_ids:
            return

        channel_group_name = TablePageType().get_permission_channel_group_name(
            field.table_id
        )
        async_to_sync(send_message_to_channel_group)(
            channel_layer,
            channel_group_name,
            {
                "type": "users_removed_from_permission_group",
                "user_ids_to_remove": user_ids,
                "permission_group_name": channel_group_name,
            },
        )
