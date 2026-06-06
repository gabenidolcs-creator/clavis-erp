# Behavior spec — Central field-permission layer with edit restriction

- **Story / epic:** 1.4 Central field-permission layer with edit restriction (Epic 1)
- **Bucket:** A (clean-room reimplement)
- **Author:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-06
- **Extends:** [1-2-rbac-role-model.md](1-2-rbac-role-model.md) (effective-role
  resolution) and [1-3-role-enforcement.md](1-3-role-enforcement.md) (the
  `PermissionException → global registry → 403` pattern). This spec adds **per-Field,
  per-Role edit restriction** on top of the role-wide enforcement.

## 1. Allowed sources consulted

| # | Source | Type (public docs / public SaaS UI / public issue / MIT free-core) | Link / location |
|---|--------|--------------------------------------------------------------------|-----------------|
| 1 | Public Airtable/Baserow field-permission UX — an admin can mark a single field so that lower-privileged members may read but not edit its values (e.g. a "Salary" column read-only to most members) | public SaaS UI / public docs | https://baserow.io/docs , https://airtable.com (observable behavior only) |
| 2 | `WriteFieldValuesOperationType` (`"database.table.field.write_values"`) — the per-field write operation already emitted per touched field on a row update | MIT free-core | `backend/src/baserow/contrib/database/fields/operations.py` |
| 3 | `UpdateFieldOperationType` (`"database.table.field.update"`) — the field-config update operation | MIT free-core | `backend/src/baserow/contrib/database/fields/operations.py` |
| 4 | `PermissionManagerType` contract — `check_multiple_permissions` (True=grant / exception=deny / absent=defer), `get_permissions_object`, `supported_actor_types` | MIT free-core | `backend/src/baserow/core/registries.py` |
| 5 | `CoreHandler.check_multiple_permissions` / `check_permissions` — batch aggregation collapses a returned exception to `False` unless `return_permissions_exceptions=True`; single-check re-raises | MIT free-core | `backend/src/baserow/core/handler.py` |
| 6 | `RowHandler._check_write_fields_values_permissions` — the existing per-field `write_values` check on the row-update path | MIT free-core | `backend/src/baserow/contrib/database/rows/handler.py` |
| 7 | `FieldHandler.update_field` — the field-config path that re-raises the manager exception | MIT free-core | `backend/src/baserow/contrib/database/fields/handler.py` |
| 8 | `BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS` — operation-`type`-string admin-gating convention | MIT free-core | `backend/src/baserow/core/permission_manager.py` |
| 9 | `RbacHandler.get_effective_role`, `roles.role_at_least` / `ROLE_ORDER` (Story 1.2) — effective-role resolution reused, not reinvented | MIT free-core (this repo, Story 1.2) | `backend/src/baserow/core/rbac/handler.py`, `roles.py` |
| 10 | `PermissionException`/`PermissionDenied` hierarchy + `api_exception_registry` global mapping + `Field.read_only` precedent | MIT free-core | `backend/src/baserow/core/exceptions.py`, `backend/src/baserow/api/registries.py`, `backend/src/baserow/contrib/database/fields/models.py` |
| 11 | Frontend `canWriteFieldValues → $hasPermission('database.table.field.write_values')` read-only cell gate (already wired) and `PermissionManagerType` frontend base | MIT free-core | `web-frontend/modules/database/fieldTypes.js`, `web-frontend/modules/core/permissionManagerTypes.js` |
| 12 | Django / DRF framework documentation | general public knowledge | https://docs.djangoproject.com , https://www.django-rest-framework.org |

> No excluded paid (PE/EE) source under `premium/` or `enterprise/` was read, copied,
> adapted, or recalled. The enterprise field-permissions feature uses a DB-driven
> `FieldPermissions` model with a `FieldPermissionsRoleEnum` (EDITOR/BUILDER/ADMIN/
> CUSTOM/NOBODY) and a custom-subject allow/deny system — that design is **not** ours.
> Our design is a **fixed-tier minimum-role threshold** derived from the publicly
> observable behavior (a field can be made read-only to lower roles), built on the
> public MIT registry shape only.

## 2. Observed behavior (UI / UX)

- An **admin** can mark an individual field edit-restricted by choosing the **minimum
  role** allowed to edit that field's values (e.g. "only Editors and above", or "only
  Admins").
- Members **below** that threshold see the field's cells **read-only** everywhere the
  value would be written (grid cell, row edit modal, and any other write surface) — but
  they can still **read** the value. The field is not hidden (hiding is Story 1.5).
- Members **at or above** the threshold edit the field exactly as before.
- The restriction **persists per field** (survives reload) and applies **uniformly** at
  every write surface, because enforcement runs in one central place rather than per
  surface.
- Only an admin may change the restriction; a non-admin attempting to change it is
  rejected.

## 3. Acceptance behavior (externally observable)

- Admin sets a field's minimum-edit-role; a member below it that attempts to write a
  cell value is rejected **server-side with HTTP 403** (distinct from the generic 401),
  on **both** the row-cell-value write path **and** the field-config update path.
- The restricted field renders **read-only** in the UI for unauthorized members.
- The rule persists per field and is enforced **uniformly** across every write surface
  (the row-update path and the Application-Builder data-source path both route writes
  through the same `write_values` operation, so both are governed by the one layer with
  no per-surface enforcement code).
- A restricted field **remains readable** — this story restricts edit only.
- Default with no rule = unrestricted (current behavior). A workspace with zero rules
  behaves exactly as before.
- A non-admin that tries to set/change a field's restriction is rejected with 403.

## 4. Free-core (MIT) symbols to build on

- `PermissionManagerType` (base; `check_multiple_permissions`, `get_permissions_object`,
  `supported_actor_types`) — `backend/src/baserow/core/registries.py`.
- `WriteFieldValuesOperationType` / `UpdateFieldOperationType` `type` strings (governed
  ops, referenced as strings to avoid a `core → contrib.database` import cycle).
- `RbacHandler.get_effective_role`, `roles.role_at_least`, `ROLE_ORDER` (Story 1.2).
- `PermissionException` subclass → `api_exception_registry` global 403 mapping (Story
  1.3 pattern), reused for a new `FieldEditProhibitedError`.
- `Field` model (the rule attaches via a `OneToOneField` in the same `database` app).
- Frontend `PermissionManagerType` base + the already-wired
  `canWriteFieldValues → $hasPermission('…write_values')` cell gate.

## 5. Design (fixed-tier, our own — NOT the enterprise model)

- A single `FieldPermission` row per field stores `editable_by_role` (a fixed tier:
  Viewer/Commenter/Editor/Admin). **Absent row = unrestricted.** `editable_by_role`
  is a **minimum threshold**: an effective role `>= editable_by_role` may edit; below it
  is denied write. Setting `ADMIN` makes the field admin-only (the "Salary" case).
- The rule row lives in the **`database`** app next to `Field` (an FK from `core` to
  `database.Field` would invert the app/migration dependency). The **enforcement** lives
  in `core/field_permissions/` as a `FieldPermissionManagerType` in the
  `PERMISSION_MANAGERS` chain.
- The manager **defers** (omits the check) for: fields with no rule, actors at/above the
  threshold, actors with no effective role, and any operation that is not a field-edit
  op. It only **denies** the specific (restricted field × insufficient role × edit op)
  tuple — never deny-by-default (reads, Editor/Admin edits, unrelated ops all pass).
- We do **not** replicate the enterprise `FieldPermissions` model, its
  `FieldPermissionsRoleEnum`, its CUSTOM/NOBODY values, its custom-subject allow/deny
  lists, or its handler/API logic. Per-member overrides are explicitly out of scope.

## 6. Error contract

A denied field edit raises `FieldEditProhibitedError(PermissionException)`, mapped
**globally** via `api_exception_registry` to **HTTP 403** with error code
`ERROR_FIELD_EDIT_PROHIBITED`, mirroring Story 1.3's `RoleProhibitedError`. The generic
`PermissionException` stays **401**; MRO most-specific-first resolution guarantees the
subclass 403 wins for field-edit denials. The field-config path re-raises the exception
directly (403 for free); the row-value batch path raises `FieldEditProhibitedError`
explicitly from the row handler (the batch aggregator otherwise collapses it to a
generic 401).

## 7. Out of scope (later stories)

Field **visibility/hiding**, value redaction, the inference-oracle guard
(filter/sort on a hidden field), and cache invalidation on permission change — **Story
1.5**. Export enforcement — **Story 1.9**. Dashboard/Builder *read* redaction — later
epics. **Per-member (custom-subject) overrides** — documented later extension; not built
here.

## 8. Self-check (must all be true)

- [x] Every source in §1 is on the allowed-source list (no `premium/`/`enterprise/`,
      no paid-instance internals, no memory of the paid product).
- [x] No `premium/`/`enterprise/` **internal** symbol is named as the thing to replicate
      (only free-core MIT symbols are named as the things we build on).
- [x] This spec captures behavior/UI only, not code adapted from PE/EE source.
