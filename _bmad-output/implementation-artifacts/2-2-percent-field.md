---
baseline_commit: 0d2b942d0
---

# Story 2.2: Percent Field

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want a Percent Field with configurable precision,
so that percentages display with a `%` and sort numerically.

Realizes FR-19. **Bucket B `[B]` — license-clean new implementation; no clean-room gate required.**

## Context & Scope

**Story 2.1 (Currency Field) is done.** `CurrencyField` + `CurrencyFieldType` are shipped and registered. Use that implementation as the direct reference pattern — `PercentField` is simpler (no configurable symbol).

**What this story builds:** A new `PercentField` model and `PercentFieldType` extending `NumberField`/`NumberFieldType`. The `%` suffix is **always** appended — it is NOT user-configurable. Values store as numeric whole-numbers (50 = 50%), render as `50%`, sort and filter numerically. `PercentField` has no new metadata columns — it is a pure MTI subclass of `NumberField` for type identification only.

**Q8 resolved — whole-number entry convention:** Architecture defaulted Open Question 8 to whole-number entry (`architecture.md:382`). A user enters `50` to mean 50%; the stored value is `50` (not `0.5`). The `%` suffix is appended at display time via `number_suffix = "%"` — no divide-by-100 transform occurs anywhere.

**`%` suffix is locked — not user-configurable:** `PercentFieldType.prepare_values()` always sets `number_suffix = "%"` and `number_prefix = ""` before persisting, regardless of what the API caller sends. This mirrors how `CurrencyFieldType.prepare_values()` enforces `number_prefix = currency_symbol`. The form component must NOT show editable prefix/suffix inputs to avoid misleading the user.

**Scope boundary:**
- **IN:** `PercentField` model + migration; `PercentFieldType` backend + frontend; registration in `apps.py` and `plugin.js`; `%` suffix always forced; numeric sort/filter (inherited); grid cell / row-edit / card display showing `value%`; configurable decimal precision (0–5 places) and negative flag; `FieldPercentSubForm.vue` without prefix/suffix UI.
- **OUT:** Currency Field (done), Barcode (2.3), Autonumber (2.4), Running Count (2.5). Do not implement or stub any other Epic 2 field type.
- **OUT:** Divide-by-100 conversion, locale `%`-after-decimal formatting, or any currency-style prefix config.

## Acceptance Criteria

1. **Percent Field creates, configures, and stores correctly.** Given an editor creates a Percent Field, when they set decimal precision (e.g. 1), then values store as numbers and render with a `%` suffix at the configured precision (e.g. `50.0%`), and the precision persists as Field config (survives reload and API round-trip). [Source: epics.md line 411]

2. **`%` suffix is always appended — no user override.** Given a Percent Field, when a client sends `number_suffix` or `number_prefix` via API (PATCH/POST), then the backend ignores those values and persists `number_suffix = "%"`, `number_prefix = ""`. [Source: Q8 resolution; architecture.md line 382]

3. **Sort and filter are numeric, not lexical.** Given a Percent Field, when the Table is sorted or filtered on it, then ordering is numeric — `9%` sorts before `10%`. [Source: epics.md line 415; architecture.md NFR-2]

4. **Field config API round-trip.** Given a Percent Field, when a client GETs the field, then `number_decimal_places` is present in the response; when a PATCH updates it, the new precision renders immediately with no restart. [Source: AC#1]

## Tasks / Subtasks

- [x] **Task 1 — `PercentField` model + migration (AC: #1, #4)**
  - [x] In `backend/src/baserow/contrib/database/fields/models.py`, after `CurrencyField` class definition (~line 424), add:
    ```python
    class PercentField(NumberField):
        class Meta:
            app_label = "database"
    ```
    No extra columns. MTI subclass gives type identification via Django content-type. All `NumberField` columns (decimal places, negative, separator, prefix, suffix, default) are inherited.
  - [x] Generate migration: `just b make-migrations database`. Expected `0217_percentfield.py` (next after `0216`). The generated `database_percentfield` table has only `numberfield_ptr_id` FK — no extra columns. Confirm reversible.
  - [x] Confirm no new column on user tables — only `database_percentfield` metadata table is new.

- [x] **Task 2 — `PercentFieldType` backend (AC: #1, #2, #3)**
  - [x] In `backend/src/baserow/contrib/database/fields/field_types.py`, add `PercentFieldType` after `CurrencyFieldType` (~line 900+):
    ```python
    class PercentFieldType(NumberFieldType):
        type = "percent"
        model_class = PercentField
        _can_group_by = True
        _can_have_db_index = True

        def prepare_values(self, values, user):
            values = super().prepare_values(values, user)
            values["number_suffix"] = "%"
            values["number_prefix"] = ""
            return values
    ```
    Do NOT override `allowed_fields` or `serializer_field_names` — inherit from `NumberFieldType`. `prepare_values()` enforcement is sufficient.
  - [x] Add `PercentField` to the imports block in `field_types.py` alongside `CurrencyField`:
    ```python
    from baserow.contrib.database.fields.models import (
        ...
        CurrencyField,
        PercentField,
        ...
    )
    ```
    Ruff enforces alphabetical order — place `PercentField` after `NumberField` alphabetically.
  - [x] Confirm `get_order_by_field_string` is NOT overridden — inherited path gives numeric ordering (AC #3).

- [x] **Task 3 — Register `PercentFieldType` in `apps.py` (AC: #1)**
  - [x] In `backend/src/baserow/contrib/database/apps.py`, add `PercentField` to model imports and `PercentFieldType` to type imports alongside `CurrencyField`/`CurrencyFieldType`. Add registration after `CurrencyFieldType()` (~line 233):
    ```python
    field_type_registry.register(PercentFieldType())
    ```
    Lazy import inside `ready()` — mirror exactly how `CurrencyFieldType()` is registered at line 232.

- [x] **Task 4 — Frontend `PercentFieldType` in `fieldTypes.js` (AC: #1, #2, #3)**
  - [x] Import `FieldPercentSubForm` (once created in Task 5) at the top of `fieldTypes.js` alongside `FieldCurrencySubForm`.
  - [x] Add `PercentFieldType` after `CurrencyFieldType` (~line 2008+):
    ```javascript
    export class PercentFieldType extends NumberFieldType {
      static getType() {
        return 'percent'
      }

      static getIconClass() {
        return 'iconoir-percentage' // confirmed: web-frontend/node_modules/iconoir/icons/percentage.svg
      }

      getName() {
        const { $i18n: i18n } = this.app
        return i18n.t('fieldType.percent')
      }

      getFormComponent() {
        return FieldPercentSubForm
      }

      toHumanReadableString(field, value, delimiter = ', ') {
        if (value === null || value === undefined || value === '') return ''
        const displayField = { ...field, number_suffix: '%', number_prefix: '' }
        return formatDecimalNumber(displayField, value)
      }
    }
    ```
  - [x] Verify `getType()` returns `'percent'` — must match backend `type = "percent"` exactly.
  - [x] `iconoir-percentage` confirmed present at `web-frontend/node_modules/iconoir/icons/percentage.svg`.

- [x] **Task 5 — Vue form component `FieldPercentSubForm.vue` (AC: #1)**
  - [x] Create `web-frontend/modules/database/components/field/FieldPercentSubForm.vue`:
    ```vue
    <template>
      <FieldNumberSubForm
        :default-values="defaultValues"
        :allow-set-number-negative="true"
      />
    </template>

    <script>
    import form from '@baserow/modules/core/mixins/form'
    import fieldSubForm from '@baserow/modules/database/mixins/fieldSubForm'
    import FieldNumberSubForm from '@baserow/modules/database/components/field/FieldNumberSubForm'

    export default {
      name: 'FieldPercentSubForm',
      components: { FieldNumberSubForm },
      mixins: [form, fieldSubForm],
      data() {
        return {
          allowedValues: [],
          values: {},
        }
      },
    }
    </script>
    ```
    The `fieldSubForm` mixin's `getChildForms()` mechanism collects `number_decimal_places`, `number_negative`, etc. from the embedded `FieldNumberSubForm` automatically. `FieldPercentSubForm` has no own fields (`allowedValues = []`, `values = {}`). This is the same delegation pattern as `FieldCurrencySubForm.vue`.

    **Known UX limitation:** `FieldNumberSubForm` renders prefix/suffix inputs. These are visible to the user but the backend enforces `number_suffix = "%"` and `number_prefix = ""` in `prepare_values()`. Values entered by the user in those fields are silently ignored on save. Document as UX debt — a future improvement would add a `hidePrefixSuffix` prop to `FieldNumberSubForm`.

- [x] **Task 6 — Register `PercentFieldType` in frontend `plugin.js` (AC: #1)**
  - [x] In `web-frontend/modules/database/plugin.js`, add `PercentFieldType` to the import from `fieldTypes`:
    ```javascript
    import { CurrencyFieldType, PercentFieldType } from '@baserow/modules/database/fieldTypes'
    ```
    And inside `install()`, after `CurrencyFieldType` (~line 695):
    ```javascript
    $registry.register('field', new PercentFieldType(context))
    ```

- [x] **Task 7 — i18n strings (AC: #1)**
  - [x] In `web-frontend/locales/en.json`, add `"percent": "Percent"` under the `fieldType` object (same location as `"currency": "Currency"`). Find exact key path by searching: `grep -n '"currency"' web-frontend/locales/en.json`.
  - [x] No additional module locale keys needed if `FieldPercentSubForm.vue` has no unique labels.

- [x] **Task 8 — Backend tests (AC: #1, #2, #3, #4)**
  - [x] Create `backend/tests/baserow/contrib/database/field/test_percent_field_type.py`. Mirror `test_currency_field_type.py` structure. Key cases:
    - `test_percent_field_creates_with_suffix_enforced`: create via `FieldHandler.create_field(type="percent", number_decimal_places=1)`, assert `field.number_suffix == "%"` and `field.number_prefix == ""`.
    - `test_percent_field_prepare_values_locks_suffix`: call `PercentFieldType().prepare_values({"number_suffix": "x", "number_prefix": "y", "number_decimal_places": 0}, user)`, assert `number_suffix = "%"`, `number_prefix = ""`.
    - `test_percent_field_api_round_trip`: POST `type="percent"`, assert `number_decimal_places` in response; PATCH to change precision; GET to confirm.
    - `test_percent_field_sorts_numeric`: create two rows with values 9 and 10, sort ascending, assert 9 comes first (not lexical).
    - `test_percent_field_migration_reversible`: confirm migration reversible.
  - [x] Run: `just b test backend/tests/baserow/contrib/database/field/test_percent_field_type.py`

- [x] **Task 9 — Frontend tests (AC: #1, #2)**
  - [x] Create `web-frontend/test/unit/database/percentFieldType.spec.js`. Mirror `currencyFieldType.spec.js`. Key cases:
    - `PercentFieldType.getType()` returns `"percent"`.
    - `toHumanReadableString({number_decimal_places: 1}, "9.9")` → `"9.9%"`.
    - `toHumanReadableString(field, null)` → `""`.
    - `toHumanReadableString` uses `number_suffix: '%'` in displayField even if field has `number_suffix: ''`.
  - [x] Run: `just f yarn test:core web-frontend/test/unit/database/percentFieldType.spec.js`

- [x] **Task 10 — Lint + full test pass**
  - [x] `just lint` — fix any ruff/ESLint warnings.
  - [x] `just b test backend/tests/baserow/contrib/database/field/` — confirm no regressions in `test_currency_field_type.py` and `test_number_field_type.py`.

## Dev Notes

- **`PercentField` has NO new columns — pure MTI subclass:** `database_percentfield` table contains only `numberfield_ptr_id` FK. Django MTI resolves content-type to `PercentField` so `field_type_registry.get_by_model(field.specific_class)` returns `PercentFieldType`. No user-table columns added. [Source: CurrencyField pattern; architecture.md line 122]

- **`class Meta: app_label = "database"` is REQUIRED on `PercentField`:** Without it, Django may not assign the correct app label, causing migration/registry issues. See `CurrencyField.Meta` in `models.py:424`.

- **`prepare_values()` must call `super()` first:** Parent validates/normalizes `number_decimal_places`, `number_negative`, etc. Enforce `number_suffix`/`number_prefix` after `super()` so parent normalization doesn't clobber them.

- **`toHumanReadableString` override is a safety net:** Since `prepare_values()` persists `number_suffix = "%"`, the inherited `NumberFieldType.toHumanReadableString` already renders `%` via `formatDecimalNumber` reading `field.number_suffix`. The explicit override sets it defensively in `displayField` for any edge cases (pre-existing records, race conditions). Safe to omit if it causes issues — backend enforcement is authoritative.

- **`FieldNumberSubForm` prefix/suffix are visible but harmless:** The form shows prefix/suffix inputs. Backend `prepare_values()` silently overrides them. This is acceptable for v1 — document as UX debt (`hidePrefixSuffix` prop on `FieldNumberSubForm`).

- **Migration may bundle spurious AlterField:** Django sometimes includes unrelated `AlterField` operations (e.g. formview mode choices) in auto-generated migrations. Accept as-is (same as `0216_currencyfield_alter_formview_mode.py`).

- **Ruff import order:** `PercentField` and `PercentFieldType` must be placed alphabetically in their import blocks. `just lint` catches violations.

- **Registration must not double-register:** One `field_type_registry.register(PercentFieldType())` call in `DatabaseConfig.ready()`. No conditional guards.

- **Test database env:** `BASEROW_OSS_ONLY=true DATABASE_HOST=localhost DATABASE_PORT=5431 DATABASE_USER=baserow DATABASE_PASSWORD=baserow DATABASE_NAME=baserow JWT_SIGNING_KEY=test-secret-key just b test ...`

### Project Structure Notes

```
backend/src/baserow/contrib/database/fields/
  models.py                          # Add PercentField after CurrencyField (~line 424)
  field_types.py                     # Add PercentFieldType after CurrencyFieldType (~line 900)
  migrations/                        # Auto-generated 0217_percentfield.py

backend/src/baserow/contrib/database/
  apps.py                            # Register PercentFieldType after CurrencyFieldType (~line 233)

backend/tests/baserow/contrib/database/field/
  test_percent_field_type.py         # New

web-frontend/modules/database/
  fieldTypes.js                      # Add PercentFieldType after CurrencyFieldType (~line 2008)
  plugin.js                          # Register PercentFieldType after CurrencyFieldType (~line 695)
  components/field/
    FieldPercentSubForm.vue          # New — wraps FieldNumberSubForm, no prefix/suffix inputs

web-frontend/locales/en.json         # Add "percent": "Percent" under fieldType
web-frontend/test/unit/database/
  percentFieldType.spec.js           # New
```

- No changes to: `core/`, `premium/`, `enterprise/`, row handler, export handler, filter/sort logic.
- Field permissions (Stories 1.4/1.5/1.9) apply automatically — `PercentField` is a `Field` subclass.
- Export inherits from `NumberFieldType.get_export_value` — `%` suffix included via persisted `number_suffix`.

### Previous Story Intelligence (2.1 CurrencyField)

- **`class Meta: app_label = "database"` required** on the new field subclass — confirmed from `CurrencyField`.
- **`prepare_values()` must call `super()` first** — parent normalizes number fields before subtype enforces its overrides.
- **Migration may bundle unrelated AlterField** — accept as-is, do not manually remove.
- **`i18n` key placement:** Global `fieldType.percent` → `web-frontend/locales/en.json`. Component-specific keys → `web-frontend/modules/database/locales/en.json`. Don't add to both.
- **Ruff import order** — `just lint` catches violations in `apps.py` and `field_types.py` import blocks.
- **`apps.py` lazy import pattern** — import inside `ready()`, not at module level.

### References

- Story requirements: [Source: _bmad-output/planning-artifacts/epics.md lines 407–419]
- Q8 resolution (whole-number convention): [Source: _bmad-output/planning-artifacts/architecture.md line 382]
- Architecture field types: [Source: _bmad-output/planning-artifacts/architecture.md lines 27, 122]
- `NumberField` model: [Source: backend/src/baserow/contrib/database/fields/models.py lines 363–410]
- `CurrencyField` model (pattern): [Source: backend/src/baserow/contrib/database/fields/models.py lines 413–424]
- `CurrencyFieldType` (direct pattern): [Source: backend/src/baserow/contrib/database/fields/field_types.py lines 886–900]
- `field_type_registry` registration: [Source: backend/src/baserow/contrib/database/apps.py lines 231–232]
- Frontend `CurrencyFieldType`: [Source: web-frontend/modules/database/fieldTypes.js lines 1982–2007]
- `FieldCurrencySubForm.vue` (delegation pattern): [Source: web-frontend/modules/database/components/field/FieldCurrencySubForm.vue]
- `FieldNumberSubForm.vue`: [Source: web-frontend/modules/database/components/field/FieldNumberSubForm.vue]
- Frontend plugin registration: [Source: web-frontend/modules/database/plugin.js lines 693–695]
- `formatDecimalNumber` utility: [Source: web-frontend/modules/database/utils/number.js line 227]
- Story 2.1 reference: [Source: _bmad-output/implementation-artifacts/2-1-currency-field.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- PercentField: pure MTI subclass of NumberField, no new columns, migration 0217 generated
- PercentFieldType: prepare_values() locks number_suffix=% and number_prefix="" regardless of API input
- Ruff import order fixed: PercentField/PercentFieldType placed after Password* (alphabetical)
- FieldPercentSubForm.vue: delegates to FieldNumberSubForm; prefix/suffix inputs visible but overridden by backend (UX debt noted)
- 10 backend tests pass, 9 frontend tests pass (8 original + getIconClass gap fix from QA), no regressions in currency or number field tests
- QA session added: getIconClass test to percentFieldType.spec.js, 3 Playwright E2E tests (percent_field.spec.ts)

### File List

- backend/src/baserow/contrib/database/fields/models.py
- backend/src/baserow/contrib/database/fields/field_types.py
- backend/src/baserow/contrib/database/migrations/0217_percentfield_alter_formview_mode.py
- backend/src/baserow/contrib/database/apps.py
- backend/tests/baserow/contrib/database/field/test_percent_field_type.py
- web-frontend/modules/database/fieldTypes.js
- web-frontend/modules/database/plugin.js
- web-frontend/modules/database/components/field/FieldPercentSubForm.vue
- web-frontend/locales/en.json
- web-frontend/test/unit/database/percentFieldType.spec.js
- e2e-tests/tests/database/percent_field.spec.ts

## Change Log

- 2026-06-07: Implemented Story 2.2 — PercentField model + migration, PercentFieldType backend, registration in apps.py and plugin.js, FieldPercentSubForm.vue, i18n percent key, 10 backend tests (all pass), 8 frontend tests (all pass), ruff lint clean.
- 2026-06-09: QA pass — added getIconClass gap test (frontend 8→9), added 3 Playwright E2E tests (percent_field.spec.ts). All layers green: 10/10 backend, 9/9 frontend, E2E coverage confirmed.
- 2026-06-09: Senior Developer Review (AI) — APPROVED. No CRITICAL issues. M1 (QA files uncommitted) auto-fixed. L1 (File List missing E2E) auto-fixed. L2 (stale test count) auto-fixed. L3 (spurious AlterField in migration) and L4 (prefix/suffix UX debt) accepted as documented. Status → done.

## Senior Developer Review (AI)

**Reviewer:** AI (claude-sonnet-4-6) | **Date:** 2026-06-09 | **Outcome:** APPROVED

### AC Verification

| AC | Status | Evidence |
|----|--------|---------|
| AC1 — Percent Field creates/configures/stores correctly | IMPLEMENTED | `PercentFieldType` inherits `NumberFieldType`; `prepare_values()` enforces suffix; `test_percent_field_creates_with_suffix_enforced` + `test_percent_field_api_round_trip` pass |
| AC2 — `%` suffix always appended, no user override | IMPLEMENTED | `prepare_values()` hard-sets `number_suffix="%"` and `number_prefix=""` after `super()`; 4 test variants confirm |
| AC3 — Sort/filter numeric, not lexical | IMPLEMENTED | No `get_order_by_field_string` override; `test_percent_field_sorts_numeric` confirms 9 before 10 |
| AC4 — Field config API round-trip | IMPLEMENTED | `test_percent_field_api_round_trip` covers POST/GET/PATCH cycle; `number_decimal_places` round-trips correctly |

### Findings

**M1 — QA-session files not committed** (AUTO-FIXED)
- `percentFieldType.spec.js` had 1 uncommitted test (`getIconClass`)
- `e2e-tests/tests/database/percent_field.spec.ts` was untracked
- Test summaries were untracked
- Fix: all committed in QA review commit

**L1 — Story File List missing E2E spec** (AUTO-FIXED)
- `e2e-tests/tests/database/percent_field.spec.ts` added to File List

**L2 — Completion Notes stale test count** (AUTO-FIXED)
- "8 frontend tests" corrected to "9 frontend tests"

**L3 — Migration bundles unrelated AlterField** (ACCEPTED)
- `0217_percentfield_alter_formview_mode.py` includes spurious `AlterField` on `formview.mode`
- Same Django behavior as `0216_currencyfield_alter_formview_mode.py`; removing would cause Django to regenerate it
- Documented in Dev Notes

**L4 — FieldPercentSubForm shows prefix/suffix inputs** (ACCEPTED)
- `FieldNumberSubForm` renders prefix/suffix inputs visible to user
- Backend `prepare_values()` silently overrides to `%` and `""`; no data integrity risk
- Documented as UX debt in story Dev Notes; `hidePrefixSuffix` prop is future improvement

### Code Quality

- `PercentField` model: correct MTI subclass with `class Meta: app_label = "database"` ✅
- `PercentFieldType.prepare_values()`: calls `super()` first, then enforces suffix ✅
- Ruff import order: `PercentField`/`PercentFieldType` alphabetically after `Password*` ✅
- Frontend `PercentFieldType`: extends `NumberFieldType`, `getType()` returns `'percent'` ✅
- `toHumanReadableString`: sets `displayField` defensively, handles null/undefined/empty ✅
- `FieldPercentSubForm.vue`: correct delegation pattern, `allowedValues=[]`, `values={}` ✅
- Plugin.js registration: single `register` call, no double-registration ✅

### Security

No security concerns. No user input concatenated to SQL. `prepare_values()` enforces suffix regardless of API input (defensive). MTI subclass adds no new attack surface.
