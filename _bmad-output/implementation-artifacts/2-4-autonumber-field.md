---
baseline_commit: 0d5121f4a
---

# Story 2.4: Autonumber Field

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want an Autonumber Field that assigns a stable auto-incrementing integer to each Row,
so that every Row has a durable sequence number in creation order.

Realizes FR-21. **Bucket B `[B]` — license-clean upstream implementation; no clean-room gate required.**

## Context & Scope

**Stories 2.1 (Currency Field), 2.2 (Percent Field), and 2.3 (Barcode Field) are done.**

**CRITICAL: AutonumberField is already fully implemented in upstream Baserow.** Unlike Stories 2.1–2.3 which required new code, Story 2.4 is an **adopt-and-verify** story. No new model, migration, backend type, or frontend type needs to be written. All production code exists. The only tasks are:

1. Verify the existing implementation satisfies all acceptance criteria
2. Write a frontend unit test spec (`autonumberFieldType.spec.js`) — missing, pattern exists in Stories 2.1–2.3
3. Write an E2E test (`autonumber_field.spec.ts`) — missing, pattern from `e2e-tests/tests/database/currency_field.spec.ts`
4. Update sprint-status.yaml from `backlog` → `ready-for-dev`

**What already exists (do NOT re-implement):**

| Artifact | Location | Status |
|---|---|---|
| `AutonumberField` model | `backend/src/baserow/contrib/database/fields/models.py:1003` | ✅ exists — `pass` class, inherits `Field` directly |
| Migration | `backend/src/baserow/contrib/database/migrations/0145_autonumberfield.py` | ✅ merged at 0145 |
| `AutonumberFieldType` backend | `field_types.py:7363` — extends `ReadOnlyFieldType` | ✅ fully implemented |
| Frontend `AutonumberFieldType` | `web-frontend/modules/database/fieldTypes.js:5040` | ✅ fully implemented |
| `FieldAutonumberSubForm.vue` | `components/field/FieldAutonumberSubForm.vue` | ✅ exists |
| `GridViewFieldAutonumber.vue` | `components/view/grid/fields/GridViewFieldAutonumber.vue` | ✅ exists |
| `FunctionalGridViewFieldAutonumber.vue` | `components/view/grid/fields/FunctionalGridViewFieldAutonumber.vue` | ✅ exists |
| `RowEditFieldAutonumber.vue` | `components/row/RowEditFieldAutonumber.vue` | ✅ exists |
| `RowCardFieldAutonumber.vue` | `components/card/RowCardFieldAutonumber.vue` | ✅ exists |
| `apps.py` registration | `apps.py:256` — `field_type_registry.register(AutonumberFieldType())` | ✅ registered |
| `plugin.js` registration | `plugin.js:719` | ✅ registered |
| Backend tests | `backend/tests/baserow/contrib/database/field/test_autonumber_field_type.py` | ✅ 712 lines, 17 tests |
| Frontend type entry in spec | `web-frontend/test/unit/database/fieldTypes.spec.js:327` | ✅ has data fixture entry |

**What does NOT exist (must create):**
- `web-frontend/test/unit/database/autonumberFieldType.spec.js` — dedicated unit spec (pattern: `barcodeFieldType.spec.js`)
- `e2e-tests/tests/database/autonumber_field.spec.ts` — E2E test (pattern: `currency_field.spec.ts`)

**Architecture reference — D10 (architecture.md line 120):**
> "Autonumber (FR-21): backed by a Postgres sequence (`nextval`), not read-then-increment — collision-free under concurrent inserts and bulk import; monotonic per Table; gaps acceptable on delete/rollback."

**Key behavioral properties of the existing implementation:**
- `AutonumberFieldType` extends `ReadOnlyFieldType` — `prepare_value_for_db()` raises `ValidationError` if called (field cannot be set manually)
- `can_be_in_form_view = False` — Autonumber field does not appear in form views
- `keep_data_on_duplication = True` — duplicated field copies existing sequence values then creates its own independent sequence
- `shouldFetchDataWhenAdded()` returns `true` — grid refreshes after field creation (critical: without this, rows show null until reload)
- Optional `view_id` parameter: when provided at field creation, orders rows by that view's active filters + sorts before assigning sequence numbers. Once assigned, values are stable even if the view changes.
- Backed by `IntegerFieldWithSequence` (`fields.py:315`) — Postgres `nextval` provides the monotonic guarantee
- `isReadOnlyField()` returns `true` — honors Epic 1 field permission layer; editors cannot edit autonumber cells

**Scope boundary:**
- **IN:** Frontend unit tests; E2E tests; sprint-status update.
- **OUT:** Any new production code — do NOT create new models, migrations, field types, Vue components, or modify `apps.py`/`plugin.js`. Running Count (2.5) is a separate story.

## Acceptance Criteria

1. **New row receives next unused integer automatically; value is not user-editable.** Given an Autonumber Field, when a new Row is created, then the grid cell displays the next integer in sequence (1-based), and attempting to edit the cell has no effect (read-only). [Source: epics.md lines 441–445]

2. **Deleted rows do not renumber others.** Given existing Rows with Autonumber values [1, 2, 3], when Row 2 is deleted, then Rows 1 and 3 retain their values (assigned values are stable, no renumbering). [Source: epics.md lines 446–449]

3. **Sequence is Postgres-sequence-backed, monotonic, collision-free; gaps are acceptable.** Given concurrent inserts or bulk import, when multiple Rows are created simultaneously, then each receives a unique integer; gaps may appear after delete/rollback but no two Rows share the same value in the same Table. [Source: epics.md lines 450–455; architecture.md D10 line 120]

## Tasks / Subtasks

- [x] **Task 1 — Verify existing implementation satisfies all ACs (AC: #1, #2, #3)**
  - [x] Read `field_types.py:7363–7570` and confirm `AutonumberFieldType` satisfies AC #1 (read-only via `ReadOnlyFieldType`), AC #2 (sequence only increments, never resets on delete), AC #3 (Postgres sequence via `IntegerFieldWithSequence`).
  - [x] Read `test_autonumber_field_type.py` and confirm: `test_autonumber_field_values_cannot_be_updated_manually` covers AC #1; `test_trash_restore_autonumber_field` covers AC #2 stability; `test_import_rows_assign_new_values` + `test_duplicate_autonumber_field` cover AC #3.
  - [x] Confirm no Epic 1 regression risk: `AutonumberFieldType.isReadOnlyField()` returns `true` in frontend — field permission layer (Story 1.4) already excludes read-only fields from edit grants. Confirm `AutonumberField` is subject to field visibility (Story 1.5): it inherits the base `Field.hidden` mechanic unchanged.
  - [x] This task requires NO code changes — it is a read-and-confirm step. If any gap is found, document it as a subtask here before proceeding.

- [x] **Task 2 — Frontend unit test: `autonumberFieldType.spec.js` (AC: #1)**
  - [x] Create `web-frontend/test/unit/database/autonumberFieldType.spec.js`. Pattern: `barcodeFieldType.spec.js` (same directory). Note: story scaffold used `toBe('42')` for `toHumanReadableString` but base impl returns `value || ''` (returns `42` not `'42'`), corrected to `toBe(42)`.
  - [x] Run: `just f test -- --reporter=verbose web-frontend/test/unit/database/autonumberFieldType.spec.js` and confirm all 6 tests pass. ✅ 6/6 passed.

- [x] **Task 3 — E2E test: `autonumber_field.spec.ts` (AC: #1, #2)**
  - [x] Create `e2e-tests/tests/database/autonumber_field.spec.ts`. Pattern: `e2e-tests/tests/database/currency_field.spec.ts`. Two tests:
    1. **Column appears after creation** — create autonumber field via API, navigate to table, assert field header is visible.
    2. **Cell is read-only** — assert `.grid-field-number` div renders and no input appears on click.
  - [x] Note: `createRows` fixture does not exist (`rows.ts` only has `updateRows`); simplified test 2 to use `firstNonPrimaryCellWrappingColumnDiv` + read-only click assertion, consistent with other field E2E patterns.
  - [x] Do NOT run E2E tests locally (requires Docker stack). File only needs to exist and be syntactically correct. ✅ File created.

- [x] **Task 4 — Update sprint-status.yaml (housekeeping)**
  - [x] Story creation already set status to `ready-for-dev`. Dev workflow set to `in-progress` at task start. Final status `review` applied at story close-out.

## Dev Notes

### Implementation is upstream — key code pointers

`AutonumberFieldType` class is at `field_types.py:7363`. It extends `ReadOnlyFieldType` (not `FieldType` directly). `ReadOnlyFieldType.prepare_value_for_db()` raises `ValidationError` — this enforces AC #1 "not user-editable" at the handler layer. No additional guard needed.

`IntegerFieldWithSequence` is at `backend/src/baserow/contrib/database/fields/fields.py:315`. It creates a Postgres `nextval` sequence column. The sequence survives row deletions (satisfies AC #2 stability) and is collision-free under concurrent inserts (satisfies AC #3).

`FieldAutonumberSubForm.vue` has only `view_id` as an `allowedValues` entry. The `getDefaultValues()` method returns `{ view_id: this.view.id }` — it automatically scopes initial numbering to the current view when a user creates the field from within a view context. Passing `view_id=null` numbers rows in DB creation order.

### Frontend tests — `toHumanReadableString` base method

`AutonumberFieldType` does not override `toHumanReadableString`. The base `FieldType.toHumanReadableString(field, value)` returns `String(value ?? '')`. For an integer value `42` this returns `'42'`; for `null` it returns `''`. Confirm via `fieldTypes.js` grep before writing tests.

### E2E test — read-only cell assertion

Autonumber cells render via `GridViewFieldAutonumber.vue` which uses only `class="grid-view__cell active"` — there is no `<input>` or `contenteditable`. To assert read-only: click the cell and assert `page.locator('.grid-view__cell.active input')` is not visible (or has count 0). Do not assert on error messages — the field simply refuses to enter edit mode.

### Field permissions integration (Epic 1) — no action required

- `isReadOnlyField()` returns `true` → the Epic 1 field permission layer (`Story 1.4`) already prevents edit grants for read-only fields. No additional permission check needed.
- Field visibility (`Story 1.5`): Autonumber inherits base `Field.hidden` — if hidden, the field column is excluded from grid response. No special case needed.
- Export honor (`Story 1.9`): integer value, included in exports by default.

### Test run commands

```bash
# Frontend unit tests only
just f test -- --reporter=verbose web-frontend/test/unit/database/autonumberFieldType.spec.js

# All field type unit tests (regression check)
just f test -- --reporter=verbose web-frontend/test/unit/database/

# E2E tests require Docker stack — do not run locally
```

### Project Structure Notes

- New frontend test: `web-frontend/test/unit/database/autonumberFieldType.spec.js` (mirrors `barcodeFieldType.spec.js`)
- New E2E test: `e2e-tests/tests/database/autonumber_field.spec.ts` (mirrors `currency_field.spec.ts`)
- Sprint status update: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- **No other files should be modified.** Production code is complete.

### References

- [Source: epics.md lines 437–455] — Story 2.4 ACs and sequence behavior spec
- [Source: architecture.md line 120] — D10 autonumber decision: Postgres sequence, not read-then-increment
- [Source: backend/src/baserow/contrib/database/fields/field_types.py:7363] — `AutonumberFieldType` implementation
- [Source: backend/src/baserow/contrib/database/fields/models.py:1003] — `AutonumberField` model
- [Source: backend/src/baserow/contrib/database/migrations/0145_autonumberfield.py] — migration (already applied)
- [Source: web-frontend/modules/database/fieldTypes.js:5040] — `AutonumberFieldType` frontend
- [Source: web-frontend/modules/database/components/field/FieldAutonumberSubForm.vue] — subform (view_id only)
- [Source: web-frontend/modules/database/components/view/grid/fields/GridViewFieldAutonumber.vue] — grid cell
- [Source: backend/tests/baserow/contrib/database/field/test_autonumber_field_type.py] — 17 existing backend tests
- [Source: web-frontend/test/unit/database/barcodeFieldType.spec.js] — frontend test pattern to follow
- [Source: e2e-tests/tests/database/currency_field.spec.ts] — E2E test pattern to follow

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Adopt-and-verify story — no new production code written. All 14 upstream artifacts verified against ACs.
- `toHumanReadableString` base impl returns `value || ''` (not `String(value ?? '')`); test uses `toBe(42)` not `toBe('42')`.
- `createRows` fixture does not exist in `e2e-tests/fixtures/database/rows.ts`; E2E test 2 uses `firstNonPrimaryCellWrappingColumnDiv` + read-only click assertion instead.
- All 6 frontend unit tests pass (vitest run confirmed).

### File List

- `web-frontend/test/unit/database/autonumberFieldType.spec.js` (new)
- `e2e-tests/tests/database/autonumber_field.spec.ts` (new)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (updated)
- `_bmad-output/implementation-artifacts/2-4-autonumber-field.md` (updated)
