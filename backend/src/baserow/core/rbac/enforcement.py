"""Story 1.3 deny policy — which operation *type* strings each read-scoped tier is
denied.

Operations are listed as plain ``operation.type`` strings, mirroring the
``BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS`` convention. This is deliberate:
``baserow.core`` must NOT import ``baserow.contrib.database`` operation classes (a
``core → contrib`` dependency would be a layering violation and an import cycle), so the
policy keys on the string identity of each operation instead.

Policy summary (see ``docs/clean-room/specs/1-3-role-enforcement.md``):

- **Both Viewer and Commenter** are denied every structural mutation (Row/Field/View
  create/update/delete), table-scoped *and* view-scoped variants.
- **Commenter** may create comments; **Viewer** may not. Comment update/delete are
  denied to both (own-comment edit is an Epic 6 policy decision).
- Read / subscribe operations (``read_row``, ``list_rows``, ``list_fields``,
  ``list_views``, ``listen_to_all`` …) are **absent** from these sets, so the manager
  defers and the legacy chain preserves read access. NEVER deny-by-default for these
  roles.
"""

# Structural mutations denied to BOTH Viewer and Commenter. Strings are verified against
# contrib/database/{rows,fields,views,table}/operations.py.
_STRUCTURAL_MUTATIONS = {
    # Rows — table-scoped
    "database.table.create_row",
    "database.table.update_row",
    "database.table.delete_row",
    # Rows — view-scoped (mutations route through _check_permissions_with_view_fallback,
    # which issues both a table-scoped and a view-scoped check; deny both variants so
    # neither path slips through).
    "database.table.view.create_row",
    "database.table.view.update_row",
    "database.table.view.delete_row",
    # Fields
    "database.table.create_field",
    "database.table.field.update",
    "database.table.field.delete",
    # Views
    "database.table.create_view",
    "database.table.view.update",
    "database.table.view.delete",
}

# Comment operations denied to both tiers (Commenter's create_comment is allowed and is
# intentionally NOT in this set — it is handled below).
_COMMENT_MUTATIONS_DENIED_TO_BOTH = {
    "database.table.view.update_comment",
    "database.table.view.delete_comment",
}

# The single operation a Commenter may do that a Viewer may not.
CREATE_COMMENT_OPERATION = "database.table.view.create_comment"

# Viewer: read-only. Denied every structural mutation AND all comment writes (including
# create_comment).
VIEWER_DENIED_OPS = frozenset(
    _STRUCTURAL_MUTATIONS
    | _COMMENT_MUTATIONS_DENIED_TO_BOTH
    | {CREATE_COMMENT_OPERATION}
)

# Commenter: read + comment. Denied every structural mutation and comment update/delete,
# but NOT create_comment.
COMMENTER_DENIED_OPS = frozenset(
    _STRUCTURAL_MUTATIONS | _COMMENT_MUTATIONS_DENIED_TO_BOTH
)
