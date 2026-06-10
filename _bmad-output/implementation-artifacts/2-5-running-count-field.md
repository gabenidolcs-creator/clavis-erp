---
baseline_commit: 355b79bf6
---

# Story 2.5: Running Count Field

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want a Running Count Field that counts Rows matching a condition,
so that I can see how many Rows satisfy a filter without a formula.

Realizes FR-21B. **Bucket B `[B]` — license-clean new implementation; no clean-room gate required.**

## Context & Scope

**Stories 2.1–2.4 are done.** This is the final field type in Epic 2.

**What this story builds:** A new `RunningCountField` model and `RunningCountFieldType`. Unlike the relational `CountFieldType` (which counts linked rows via a `through_field`), Running Count counts rows **in the same table** matching an optional filter condition. For V1, the default scope is whole-table (no filter). **Every row in the table shows the same count value.**

**Architecture reference (architecture.md line 122):**
> "Running Count computes count-of-matching-rows (default whole-table filter). New field metadata only — migration on field-metadata model, not user tables (dynamic-model pattern)."

**Open Q11 resolution (architecture.md line 104):**
> "Running Count default whole-table scope (Q11 → whole-table)"

**How it differs from existing `CountFieldType` (field_types.py:6089):**
- `CountFieldType` extends `FormulaFieldType`; counts rows in a **linked/related** table via `through_field` (a `LinkRowField`).
- `RunningCountFieldType` extends `ReadOnlyFieldType`; counts rows in the **same** table. No formula engine involved. **Do NOT extend `FormulaFieldType` or `CountFieldType`.**

**V1 scope boundary:**
- **IN:** Whole-table count (no filter condition applied). `filter_conditions` JSONField on the model, always `null` for V1. Field is read-only, value updates on row create/delete. Full component set, registration, tests.
- **OUT:** Filter condition configuration UI (SubForm is a no-op stub for V1; conditions are persisted in model for future use). Per-grouping scope. Camera input. Any changes to existing `CountFieldType`/`CountField`.

**Implementation approach — stored integer column + update hooks:**
- `get_model_field()` returns `models.IntegerField(null=True)` — value stored per-row in the dynamic model table (same as `AutonumberField` stores its sequence value).
- `after_create()` — compute count and bulk-update ALL rows.
- `after_rows_created()` (FieldType hook, registries.py:1187) — recompute and bulk-update ALL rows. Called by `RowHandler.create_rows()` (rows/handler.py:1641).
- `rows_deleted` Django signal (rows/signals.py:12) connected in `apps.py` ready() — recompute on deletion.
- **Why stored, not annotated:** The annotation approach (Subquery via `enhance_queryset`) would require `get_model_field()` to return a computed/virtual field. Baserow's queryset machinery does not have a supported path for purely virtual fields without a DB column; all existing read-only fields (Autonumber, Formula, Count, Lookup) store their values. Use stored integer.

**Key file locations:**
- `backend/src/baserow/contrib/database/fields/models.py` — add `RunningCountField` after `AutonumberField` (~line 1007)
- `backend/src/baserow/contrib/database/fields/field_types.py` — add `RunningCountFieldType` after `AutonumberFieldType` (~line 7530+)
- `backend/src/baserow/contrib/database/migrations/` — next migration after `0218_barcodefield_alter_formview_mode.py` = `0219_runningcountfield.py`
- `backend/src/baserow/contrib/database/apps.py` — register at ~line 256 (after `AutonumberFieldType`)
- `web-frontend/modules/database/fieldTypes.js` — add `RunningCountFieldType` after `AutonumberFieldType` (~line 5135+)
- `web-frontend/modules/database/plugin.js` — register after AutonumberFieldType line 719

## Acceptance Criteria

1. **Running Count Field displays the total row count for the table (whole-table scope).** Given a Running Count Field with default configuration (`filter_conditions = null`), when the field is added to a table with N non-trashed rows, then every row's Running Count cell displays `N`, and the field is not user-editable (read-only). [Source: epics.md lines 461–465; architecture.md line 122]

2. **Count updates on row create.** Given a Running Count Field, when a new row is created in the table, then all rows (including the new one) show the updated count. [Source: epics.md lines 462–465]

3. **Count updates on row delete.** Given a Running Count Field, when a row is deleted from the table, then all remaining rows show the decremented count. [Source: epics.md lines 462–465]

4. **Existing relational Count behavior is unaffected.** Given any table with an existing `CountFieldType` (linked-row count via `through_field`), when a Running Count Field is added or rows are mutated, then the linked-row count values are unchanged and the field type registry still resolves `"count"` to `CountFieldType`. [Source: epics.md line 469]

## Tasks / Subtasks

- [x] **Task 1 — `RunningCountField` model + migration (AC: #1, #4)**
  - [x] In `backend/src/baserow/contrib/database/fields/models.py`, after `AutonumberField` (~line 1007), add:
    ```python
    class RunningCountField(Field):
        filter_conditions = models.JSONField(
            default=None,
            null=True,
            blank=True,
            help_text=(
                "Optional filter conditions in Baserow ViewFilter format. "
                "Null means count all non-trashed rows in the table (whole-table scope)."
            ),
        )

        class Meta:
            app_label = "database"
    ```
    `RunningCountField` extends `Field` directly (not `NumberField`, not `FormulaField`). The integer count is stored in the dynamic user-table column (added via `get_model_field()` in the FieldType).
  - [x] Generate migration: `just b make-migrations database`. Expected `0219_runningcountfield.py` (after `0218`). Verify: creates `database_runningcountfield` MTI table with `field_ptr_id` FK and `filter_conditions` JSONField. No column added to any user data table via migration — the integer column is added dynamically via the field-type registry.
  - [x] Confirm `0218` is the current latest migration via `ls backend/src/baserow/contrib/database/migrations/ | sort -r | head -1`.

- [x] **Task 2 — `RunningCountFieldType` backend (AC: #1, #2, #3, #4)**
  - [x] In `backend/src/baserow/contrib/database/fields/field_types.py`, import `RunningCountField` alongside `AutonumberField` at the top-of-file imports, then add after `AutonumberFieldType`:
    ```python
    class RunningCountFieldType(ReadOnlyFieldType):
        type = "running_count"
        model_class = RunningCountField
        can_be_in_form_view = False
        keep_data_on_duplication = True
        _can_have_db_index = False
        allowed_fields = ["filter_conditions"]
        serializer_field_names = ["filter_conditions"]
        serializer_field_overrides = {
            "filter_conditions": serializers.JSONField(
                required=False,
                allow_null=True,
                help_text=(
                    "Filter conditions for rows to count. Null = count all rows "
                    "(whole-table scope)."
                ),
            ),
        }

        def get_serializer_field(self, instance, **kwargs):
            return serializers.IntegerField(required=False, allow_null=True, **kwargs)

        def get_serializer_help_text(self, instance):
            return (
                "Count of rows in this table matching the configured condition. "
                "Defaults to total non-trashed row count (whole-table scope)."
            )

        def get_model_field(self, instance, **kwargs):
            return models.IntegerField(null=True, **kwargs)

        def _get_count(self, field):
            """Compute current row count for the table (V1: whole-table, no filter)."""
            model = field.table.get_model(fields=[field])
            return model.objects.filter(trashed=False).count()

        def _update_all_rows(self, field):
            """Set all rows' running_count column to the current count."""
            count = self._get_count(field)
            model = field.table.get_model(fields=[field])
            model.objects.filter(trashed=False).update(
                **{f"field_{field.id}": count}
            )

        def after_create(self, field, model, user, connection, before, field_kwargs):
            self._update_all_rows(field)

        def after_rows_created(
            self,
            field,
            rows,
            update_collector,
            field_cache,
        ):
            self._update_all_rows(field)

        def after_rows_imported(
            self,
            field,
            update_collector=None,
            field_cache=None,
            via_path_to_starting_table=None,
        ):
            self._update_all_rows(field)

        def shouldFetchDataWhenAdded(self):
            # Frontend JS method: see fieldTypes.js for the JS equivalent
            return True
    ```
  - [x] **`rows_deleted` signal handler in `apps.py`:** Connect to `rows_deleted` (rows/signals.py:12) so that deleting rows also triggers a recompute. In `apps.py`, inside `ready()`, after the existing signal connections, add:
    ```python
    from baserow.contrib.database.rows.signals import rows_deleted as _rows_deleted
    from baserow.contrib.database.fields.models import RunningCountField
    from baserow.contrib.database.fields.registries import field_type_registry

    def _on_rows_deleted(sender, rows, table, model, **kwargs):
        for field in RunningCountField.objects.filter(table=table):
            field_type = field_type_registry.get_by_model(field)
            field_type._update_all_rows(field.specific)

    _rows_deleted.connect(_on_rows_deleted)
    ```
    Place this inside `DatabaseConfig.ready()` (apps.py:~line 30), below existing signal hooks. Import `RunningCountField` here to avoid circular imports.
  - [x] Register `RunningCountFieldType` in `apps.py`: after `field_type_registry.register(AutonumberFieldType())` (~line 256), add:
    ```python
    field_type_registry.register(RunningCountFieldType())
    ```
    Also add `RunningCountFieldType` to the import at line ~197.
  - [x] Confirm `"count"` type still resolves to `CountFieldType` (not affected): `field_type_registry.get("count")` must return `CountFieldType` instance.

- [x] **Task 3 — Frontend `RunningCountFieldType` (AC: #1)**
  - [x] In `web-frontend/modules/database/fieldTypes.js`:
    - Import new Vue components at the top of the file (alongside existing autonumber imports):
      ```js
      import GridViewFieldRunningCount from '@baserow/modules/database/components/view/grid/fields/GridViewFieldRunningCount'
      import FunctionalGridViewFieldRunningCount from '@baserow/modules/database/components/view/grid/fields/FunctionalGridViewFieldRunningCount'
      import RowEditFieldRunningCount from '@baserow/modules/database/components/row/RowEditFieldRunningCount'
      import RowCardFieldRunningCount from '@baserow/modules/database/components/card/RowCardFieldRunningCount'
      import FieldRunningCountSubForm from '@baserow/modules/database/components/field/FieldRunningCountSubForm'
      ```
    - Add `RunningCountFieldType` class after `AutonumberFieldType`:
      ```js
      export class RunningCountFieldType extends FieldType {
        static getType() {
          return 'running_count'
        }

        static getIconClass() {
          return 'iconoir-stats-up-square'
        }

        getName() {
          const { $i18n: i18n } = this.app
          return i18n.t('fieldType.runningCount')
        }

        getFormViewFieldComponents(field) {
          return {}
        }

        isReadOnlyField() {
          return true
        }

        shouldFetchDataWhenAdded() {
          return true
        }

        getGridViewFieldComponent() {
          return GridViewFieldRunningCount
        }

        getFormComponent() {
          return FieldRunningCountSubForm
        }

        getFunctionalGridViewFieldComponent() {
          return FunctionalGridViewFieldRunningCount
        }

        getRowEditFieldComponent(field) {
          return RowEditFieldRunningCount
        }

        getCardComponent() {
          return RowCardFieldRunningCount
        }

        canUpsert() {
          return false
        }

        getSort(name, order) {
          return (a, b) => {
            if (a[name] === b[name]) return 0
            if ((a[name] === null && order === 'ASC') || (b[name] === null && order === 'DESC')) return -1
            if ((b[name] === null && order === 'ASC') || (a[name] === null && order === 'DESC')) return 1
            const numberA = new BigNumber(a[name])
            const numberB = new BigNumber(b[name])
            if (order === 'ASC') return numberA.isLessThan(numberB) ? -1 : 1
            return numberB.isLessThan(numberA) ? -1 : 1
          }
        }

        toHumanReadableString(field, value) {
          return value || ''
        }

        getDocsDataType(field) {
          return 'running_count'
        }

        getDocsDescription(field) {
          return this.app.$i18n.t('fieldType.runningCountDescription')
        }

        getDocsRequestExample(field) {
          return null
        }

        getDocsResponseExample(field) {
          return 42
        }
      }
      ```
    - `BigNumber` is already imported in `fieldTypes.js` (used by AutonumberFieldType and others).
  - [x] Add `RunningCountFieldType` to the export list at the bottom of `fieldTypes.js`.

- [x] **Task 4 — Vue components (AC: #1)**
  - [x] `web-frontend/modules/database/components/view/grid/fields/GridViewFieldRunningCount.vue` — identical structure to `GridViewFieldAutonumber.vue`:
    ```vue
    <template>
      <div ref="cell" class="grid-view__cell active">
        <div class="grid-field-number">{{ value }}</div>
      </div>
    </template>

    <script>
    import gridField from '@baserow/modules/database/mixins/gridField'

    export default {
      mixins: [gridField],
    }
    </script>
    ```
  - [x] `web-frontend/modules/database/components/view/grid/fields/FunctionalGridViewFieldRunningCount.vue` — copy `FunctionalGridViewFieldAutonumber.vue`, rename component to `FunctionalGridViewFieldRunningCount`.
  - [x] `web-frontend/modules/database/components/row/RowEditFieldRunningCount.vue` — copy `RowEditFieldAutonumber.vue` (displays `{{ value }}` in `control__elements`, read-only).
  - [x] `web-frontend/modules/database/components/card/RowCardFieldRunningCount.vue` — copy `RowCardFieldAutonumber.vue`, rename to `RowCardFieldRunningCount`.
  - [x] `web-frontend/modules/database/components/field/FieldRunningCountSubForm.vue` — empty stub (no configurable options for V1):
    ```vue
    <script>
    import form from '@baserow/modules/core/mixins/form'
    import fieldSubForm from '@baserow/modules/database/mixins/fieldSubForm'

    export default {
      name: 'FieldRunningCountSubForm',
      mixins: [form, fieldSubForm],
      setup() {
        return () => null
      },
      data() {
        return {
          allowedValues: [],
          values: {},
        }
      },
    }
    </script>
    ```

- [x] **Task 5 — Register in plugin.js (AC: #1)**
  - [x] In `web-frontend/modules/database/plugin.js`:
    - Add import: `import { RunningCountFieldType } from '@baserow/modules/database/fieldTypes'`
    - Add registration after AutonumberFieldType registration (~line 719):
      ```js
      $registry.register('field', new RunningCountFieldType(context))
      ```

- [x] **Task 6 — i18n keys (AC: #1)**
  - [x] In `web-frontend/modules/database/locales/en.json`, add under `fieldType`:
    ```json
    "runningCount": "Running Count",
    "runningCountDescription": "Counts the number of rows in this table matching the configured condition."
    ```
    (Check exact key path by searching for `"autonumber"` in `en.json` to confirm the structure.)

- [x] **Task 7 — Backend unit tests (AC: #1, #2, #3, #4)**
  - [x] Create `backend/tests/baserow/contrib/database/field/test_running_count_field_type.py`. Pattern: `test_barcode_field_type.py` and `test_autonumber_field_type.py`. Minimum tests:
    1. `test_running_count_field_registered` — `field_type_registry.get("running_count")` returns `RunningCountFieldType`; `"count"` still returns `CountFieldType` (AC #4).
    2. `test_running_count_field_creates` — `FieldHandler().create_field(..., type_name="running_count")` creates a `RunningCountField` instance.
    3. `test_running_count_shows_total_row_count` — Create table, add 3 rows, create running_count field; all rows show value `3`.
    4. `test_running_count_updates_on_row_create` — Create table + field, value is N; create new row; all rows now show `N+1`.
    5. `test_running_count_updates_on_row_delete` — Create table + field, value is N; delete a row; all rows now show `N-1`.
    6. `test_running_count_api_round_trip` — Create via API; GET confirms `type = "running_count"` and value appears in row data.
  - [x] Run: `EXTRA_VITEST_PARAMS="" just b test backend/tests/baserow/contrib/database/field/test_running_count_field_type.py`

- [x] **Task 8 — Frontend unit tests (AC: #1)**
  - [x] Create `web-frontend/test/unit/database/runningCountFieldType.spec.js`. Pattern: `autonumberFieldType.spec.js`. Minimum tests:
    1. `getType returns running_count`
    2. `getIconClass returns iconoir-stats-up-square`
    3. `toHumanReadableString returns value for integer` — `toBe(42)` for value `42` (base impl returns `value || ''`; integer `42` returns `42` not `'42'`).
    4. `toHumanReadableString returns empty string for null`
    5. `isReadOnlyField returns true`
    6. `shouldFetchDataWhenAdded returns true`
  - [x] Run: `EXTRA_VITEST_PARAMS="" just f test -- --reporter=verbose web-frontend/test/unit/database/runningCountFieldType.spec.js`

- [x] **Task 9 — E2E tests (AC: #1, #2)**
  - [x] Create `e2e-tests/tests/database/running_count_field.spec.ts`. Pattern: `e2e-tests/tests/database/currency_field.spec.ts` and `autonumber_field.spec.ts`. Three tests:
    1. **Column appears after creation** — create running_count field via API, navigate to table, assert field header is visible.
    2. **Cell is read-only** — click running_count cell, assert no `<input>` appears (read-only like autonumber).
    3. **Cell displays numeric count** — after `createTable` seeds example rows, assert first non-primary cell shows a numeric value (truthy integer).
  - [x] Note: `createRows` fixture does not exist in `e2e-tests/fixtures/database/rows.ts` — do not use it. Use `firstNonPrimaryCellWrappingColumnDiv` for cell assertions (established pattern from autonumber).
  - [x] Do NOT run E2E tests locally (requires Docker stack).

- [x] **Task 10 — Update sprint-status.yaml (housekeeping)**
  - [x] Update `_bmad-output/implementation-artifacts/sprint-status.yaml`: set `2-5-running-count-field` from `backlog` → `ready-for-dev`.

## Dev Notes

### `RunningCountField` vs `CountField` — critical distinction

`CountField` (models.py:837) extends `FormulaField` and counts rows in a **linked** (related) table via `through_field`. It uses the formula engine to compile a `count(field)` expression. Do NOT extend or modify `CountField`/`CountFieldType`.

`RunningCountField` extends `Field` directly. No formula engine. The integer count is stored as a plain `IntegerField` column in the user's dynamic model table, computed via a bulk `UPDATE` on relevant FieldType hooks.

### `ReadOnlyFieldType` behavior (registries.py:2106)

`ReadOnlyFieldType.prepare_value_for_db()` raises `ValidationError` if called — this enforces AC #1 read-only at the handler layer. No additional guard needed. `keep_data_on_duplication = True` means when a table is duplicated, the stored count values are copied as-is (acceptable; they'll drift until the next row mutation, but that's OK for V1).

### `after_rows_created` hook signature (registries.py:1187)

```python
def after_rows_created(self, field, rows, update_collector, field_cache):
```

This is called from `RowHandler.create_rows()` (rows/handler.py:1641) after rows are persisted. For Running Count, instead of using `update_collector`, do a direct `model.objects.filter(trashed=False).update(...)` — the update_collector is designed for formula/dependency tree updates; a simple bulk UPDATE is correct here.

### `rows_deleted` signal (rows/signals.py:12)

The signal sends: `sender=model, rows=list_of_deleted_rows, table=table_instance, model=model_class`. The handler needs the `table` kwarg to look up `RunningCountField.objects.filter(table=table)`.

Avoid importing `RunningCountField` at module level in `apps.py` — use a lazy import inside the signal handler function to prevent circular imports during Django startup.

### `_update_all_rows` model access pattern

`field.table.get_model(fields=[field])` builds the minimal dynamic model with only this field's column. This is more efficient than `get_model()` (which builds all fields). Pattern from AutonumberFieldType:

```python
model = field.table.get_model(fields=[field])
count = model.objects.filter(trashed=False).count()
model.objects.filter(trashed=False).update(**{f"field_{field.id}": count})
```

Do NOT use `model.objects.all()` — always use `filter(trashed=False)` for row counts in Baserow.

### Frontend — `toHumanReadableString` base method

`RunningCountFieldType` does NOT override `toHumanReadableString`. The base `FieldType.toHumanReadableString(field, value)` returns `value || ''` (see `fieldTypes.js:574`). For integer value `42` this returns `42` (number, not string). Frontend test assertion: `toBe(42)` not `toBe('42')`.

### i18n key lookup

Search `web-frontend/modules/database/locales/en.json` for `"autonumber"` to confirm the exact path (likely `fieldType.autonumber`). Add `runningCount` and `runningCountDescription` at the same level.

### Migration number

Latest migration as of baseline: `0218_barcodefield_alter_formview_mode.py`. Running Count migration = `0219_runningcountfield.py`. Verify via `ls backend/src/baserow/contrib/database/migrations/ | sort -r | head -3` before generating.

### Epic 1 integration — no action required

- `ReadOnlyFieldType` ensures the field can't be set manually (AC #1 read-only, covers Story 1.4 field-permission layer).
- Field visibility (Story 1.5): inherits base `Field.hidden` — no special case.
- Export honor (Story 1.9): integer value, included in exports by default.

### Test run commands

```bash
# Backend tests
just b test backend/tests/baserow/contrib/database/field/test_running_count_field_type.py

# Frontend unit tests
EXTRA_VITEST_PARAMS="" just f test -- --reporter=verbose web-frontend/test/unit/database/runningCountFieldType.spec.js

# E2E tests require Docker stack — do NOT run locally
```

### Project Structure Notes

New files:
- `backend/tests/baserow/contrib/database/field/test_running_count_field_type.py` (new)
- `backend/src/baserow/contrib/database/migrations/0219_runningcountfield.py` (new, generated)
- `web-frontend/modules/database/components/view/grid/fields/GridViewFieldRunningCount.vue` (new)
- `web-frontend/modules/database/components/view/grid/fields/FunctionalGridViewFieldRunningCount.vue` (new)
- `web-frontend/modules/database/components/row/RowEditFieldRunningCount.vue` (new)
- `web-frontend/modules/database/components/card/RowCardFieldRunningCount.vue` (new)
- `web-frontend/modules/database/components/field/FieldRunningCountSubForm.vue` (new)
- `web-frontend/test/unit/database/runningCountFieldType.spec.js` (new)
- `e2e-tests/tests/database/running_count_field.spec.ts` (new)

Modified files:
- `backend/src/baserow/contrib/database/fields/models.py` (add `RunningCountField`)
- `backend/src/baserow/contrib/database/fields/field_types.py` (add `RunningCountFieldType`)
- `backend/src/baserow/contrib/database/apps.py` (register + signal handler)
- `web-frontend/modules/database/fieldTypes.js` (add `RunningCountFieldType` + imports)
- `web-frontend/modules/database/plugin.js` (register)
- `web-frontend/modules/database/locales/en.json` (i18n keys)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (status update)

### References

- [Source: epics.md lines 457–470] — Story 2.5 user story + ACs
- [Source: architecture.md line 122] — D-fields: Running Count whole-table filter
- [Source: architecture.md line 104] — Open Q11 resolved: whole-table
- [Source: backend/src/baserow/contrib/database/fields/models.py:1003] — AutonumberField pattern (extends Field directly)
- [Source: backend/src/baserow/contrib/database/fields/models.py:837] — CountField (extends FormulaField — DO NOT follow this pattern)
- [Source: backend/src/baserow/contrib/database/fields/registries.py:2106] — ReadOnlyFieldType
- [Source: backend/src/baserow/contrib/database/fields/registries.py:1187] — after_rows_created hook
- [Source: backend/src/baserow/contrib/database/rows/signals.py:12] — rows_deleted signal
- [Source: backend/src/baserow/contrib/database/rows/handler.py:1641] — after_rows_created call site
- [Source: backend/src/baserow/contrib/database/fields/field_types.py:7363] — AutonumberFieldType (read-only pattern to follow)
- [Source: backend/src/baserow/contrib/database/fields/field_types.py:6089] — CountFieldType (relational count — DO NOT extend)
- [Source: web-frontend/modules/database/fieldTypes.js:5040] — AutonumberFieldType (frontend pattern to follow)
- [Source: web-frontend/modules/database/components/view/grid/fields/GridViewFieldAutonumber.vue] — grid cell pattern
- [Source: web-frontend/modules/database/components/field/FieldAutonumberSubForm.vue] — subform stub pattern
- [Source: backend/tests/baserow/contrib/database/field/test_barcode_field_type.py] — backend test pattern
- [Source: web-frontend/test/unit/database/autonumberFieldType.spec.js] — frontend test pattern
- [Source: e2e-tests/tests/database/currency_field.spec.ts] — E2E test pattern

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Opus 4.8)

### Debug Log References

- **Migration generation:** `makemigrations` requires `--skip-checks` to bypass a
  pre-existing `fields.E304/E305` clash between `database.FieldPermission.field` and
  `baserow_enterprise.FieldPermissions.field` (unrelated to this story). Command run
  with `PYTHONPATH=src:../premium/backend/src:../enterprise/backend/src`. Generated
  `0219_runningcountfield_alter_formview_mode.py` — the bundled `AlterField` on
  `formview.mode` is recurring churn identical to `0218_barcodefield_alter_formview_mode.py`.
- **`rows_deleted` signal handler did not fire (AC #3 initially failed [3,3] vs [2,2]):**
  the handler is a local nested function inside `DatabaseConfig.ready()`. Django's
  `Signal.connect()` defaults to a weak reference, so the function was garbage-collected
  once `ready()` returned and never ran. Fixed with `connect(..., weak=False)`.
- Backend tests run against the `baserow-test-db` container: `DATABASE_HOST=127.0.0.1 DATABASE_PORT=5431`.

### Completion Notes List

- **AC #1 (whole-table count, read-only):** `RunningCountFieldType` extends
  `ReadOnlyFieldType`; stores an `IntegerField` per row via `get_model_field`.
  `after_create` runs `_update_all_rows` (bulk UPDATE to the current `filter(trashed=False).count()`).
- **AC #2 (update on create):** `after_rows_created` hook recomputes and bulk-updates all rows.
- **AC #3 (update on delete):** `rows_deleted` signal handler in `apps.py` recomputes for
  every `RunningCountField` on the affected table (lazy imports + `weak=False`).
- **AC #4 (relational Count unaffected):** new type registered as `running_count`; `count`
  still resolves to `CountFieldType`. `RunningCountField` extends `Field` directly — no
  change to `CountField`/`CountFieldType`/`FormulaFieldType`. Verified by
  `test_running_count_field_registered`.
- **i18n deviation from story text:** story Task 6 specified key `fieldType.runningCountDescription`,
  but the repo convention (and all other field types) puts field-type names under
  `fieldType.<type>` and docs descriptions under `fieldDocs.<type>` in
  `web-frontend/locales/en.json` (NOT `modules/database/locales/en.json`, which has no
  such block). Added `fieldType.runningCount` + `fieldDocs.runningCount`; the frontend
  class `getDocsDescription` uses `fieldDocs.runningCount`. Functionally equivalent and
  consistent with the codebase.
- **Migration filename:** landed as `0219_runningcountfield_alter_formview_mode.py`
  (story anticipated `0219_runningcountfield.py`); the `_alter_formview_mode` suffix matches
  the recurring formview churn already present in `0217`/`0218`.
- **Frontend `export class`:** `RunningCountFieldType` is exported via `export class`
  (same as `AutonumberFieldType`); there is no separate export list to amend.
- **Tests:** backend 6/6 pass, frontend unit 6/6 pass, no regressions in row create/delete
  API tests. E2E spec authored but not run locally (requires Docker stack, per story).

### File List

**New files:**
- `backend/tests/baserow/contrib/database/field/test_running_count_field_type.py`
- `backend/src/baserow/contrib/database/migrations/0219_runningcountfield_alter_formview_mode.py`
- `web-frontend/modules/database/components/view/grid/fields/GridViewFieldRunningCount.vue`
- `web-frontend/modules/database/components/view/grid/fields/FunctionalGridViewFieldRunningCount.vue`
- `web-frontend/modules/database/components/row/RowEditFieldRunningCount.vue`
- `web-frontend/modules/database/components/card/RowCardFieldRunningCount.vue`
- `web-frontend/modules/database/components/field/FieldRunningCountSubForm.vue`
- `web-frontend/test/unit/database/runningCountFieldType.spec.js`
- `e2e-tests/tests/database/running_count_field.spec.ts`

**Modified files:**
- `backend/src/baserow/contrib/database/fields/models.py` (add `RunningCountField`)
- `backend/src/baserow/contrib/database/fields/field_types.py` (add `RunningCountFieldType` + import)
- `backend/src/baserow/contrib/database/apps.py` (register type + `rows_deleted` signal handler)
- `web-frontend/modules/database/fieldTypes.js` (add `RunningCountFieldType` + component imports)
- `web-frontend/modules/database/plugin.js` (register `RunningCountFieldType`)
- `web-frontend/locales/en.json` (i18n `fieldType.runningCount` + `fieldDocs.runningCount`)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (status → review)

## Senior Developer Review (AI)

**Reviewer:** gabenidolcs · **Date:** 2026-06-09 · **Outcome:** Approve (1 CRITICAL found and fixed automatically)

### Git vs Story File List
No discrepancies. All git-changed source files are documented in the Dev Agent Record File List, and every listed file has a corresponding git change. (`_bmad-output/` artifacts excluded from review per workflow.)

### Acceptance Criteria validation
- **AC #1 (whole-table count, read-only):** IMPLEMENTED. `RunningCountFieldType(ReadOnlyFieldType)`, stored `IntegerField`, `after_create` → `_update_all_rows`. `ReadOnlyFieldType.prepare_value_for_db` enforces read-only. Verified by `test_running_count_shows_total_row_count`, `test_running_count_field_registered`.
- **AC #2 (update on create):** ❌ **WAS BROKEN — now fixed.** The implementation relied on the `after_rows_created` FieldType hook, which is invoked **only** by the batch `RowHandler.force_create_rows` path (`rows/handler.py:1641`). The single-row create path — `RowHandler.create_row` → `force_create_row`, used by the `create_row` REST endpoint (`CreateRowActionType`) and the grid "add row" button — never calls it, so counts went stale on the primary user flow. The original unit test masked this by exercising `create_rows` (batch) directly. **Fix:** connected a `rows_created` signal handler in `apps.py` (`weak=False`), mirroring the existing `rows_deleted` handler. `rows_created` fires on both single-row (`handler.py:998`) and batch (`handler.py:1510`) paths. Removed the now-redundant `after_rows_created` hook. Added `test_running_count_updates_on_single_row_create` regression guard. Now IMPLEMENTED.
- **AC #3 (update on delete):** IMPLEMENTED. `rows_deleted` signal (`weak=False`) fires on both single (`handler.py:2973`) and batch (`handler.py:3202`) delete paths; both carry the `table` kwarg. Verified by `test_running_count_updates_on_row_delete`.
- **AC #4 (relational Count unaffected):** IMPLEMENTED. New type registered as `running_count`; `count` still resolves to `CountFieldType`; `RunningCountField` extends `Field` directly. Verified by `test_running_count_field_registered`.

### Task audit
All tasks marked `[x]` verified against source. i18n deviation (Task 6) is documented and correct: keys live in `web-frontend/locales/en.json` as `fieldType.runningCount` + `fieldDocs.runningCount`, consumed by `getName`/`getDocsDescription`. Vue components are byte-for-byte parity with the Autonumber originals. Migration `0219` creates the MTI table only — no user-table column (added dynamically via `get_model_field`).

### Lower-severity notes (not blocking; left as-is)
- **LOW (perf):** `_get_count` and `_update_all_rows` each call `field.table.get_model(fields=[field])`. Baserow caches generated models, so the second call is a cache hit — negligible.
- **LOW (scope):** restore-from-trash does not recompute (uses `rows_restored`, not `rows_created`/`rows_deleted`). Out of V1 AC scope.
- **LOW (pattern):** `get_serializer_field` returns a writable `IntegerField`; writes are still blocked by `ReadOnlyFieldType.prepare_value_for_db`. Matches the established Autonumber pattern.

### Tests
Backend 7/7 pass (was 6, +1 single-row regression guard). Frontend unit 6/6 pass. E2E spec authored (5 tests, covers AC #1/#2/#3); the "increments on row create" E2E uses the single-row `createRow` fixture and now matches the fixed behavior. E2E not run locally (requires Docker stack, per story).

## Change Log

| Date | Version | Description |
|------|---------|-------------|
| 2026-06-09 | 1.0 | Implemented Running Count Field (FR-21B): `RunningCountField` model + migration, `RunningCountFieldType` (whole-table count, read-only, stored integer), recompute on row create (`after_rows_created`) and delete (`rows_deleted` signal, `weak=False`), full frontend component set + registration + i18n, backend (6) and frontend (6) unit tests, E2E spec. Status → review. |
| 2026-06-09 | 1.1 | Adversarial review fix (CRITICAL AC #2): single-row create path (`RowHandler.create_row` → `force_create_row`, the create_row API + grid "add row" button) never fired the `after_rows_created` FieldType hook — that hook is only invoked by the batch `force_create_rows` path. Counts only updated on batch create, so the primary user flow silently left counts stale. Replaced the hook with a `rows_created` signal handler in `apps.py` (`weak=False`, mirrors `rows_deleted`); the signal fires on both single-row and batch paths. Added `test_running_count_updates_on_single_row_create` regression guard (backend 7/7 pass). Status → done. |
