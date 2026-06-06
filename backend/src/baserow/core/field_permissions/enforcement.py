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
- Read / list / subscribe operations are **absent** from this set, so the manager defers
  and the read path is untouched (read-redaction is Story 1.5). NEVER deny-by-default.
"""

# Per-field value write (row-update path + Application-Builder LocalBaserow data source).
WRITE_FIELD_VALUES_OPERATION = "database.table.field.write_values"

# Field-config update (re-raises the manager exception → 403 for free).
UPDATE_FIELD_OPERATION = "database.table.field.update"

# The set of operations whose denial is decided by the field-permission threshold.
FIELD_EDIT_OPERATIONS = frozenset(
    {WRITE_FIELD_VALUES_OPERATION, UPDATE_FIELD_OPERATION}
)

# Managing the rule itself is admin-only. The manager denies a non-admin attempting it
# with FieldEditProhibitedError so the API returns 403 (basic's admin-only path would
# otherwise yield a generic 401). This is independent of any field's threshold.
UPDATE_FIELD_PERMISSION_OPERATION = "database.table.field.update_permission"
