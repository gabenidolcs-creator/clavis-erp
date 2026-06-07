---
baseline_commit: f2321afb3
---

# Story 2.1: Currency Field

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want a Currency Field with a configurable symbol and precision,
so that monetary values store and display correctly.

Realizes FR-18. **Bucket B `[B]` — license-clean new implementation; no clean-room gate required.**

## Context & Scope

**Epic 1 (Trust & Access Foundation) is complete.** Stories 1.1–1.9 are done: the clean-room gate, RBAC tiers, field-permission enforcement layer (edit restriction + visibility hiding + export redaction), and password-protected share links are all shipped. Epic 2 begins now.

**What this story builds:** A new `CurrencyField` model and `CurrencyFieldType` that extend the existing `NumberField`/`NumberFieldType` hierarchy with a dedicated `currency_symbol` CharField. Currency values store as `Decimal` numbers (no new DB column on user tables — dynamic-model pattern), render with the configured symbol prefixed, sort and filter numerically, and persist symbol + precision per field config. No floating-point storage; the underlying column type is unchanged from `NumberField`.

**Why extend `NumberFieldType` rather than `TextField`:** Numeric storage gives correct sort (NFR-2 demands `get_order_by_field_string` numeric ordering — lexical order produces `"$10" < "$9"`, which is wrong). The `NumberField` already handles `number_decimal_places` (0–5), `number_negative`, prefix/suffix display, and separator formatting — `CurrencyFieldType` inherits all of this and adds only the named `currency_symbol` field for a clean API.

**Key insight — `NumberField` already has `number_prefix`:** `NumberField.number_prefix` (max_length=10) already exists and `NumberFieldType.get_export_value` already uses it for rendering. However, the architecture explicitly names `currency_symbol` as a distinct metadata field (`architecture.md:122`), so `CurrencyField` carries a dedicated `currency_symbol` CharField. In the `CurrencyFieldType` implementation, override `get_export_value` and display components to read `currency_symbol` instead of `number_prefix` (or map `currency_symbol → number_prefix` before calling `super()`). Either approach is acceptable; the key constraint is: **the `currency_symbol` field name appears in the serializer API.**

**Scope boundary:**
- **IN:** `CurrencyField` model + migration; `CurrencyFieldType` backend + frontend; registration in `apps.py` and `plugin.js`; numeric sort/filter (inherited from NumberFieldType); grid cell / row-edit / card display showing `symbol + value`; configurable symbol (default `$`) and precision (decimal places 0–5); field config persists per Field.
- **OUT:** Percent Field (Story 2.2); Barcode (2.3); Autonumber (2.4); Running Count (2.5). Do not implement or stub any Epic 2 field type beyond currency in this story.
- **OUT:** Multi-currency conversion, locale-aware formatting beyond symbol prefix, or camera-based barcode scanning.

## Acceptance Criteria

1. **Currency Field creates, configures, and stores correctly.** Given an editor creates a Currency Field, when they set a `currency_symbol` (e.g. `€`) and decimal precision (e.g. 2), then values store as numbers and render with the configured symbol and decimal places (e.g. `€12.50`), and the symbol and precision persist as Field config (survive reload and API round-trip). [Source: epics.md line 395]

2. **Sort and filter are numeric, not lexical.** Given a Currency Field, when the Table is sorted or filtered on it, then ordering is numeric (correct `get_order_by_field_string` + indexing) — `€9` sorts before `€10`. [Source: epics.md line 399; architecture.md NFR-2]

3. **Field config API round-trip.** Given a Currency Field, when a client GETs the field, then `currency_symbol` and `number_decimal_places` are present in the response; when a PATCH updates them, the new values render immediately with no restart. [Source: AC#1; architecture.md line 122]

## Tasks / Subtasks

- [x] **Task 1 — `CurrencyField` model + migration (AC: #1, #3)**
  - [x] In `backend/src/baserow/contrib/database/fields/models.py`, after the `NumberField` class definition (~line 410), add:
    ```python
    class CurrencyField(NumberField):
        currency_symbol = models.CharField(
            max_length=10,
            default="$",
            help_text="The currency symbol to display before the value.",
        )

        class Meta:
            app_label = "database"
    ```
    Note: precision (decimal places 0–5) is inherited from `NumberField.number_decimal_places`. No `number_type` field needed — architecture dropped it (`field_types.py:598` shows it's a deprecated no-op field).
  - [x] Generate migration: `just b make-migrations database` (with `BASEROW_OSS_ONLY=true` env if required). Confirm migration is in `backend/src/baserow/contrib/database/fields/migrations/` and is reversible.
  - [x] Confirm `CurrencyField` does NOT create a new DB column on user tables — it inherits the parent's `DecimalField` column from `NumberField`'s dynamic-model pattern. The new `currency_symbol` column lives only in the `database_currencyfield` metadata table (standard Django multi-table inheritance). [Source: architecture.md line 122]

- [x] **Task 2 — `CurrencyFieldType` backend (AC: #1, #2, #3)**
  - [x] In `backend/src/baserow/contrib/database/fields/field_types.py`, add `CurrencyFieldType` after `NumberFieldType` (~line 740+):
    ```python
    class CurrencyFieldType(NumberFieldType):
        type = "currency"
        model_class = CurrencyField
        allowed_fields = NumberFieldType.allowed_fields + ["currency_symbol"]
        serializer_field_names = NumberFieldType.serializer_field_names + ["currency_symbol"]
        _can_group_by = True
        _can_have_db_index = True

        def get_serializer_field(self, instance, **kwargs):
            # Inherit decimal serializer; currency_symbol is on the field model
            return super().get_serializer_field(instance, **kwargs)

        def get_export_value(self, value, field_object, rich_value=False):
            if value is None:
                return value if rich_value else ""
            symbol = field_object["field"].currency_symbol or "$"
            # Let NumberFieldType format decimal places and separators, then prepend symbol
            formatted = super().get_export_value(value, field_object, rich_value=rich_value)
            if rich_value:
                return formatted  # rich value is raw Decimal; caller formats display
            return f"{symbol}{formatted}"
    ```
    Verify `allowed_fields` includes all `NumberField` fields (decimal places, negative, separator, default) so existing `NumberFieldType` serialization paths are not broken.
  - [x] Confirm `CurrencyFieldType` does NOT override `get_order_by_field_string` — the inherited `NumberFieldType` implementation returns numeric ordering (AC #2 requirement). Run a quick grep: `grep -n "get_order_by_field_string" backend/src/baserow/contrib/database/fields/field_types.py` to confirm the parent path.
  - [x] Confirm `_can_have_db_index = True` is set (inherits from `NumberFieldType` — verify no explicit override needed).

- [x] **Task 3 — Register `CurrencyFieldType` in backend `apps.py` (AC: #1)**
  - [x] In `backend/src/baserow/contrib/database/apps.py`, in the `DatabaseConfig.ready()` method (~line 230), add after `NumberFieldType` registration:
    ```python
    from baserow.contrib.database.fields.field_types import CurrencyFieldType
    field_type_registry.register(CurrencyFieldType())
    ```
    The import should be lazy (inside `ready()`) consistent with the surrounding pattern.

- [x] **Task 4 — Frontend `CurrencyFieldType` in `fieldTypes.js` (AC: #1, #2, #3)**
  - [x] In `web-frontend/modules/database/fieldTypes.js`, after `NumberFieldType` (~line 1979+), add:
    ```javascript
    export class CurrencyFieldType extends NumberFieldType {
      static getType() {
        return 'currency'
      }

      static getIconClass() {
        return 'baserow-icon-currency' // or reuse a suitable existing icon
      }

      getName() {
        const { $i18n: i18n } = this.app
        return i18n.t('fieldType.currency')
      }

      // Reuse NumberFieldType grid/row-edit/card components — they already handle
      // number_prefix for display. Override only if a dedicated currency component
      // is needed for the symbol UX in the form.
      getFormComponent() {
        return FieldCurrencySubForm  // new component (see Task 5); or FieldNumberSubForm if sufficient
      }

      // Format display value: prepend currency_symbol to the formatted number
      toHumanReadableString(field, value) {
        if (value === null || value === undefined || value === '') return ''
        const symbol = field.currency_symbol || '$'
        const formatted = super.toHumanReadableString(field, value)
        return `${symbol}${formatted}`
      }
    }
    ```
  - [x] Verify `getType()` matches backend `CurrencyFieldType.type = "currency"` exactly — the frontend registry key must equal the backend type string.
  - [x] Verify sort indicator inherits from `NumberFieldType.getSortIndicator()` (returns `['text', '1', '9']`), which triggers numeric sort in the view — no override needed.

- [x] **Task 5 — Vue form component for currency symbol input (AC: #1, #3)**
  - [x] Create `web-frontend/modules/database/components/field/FieldCurrencySubForm.vue`. Minimal implementation:
    - Extends or wraps `FieldNumberSubForm.vue` to add a `currency_symbol` text input (max 10 chars, labelled `i18n.t('field.currencySymbol')`).
    - Emits `update:value` on change; binds to `field.currency_symbol`.
    - If `FieldNumberSubForm` is easily extensible via slots, prefer using it with a slot rather than a full copy.
  - [x] Check existing `FieldNumberSubForm.vue` path: `grep -rn "FieldNumberSubForm" web-frontend/modules/database/` to locate it.

- [x] **Task 6 — Register `CurrencyFieldType` in frontend `plugin.js` (AC: #1)**
  - [x] In `web-frontend/modules/database/plugin.js`, import and register after `NumberFieldType`:
    ```javascript
    import { CurrencyFieldType } from '@baserow/modules/database/fieldTypes'
    // ...inside install():
    $registry.register('field', new CurrencyFieldType(context))
    ```

- [x] **Task 7 — i18n strings (AC: #1)**
  - [x] In `web-frontend/modules/database/locales/en.json`, add under `fieldType`:
    ```json
    "currency": "Currency"
    ```
    And under `field`:
    ```json
    "currencySymbol": "Currency symbol"
    ```
  - [x] Add the same keys to any other locale files touched by the database module (check what `en.json` pattern is used — confirm if other locale stubs exist at `web-frontend/modules/database/locales/`).

- [x] **Task 8 — Backend tests (AC: #1, #2, #3)**
  - [x] Create `backend/tests/baserow/contrib/database/field/test_currency_field_type.py`. Mirror `test_number_field_type.py` structure. Key test cases:
    - `test_currency_field_creates_with_symbol`: create a `CurrencyField` via `FieldHandler.create_field(type="currency", currency_symbol="€", number_decimal_places=2)`, assert field persists with correct symbol and decimal places.
    - `test_currency_field_round_trips_api`: POST to `/api/database/fields/table/<id>/` with `type="currency"`, assert response contains `currency_symbol` and `number_decimal_places`; PATCH to update symbol; GET to confirm updated value.
    - `test_currency_field_sorts_numeric`: create two rows with values 9 and 10, sort ascending, assert 9 comes first (not lexical order).
    - `test_currency_field_export_value`: call `CurrencyFieldType().get_export_value(Decimal("12.50"), {"field": field})` with `currency_symbol="$"` and `number_decimal_places=2`, assert result is `"$12.50"`.
    - `test_currency_field_migration_reversible`: use `call_command("migrate", "database", <prev_migration>)` to confirm migration is reversible.
  - [x] Run tests: `just b test backend/tests/baserow/contrib/database/field/test_currency_field_type.py`

- [x] **Task 9 — Frontend tests (AC: #1)**
  - [x] Create `web-frontend/modules/database/test/unit/field/currencyFieldType.spec.js`. Key cases:
    - `CurrencyFieldType.getType()` returns `"currency"`.
    - `toHumanReadableString` prepends the symbol: `toHumanReadableString({currency_symbol: "£", number_decimal_places: 2}, "9.99")` → `"£9.99"`.
    - `toHumanReadableString` handles `null` → returns `""`.
  - [x] Run: `just f yarn test:core web-frontend/modules/database/test/unit/field/currencyFieldType.spec.js`

- [x] **Task 10 — Lint + full test pass**
  - [x] `just lint` (backend + frontend). Fix any ruff or ESLint warnings.
  - [x] `just b test backend/tests/baserow/contrib/database/field/` — confirm no regressions in existing field type tests.

## Dev Notes

- **Dynamic-model pattern confirmed:** `CurrencyField` extends `NumberField` via Django multi-table inheritance. The `database_currencyfield` metadata table stores only `currency_symbol` (and the `numberfield_ptr` FK). The actual data column on the user's table is unchanged — it inherits the parent's `DecimalField` column through `NumberField`'s dynamic-model mechanics. No migration touches user tables. [Source: architecture.md line 122]

- **`number_type` is deprecated — ignore it:** `NumberFieldType.serializer_field_overrides` has `number_type = MustBeEmptyField(...)` (`field_types.py:598`). This is a removed API field. Do NOT add `number_type` to `CurrencyFieldType`; the architecture reference to `number_type` in `architecture.md:122` is historical context from planning, not a new field to add.

- **`number_prefix` vs `currency_symbol`:** `NumberField` already has a `number_prefix` CharField (max_length=10). `CurrencyFieldType` introduces a dedicated `currency_symbol` to give the API clean naming and a non-null default (`$`). In `get_export_value`, DO NOT set `number_prefix` on the field instance — instead read `field_object["field"].currency_symbol` directly and prepend it. The inherited `number_prefix` on `NumberField` is still available for any `NumberFieldType` display path that uses it, but `CurrencyFieldType` overrides display to use `currency_symbol`.

- **Numeric sort is inherited, not implemented:** `NumberFieldType._can_have_db_index = True` and `_can_group_by = True` are inherited. The underlying column type is `DecimalField` — PostgreSQL sorts this numerically by default. The `get_order_by_field_string` override (if any in `NumberFieldType`) handles ordering; confirm via grep. No new ordering code needed for `CurrencyFieldType`. [Source: architecture.md NFR-2]

- **Registration must not double-register:** `field_type_registry` is a singleton. If `CurrencyFieldType` is registered in both `database/apps.py` and somewhere else, `FieldTypeAlreadyRegistered` will be raised. Pattern: one `field_type_registry.register(CurrencyFieldType())` call, in `DatabaseConfig.ready()`, surrounded by no conditional guards (the `ready()` hook itself is called once). Mirror exactly how `NumberFieldType()` is registered at `apps.py:230`. [Source: `backend/src/baserow/contrib/database/fields/registries.py:2256`; `apps.py:230`]

- **Test database env:** `BASEROW_OSS_ONLY=true DATABASE_HOST=localhost DATABASE_PORT=5431 DATABASE_USER=baserow DATABASE_PASSWORD=baserow DATABASE_NAME=baserow JWT_SIGNING_KEY=test-secret-key just b test ...` (confirmed working pattern from Story 1.9 QA). Use `just b test` wrapper.

### Project Structure Notes

```
backend/src/baserow/contrib/database/fields/
  models.py                          # Add CurrencyField class after NumberField (~line 410)
  field_types.py                     # Add CurrencyFieldType after NumberFieldType (~line 740)
  migrations/                        # New auto-generated migration for CurrencyField

backend/src/baserow/contrib/database/
  apps.py                            # Register CurrencyFieldType in ready() (~line 231)

backend/tests/baserow/contrib/database/field/
  test_currency_field_type.py        # New test file

web-frontend/modules/database/
  fieldTypes.js                      # Add CurrencyFieldType after NumberFieldType (~line 1979)
  plugin.js                          # Register CurrencyFieldType (~line 693)
  components/field/
    FieldCurrencySubForm.vue         # New — currency symbol input form
  locales/en.json                    # Add "currency" and "currencySymbol" keys
  test/unit/field/
    currencyFieldType.spec.js        # New frontend test
```

- No changes needed to: `core/`, `premium/`, `enterprise/`, row handler, export handler — this is a pure field-type addition.
- Field permissions (Story 1.4/1.5/1.9) apply automatically: `CurrencyField` is a `Field` subclass and passes through the existing `FieldPermissionManagerType` without any new wiring.

### References

- Story requirements: [Source: _bmad-output/planning-artifacts/epics.md lines 390–402]
- Architecture field-types design: [Source: _bmad-output/planning-artifacts/architecture.md lines 27, 122, 156, 183, 196, 208, 221, 285, 304, 318, 328]
- `NumberField` model: [Source: backend/src/baserow/contrib/database/fields/models.py lines 363–410]
- `NumberFieldType` implementation: [Source: backend/src/baserow/contrib/database/fields/field_types.py lines 575–740]
- `field_type_registry` registration pattern: [Source: backend/src/baserow/contrib/database/apps.py lines 226–245]
- Frontend `NumberFieldType`: [Source: web-frontend/modules/database/fieldTypes.js lines 1745–1979]
- Frontend plugin registration: [Source: web-frontend/modules/database/plugin.js lines 689–704]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- CurrencyField model already existed in models.py from create-story step; migration 0216 generated.
- CurrencyFieldType already implemented in field_types.py from create-story step.
- FieldCurrencySubForm.vue created; uses fieldSubForm mixin with currency_symbol field.
- All 6 backend tests pass; all 4 frontend tests pass.
- i18n: "currency" key added to /web-frontend/locales/en.json fieldType section; fieldCurrencySubForm section added to modules/database/locales/en.json.
- Ruff import-order fix applied to apps.py (pre-existing issue, auto-fixed).

### File List
