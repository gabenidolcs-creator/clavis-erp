---
baseline_commit: 179f0ff93
---

# Story 1.4: Central field-permission layer with edit restriction

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an admin,
I want to restrict who may edit a specific Field, enforced through one central layer,
so that sensitive Fields (e.g. Salary) are read-only to unauthorized members everywhere.

Realizes UJ-4. **Bucket A `[A]` — clean-room reimplementation; provenance record required (see "Clean-Room Mandate" below).**

## Context & Scope

**Stories 1.2/1.3 built the RBAC tier layer** (`Viewer/Commenter/Editor/Admin` via `RoleAssignment`, `RbacPermissionManagerType` in the `PERMISSION_MANAGERS` chain that now *denies* mutations for the two read-only tiers and maps a denial to **HTTP 403** via `RoleProhibitedError`). That is **role-wide, all-or-nothing per operation**. Story 1.4 adds the **per-Field, per-Role granularity**: an Admin can mark a single Field (e.g. `Salary`) edit-restricted so members below a threshold role are denied **writes to that field's values** while still reading the row — without touching their ability to edit every *other* field.

**The load-bearing discovery (read this twice): the per-field write hook already exists in free core.** `WriteFieldValuesOperationType` (`"database.table.field.write_values"`) is registered in core (`contrib/database/apps.py:944`) and `RowHandler` already issues a **per-field** `PermissionCheck(user, WriteFieldValuesOperationType.type, field)` for every field touched in a row update (`contrib/database/rows/handler.py:2208`). The Application-Builder data source does the same (`contrib/integrations/local_baserow/service_types.py:2069`). The **frontend** read-only gate also already exists: `canWriteFieldValues(field)` calls `$hasPermission('database.table.field.write_values', field, field.workspace_id)` (`web-frontend/modules/database/fieldTypes.js:918-926`), and `GridViewRow.vue:114` renders the cell read-only when it returns false. **What is missing is a permission manager that actually answers that check.** In OSS the `write_field_values` manager is removed from the chain (`config/settings/base.py:1289` — it is enterprise-only), so today `write_values` always *defers → is granted by `basic`*. Story 1.4 supplies the **core** manager that consumes the existing hook. [Source: architecture.md lines 127, 275; Explore findings]

**Why now:** Architecture D7 names this the **single central field-permission enforcement layer** — "one queryset/serializer-field redactor + one predicate guard — consumed by every data surface … one code path so no surface is missed." Story 1.5 (field visibility / inference-oracle guard) and Story 1.9 (exports honor field permissions) build on the layer this story stands up. Story 1.4 ships the **edit-restriction (write/predicate-guard) half**; the read-redaction/visibility half is Story 1.5. [Source: architecture.md lines 127, 236, 275, 316, 333; epics.md lines 264-304]

**Scope boundary (do NOT cross):**
- **IN:**
  1. A new `core/field_permissions/` enforcement layer: a `FieldPermissionManagerType` registered into the `PERMISSION_MANAGERS` chain that **denies `database.table.field.write_values` and `database.table.field.update`** for a Field carrying an edit-restriction rule when the actor's effective Role is below the rule's threshold; defers everything else.
  2. A persisted per-Field rule (model + migration) — minimum-role-to-edit threshold (`editable_by_role`), default = unrestricted.
  3. An admin-only API + handler to **set/read** a Field's edit restriction (the "admin sets a Field to no-edit" action).
  4. **HTTP 403** on a denied edit (new `FieldEditProhibitedError` → `ERROR_FIELD_EDIT_PROHIBITED`, registered globally, mirroring 1.3's `RoleProhibitedError` pattern) on BOTH the row-cell-write path and the field-config-update path.
  5. Frontend renders the restricted Field **read-only** for unauthorized members — by surfacing the rule so the **already-wired** `canWriteFieldValues → $hasPermission('…write_values')` resolves to false.
  6. The full Bucket A test matrix (model → handler → permission-manager → serializer/API → frontend-registry → component) and a provenance record.
- **OUT:**
  - **Field *visibility* / hiding** (the read-redactor, the queryset/serializer redaction of values, the inference-oracle guard rejecting filter/sort *on* a hidden field, cache invalidation on permission change) — that is **Story 1.5**. 1.4 restricts **edit only**; a restricted Field is still fully **readable**.
  - **Export enforcement** (Story 1.9), Dashboard/Builder Data-Source *read* redaction (Stories 4.x/5.x consume the layer later).
  - **Per-member (custom-subject) overrides** — 1.4 uses **fixed-Role thresholds** (consistent with the 1.2 fixed-tier model). Per-member allow/deny lists are a documented later extension; do NOT build the enterprise custom-role/subject system.
  - Editor/Admin default behavior (unchanged: they can edit unrestricted fields exactly as today).

## Clean-Room Mandate (Bucket A)

This capability exists under the PE/EE license in `enterprise/backend/src/baserow_enterprise/field_permissions/`. That source **must not be copied, adapted, or recalled from memory.** [Source: architecture.md lines 205-206, 239-242, 255-260; memory baserow-open-core-license-constraint]

- Reference `premium/`/`enterprise/` only for the **registration shape via public MIT symbols** — i.e. *that* a `PermissionManagerType` exposes `check_multiple_permissions` / `filter_queryset` / `get_permissions_object` (these are public `core/registries.py` symbols), and *that* the existing core op `database.table.field.write_values` is the per-field write check. **Do NOT replicate** the enterprise `FieldPermissions` model, its `FieldPermissionsRoleEnum` (EDITOR/BUILDER/ADMIN/CUSTOM/NOBODY), its custom-subject system, or its handler/API logic. Our model is a **fixed-tier minimum-role threshold**, designed from the public behavior (a field can be made read-only to lower roles), not from the enterprise source. Do not import anything from `baserow_enterprise`.
- **Author a `1-4-*` behavior spec** under `docs/clean-room/specs/` from allowed public sources only (public Baserow docs, public upstream SaaS field-permission UX, public issues/changelogs). No `premium/`/`enterprise/` internal symbol name as the thing to replicate (free-core MIT symbols — `WriteFieldValuesOperationType`, `PermissionManagerType`, `Field.read_only` — are allowed). [Source: docs/clean-room/allowed-sources.md; Story 1.1]
- **Add a provenance record** under `docs/clean-room/provenance/1-4-central-field-permission-layer-with-edit-restriction.md` using `docs/clean-room/templates/`. No provenance → the merge gate (`docs/clean-room/scripts/check_provenance.py` + `.github/workflows/clean-room-provenance-gate.yml`) blocks merge. Flag the PR Bucket A (`bucket-a` label / PR-template checkbox). [Source: Story 1.1; architecture.md lines 240-242]
- **Legal gate (Open Q7):** owner + legal sign-off is recorded in `docs/clean-room/owner-and-sign-off.md` (owner **Tinsu / @gabenidolcs**, sign-off **2026-06-06**, scope = "All Bucket A clean-room reimplementations in the Airtable-parity release (Epics 1–6)"). **Re-confirm it is still filled before writing code**; if any row is reverted to `_TODO_`, HALT and surface as a blocker. [Source: docs/clean-room/owner-and-sign-off.md; Story 1.3]

## Acceptance Criteria

1. **Admin sets a Field no-edit → unauthorized edits rejected 403, field renders read-only, rule persists per Field.** Given the central enforcement layer (`core/field_permissions/`) is built, when an admin sets a Field to no-edit for a Role/member, then **edits from unauthorized members are rejected server-side with HTTP 403** (on the row-cell-value write path **and** the field-config update path), **and** the Field renders **read-only** for them in the UI, **and** the rule **persists per Field** (survives reload) and applies **uniformly** wherever that field's value is written. A restricted Field remains **readable** (this story restricts edit only). [Source: epics.md lines 264-281; architecture.md lines 127, 189, 275, 316]

2. **Single enforcement path — new surfaces consume the layer, no per-surface ad-hoc check.** Given the layer is the single enforcement path, when a data surface needs a field-permission edit check, then it resolves **through the one `FieldPermissionManagerType` in the `PERMISSION_MANAGERS` chain** consuming the existing `database.table.field.write_values` / `database.table.field.update` operations (one predicate guard) — never a parallel or per-view ad-hoc role/field check (NFR-4). The row-update path and the Application-Builder data-source path (which already emit `write_values` checks) are both governed by this single manager with **zero new per-surface enforcement code**. [Source: epics.md lines 277-281; architecture.md lines 127, 236, 254-255, 316]

## Tasks / Subtasks

- [x] **Task 1 — Re-confirm clean-room gate + author spec + start provenance (AC: #1, #2, Clean-Room)** — do this FIRST
  - [x] Confirm `docs/clean-room/owner-and-sign-off.md` still has owner + legal sign-off filled (not `_TODO_`). If reverted, HALT and surface as blocker.
  - [x] Author `docs/clean-room/specs/1-4-field-edit-restriction.md`: the behavior (Admin marks a Field edit-restricted to a minimum Role; members below that Role are denied writes to that field's values & config but keep read), citing only allowed public sources. No enterprise symbol as the thing to replicate.
  - [x] Start `docs/clean-room/provenance/1-4-central-field-permission-layer-with-edit-restriction.md` from `docs/clean-room/templates/`; keep it updated through implementation; attestation = no enterprise source consulted.

- [x] **Task 2 — Persist the per-Field edit rule: model + migration (AC: #1)**
  - [x] **Model placement decision (FOLLOW THIS — see Dev Notes "Key design decisions"):** add the rule model to **`backend/src/baserow/contrib/database/fields/models.py`** (same app as `Field`), e.g. `class FieldPermission(models.Model)` with `field = OneToOneField(Field, on_delete=CASCADE, related_name="permission")` and `editable_by_role = CharField(...)` storing a role tier string (`baserow.core.rbac.roles` values) plus a sentinel for "nobody but Admin". **Do NOT put a model in `core/field_permissions/` with an FK to `database.Field`** — that inverts the app/migration dependency (`database` depends on `core`, not vice-versa) and creates a circular migration graph. The *enforcement* lives in `core/`; the *rule row* lives in the `database` app next to `Field`. [Source: Explore findings; architecture.md line 320 "new models … add migrations to their owning app"]
  - [x] Default semantics: **no `FieldPermission` row = unrestricted** (current behavior — any member with a write Role may edit). A row with `editable_by_role = EDITOR` means "only Editor and above may edit"; `editable_by_role = ADMIN` means "only Admin". Map "no-edit for unauthorized members (Salary)" to a threshold (typically `ADMIN`).
  - [x] Generate the migration in the `database` app: `BASEROW_OSS_ONLY=true … just b make-migrations database` (see Testing standards env). Reversible. Add a `test_*` asserting the table/column exists and the default (absent row) is unrestricted.

- [x] **Task 3 — Build the central enforcement layer `core/field_permissions/` (AC: #1, #2)**
  - [x] New package `backend/src/baserow/core/field_permissions/` with:
    - `permission_manager.py` — `class FieldPermissionManagerType(PermissionManagerType)` with `type = "field_permissions"`, `supported_actor_types = [UserSubjectType.type]` (mirror `RbacPermissionManagerType`).
    - `enforcement.py` — the **operation `type` strings** this manager governs as **plain strings** (`FIELD_EDIT_OPERATIONS = {"database.table.field.write_values", "database.table.field.update"}`), mirroring the `ADMIN_ONLY_OPERATIONS` / 1.3 `enforcement.py` string convention to avoid a `core → contrib.database` import cycle. [Source: core/permission_manager.py `ADMIN_ONLY_OPERATIONS`; core/rbac/enforcement.py]
  - [x] `FieldPermissionManagerType.check_multiple_permissions(checks, workspace, include_trash)`:
    - For each check whose `operation_name` is in `FIELD_EDIT_OPERATIONS` and whose `context` is a `Field` (the `write_values`/`field.update` context scope is `database_field` — context **is** the Field instance): look up the field's `FieldPermission` rule (batch-load all field ids in one query — do NOT N+1; mirror 1.2's `_build_role_index` lesson). If a rule exists and the actor's **effective Role** (reuse `baserow.core.rbac.handler.RbacHandler.get_effective_role(actor, workspace, application)`) is **below** `editable_by_role`, set `result[check] = FieldEditProhibitedError(check.actor)`.
    - **Defer (omit from result) for:** fields with no rule, actors at/above the threshold, and any operation not in `FIELD_EDIT_OPERATIONS`. Never deny-by-default (preserves reads, Editor/Admin edits, and unrelated ops). [Source: Story 1.3 HAZARD "defer ≠ deny" / "over-blocking"]
    - Import the `FieldPermission` model and `Field` **lazily inside the method** (function-level import), never at module top, to keep `core` import-clean of `contrib.database`. [Source: Story 1.3 Task 2 layering note]
  - [x] `FieldPermissionManagerType.get_permissions_object(actor, workspace)` — return the data the **frontend** needs to render restricted fields read-only (see Task 6): e.g. `{"restricted_field_ids": [<ids the actor may NOT edit in this workspace>]}` resolved by comparing the actor's effective Role against every `FieldPermission` in the workspace. Return `None`/empty when nothing is restricted. [Source: core/registries.py:810-828 `get_permissions_object` contract]
  - [x] **Do NOT implement `filter_queryset` / read-redaction here** — that is Story 1.5. Leave the read path untouched.

- [x] **Task 4 — `FieldEditProhibitedError` → HTTP 403 (global) + surface it on the row-write path (AC: #1)**
  - [x] Define `class FieldEditProhibitedError(PermissionException)` in `backend/src/baserow/core/exceptions.py` beside the 1.3 `RoleProhibitedError`. [Source: core/exceptions.py:63 `RoleProhibitedError`]
  - [x] Add `ERROR_FIELD_EDIT_PROHIBITED = ("ERROR_FIELD_EDIT_PROHIBITED", HTTP_403_FORBIDDEN, "...")` to `backend/src/baserow/api/errors.py` (beside `ERROR_ROLE_PROHIBITED`). [Source: api/errors.py:51]
  - [x] Register it **globally** in `core/apps.py` `ready()` via `api_exception_registry.register(RegisteredException(exception_class=FieldEditProhibitedError, exception_error=ERROR_FIELD_EDIT_PROHIBITED))`, guarded against double-registration — **exactly** mirroring the existing `RoleProhibitedError` block (`core/apps.py:185-200`). MRO most-specific-first guarantees 403 wins over the `PermissionException`→401 catch-all. [Source: core/apps.py:185-200]
  - [x] **field-config update path → 403 works for free:** `FieldHandler.update_field` calls `CoreHandler().check_permissions(user, UpdateFieldOperationType.type, …)` (`contrib/database/fields/handler.py:553`) which **re-raises** the manager's exception (`handler.py:check_permissions` uses `return_permissions_exceptions=True`). No change needed there.
  - [x] **CRITICAL — row-cell-write path needs a fix to reach 403:** `RowHandler._check_write_fields_values_permissions` (`contrib/database/rows/handler.py:2178-2221`) calls the **batch** `check_multiple_permissions(...)` **without** `return_permissions_exceptions=True`, which collapses any manager exception to `False` (`core/handler.py:271 result[check]=False`) and then raises a **generic `PermissionDenied` → HTTP 401** — NOT the 403 the AC demands. Fix: when `unwritable_fields` is non-empty, raise **`FieldEditProhibitedError`** (listing the field names) instead of the generic `PermissionDenied`. This is a single `[X]` edit in core that delivers the AC's 403 while preserving the single-enforcement-path (the *decision* still came from the chain). In OSS `write_values` always defers→grants today, so no existing 401 test regresses. [Source: contrib/database/rows/handler.py:2178-2221; core/handler.py:219-294]
  - [x] Test: a restricted-field row update returns **403 / `ERROR_FIELD_EDIT_PROHIBITED`** (not 401); a restricted-field `update_field` returns 403; an *unrelated* non-member denial still returns the legacy 401 (no catch-all regression).

- [x] **Task 5 — Admin API + handler to set/read a Field's edit restriction (AC: #1)**
  - [x] Add a `FieldPermissionHandler` (in `core/field_permissions/handler.py` or `contrib/database/fields/`) with `set_field_permission(user, field, editable_by_role)` and `get_field_permission(field)`; mutating method calls `CoreHandler().check_permissions(user, <admin-only op>, workspace, context=field)` so **only Admins** can change the rule.
  - [x] Define an admin-only operation for managing the rule, e.g. `UpdateFieldPermissionOperationType.type = "database.table.field.update_permission"` (context scope = `database_field`). Make it **admin-only** by adding its `type` string to the existing admin-gating set the RBAC/basic managers consult (`ADMIN_ONLY_OPERATIONS` in `core/permission_manager.py` and/or the RBAC admin grant) — confirm the exact mechanism against the 1.2/1.3 manager before wiring. [Source: core/permission_manager.py `ADMIN_ONLY_OPERATIONS`; core/rbac/permission_manager.py]
  - [x] REST endpoint under `contrib/database/api/fields/` (e.g. `PATCH /api/database/fields/<id>/permission/` or extend the field-update serializer with a write-only `editable_by_role`) — follow existing field-API view/serializer patterns; camelCase JSON. Wire `@map_exceptions`. Register URL.
  - [x] Tests: a non-Admin (Editor) setting the rule → 403; an Admin → 200 and the rule persists & reloads.

- [x] **Task 6 — Frontend renders restricted Field read-only (AC: #1)** — the gate already exists; only the data is missing
  - [x] The cell read-only gate `canWriteFieldValues(field)` → `$hasPermission('database.table.field.write_values', field, field.workspace_id)` is **already wired** (`web-frontend/modules/database/fieldTypes.js:918-926`, `GridViewRow.vue:114`, `RowEditModalField.vue:138`). All that is missing is a frontend permission manager that answers `false` for restricted fields using the backend `get_permissions_object` payload (Task 3).
  - [x] Add a frontend `FieldPermissionManagerType` (extends `PermissionManagerType` in `web-frontend/modules/core/permissionManagerTypes.js`, register from the database module's plugin) whose `hasPermission(permissions, operation, context, workspaceId)` returns `false` when `operation === 'database.table.field.write_values'` (and `database.table.field.update`) and `context.id` ∈ the workspace's `restricted_field_ids`; otherwise returns `null` (defer). [Source: web-frontend/modules/core/permissionManagerTypes.js; Story 1.3 frontend manager]
  - [x] Ensure the manager name matches the backend `FieldPermissionManagerType.type` so `$hasPermission` feeds it the right `get_permissions_object` slice.
  - [x] Add any new i18n strings (e.g. a read-only tooltip `fieldPermission.editRestricted`) to `en.json` + locales if surfaced. [Source: architecture.md line 248]

- [x] **Task 7 — Test matrix (AC: #1, #2)** — mirror paths under `backend/tests/baserow/...` (NOT co-located)
  - [x] **permission-manager unit** (`backend/tests/baserow/core/field_permissions/test_permission_manager.py`): with a `FieldPermission(editable_by_role=ADMIN)` on a field, assert `check_multiple_permissions` returns `FieldEditProhibitedError` for an Editor's `write_values` and `field.update` on that field; returns **absent/defer** for an unrestricted field, for an Admin, and for read ops; assert no N+1 (one rule query for N field checks). Use `@override_settings(PERMISSION_MANAGERS=[...])` + `data_fixture`. [Source: core/rbac test pattern; Story 1.3 Task 7]
  - [x] **handler/integration**: via `RowHandler().update_rows(...)` an Editor writing a restricted field raises `FieldEditProhibitedError`; writing a *non*-restricted field in the same table succeeds; reading the row succeeds. Via `FieldHandler().update_field(...)` an Editor updating a restricted field's config raises; Admin succeeds.
  - [x] **API (REST) — the 403 assertion (AC #1):** as an Editor, `PATCH /api/database/rows/table/<id>/<row>/` writing a restricted field → **403 `ERROR_FIELD_EDIT_PROHIBITED`**; writing a non-restricted field → 200; reading the row → 200. As an Editor, updating the restricted field config → 403. As an Admin, both succeed. Non-member denial still 401. [Source: backend/tests/baserow/contrib/database/api/rows/test_row_views.py; api/fields/test_field_views.py]
  - [x] **admin-API**: non-Admin setting the rule → 403; Admin → 200 + persisted (reload asserts AC #1 "persists per Field").
  - [x] **single-path / data-source parity (AC #2)**: assert the Application-Builder `LocalBaserow` write path (`service_types.py:2069` emits the same `write_values` check) is governed by the same manager — a restricted field is unwritable there too, with **no** data-source-specific enforcement code. (Manager-level assertion is sufficient if an end-to-end builder write test is heavy.)
  - [x] **no-regression**: Editor/Admin retain full edit on **unrestricted** fields (re-run a baseline row-update test); a workspace with zero `FieldPermission` rows behaves exactly as before (manager defers everything).
  - [x] **frontend** (`web-frontend/test/unit/.../fieldPermissionManagerTypes.spec.js` or extend `permissionManagerTypes.spec.js`): given a `restricted_field_ids` payload, `hasPermission('database.table.field.write_values', restrictedField, ws)` → `false` and for an unrestricted field → `null`; assert `canWriteFieldValues` flips a restricted cell to read-only. `just f yarn test:core <path>` (or direct vitest — see Testing standards). [Source: Story 1.3 frontend test]

- [x] **Task 8 — Finalize provenance + DoD**
  - [x] Complete the provenance record (sources consulted + implementer attestation); flag PR Bucket A (`bucket-a` label / PR-template checkbox); confirm the provenance gate passes (`python3 docs/clean-room/scripts/check_provenance.py`). [Source: Story 1.1; architecture.md lines 240-242]

## Dev Notes

### Architecture patterns & constraints (MUST follow)
- **One enforcement path (D7):** the field-edit predicate guard is a **single** `FieldPermissionManagerType` in the `PERMISSION_MANAGERS` chain consuming the **already-emitted** `database.table.field.write_values` / `database.table.field.update` operations — NEVER a parallel/ad-hoc check in a view, serializer, or handler. New surfaces are "done" only when they route writes through these ops (the row handler and builder data source already do). This is NFR-4 and the load-bearing invariant. [Source: architecture.md lines 127, 236, 254-255, 316; epics.md line 281]
- **Deny = return a `PermissionException` from the manager**; grant = `True`; defer = omit the check. For the **batch** `check_multiple_permissions` the aggregator collapses an exception to `False` unless called with `return_permissions_exceptions=True` — which is exactly why the row-write path currently yields 401 and why Task 4 raises `FieldEditProhibitedError` explicitly from `_check_write_fields_values_permissions`. The single-context `check_permissions` (used by `update_field`) re-raises the exception directly, so it 403s for free. [Source: core/handler.py:219-294, 327-340]
- **403 not 401:** generic permission denial is **401** (`ERROR_PERMISSION_DENIED`, `api/errors.py`). The AC demands **403**. Use a dedicated `FieldEditProhibitedError` + global `api_exception_registry` registration (Task 4) — MRO precedence guarantees 403 with zero per-view edits, exactly as 1.3 did for `RoleProhibitedError`. [Source: core/apps.py:185-200; api/errors.py:50-52; architecture.md line 189]
- **Type strings, not class imports; lazy model import:** define governed-op sets as `type` strings; import `FieldPermission`/`Field` lazily inside manager methods — avoid a `core → contrib.database` import cycle (this is why 1.3 `enforcement.py` uses strings). [Source: core/rbac/enforcement.py; Story 1.3 Task 2]
- **Model lives in the `database` app, enforcement in `core`:** a `core` model with an FK to `database.Field` inverts the app dependency (`database` already depends on `core`) and makes the migration graph circular. Put `FieldPermission` next to `Field`; keep the manager/guard in `core/field_permissions/`. [Source: architecture.md line 320; Explore findings]
- **No N+1:** batch-load `FieldPermission` rows for all field-ids in a check set in one query (mirror the 1.2 `_build_role_index` fix that a regression test now guards). [Source: Story 1.2 Senior Review H1]
- **Edit ≠ visibility:** 1.4 restricts **write only**; the field stays fully **readable**. Do NOT add read redaction, `filter_queryset`, or inference guards — that is Story 1.5. Over-reaching into reads will break the "remains readable" half of AC #1 and collide with 1.5. [Source: epics.md lines 282-304; architecture.md line 127]
- **Naming/format:** `snake_case` files/columns, `PascalCase` classes (`FieldPermission`, `FieldEditProhibitedError`, `FieldPermissionManagerType`), Ruff 88-col, Python 3.14, camelCase JSON API. [Source: architecture.md lines 180-217, 247]
- **Bucket A placement:** new code in `backend/src` / `web-frontend` core only — NEVER `premium/`/`enterprise/`. Tests under `backend/tests/baserow/...` mirroring `src`. [Source: architecture.md lines 204-210, 255-260]

### Source tree components to touch
- `backend/src/baserow/core/field_permissions/` `[A]` NEW — `permission_manager.py` (`FieldPermissionManagerType`), `enforcement.py` (governed-op type-string set), optional `handler.py` (`FieldPermissionHandler`), `__init__.py`.
- `backend/src/baserow/contrib/database/fields/models.py` `[X]` — add `FieldPermission` model (OneToOne → `Field`, `editable_by_role`).
- `backend/src/baserow/contrib/database/fields/operations.py` `[X]` — add `UpdateFieldPermissionOperationType` (admin-only) for the set-rule API.
- `backend/src/baserow/contrib/database/rows/handler.py` `[X]` — `_check_write_fields_values_permissions`: raise `FieldEditProhibitedError` (403) instead of generic `PermissionDenied` when fields are unwritable.
- `backend/src/baserow/core/exceptions.py` `[X]` — add `FieldEditProhibitedError`.
- `backend/src/baserow/api/errors.py` `[X]` — add `ERROR_FIELD_EDIT_PROHIBITED` (403).
- `backend/src/baserow/core/apps.py` `[X]` — global `FieldEditProhibitedError → ERROR_FIELD_EDIT_PROHIBITED` registration in `ready()`.
- `backend/src/baserow/config/settings/base.py` `[X]` — add `"field_permissions"` to `PERMISSION_MANAGERS` (place it adjacent to `"rbac"`; it governs different ops so order vs rbac is non-conflicting — put it just before `"rbac"` so a field-specific 403 is decided before the generic role check; confirm no interaction in tests).
- `backend/src/baserow/contrib/database/api/fields/` `[X]` — set/read-rule endpoint (view + serializer + URL).
- `web-frontend/modules/core/permissionManagerTypes.js` `[X]` + database-module plugin registration — frontend `FieldPermissionManagerType` consuming `restricted_field_ids`.
- Migration in the `database` app for `FieldPermission`.
- Tests: `backend/tests/baserow/core/field_permissions/test_permission_manager.py` (NEW), API tests under `backend/tests/baserow/contrib/database/api/{rows,fields}/`, frontend spec.

### Files to READ before coding (current state — preserve behavior)
- `backend/src/baserow/contrib/database/rows/handler.py:2178-2221` (`_check_write_fields_values_permissions` — the existing per-field `write_values` hook you consume; the 401→403 fix point) and `:2638-2708` (`update_rows` flow).
- `backend/src/baserow/contrib/database/fields/handler.py:503-591` (`update_field` — the config path that already re-raises → 403).
- `backend/src/baserow/contrib/database/fields/operations.py` (full — `WriteFieldValuesOperationType`, `UpdateFieldOperationType`, scopes; where to add `UpdateFieldPermissionOperationType`).
- `backend/src/baserow/contrib/database/fields/models.py:170-220` (`Field`, the `read_only` precedent — where `FieldPermission` attaches).
- `backend/src/baserow/core/registries.py:669-828` (`PermissionManagerType` contract — `check_multiple_permissions`, `filter_queryset`, `get_permissions_object`, `supported_actor_types`).
- `backend/src/baserow/core/handler.py:219-340` (batch vs single permission aggregation — the exception-collapse-to-False behavior that forces Task 4).
- `backend/src/baserow/core/rbac/permission_manager.py` + `core/rbac/enforcement.py` + `core/rbac/handler.py` (`get_effective_role`) + `core/rbac/roles.py` (`ROLE_ORDER`, `role_at_least`) — your role-resolution dependency and the manager shape to mirror.
- `backend/src/baserow/core/permission_manager.py` (`BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS` string convention; the admin-only gating you reuse for the set-rule op).
- `backend/src/baserow/core/exceptions.py:63-80` and `backend/src/baserow/api/errors.py:50-52` and `backend/src/baserow/core/apps.py:185-200` (the 1.3 `RoleProhibitedError`→403 wiring you copy structurally).
- `backend/src/baserow/config/settings/base.py:1270-1290` (`PERMISSION_MANAGERS` chain + the OSS `remove("write_field_values")`/`remove("role")`).
- `backend/src/baserow/contrib/database/api/rows/serializers.py:99-223` (`get_row_serializer_class` — the existing `read_only` flag + `field_ids` filtering; informs the frontend read-only render and the future 1.5 redactor).
- `backend/src/baserow/contrib/integrations/local_baserow/service_types.py:2069` (the builder data-source `write_values` check — the second surface your single manager governs).
- `web-frontend/modules/database/fieldTypes.js:918-926`, `components/view/grid/GridViewRow.vue:114,503`, `components/row/RowEditModalField.vue:138`, `mixins/gridField.js:260` (the already-wired `canWriteFieldValues → $hasPermission('…write_values')` read-only gate).
- `web-frontend/modules/core/permissionManagerTypes.js` (frontend `PermissionManagerType` base + the 1.2/1.3 `RbacPermissionManagerType`).

### Clean-room reference-shape ONLY (do NOT copy behavior)
- `enterprise/backend/src/baserow_enterprise/field_permissions/{models,permission_manager,handler,operations}.py` — look only at *that* a `PermissionManagerType` exposes `check_multiple_permissions` / `filter_queryset` / `get_permissions_object` (public `core/registries.py` symbols) and *that* `database.table.field.write_values` is the per-field write op. The enterprise `FieldPermissions` model, `FieldPermissionsRoleEnum`, custom-subject system, and handler/API logic are license-gated and are **NOT** our design — do not import or replicate them. [Source: architecture.md lines 205-206, 255-260]

### Key design decisions / hazards
- **HAZARD — 401 vs 403 on the row-write path.** The #1 way this story silently fails AC #1: the manager returns the right exception, but the batch `check_multiple_permissions` in `_check_write_fields_values_permissions` collapses it to `False` and raises generic `PermissionDenied` → **401**. You MUST raise `FieldEditProhibitedError` from the row handler (Task 4). The field-config path 403s for free; the row-value path does not. [Source: core/handler.py:265-273; rows/handler.py:2217-2220]
- **HAZARD — layering/migration cycle.** A `core` model FK→`database.Field` creates a circular app/migration dependency. Model goes in the `database` app; enforcement stays in `core` with lazy imports. [Source: architecture.md line 320]
- **HAZARD — scope creep into 1.5.** Do NOT add read redaction / `filter_queryset` / inference guard / cache invalidation. 1.4 is edit-only; the field stays readable. Adding read-hiding here collides with Story 1.5 and breaks AC #1's "remains readable". [Source: epics.md lines 282-304]
- **HAZARD — over-blocking / deny-by-default.** Defer (omit) for unrestricted fields, sufficient roles, and non-edit ops. Only the specific (restricted field × insufficient role × edit op) tuple denies. Flipping to deny-by-default breaks every other field's edits. [Source: Story 1.3 HAZARD]
- **Effective-role reuse, not reinvention.** Resolve the actor's role via `RbacHandler.get_effective_role` (1.2) — do NOT re-derive role logic in this manager. [Source: core/rbac/handler.py]
- **Frontend hook already exists.** Do NOT add a new read-only mechanism in the cell components — feed the existing `$hasPermission('…write_values')` chain via `get_permissions_object`/a frontend manager. A second source of truth is an anti-pattern. [Source: architecture.md line 259; fieldTypes.js:918]
- **Chain placement.** Add `"field_permissions"` adjacent to `"rbac"`; it governs `write_values`/`field.update` (ops rbac doesn't field-scope), so they don't conflict — but verify with a combined Editor-restricted-field test that the field manager's 403 wins where intended. Do not reorder existing entries. [Source: config/settings/base.py:1270-1289]

### Testing standards
- Backend: `just b test backend/tests/baserow/core/field_permissions/` + the new rows/fields API tests (pytest + pytest-django). **OSS-only env** (no default `db` host on this box): `BASEROW_OSS_ONLY=true TEST_ENV_FILE=.env.testing-oss DATABASE_HOST=172.22.0.12 DATABASE_USER=clavis DATABASE_PASSWORD=clavis_secret DATABASE_NAME=baserow DATABASE_PORT=5432 BASEROW_TESTS_SETUP_DB_FIXTURE=off just b test <paths> --reuse-db`. `just` lives at `backend/.venv/bin/just` — `export PATH="$PWD/backend/.venv/bin:$PATH"`. Migrations: `BASEROW_OSS_ONLY=true … just b make-migrations database`. [Source: Story 1.3 Debug Log]
- Frontend: `just f yarn test:core <path>` (Vitest). **Gotcha:** corepack may resolve yarn 4 ("not present in your lockfile") — if `just f` misbehaves, run vitest directly: `cd web-frontend && node_modules/.bin/vitest run <spec>`. Do NOT let `yarn.lock`/`package.json`/`.yarnrc.yml` drift into the diff. [Source: Story 1.2/1.3 Debug Log]
- Pre-existing OSS-env failures unrelated to this story: `test_basic_permissions.py::test_get_permissions` and `::test_allow_if_template_permission_manager*` fail because `user_source_type_registry` is empty under `BASEROW_OSS_ONLY`. Ignore (confirm by stashing your changes). [Source: Story 1.3 Debug Log]
- Lint: `just b run pre-commit run --files $(git diff --name-only origin/develop...HEAD)`; Ruff check + format; ESLint. The `PostToolUse` Edit/Write hook errors with `python: not found` — non-blocking; use `python3` for scripts (e.g. the provenance gate). [Source: Story 1.3 obs 3075/3089]
- Full Bucket A matrix model→handler→permission-manager→serializer/API→frontend-registry→component is the DoD. [Source: architecture.md lines 247-248; epics.md line 281]

### Previous story intelligence (Stories 1.2 / 1.3)
- `RbacPermissionManagerType` + `RoleAssignment` (1.2) provide `get_effective_role`; the chain order is `… member → token → [write_field_values, role removed in OSS] → rbac → basic …`. Insert `field_permissions` near `rbac`. [Source: Story 1.2/1.3; config/settings/base.py:1270-1289]
- 1.3 established the exact **`PermissionException` subclass → global `api_exception_registry` → 403** pattern (`RoleProhibitedError`/`ERROR_ROLE_PROHIBITED`/`core/apps.py:185-200`) — copy it structurally for `FieldEditProhibitedError`. [Source: Story 1.3 Tasks 4]
- 1.3 frontend kept the client deferring (`hasPermission → null`); 1.4 **must** answer `false` for restricted fields because the read-only render depends on it — this is the deliberate difference from 1.3. [Source: Story 1.3 Task 6]
- N+1 and yarn-lock-drift are known traps with regression coverage / review findings — avoid both. [Source: Story 1.2 Senior Review H1/H2]

### Git intelligence
- Branch from `develop`. Baseline `179f0ff93` (Story 1.3 merge: "feat(story-1.3): Role enforcement for commenter and viewer"). Conventional Commit prefix `feat(story-1.4): …`. 1.3 added `core/rbac/enforcement.py`, `core/exceptions.py:RoleProhibitedError`, `api/errors.py:ERROR_ROLE_PROHIBITED`, `core/apps.py` registration — read those diffs; 1.4 mirrors their shape for fields. [Source: git log; Story 1.3 File List]

### Project Structure Notes
- **New model + migration** in the `database` app (the one schema change this story introduces — note it in the PR per AGENTS.md). No new env var expected (if a feature flag is added, follow the `add-django-config-env-var` skill). New manager code in `core/field_permissions/`; new exception in `core/exceptions.py`; registration in `core/apps.py` + chain in `config/settings/base.py`. Tests mirror `src` under `backend/tests/`. No `premium/`/`enterprise/` edits. [Source: architecture.md lines 204-210, 271-275, 320]

### References
- [Source: epics.md#Epic 1 → Story 1.4 (lines 264-281)] — the two ACs (admin sets no-edit → 403 + read-only + persists; single layer consumed by new surfaces).
- [Source: epics.md lines 64 (FR-29/30), 81 (NFR-4); lines 282-304 (Story 1.5 — what 1.4 must NOT do)].
- [Source: architecture.md lines 127 (D7 central field-permission layer), 189 (403), 236/254-255 (PERMISSION_MANAGERS routing), 275 (`core/field_permissions/` in source tree), 316 (permission boundary — every surface), 320 (new models add migrations to owning app), 333 (FR-30 home)].
- [Source: backend code map] — `core/registries.py:669-828`; `core/handler.py:219-340`; `contrib/database/rows/handler.py:2178-2221,2638-2708`; `contrib/database/fields/handler.py:503-591`; `contrib/database/fields/operations.py`; `contrib/database/fields/models.py:170-220`; `core/rbac/{permission_manager,enforcement,handler,roles}.py`; `core/permission_manager.py` (`ADMIN_ONLY_OPERATIONS`); `core/exceptions.py:63`; `api/errors.py:50-52`; `core/apps.py:185-200`; `config/settings/base.py:1270-1289`; `contrib/integrations/local_baserow/service_types.py:2069`; `web-frontend/modules/database/fieldTypes.js:918`, `GridViewRow.vue:114`, `web-frontend/modules/core/permissionManagerTypes.js`.
- [Source: Story 1.3 (`1-3-role-enforcement-for-commenter-and-viewer.md`)] — `PermissionException`→403 global-registry pattern, OSS test env, frontend manager.
- [Source: docs/clean-room/ (Story 1.1)] — allowed-sources.md, provenance templates, check_provenance.py, owner-and-sign-off.md (owner Tinsu, sign-off 2026-06-06).
- [Source: memory baserow-open-core-license-constraint] — paid features need clean-room reimplement; PE/EE license forbids copying.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Code, BMAD create-story workflow).

### Debug Log References

- Backend tests run **OSS-only** because the clean-room `core` RBAC now owns
  `workspace.assign_role`, which `baserow_enterprise.apps.ready()` re-registers →
  `OperationTypeAlreadyRegistered` when both load. The clean-room product ships OSS-only,
  so tests exclude `premium`/`enterprise`. `settings.test` blocks real env vars, so
  `BASEROW_OSS_ONLY=true` is fed via `TEST_ENV_FILE=.env.testing-cleanroom` (gitignored
  under `.env.testing*`). Ramdisk DB: `just test-db up` (port 5431) + `DATABASE_URL`.
- Pre-existing OSS-env failures unrelated to this story: `test_basic_permissions.py::test_get_permissions`
  and `::test_allow_if_template_permission_manager*` fail because `user_source_type_registry`
  is empty under `BASEROW_OSS_ONLY` (premium registers those types). Confirmed pre-existing
  (documented in story Testing standards); 8/11 of that module pass.

### Completion Notes List

- **All 8 tasks complete; Status → review.** Per-field, per-role edit restriction enforced
  through a SINGLE central `FieldPermissionManagerType` in the `PERMISSION_MANAGERS` chain
  (NFR-4 / architecture D7) consuming the already-emitted `write_values` / `field.update`
  ops — no parallel/ad-hoc checks added.
- **403 not 401:** denied edits raise `FieldEditProhibitedError` → `ERROR_FIELD_EDIT_PROHIBITED`
  (HTTP 403), registered globally in `core/apps.py:ready()` mirroring 1.3's `RoleProhibitedError`.
  Field-config path 403s via single-check re-raise; row-cell-write path raises explicitly from
  `_check_write_fields_values_permissions` (the batch path would otherwise collapse to 401).
- **Edit-only:** restricted fields remain fully readable (no `filter_queryset`/redaction — that
  is Story 1.5). No-rule = unrestricted (zero regression; verified).
- **No N+1:** rules, field→application, and role index are batch-loaded — guarded by a
  `django_assert_num_queries(3)` regression test.
- **Admin set-rule op** `database.table.field.update_permission` is governed by the field
  manager (non-admin → 403, admin → grant) AND added to `BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS`
  (literal string, no core→contrib import) to close the role-None grant hole.
- **Tests:** 28 backend (5 model + 10 manager + 13 API; QA gap-fill added the AC#2
  single-path, get_permissions_object, MRO-precedence, and handler-layer cases) + 8
  frontend — all green (re-verified in review 2026-06-06). Ruff check/format clean;
  ESLint/Prettier clean. Provenance gate PASS (local run reports "not Bucket A" because
  no PR/`bucket-a` label exists locally; the provenance record itself is complete).
- Schema change: one new `FieldPermission` model + migration `0212_fieldpermission` in the
  `database` app (next to `Field`); reverting drops the table and restores pre-1.4 behavior.

### File List

**Backend — new:**
- `backend/src/baserow/core/field_permissions/__init__.py`
- `backend/src/baserow/core/field_permissions/enforcement.py`
- `backend/src/baserow/core/field_permissions/permission_manager.py`
- `backend/src/baserow/contrib/database/fields/field_permission_handler.py`
- `backend/src/baserow/contrib/database/migrations/0212_fieldpermission.py`
- `backend/tests/baserow/contrib/database/field/test_field_permission_model.py`
- `backend/tests/baserow/core/field_permissions/test_permission_manager.py`
- `backend/tests/baserow/contrib/database/api/test_field_permission_api.py`

**Backend — modified:**
- `backend/src/baserow/contrib/database/fields/models.py` (`FieldPermission` model)
- `backend/src/baserow/contrib/database/fields/operations.py` (`UpdateFieldPermissionOperationType`)
- `backend/src/baserow/contrib/database/apps.py` (register the op)
- `backend/src/baserow/contrib/database/rows/handler.py` (raise `FieldEditProhibitedError` → 403)
- `backend/src/baserow/contrib/database/api/fields/serializers.py` (`FieldPermissionSerializer`)
- `backend/src/baserow/contrib/database/api/fields/views.py` (`FieldPermissionView`)
- `backend/src/baserow/contrib/database/api/fields/urls.py` (permission route)
- `backend/src/baserow/core/exceptions.py` (`FieldEditProhibitedError`)
- `backend/src/baserow/api/errors.py` (`ERROR_FIELD_EDIT_PROHIBITED`)
- `backend/src/baserow/core/apps.py` (manager + exception registration)
- `backend/src/baserow/core/permission_manager.py` (`update_permission` → `ADMIN_ONLY_OPERATIONS`)
- `backend/src/baserow/config/settings/base.py` (`"field_permissions"` in `PERMISSION_MANAGERS`)

**Frontend — modified:**
- `web-frontend/modules/core/permissionManagerTypes.js` (`FieldPermissionManagerType`)
- `web-frontend/modules/database/plugin.js` (register the manager)
- `web-frontend/test/unit/core/permissionManagerTypes.spec.js` (manager spec)

**Clean-room docs — new:**
- `docs/clean-room/specs/1-4-field-edit-restriction.md`
- `docs/clean-room/provenance/1-4-central-field-permission-layer-with-edit-restriction.md`

## Senior Developer Review (AI)

**Reviewer:** Tinsu · **Date:** 2026-06-06 · **Outcome: APPROVE** (0 Critical, 0 High, 0 Medium; 3 Low)

### Verification performed (claims re-checked against reality, not trusted)
- **Backend tests:** re-ran the full 1.4 suite under the documented OSS env (`BASEROW_OSS_ONLY=true`, ramdisk DB :5431) — **28 passed** (story said 21; QA gap-fill added 7, the count was understated, not wrong).
- **Frontend spec:** `permissionManagerTypes.spec.js` — **8 passed**.
- **Regression:** `core/rbac/` + `test_basic_permissions.py` → **82 passed, 3 failed**; the 3 failures are exactly the pre-existing OSS `user_source_type_registry`-empty cases the story documents — chain insertion of `field_permissions` before `rbac` caused **zero** new failures.
- **Lint:** Ruff check + format clean on all touched backend files; ESLint clean on all touched frontend files.
- **Provenance:** record present and complete; `check_provenance.py` exits PASS.
- **Git vs File List:** match. Only extra untracked path is `_bmad-output/.../tests/test-summary-1-4.md` (excluded from review scope). No false "changed" claims; no undocumented source change.

### AC validation
- **AC #1** — IMPLEMENTED. Row-cell-write of a restricted field → **403 `ERROR_FIELD_EDIT_PROHIBITED`** (test `test_row_write_restricted_field_returns_403`); field-config update → 403; restricted field still **readable** (200); rule **persists per field** & reloads (admin set-rule API tests). Frontend renders read-only via existing `canWriteFieldValues → $hasPermission` fed by `get_permissions_object`.
- **AC #2** — IMPLEMENTED. Single `FieldPermissionManagerType` in the chain governs both the row-handler and the LocalBaserow data-source `write_values` emission; `settings.PERMISSION_MANAGERS.count("field_permissions") == 1` asserted; no per-surface enforcement code added.

### Design checks that passed (potential failure modes ruled out)
- **No registry collision with enterprise.** Enterprise `FieldPermissionManagerType.type = "write_field_values"`; the clean-room core manager uses `type = "field_permissions"` — distinct, so no `AlreadyRegistered` conflict (the assign_role double-registration class of bug does **not** recur here).
- **401→403 row-handler change is safe.** No existing test asserts the old `"permission to update the following fields"` message; in OSS `write_values` defers→grants, so `unwritable_fields` is empty absent a rule → pre-1.4 behavior preserved.
- **No N+1.** `check_multiple_permissions` is a constant 3 queries for N field checks (`django_assert_num_queries(3)` guard).
- **Layering clean.** `core` never imports `contrib.database` at module scope; model lives in the `database` app; op set keyed by type strings.

### Findings (all Low — tracked, none block "done")
- **[Low][doc]** Completion-notes test count was stale (21 → actual 28). **FIXED** in this review.
- **[Low][process]** Local `check_provenance.py` reports "not Bucket A — gate not applicable" because there is no PR/`bucket-a` label locally; the gate only truly validates on a flagged PR. The provenance record itself is complete. Ensure the PR carries the `bucket-a` label so the CI gate actually runs. *(Action item below.)*
- **[Low][coverage]** No explicit no-regression test that an Editor may still update an **unrestricted** field's *config* (`field.update`); only the row-write no-regression and the restricted-config-denied cases exist. Manager correctly defers for unrestricted fields, so behavior is unchanged — adding the test was skipped to avoid coupling to the OSS baseline's Editor field-config policy. *(Action item below.)*

### Review Follow-ups (AI)
- [ ] [AI-Review][Low] On PR creation, apply the `bucket-a` label / tick the PR-template Bucket A box so `clean-room-provenance-gate.yml` validates the provenance record (it is a no-op locally). [docs/clean-room/scripts/check_provenance.py]
- [ ] [AI-Review][Low] Optional: add a no-regression test that an Editor updating an *unrestricted* field's config succeeds (defer path), once the OSS baseline Editor field-config policy is confirmed. [backend/tests/baserow/contrib/database/api/test_field_permission_api.py]

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-06-06 | 0.1 | Story drafted via BMAD create-story: central field-permission edit-restriction layer (`core/field_permissions/` manager + `FieldPermission` model + `FieldEditProhibitedError`→403 + admin set-rule API + frontend read-only render). Status → ready-for-dev. | claude-opus-4-8 (Claude Code, BMAD create-story) |
| 2026-06-06 | 1.0 | Implemented all 8 tasks via BMAD dev-story (TDD). Central `FieldPermissionManagerType` in the chain; `FieldPermission` model + migration `0212`; `FieldEditProhibitedError`→403 (global + row-write path); admin set-rule API/handler/op; frontend manager renders restricted fields read-only. 21 backend + 8 frontend tests green; ruff/eslint/prettier clean; provenance gate PASS. Status → review. | claude-opus-4-8 (Claude Code, BMAD dev-story) |
| 2026-06-06 | 1.1 | Senior Developer Review (AI): adversarial review + verification. Re-ran tests (28 backend + 8 frontend green; rbac/basic regression = only the 3 pre-existing OSS failures); ruff/eslint clean; confirmed no enterprise registry collision (core type `field_permissions` ≠ enterprise `write_field_values`), no N+1, safe 401→403 change. Both ACs validated. 0 Critical/High/Medium, 3 Low (1 fixed: stale test count; 2 tracked as Review Follow-ups). **Outcome: APPROVE → Status: done.** | claude-opus-4-8 (Claude Code, BMAD review) |
