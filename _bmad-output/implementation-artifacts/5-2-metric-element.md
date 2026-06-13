# Story 5.2: Metric Element

---
baseline_commit: 2f8c3235aeec1cbf28376d243444417d7f7c8b0f
---

Status: done

## Story

As a builder,
I want to place a summary metric Element on a Page bound to a Data Source,
so that published apps show a key aggregated number from live table data. Realizes FR-23, UJ-3. `[B]`

## Acceptance Criteria

1. **Given** an App Builder Page, **when** a builder adds a Metric Element and selects a `local_baserow_aggregate_rows` Data Source (with field + aggregation type configured), **then** the element renders the formatted scalar result on the published Page.
2. **Given** a Metric Element whose Data Source returns a numeric aggregation (e.g., SUM of a number field), **when** the Page loads, **then** the displayed value is formatted by `LocalBaserowAggregateRowsServiceType.getResult()` (field-type-aware formatting — same as Dashboard SummaryWidget).
3. **Given** a Metric Element with no `data_source_id` set or whose Data Source is misconfigured (returns `_error`), **when** the element renders, **then** it shows a visible error/empty state instead of crashing.
4. **Given** the `MetricElementType` is registered, **when** a builder opens the add-element modal, **then** the Metric Element type appears as a selectable option with the `iconoir-sigma-function` icon.
5. **Given** field-permission rules are active, **when** the Metric Element dispatches its Data Source, **then** the aggregate query passes through `PERMISSION_MANAGERS` (enforced by `LocalBaserowAggregateRowsServiceType` — verify no bypass is introduced, same guard as Story 5.1 AC 7).
6. **Given** a Metric Element on a Page, **when** the element content store fetches via `local_baserow_aggregate_rows`, **then** `element._.content` is populated with the raw service response `{ result: <value> }` and the computed `displayValue` calls `serviceType.getResult(dataSource, content)` to produce the formatted string.
7. **Given** a `MetricElement` record in the database, **when** the element is serialized via the API, **then** `data_source_id` is returned; `chart_type` is NOT a field on this element (Metric Element is simpler than Chart Element — no chart type variant).

## Tasks / Subtasks

- [x] Task 1 — Backend: `MetricElement` model (AC: 1, 7)
  - [x] Add `MetricElement(Element)` class to `backend/src/baserow/contrib/builder/elements/models.py` after `ChartElement`, with only a `data_source` FK to `builder.DataSource` (`SET_NULL`, nullable). No `chart_type` field.
  - [x] Add `MetricElementType` to `backend/src/baserow/contrib/builder/elements/element_types.py` after `ChartElementType`: `type = "metric"`, `model_class = MetricElement`, `allowed_fields = ["data_source", "data_source_id"]`, `serializer_field_names = ["data_source_id"]`, `request_serializer_field_names = ["data_source_id"]`. Serializer override: `data_source_id` as nullable IntegerField. `get_pytest_params` returns `{"data_source_id": None}`.
  - [x] Import `MetricElement` in `element_types.py` (top-level import block, line ~45).

- [x] Task 2 — Backend: Registration and migration (AC: 4, 7)
  - [x] In `backend/src/baserow/contrib/builder/apps.py`: import `MetricElementType` alongside `ChartElementType` (line ~174) and register `MetricElementType()` in `ready()` (line ~219).
  - [x] Create `backend/src/baserow/contrib/builder/migrations/0071_metricelement.py`. Depends on `('builder', '0070_chartelement')`. `CreateModel` named `MetricElement` with `element_ptr` (OneToOneField, parent_link, PK) and `data_source` (ForeignKey to `builder.datasource`, SET_NULL, null=True, blank=True). No other fields.

- [x] Task 3 — Frontend: `MetricElement.vue` display component (AC: 1, 2, 3, 6)
  - [x] Create `web-frontend/modules/builder/components/elements/components/MetricElement.vue`.
  - [x] Props: `element` (Object, required), `builder` (Object, required), `page` (Object, required), `mode` (String, required) — mirrors ChartElement props.
  - [x] Computed `elementContent`: `this.$store.getters['elementContent/getElementContent'](this.element)` — returns `element._.content` which is `{ result: <value> }` or `{ _error: "..." }` or `[]` (before load).
  - [x] Computed `misconfigured`: true when `elementContent?._error` is set OR `element.data_source_id` is null/undefined.
  - [x] Computed `dataSource`: `this.$store.getters['dataSource/getPageDataSourceById'](this.page, this.element.data_source_id)`.
  - [x] Computed `displayValue`: if `!misconfigured && dataSource && elementContent?.result !== undefined`, call `this.$registry.get('service', this.dataSource.type).getResult(this.dataSource, this.elementContent)`; else return `null`.
  - [x] Template: renders `<div class="metric-element">` containing: (a) `<p class="metric-element__value">{{ displayValue }}</p>` when `displayValue !== null`; (b) `<p class="metric-element__error">{{ $t('metricElement.dataSourceError') }}</p>` when content has `_error`; (c) `<p class="metric-element__empty">{{ $t('metricElement.noData') }}</p>` otherwise.

- [x] Task 4 — Frontend: `MetricElementForm.vue` settings form (AC: 1)
  - [x] Create `web-frontend/modules/builder/components/elements/components/forms/general/MetricElementForm.vue`.
  - [x] Uses `elementForm` mixin from `@baserow/modules/builder/mixins/elementForm`.
  - [x] `allowedValues: ['data_source_id']`, `values: { data_source_id: null }`.
  - [x] Template: single `FormGroup` with label `$t('metricElementForm.dataSource')`, containing `<DataSourceDropdown v-model="values.data_source_id" small />`.
  - [x] Import `DataSourceDropdown` from `@baserow/modules/builder/components/dataSource/DataSourceDropdown`.
  - [x] No chart-type dropdown — Metric Element has no type variant.

- [x] Task 5 — Frontend: `MetricElementType` in `elementTypes.js` (AC: 4)
  - [x] Import `MetricElement` and `MetricElementForm` at the top of `web-frontend/modules/builder/elementTypes.js` alongside the ChartElement imports (lines ~108-109).
  - [x] Import `elementImageMetric` from `@baserow/modules/builder/assets/icons/element-metric.svg?url` (line ~99 import block). Created placeholder SVG at `web-frontend/modules/builder/assets/icons/element-metric.svg` (designer asset needed for production).
  - [x] Add `MetricElementType` class after `ChartElementType` at the bottom of `elementTypes.js`.

- [x] Task 6 — Frontend: Plugin registration (AC: 4)
  - [x] In `web-frontend/modules/builder/plugin.js`: import `MetricElementType` alongside `ChartElementType` (line ~52). Register `new MetricElementType(context)` immediately after `ChartElementType` registration (line ~231).

- [x] Task 7 — Frontend: i18n strings (AC: 3, 4)
  - [x] Add to `web-frontend/modules/builder/locales/en.json` in the `elementType` object (after `chartDescription`): `"metric"` and `"metricDescription"` keys.
  - [x] Add new top-level keys `"metricElement"` and `"metricElementForm"` sections after `chartElementForm`.

- [x] Task 8 — Frontend: Unit test (AC: 1, 2, 3, 6)
  - [x] Create `web-frontend/test/unit/builder/components/elements/components/MetricElement.spec.js`.
  - [x] 5 test cases: renders value, renders error state, renders empty state, displayValue null when no dataSource, calls getResult with correct args. All pass.

- [x] Task 9 — E2E test (AC: 1, 3, 4, 7)
  - [x] Create `e2e-tests/tests/builder/elements/metricElement.spec.ts`.
  - [x] Scenarios: API creates metric element, no chart_type field on serialization, UI add from modal, empty state with no data source, configured data source renders formatted scalar.
  - [x] Note at top: E2E tests require a running dev stack (`just dev up`). No local deps installed — run via `just` commands.

## Dev Notes

### Architecture Context

- **Data source type:** `local_baserow_aggregate_rows` (registered in `web-frontend/modules/integrations/plugin.js` line 46). Returns `{ result: <scalar> }` per dispatch — NOT an array like `local_baserow_grouped_aggregate_rows` (used by ChartElement).
- **Builder element content flow:** `elementContent/getElementContent(element)` getter reads `element._.content`. For aggregate_rows, the service response shape is `{ result: <value> }`. The content is stored per-element after builder data source dispatch (`web-frontend/modules/builder/store/elementContent.js` line 230).
- **Formatted display:** `LocalBaserowAggregateRowsServiceType.getResult(service, data)` at `web-frontend/modules/integrations/localBaserow/serviceTypes.js:353` formats the scalar using field-type-aware aggregation formatting (`aggregationType.formatValue`). MetricElement must call this — do not display `data.result` raw.
- **Data source resolution:** Use `this.$store.getters['dataSource/getPageDataSourceById'](page, element.data_source_id)` from `web-frontend/modules/builder/store/dataSource.js:401`.
- **Pattern to follow:** `ChartElement` (Story 5.1) is the direct predecessor. Mirror its `props`, store getter patterns, and error/empty state guards. Metric is simpler — no `chart_type`, no ECharts rendering.
- **Dashboard SummaryWidget parallel:** `web-frontend/modules/dashboard/components/widget/SummaryWidget.vue` implements the same `getResult()` pattern in Dashboard context. Metric Element brings this capability to App Builder Pages.
- **Permission guard:** `LocalBaserowAggregateRowsServiceType` already enforces permission checks server-side. Do not add client-side bypass — just use the standard builder dispatch pipeline (same principle as Story 5.1 AC 7).

### Project Structure Notes

- Backend model: append after `ChartElement` in `models.py` (line ~1139 block). No new abstract base needed.
- Backend element_types.py: `ChartElementType` ends around line 2580. Add `MetricElementType` immediately after.
- Frontend components: same dir as `ChartElement.vue` → `web-frontend/modules/builder/components/elements/components/`.
- Frontend form: same dir as `ChartElementForm.vue` → `.../forms/general/`.
- Migration: next after `0070_chartelement.py` → `0071_metricelement.py`.
- SVG asset: `web-frontend/modules/builder/assets/icons/element-metric.svg`. No existing file — create placeholder. `element-chart.svg` is the closest visual reference.

### References

- ChartElement model: `backend/src/baserow/contrib/builder/elements/models.py` line ~1139
- ChartElementType: `backend/src/baserow/contrib/builder/elements/element_types.py` line ~2530
- ChartElement migration: `backend/src/baserow/contrib/builder/migrations/0070_chartelement.py`
- ChartElement frontend: `web-frontend/modules/builder/components/elements/components/ChartElement.vue`
- ChartElementForm: `.../forms/general/ChartElementForm.vue`
- ChartElementType frontend: `web-frontend/modules/builder/elementTypes.js` line ~2760
- Builder plugin registration: `web-frontend/modules/builder/plugin.js` lines ~52, ~231
- elementContent store getter: `web-frontend/modules/builder/store/elementContent.js` line ~230
- dataSource store getter `getPageDataSourceById`: `web-frontend/modules/builder/store/dataSource.js` line ~401
- `LocalBaserowAggregateRowsServiceType.getResult`: `web-frontend/modules/integrations/localBaserow/serviceTypes.js` line ~353
- SummaryWidget (Dashboard parallel): `web-frontend/modules/dashboard/components/widget/SummaryWidget.vue`
- en.json i18n: `web-frontend/modules/builder/locales/en.json` lines ~148, ~174
- ChartElement unit test: `web-frontend/test/unit/builder/components/elements/components/ChartElement.spec.js`
- ChartElement E2E test: `e2e-tests/tests/builder/elements/chartElement.spec.ts`
- add-update-builder-element-type skill: `.agents/skills/add-update-builder-element-type/SKILL.md`
- Story 5.1 (Chart Element, predecessor): `_bmad-output/implementation-artifacts/5-1-chart-element.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Template logic: `misconfigured` computed returns `true` when `data_source_id = null`; template uses `elementContent._error` check (not `misconfigured`) for error state, so no-data-source renders `empty` (not `error`). Confirmed by unit test.

### Completion Notes List

- All 9 tasks complete. MetricElement is a clean-room greenfield implementation mirroring ChartElement patterns but simpler: no `chart_type` field, no ECharts rendering, uses `local_baserow_aggregate_rows` service type (scalar result) instead of grouped_aggregate.
- Backend: `MetricElement` model + `MetricElementType` + migration 0071 + registration in apps.py. Ruff lint clean.
- Frontend: `MetricElement.vue`, `MetricElementForm.vue`, `MetricElementType` in elementTypes.js + plugin.js registration, i18n strings in en.json, placeholder SVG icon (designer asset needed).
- Unit tests: 5/5 pass using `mountSuspended` pattern from ChartElement.spec.js.
- E2E tests: created following chartElement.spec.ts structure (requires running dev stack).
- Permission guard: no bypass introduced — standard builder dispatch pipeline used (inherits `PERMISSION_MANAGERS` enforcement from `LocalBaserowAggregateRowsServiceType`).

### File List

- `backend/src/baserow/contrib/builder/elements/models.py`
- `backend/src/baserow/contrib/builder/elements/element_types.py`
- `backend/src/baserow/contrib/builder/apps.py`
- `backend/src/baserow/contrib/builder/migrations/0071_metricelement.py`
- `web-frontend/modules/builder/components/elements/components/MetricElement.vue`
- `web-frontend/modules/builder/components/elements/components/forms/general/MetricElementForm.vue`
- `web-frontend/modules/builder/elementTypes.js`
- `web-frontend/modules/builder/plugin.js`
- `web-frontend/modules/builder/locales/en.json`
- `web-frontend/modules/builder/assets/icons/element-metric.svg`
- `web-frontend/test/unit/builder/components/elements/components/MetricElement.spec.js`
- `e2e-tests/tests/builder/elements/metricElement.spec.ts`
- `_bmad-output/implementation-artifacts/5-2-metric-element.md`
