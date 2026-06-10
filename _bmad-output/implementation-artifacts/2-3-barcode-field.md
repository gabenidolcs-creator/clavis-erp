---
baseline_commit: 6f4946ac9
---

# Story 2.3: Barcode Field

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want a Barcode Field that renders a stored value as a scannable code,
so that QR codes or Code 128 barcodes are displayed client-side from data.

Realizes FR-20. **Bucket B `[B]` — license-clean new implementation; no clean-room gate required.**

## Context & Scope

**Stories 2.1 (Currency Field) and 2.2 (Percent Field) are done.** Both extend `NumberField`/`NumberFieldType`. Barcode is architecturally different: it **wraps `TextField`** with a `barcode_type` metadata column.

**What this story builds:** A `BarcodeField` model (MTI subclass of `TextField`) and `BarcodeFieldType` (extends `TextFieldType`). The field stores a plain text string. Display renders client-side as a QR code or Code 128 barcode SVG depending on `barcode_type`. Camera-based scanning is out of scope.

**Architecture reference — D5 (architecture.md line 114):**
> "Barcode (display only) | qrcode.vue + Code128 renderer (jsbarcode-class lib) | MIT | latest | client-side render from stored value; symbology configurable. Camera scanning deferred (FR-20)."

**D-fields summary (architecture.md line 122):**
> "Barcode wraps `TextField` with `barcode_type`"

**Symbology choices (both MIT-licensed):**
- `'qr'` — QR Code via [`qrcode.vue`](https://github.com/scopewu/qrcode.vue) — Vue 3 component, renders SVG, supports any string up to ~4KB
- `'code128'` — Code 128 barcode via [`jsbarcode`](https://github.com/lindell/JsBarcode) — renders to SVG element imperatively, supports ASCII chars 0–127

Both packages are new dependencies that must be added via `yarn add qrcode.vue jsbarcode` in `web-frontend/`.

**Scope boundary:**
- **IN:** `BarcodeField` model + migration; `BarcodeFieldType` backend + frontend; `barcode_type` configurable (`'qr'` | `'code128'`, default `'qr'`); `FieldBarcodeSubForm.vue` with type dropdown; `GridViewFieldBarcode.vue` rendering barcode SVG in grid cells; registration in `apps.py` and `plugin.js`; i18n keys; backend + frontend tests.
- **OUT:** Camera scanning (deferred per FR-20), Autonumber (2.4), Running Count (2.5). Do not stub or implement any other Epic 2 field type.
- **OUT:** Backend validation of value against symbology charset — Code128 encoding errors are handled in the frontend with a silent fallback; no backend reject.

## Acceptance Criteria

1. **Barcode Field creates, configures, and persists symbology.** Given an editor creates a Barcode Field, when they leave `barcode_type` at default (`qr`) and a row has a text value, then the grid cell renders a QR code SVG for that value; the `barcode_type` persists through PATCH and GET round-trip. [Source: epics.md lines 425–428]

2. **Code 128 symbology renders correctly.** Given a Barcode Field with `barcode_type = 'code128'`, when a row has a value containing only ASCII chars 0–127, then the grid cell renders a Code 128 barcode SVG. [Source: epics.md lines 425–428; architecture.md line 114]

3. **Display only — editing stores plain text.** Given a Barcode Field, when a user edits a row via the row edit modal, then they type a plain text string (no camera input); the stored value is the raw text; the grid cell renders the barcode from that value. [Source: epics.md lines 432–435]

4. **Empty value renders nothing.** Given a Barcode Field, when a row value is null or empty, then the grid cell displays empty (no barcode, no error). [Source: standard UX convention]

5. **Invalid Code128 input degrades gracefully.** Given a Barcode Field with `barcode_type = 'code128'`, when the stored value contains characters outside ASCII 0–127, then the grid cell renders an empty cell (no crash, no unhandled exception). [Source: scope boundary above]

## Tasks / Subtasks

- [x] **Task 1 — `BarcodeField` model + migration (AC: #1, #2)**
  - [x] In `backend/src/baserow/contrib/database/fields/models.py`, after the `TextField` class definition (~line 350), add:
    ```python
    BARCODE_TYPE_CHOICES = [
        ('qr', 'QR Code'),
        ('code128', 'Code 128'),
    ]


    class BarcodeField(TextField):
        barcode_type = models.CharField(
            max_length=20,
            choices=BARCODE_TYPE_CHOICES,
            default='qr',
            help_text='The barcode symbology to render (qr or code128).',
        )

        class Meta:
            app_label = 'database'
    ```
    `BarcodeField` is a Django MTI subclass of `TextField`. The text value (barcode content) is stored in the user table column via `TextField.get_model_field()` — unchanged. Only `barcode_type` is new metadata, stored in a new `database_barcodefield` table.
  - [x] Generate migration: `just b make-migrations database`. Expected `0218_barcodefield.py` (next after `0217`). Verify: new `database_barcodefield` table has `textfield_ptr_id` FK + `barcode_type` VARCHAR(20) column with `db_default='qr'`. No user-table columns added. Confirm migration is reversible.

- [x] **Task 2 — `BarcodeFieldType` backend (AC: #1, #2, #3)**
  - [x] In `backend/src/baserow/contrib/database/fields/field_types.py`, add `BarcodeFieldType` after `PercentFieldType` (~line 913):
    ```python
    class BarcodeFieldType(TextFieldType):
        type = "barcode"
        model_class = BarcodeField
        allowed_fields = TextFieldType.allowed_fields + ["barcode_type"]
        serializer_field_names = TextFieldType.serializer_field_names + ["barcode_type"]
        _can_group_by = True
        _can_have_db_index = True
    ```
    No `prepare_values()` override needed — `barcode_type` is user-configurable and passes through unchanged. `get_serializer_field`, `get_model_field`, `contains_query`, and `get_value_for_filter` are all inherited from `TextFieldType` without change.
  - [x] Add `BarcodeField` to the imports block in `field_types.py` alphabetically. Search the existing import block: `grep -n "from baserow.contrib.database.fields.models import" backend/src/baserow/contrib/database/fields/field_types.py`. `BarcodeField` sorts before `CurrencyField` alphabetically — insert it first in the list.
  - [x] No serializer field override required — DRF serializes `CharField(choices=...)` from the model field automatically, returning valid choice strings.

- [x] **Task 3 — Register `BarcodeFieldType` in `apps.py` (AC: #1)**
  - [x] In `backend/src/baserow/contrib/database/apps.py`, add `BarcodeField` to model imports and `BarcodeFieldType` to type imports. Add registration inside `ready()` after `PercentFieldType()`:
    ```python
    field_type_registry.register(BarcodeFieldType())
    ```
    Lazy import inside `ready()` — mirror exactly how `CurrencyFieldType()` and `PercentFieldType()` are registered at lines 233–234. `BarcodeFieldType` sorts before `CurrencyFieldType` alphabetically in the import statement.

- [x] **Task 4 — Install npm packages (AC: #1, #2)**
  - [x] In `web-frontend/`, run: `yarn add qrcode.vue jsbarcode`
  - [x] Confirm both packages install and `package.json` + `yarn.lock` are updated. `qrcode.vue` is MIT, Vue 3 compatible. `jsbarcode` (v3.9.x) is MIT, framework-agnostic. Do NOT add `@types/jsbarcode` — the project is not using TypeScript in this module.
  - [x] These packages do NOT need to be lazy-loaded — they are small (qrcode.vue ~7KB, jsbarcode ~30KB) and only used when a Barcode Field exists. The bundle-discipline rule (D1) applies specifically to ECharts/MapLibre/Frappe Gantt; barcode libs are below the threshold.

- [x] **Task 5 — Frontend `BarcodeFieldType` in `fieldTypes.js` (AC: #1, #2, #3)**
  - [x] Import `FieldBarcodeSubForm` and `GridViewFieldBarcode` at the top of `fieldTypes.js` alongside other subform and grid component imports (tasks 6 and 7 must be created first):
    ```javascript
    import FieldBarcodeSubForm from '@baserow/modules/database/components/field/FieldBarcodeSubForm'
    import GridViewFieldBarcode from '@baserow/modules/database/components/view/grid/fields/GridViewFieldBarcode'
    ```
  - [x] Add `BarcodeFieldType` class after `PercentFieldType` (~line 2038):
    ```javascript
    export class BarcodeFieldType extends TextFieldType {
      static getType() {
        return 'barcode'
      }

      static getIconClass() {
        return 'iconoir-barcode'
      }

      getName() {
        const { $i18n: i18n } = this.app
        return i18n.t('fieldType.barcode')
      }

      getFormComponent() {
        return FieldBarcodeSubForm
      }

      getGridViewFieldComponent() {
        return GridViewFieldBarcode
      }

      getDefaultValueFieldName() {
        return 'text_default'
      }

      toHumanReadableString(field, value) {
        if (value === null || value === undefined) return ''
        return String(value)
      }
    }
    ```
    `getType()` must match backend `type = "barcode"` exactly. `iconoir-barcode` confirmed at `web-frontend/node_modules/iconoir/icons/barcode.svg`.

- [x] **Task 6 — Vue form component `FieldBarcodeSubForm.vue` (AC: #1)**
  - [x] Create `web-frontend/modules/database/components/field/FieldBarcodeSubForm.vue`:
    ```vue
    <template>
      <div>
        <FormGroup
          small-label
          :label="$t('fieldBarcodeSubForm.typeLabel')"
          class="margin-bottom-2"
        >
          <Dropdown
            v-model="values.barcode_type"
            :show-search="false"
            :fixed-items="true"
          >
            <DropdownItem name="QR Code" value="qr" />
            <DropdownItem name="Code 128" value="code128" />
          </Dropdown>
        </FormGroup>
        <FieldTextSubForm :default-values="defaultValues" />
      </div>
    </template>

    <script>
    import form from '@baserow/modules/core/mixins/form'
    import fieldSubForm from '@baserow/modules/database/mixins/fieldSubForm'
    import FieldTextSubForm from '@baserow/modules/database/components/field/FieldTextSubForm'

    export default {
      name: 'FieldBarcodeSubForm',
      components: { FieldTextSubForm },
      mixins: [form, fieldSubForm],
      data() {
        return {
          allowedValues: ['barcode_type'],
          values: {
            barcode_type: 'qr',
          },
        }
      },
    }
    </script>
    ```
    `allowedValues: ['barcode_type']` — only `barcode_type` is owned by this form. `text_default` is collected from the embedded `FieldTextSubForm` via the `fieldSubForm` mixin's `getChildForms()` mechanism. `Dropdown` and `DropdownItem` are globally registered Baserow core components — no import needed. `defaultValues` prop is provided by the `fieldSubForm` mixin.

- [x] **Task 7 — Vue grid component `GridViewFieldBarcode.vue` (AC: #1, #2, #4, #5)**
  - [x] Create `web-frontend/modules/database/components/view/grid/fields/GridViewFieldBarcode.vue`:
    ```vue
    <template>
      <div ref="cell" class="grid-view__cell active">
        <div v-if="value" class="grid-field-barcode">
          <qrcode-vue
            v-if="field.barcode_type === 'qr'"
            :value="String(value)"
            :size="64"
            render-as="svg"
          />
          <svg v-else ref="code128Svg" class="grid-field-barcode__code128" />
        </div>
      </div>
    </template>

    <script>
    import gridField from '@baserow/modules/database/mixins/gridField'
    import QrcodeVue from 'qrcode.vue'
    import JsBarcode from 'jsbarcode'

    export default {
      name: 'GridViewFieldBarcode',
      components: { QrcodeVue },
      mixins: [gridField],
      watch: {
        value: {
          immediate: true,
          handler(val) {
            this.$nextTick(() => this._renderCode128(val))
          },
        },
        'field.barcode_type': {
          handler() {
            this.$nextTick(() => this._renderCode128(this.value))
          },
        },
      },
      methods: {
        _renderCode128(val) {
          if (!val || this.field.barcode_type !== 'code128') return
          if (!this.$refs.code128Svg) return
          try {
            JsBarcode(this.$refs.code128Svg, String(val), {
              format: 'CODE128',
              width: 1,
              height: 40,
              displayValue: false,
              margin: 0,
            })
          } catch (e) {
            // Invalid Code128 characters — clear SVG rather than leaving garbage (AC #5)
            this.$refs.code128Svg.innerHTML = ''
          }
        },
      },
    }
    </script>
    ```
    The `gridField` mixin provides `field` and `value` props plus cell focus/blur handling. `QrcodeVue` is used as a component for QR rendering. `JsBarcode` is called imperatively via a `$refs.code128Svg` SVG element for Code128. The `try/catch` in `_renderCode128` handles invalid Code128 characters (AC #5). Both watchers use `$nextTick` to ensure the SVG ref is in the DOM before JsBarcode is invoked.

- [x] **Task 8 — Register `BarcodeFieldType` in frontend `plugin.js` (AC: #1)**
  - [x] In `web-frontend/modules/database/plugin.js`, add `BarcodeFieldType` to the import from `fieldTypes`:
    ```javascript
    import { ..., BarcodeFieldType } from '@baserow/modules/database/fieldTypes'
    ```
    And inside `install()`, after `PercentFieldType` registration (~line 696):
    ```javascript
    $registry.register('field', new BarcodeFieldType(context))
    ```

- [x] **Task 9 — i18n strings (AC: #1)**
  - [x] In `web-frontend/locales/en.json`, add `"barcode": "Barcode"` under the `fieldType` object (same location where `"currency"` and `"percent"` keys live). Confirm exact key path: `grep -n '"fieldType"' web-frontend/locales/en.json`.
  - [x] In `web-frontend/modules/database/locales/en.json`, add under the root object:
    ```json
    "fieldBarcodeSubForm": {
      "typeLabel": "Barcode type"
    }
    ```

- [x] **Task 10 — Backend tests (AC: #1, #2, #3)**
  - [x] Create `backend/tests/baserow/contrib/database/field/test_barcode_field_type.py`. Mirror `test_currency_field_type.py` structure. Required test cases:
    - `test_barcode_field_registered`: `field_type_registry.get("barcode")` returns a `BarcodeFieldType` instance.
    - `test_barcode_field_creates_with_default_qr_type`: create via `FieldHandler().create_field(user, table, type_name="barcode", name="Code")`, assert `field.barcode_type == "qr"` and `isinstance(field, BarcodeField)`.
    - `test_barcode_field_creates_with_code128_type`: create with `barcode_type="code128"`, assert `field.barcode_type == "code128"`.
    - `test_barcode_field_api_round_trip`: POST `{"type": "barcode", "name": "QR"}`, assert `barcode_type` in response; PATCH with `{"barcode_type": "code128"}`; GET to confirm change persists.
    - `test_barcode_field_stores_text_value`: create field, create row with string value, assert row value reads back unchanged (BarcodeField stores and retrieves plain text).
    - `test_barcode_field_migration_reversible`: confirm migration is reversible.
  - [x] Run: `just b test backend/tests/baserow/contrib/database/field/test_barcode_field_type.py`

- [x] **Task 11 — Frontend tests (AC: #1)**
  - [x] Create `web-frontend/test/unit/database/barcodeFieldType.spec.js`. Key cases:
    - `BarcodeFieldType.getType()` returns `"barcode"`.
    - `BarcodeFieldType.getIconClass()` returns `"iconoir-barcode"`.
    - `toHumanReadableString(field, "ABC-123")` returns `"ABC-123"`.
    - `toHumanReadableString(field, null)` returns `""`.
    - `toHumanReadableString(field, undefined)` returns `""`.
  - [x] Run: `just f yarn test:core web-frontend/test/unit/database/barcodeFieldType.spec.js`

- [x] **Task 12 — Lint + full test pass**
  - [x] `just lint` — fix any ruff/ESLint warnings.
  - [x] `just b test backend/tests/baserow/contrib/database/field/` — confirm no regressions in `test_text_field_type.py`, `test_currency_field_type.py`, `test_percent_field_type.py`.

## Dev Notes

- **`BarcodeField` extends `TextField`, NOT `NumberField`:** The stored value is plain text (barcode content). Architecture confirms: "Barcode wraps `TextField` with `barcode_type`". Pattern differs from Currency/Percent which extend NumberField. [Source: architecture.md line 122]

- **`class Meta: app_label = "database"` required on `BarcodeField`:** Without it, Django assigns wrong app label causing migration/registry issues. Confirmed lesson from stories 2.1 and 2.2. [Source: story 2.2 Dev Notes]

- **Migration creates `database_barcodefield` table** with `textfield_ptr_id` FK + `barcode_type` VARCHAR(20) column. No user-table columns added. Barcode content is stored in the text column of the user table via the inherited `TextFieldType.get_model_field()` path. The MTI chain: user row → text column in `{table_name}` → field metadata in `database_textfield` + `database_barcodefield`.

- **`allowed_fields` inclusion is critical:** `BarcodeFieldType.allowed_fields = TextFieldType.allowed_fields + ["barcode_type"]`. Without this, `FieldHandler.create_field(barcode_type='qr')` silently ignores the value. Mirrors `CurrencyFieldType` pattern for `currency_symbol`. [Source: field_types.py lines 888–890]

- **Ruff import order — `BarcodeField` before `CurrencyField`:** Alphabetically, `B` < `C`, so `BarcodeField` and `BarcodeFieldType` must appear before `CurrencyField`/`CurrencyFieldType` in import lists in `field_types.py` and `apps.py`. `just lint` catches violations.

- **`apps.py` lazy import pattern:** Import inside `ready()`, not at module level. Mirror lines 202/218/233 for CurrencyFieldType/PercentFieldType registration.

- **Frontend `BarcodeFieldType` extends `TextFieldType`:** Inherits text editing (row edit modal renders `RowEditFieldText`), text sort/filter, `contains_query`/`contains_word_query`, and `getDefaultValue`. Only overrides: grid view component (visual barcode), form component (barcode_type selector), icon, and name. [Source: fieldTypes.js line 1122]

- **`_renderCode128` watcher pattern:** Code128 rendering is imperative (JsBarcode needs a DOM SVG ref). The Vue watcher fires after reactive data changes; `$nextTick` ensures the SVG element is present in the DOM before JsBarcode is called. Two watchers: one on `value` (new row data) and one on `field.barcode_type` (user switches symbology). [Source: Vue 3 $nextTick docs]

- **JsBarcode throws on invalid Code128 input:** Characters outside ASCII 0–127 cause JsBarcode to throw. The `try/catch` in `_renderCode128` clears the SVG element on error, giving a blank cell instead of a crash (AC #5). Do NOT rethrow — silently degrade. [Source: jsbarcode GitHub issues]

- **qrcode.vue Vue 3 API:** `import QrcodeVue from 'qrcode.vue'`; render as `<qrcode-vue :value="..." :size="64" render-as="svg" />`. The `size` prop is in pixels. `render-as="svg"` is preferred over `"canvas"` for grid cells (no CORS issues, scales cleanly). [Source: qrcode.vue README]

- **Grid cell overflow:** QR code size=64px may exceed default grid row height (33px). Add `overflow: hidden` CSS to `.grid-field-barcode` or set `size` to a smaller value (e.g., 32) to fit. CSS is local to the component — no global scope needed.

- **`toHumanReadableString` override:** Returns the raw string value (barcode content), not a visual. This is correct: exports/copy operations need the text, not an SVG. The inherited `TextFieldType.toHumanReadableString` already does this, but the explicit override documents the intent and guards against edge cases.

- **No `FunctionalGridViewFieldBarcode` needed for v1:** Functional grid variants exist for performance-critical fields. Barcode is display-only with moderate frequency — a standard Vue SFC component is sufficient. Add functional variant in a future story if profiling shows need.

- **Test database env:** `BASEROW_OSS_ONLY=true DATABASE_HOST=localhost DATABASE_PORT=5431 DATABASE_USER=baserow DATABASE_PASSWORD=baserow DATABASE_NAME=baserow JWT_SIGNING_KEY=test-secret-key just b test ...`

### Project Structure Notes

```
backend/src/baserow/contrib/database/fields/
  models.py                                    # Add BARCODE_TYPE_CHOICES + BarcodeField after TextField (~line 350)
  field_types.py                               # Add BarcodeFieldType after PercentFieldType (~line 913)
  migrations/
    0218_barcodefield.py                       # Auto-generated

backend/src/baserow/contrib/database/
  apps.py                                      # Register BarcodeFieldType (import + register after PercentFieldType)

backend/tests/baserow/contrib/database/field/
  test_barcode_field_type.py                   # New

web-frontend/
  package.json                                 # Add qrcode.vue and jsbarcode
  yarn.lock                                    # Updated by yarn add

web-frontend/modules/database/
  fieldTypes.js                                # Add BarcodeFieldType after PercentFieldType (~line 2038)
  plugin.js                                    # Register BarcodeFieldType after PercentFieldType (~line 696)
  components/field/
    FieldBarcodeSubForm.vue                    # New — barcode_type dropdown + embeds FieldTextSubForm
  components/view/grid/fields/
    GridViewFieldBarcode.vue                   # New — renders QR/Code128 SVG from field value

web-frontend/locales/en.json                   # Add "barcode": "Barcode" under fieldType
web-frontend/modules/database/locales/en.json  # Add fieldBarcodeSubForm.typeLabel
web-frontend/test/unit/database/
  barcodeFieldType.spec.js                     # New
```

- No changes to: `core/`, `premium/`, `enterprise/`, row handler, export handler, filter/sort logic.
- Field permissions (Stories 1.4/1.5/1.9) apply automatically — `BarcodeField` is a `Field` subclass.
- Export via `TextFieldType.get_export_value` returns raw text (no barcode image). Correct for CSV export.
- `contains_query` and `contains_word_query` inherited from `TextFieldType` — text search on barcode content works without changes.

### Previous Story Intelligence (2.1 CurrencyField + 2.2 PercentField)

- **`class Meta: app_label = "database"` required** on new field subclass — confirmed critical from both prior stories.
- **Migration may bundle spurious `AlterField` operations** — accept as-is (same pattern as `0216` and `0217`). Do not manually remove.
- **`apps.py` lazy import pattern** — import inside `ready()`, not at module level.
- **Ruff import order** — alphabetical in import blocks. `BarcodeField`/`BarcodeFieldType` (B) sorts before `CurrencyField`/`CurrencyFieldType` (C) — insert it first in combined import lists.
- **i18n key placement:** Global `fieldType.barcode` → `web-frontend/locales/en.json`. Component-specific keys (`fieldBarcodeSubForm.*`) → `web-frontend/modules/database/locales/en.json`. Do NOT add to both files.
- **Registration order in `plugin.js`** — place after PercentFieldType registration for consistency with `apps.py`.

### References

- Story requirements: [Source: _bmad-output/planning-artifacts/epics.md lines 420–436]
- Architecture D5 (barcode library decision): [Source: _bmad-output/planning-artifacts/architecture.md line 114]
- Architecture D-fields (barcode wraps TextField): [Source: _bmad-output/planning-artifacts/architecture.md line 122]
- `TextField` model (parent class): [Source: backend/src/baserow/contrib/database/fields/models.py line ~343]
- `TextFieldType` backend (parent type): [Source: backend/src/baserow/contrib/database/fields/field_types.py line 430]
- `CurrencyFieldType.allowed_fields` pattern: [Source: backend/src/baserow/contrib/database/fields/field_types.py lines 888–890]
- `PercentFieldType` (direct predecessor): [Source: backend/src/baserow/contrib/database/fields/field_types.py lines 901–913]
- `apps.py` registration (CurrencyFieldType/PercentFieldType lines): [Source: backend/src/baserow/contrib/database/apps.py lines 202, 218, 233–234]
- Frontend `TextFieldType` (parent): [Source: web-frontend/modules/database/fieldTypes.js line 1122]
- Frontend `PercentFieldType` (predecessor): [Source: web-frontend/modules/database/fieldTypes.js line 2009]
- `FieldCurrencySubForm.vue` (subform with extra field — model for FieldBarcodeSubForm): [Source: web-frontend/modules/database/components/field/FieldCurrencySubForm.vue]
- `FieldTextSubForm.vue` (text_default subform to embed): [Source: web-frontend/modules/database/components/field/FieldTextSubForm.vue]
- `FieldRatingSubForm.vue` (Dropdown usage pattern): [Source: web-frontend/modules/database/components/field/FieldRatingSubForm.vue]
- `GridViewFieldAutonumber.vue` (grid component pattern): [Source: web-frontend/modules/database/components/view/grid/fields/GridViewFieldAutonumber.vue]
- `gridField` mixin: [Source: web-frontend/modules/database/mixins/gridField]
- `plugin.js` field registration lines: [Source: web-frontend/modules/database/plugin.js lines 695–696]
- iconoir barcode icon: [Source: web-frontend/node_modules/iconoir/icons/barcode.svg]
- Story 2.2 reference (PercentField): [Source: _bmad-output/implementation-artifacts/2-2-percent-field.md]
- `test_currency_field_type.py` (test pattern): [Source: backend/tests/baserow/contrib/database/field/test_currency_field_type.py]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None.

### Completion Notes List

- BarcodeField MTI subclass of TextField added to models.py with BARCODE_TYPE_CHOICES and `class Meta: app_label = "database"`.
- Migration 0218 auto-generated: creates `database_barcodefield` table with `textfield_ptr_id` FK + `barcode_type` VARCHAR(20).
- BarcodeFieldType added to field_types.py after PercentFieldType; BarcodeField import inserted before CurrencyField (alphabetical).
- BarcodeFieldType registered in apps.py before CurrencyFieldType (alphabetical); lazy import inside ready().
- qrcode.vue + jsbarcode installed via yarn add; package.json + yarn.lock updated.
- BarcodeFieldType class added to fieldTypes.js extending TextFieldType with barcode-specific overrides.
- FieldBarcodeSubForm.vue created with barcode_type Dropdown + embedded FieldTextSubForm.
- GridViewFieldBarcode.vue created with QrcodeVue for QR and JsBarcode imperative SVG for Code128; try/catch for invalid chars (AC #5).
- BarcodeFieldType registered in plugin.js before CurrencyFieldType.
- i18n: "barcode": "Barcode" in web-frontend/locales/en.json; fieldBarcodeSubForm.typeLabel in database locales/en.json.
- 6 backend tests pass; 5 frontend tests pass; no regressions in currency/percent test suites.

### File List

- backend/src/baserow/contrib/database/fields/models.py
- backend/src/baserow/contrib/database/fields/field_types.py
- backend/src/baserow/contrib/database/apps.py
- backend/src/baserow/contrib/database/migrations/0218_barcodefield_alter_formview_mode.py
- backend/tests/baserow/contrib/database/field/test_barcode_field_type.py
- web-frontend/modules/database/fieldTypes.js
- web-frontend/modules/database/plugin.js
- web-frontend/modules/database/components/field/FieldBarcodeSubForm.vue
- web-frontend/modules/database/components/view/grid/fields/GridViewFieldBarcode.vue
- web-frontend/locales/en.json
- web-frontend/modules/database/locales/en.json
- web-frontend/test/unit/database/barcodeFieldType.spec.js
- web-frontend/package.json
- web-frontend/yarn.lock
