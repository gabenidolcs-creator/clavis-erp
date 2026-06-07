"""Story 1.4 field-edit policy — which operation *type* strings the field-permission
layer governs.

Operations are listed as plain ``operation.type`` strings, mirroring the
``BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS`` and Story 1.3 ``enforcement.py``
convention. This is deliberate: ``baserow.core`` must NOT import
``baserow.contrib.database`` operation classes (a ``core → contrib`` dependency would be
a layering violation and an import cycle), so the policy keys on the string identity of
each operation instead.

Policy summary (see ``docs/clean-room/specs/1-4-field-edit-restriction.md``):

- A ``FieldPermission`` row stores ``editable_by_role`` — the *minimum* fixed tier
  allowed to edit a field's values/config. **No row = unrestricted** (pre-1.4 behavior).
- The two governed write operations are the per-field value write (emitted per touched
  field on a row update, and by the Application-Builder data source) and the
  field-config update. Both already exist in free core; this layer only answers them.
- Story 1.5 adds the **read/visibility** half: ``database.table.field.read`` is now
  governed too, decided against the field's ``readable_by_role`` threshold. The manager
  still NEVER denies by default — a read is denied only for the precise tuple
  *(field carrying a readable_by_role rule × read operation × effective role below that
  threshold)*. Every other read defers and the field stays visible. The redaction path
  (``filter_queryset``) silently omits hidden fields; only an explicit filter/sort *on* a
  hidden field surfaces the read denial as a 403 (the inference-oracle guard).
"""

# Per-field value write (row-update path + Application-Builder LocalBaserow data source).
WRITE_FIELD_VALUES_OPERATION = "database.table.field.write_values"

# Field-config update (re-raises the manager exception → 403 for free).
UPDATE_FIELD_OPERATION = "database.table.field.update"

# The set of operations whose denial is decided by the field-permission EDIT threshold.
FIELD_EDIT_OPERATIONS = frozenset(
    {WRITE_FIELD_VALUES_OPERATION, UPDATE_FIELD_OPERATION}
)

# Per-field read (Story 1.5). Governs redaction (filter_queryset omits the field) and the
# inference-oracle guard (an explicit filter/sort on the field raises 403). Mirrors the
# free-core ReadFieldOperationType.type without importing the contrib operation class.
READ_FIELD_OPERATION = "database.table.field.read"

# The set of operations whose denial is decided by the field's READ/visibility threshold.
FIELD_READ_OPERATIONS = frozenset({READ_FIELD_OPERATION})

# Managing the rule itself is admin-only. The manager denies a non-admin attempting it
# with FieldEditProhibitedError so the API returns 403 (basic's admin-only path would
# otherwise yield a generic 401). This is independent of any field's threshold.
UPDATE_FIELD_PERMISSION_OPERATION = "database.table.field.update_permission"
