---
status: done
baseline_commit: 35afcf8b4
---
# Story 4.5: Metric Widget Non-Regression

Status: done

## Story

As a user,
I want the existing summary metric Widget to keep working alongside new chart Widgets,
so that adding charts does not break existing dashboards.

## Acceptance Criteria

1. **Given** a Dashboard with the existing free summary metric Widget, **When** chart Widgets are added, **Then** the metric Widget continues to compute and render correctly (non-regression check only, no new build).

2. **Given** the dashboard widget test suite, **When** it runs, **Then** an automated test asserts metric+chart coexistence — both widget types appear in the same dashboard's Widget queryset and both type registrations resolve.

3. **Given** a SummaryWidget rendered in the frontend with a configured data source, **When** the store has data for that data source, **Then** the widget displays the formatted aggregation result returned by `serviceType.getResult()`.

4. **Given** a SummaryWidget rendered alongside ChartWidget data in dashboardApplication store state, **When** the component reads from the shared store, **Then** it correctly resolves only its own data source without conflict.

## Tasks / Subtasks

- [x] Task 1 — Verify backend coexistence test exists and passes (AC: 1, 2)
  - [x] 1.1 Confirm `test_chart_widget_and_summary_widget_coexist` exists in `backend/tests/baserow/contrib/dashboard/widgets/test_chart_widget_type.py` (it was added during Story 4.4 implementation — do NOT re-add it; just verify its presence)
  - [x] 1.2 Run full dashboard widget suite: `just b test backend/tests/baserow/contrib/dashboard/widgets/` — all tests must pass (the suite currently covers ~50+ tests including the coexistence test)
  - [x] 1.3 If the coexistence test is somehow missing (unexpected), add it following the pattern in `test_chart_widget_type.py` — but check first

- [x] Task 2 — Add frontend SummaryWidget component unit tests (AC: 3, 4)
  - [x] 2.1 Create `web-frontend/test/unit/dashboard/components/SummaryWidget.spec.js` with the following test cases:
    - `renders result from data source` — mount SummaryWidget with a store that has a data source and data entry; assert the rendered `.dashboard-summary-widget__summary` text equals the expected formatted value (use a mock `serviceType.getResult()` returning a number string)
    - `renders 0 when data source has no data` — store has data source but `data[id]` is empty/undefined; assert result is `0`
    - `shows misconfigured badge when data has _error` — store data for the data source has `{ _error: 'Something failed' }`; assert `Badge` with color `red` is rendered
    - `coexistence: SummaryWidget reads only its data source from store that also has chart data` — store state has two data sources (one for SummaryWidget, one for a hypothetical ChartWidget); SummaryWidget only reads the one matching `widget.data_source_id`
  - [x] 2.2 Use TestApp pattern from `web-frontend/test/unit/dashboard/components/chart/baseChart.spec.js` — `new TestApp()` in `beforeEach`, `testApp.afterEach()` in `afterEach`
  - [x] 2.3 Mock the Vuex store using `testApp.mount(SummaryWidget, { props, global: { mocks } })` — stub `$store.getters` for `dashboardApplication/getDataSourceById`, `dashboardApplication/getDataForDataSource`, `dashboardApplication/isEditMode`; stub `$registry.get` for the service type
  - [x] 2.4 Do NOT import or mock ECharts — SummaryWidget has no chart dependency

- [x] Task 3 — Run broader non-regression check and finalize (AC: 1, 2, 3, 4)
  - [x] 3.1 Run full dashboard backend suite: `just b test backend/tests/baserow/contrib/dashboard/` — all tests pass
  - [x] 3.2 Run frontend SummaryWidget tests: `just f yarn test:core web-frontend/test/unit/dashboard/components/SummaryWidget.spec.js`
  - [x] 3.3 Run full frontend dashboard test suite: `just f yarn test:core web-frontend/test/unit/dashboard/` — all existing tests still pass (no regressions in baseChart.spec.js, realtime.spec.js)

## Dev Notes

### Critical: This is a non-regression story — no new implementation

Story 4.5 is marked `[X]` (NON-GOAL — already free) in the epics. The SummaryWidget exists and works. **Do not**:
- Change `SummaryWidget.vue`, `SummaryWidgetSettings.vue`, or `SummaryWidgetType`
- Add backend models or migrations
- Modify `widgetTypes.js` (other than reading it for test setup context)
- Touch `ChartWidget.vue` or any chart implementation

The **only deliverables** are:
1. Confirm the backend coexistence test passes
2. Add a frontend SummaryWidget component spec file

### What already exists from Story 4.4

The backend coexistence test was added as part of Story 4.4's Task 5 (`test_chart_widget_and_summary_widget_coexist` in `test_chart_widget_type.py`, lines ~96–119). It:
- Creates a SummaryWidget via `WidgetService().create_widget()` (no premium license)
- Creates a ChartWidget via `WidgetHandler().create_widget(CoreChartWidgetType(), ...)`
- Asserts both widget IDs appear in `Widget.objects.filter(dashboard=dashboard)`
- Asserts `widget_type_registry.get("summary")` and `widget_type_registry.get("chart")` both resolve

This satisfies AC1 and AC2 at the backend level. Story 4.5's dev work is primarily the **frontend** SummaryWidget component test (Task 2).

### SummaryWidget data flow

```
SummaryWidget.vue
  ↓ props: widget (has data_source_id), dashboard, storePrefix, loading
  ↓ computed: dataSource = store.getters['dashboardApplication/getDataSourceById'](widget.data_source_id)
  ↓ computed: dataForDataSource = store.getters['dashboardApplication/getDataForDataSource'](dataSource.id)
  ↓ computed: result = serviceType.getResult(dataSource, dataForDataSource)
      where serviceType = $registry.get('service', dataSource.type)
              ≡ LocalBaserowAggregateRowsServiceType (type: 'local_baserow_aggregate_rows')
  ↓ renders: <div class="widget__content dashboard-summary-widget__summary">{{ result }}</div>
```

Key: SummaryWidget uses **`local_baserow_aggregate_rows`** service type (single-value aggregate), while ChartWidget uses **`local_baserow_grouped_aggregate_rows`** (multi-row grouped aggregate). The two service types are independent — they share no state.

### Frontend test mock pattern

Use shallow store stubs rather than full Vuex. Pattern from `baseChart.spec.js`:

```js
import { TestApp } from '@baserow/test/helpers/testApp'
import SummaryWidget from '@baserow/modules/dashboard/components/widget/SummaryWidget'

let testApp
beforeEach(() => { testApp = new TestApp() })
afterEach(async () => { await testApp.afterEach() })

it('renders result from data source', async () => {
  const dataSourceId = 99
  const widget = { id: 1, data_source_id: dataSourceId, title: 'My metric', description: '' }
  const dashboard = { id: 10 }
  const storeData = { result: 42, _error: undefined }

  const wrapper = await testApp.mount(SummaryWidget, {
    props: { widget, dashboard, loading: false },
    mocks: {
      $store: {
        getters: {
          'dashboardApplication/getDataSourceById': () => (id) =>
            id === dataSourceId ? { id: dataSourceId, type: 'local_baserow_aggregate_rows' } : null,
          'dashboardApplication/getDataForDataSource': () => (id) =>
            id === dataSourceId ? storeData : null,
          'dashboardApplication/isEditMode': false,
        },
      },
      $registry: {
        get: (namespace, type) => ({
          getResult: (_svc, data) => String(data.result),
        }),
      },
    },
  })

  expect(wrapper.find('.dashboard-summary-widget__summary').text()).toBe('42')
})
```

**Note**: `$store.getters` in Vuex are curried when defined as functions-returning-functions — `getDataSourceById(state)(id)` becomes `getDataSourceById(id)` in the getter. Mock accordingly.

### Backend fixture availability

- `data_fixture.create_summary_widget(dashboard=dashboard)` — creates SummaryWidget with auto-created data source (fixture defined in test utils)
- `data_fixture.create_chart_widget(dashboard=dashboard)` — creates ChartWidget with auto-created grouped-aggregate data source
- `data_fixture.create_dashboard_application(user=user)` — creates a Dashboard

### Project Structure Notes

- **Read-only** (existing, no changes): `web-frontend/modules/dashboard/components/widget/SummaryWidget.vue`
- **Read-only** (existing, no changes): `web-frontend/modules/dashboard/widgetTypes.js`
- **Read-only** (verify passes): `backend/tests/baserow/contrib/dashboard/widgets/test_chart_widget_type.py` (lines ~96–119 have coexistence test)
- **Create**: `web-frontend/test/unit/dashboard/components/SummaryWidget.spec.js`

### References

- SummaryWidget.vue component: `web-frontend/modules/dashboard/components/widget/SummaryWidget.vue`
- SummaryWidgetType (frontend): `web-frontend/modules/dashboard/widgetTypes.js#SummaryWidgetType`
- SummaryWidgetType (backend): `backend/src/baserow/contrib/dashboard/widgets/widget_types.py#SummaryWidgetType`
- SummaryWidget model: `backend/src/baserow/contrib/dashboard/widgets/models.py#SummaryWidget`
- Backend coexistence test: `backend/tests/baserow/contrib/dashboard/widgets/test_chart_widget_type.py#test_chart_widget_and_summary_widget_coexist`
- LocalBaserowAggregateRowsServiceType.getResult(): `web-frontend/modules/integrations/localBaserow/serviceTypes.js#LocalBaserowAggregateRowsServiceType` (L353)
- Frontend test pattern: `web-frontend/test/unit/dashboard/components/chart/baseChart.spec.js`
- dashboardApplication store getters: `web-frontend/modules/dashboard/store/dashboardApplication.js` (L270–L290)
- Epics AC: `_bmad-output/planning-artifacts/epics.md#Story 4.5` (lines 770–781)
- Architecture FR-16 note: `_bmad-output/planning-artifacts/architecture.md` ("metric widget already free, non-regression only")

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Task 1: Confirmed `test_chart_widget_and_summary_widget_coexist` exists in `test_chart_widget_type.py`. Ran 49-test widget suite — all passed.
- Task 2: Created `web-frontend/test/unit/dashboard/components/SummaryWidget.spec.js` with 4 tests covering result rendering, 0-on-no-data, misconfigured badge, and coexistence store isolation. All 4 passed.
  - Key discovery: Vue Test Utils v2 requires mocks under `global.mocks`, not top-level `mocks`. Getters are single-curried `(id) => ...` in test mocks.
- Task 3: Full backend dashboard suite 136 passed; full frontend dashboard suite 19 passed. Zero regressions.

### File List

- `web-frontend/test/unit/dashboard/components/SummaryWidget.spec.js` (created)
- `e2e-tests/tests/dashboard/summary_widget.spec.ts` (created)
- `_bmad-output/implementation-artifacts/tests/test-summary-4-5.md` (created)

## QA Agent Record

**QA completed:** Story 4.5 QA E2E workflow

### E2E Tests Generated

- `e2e-tests/tests/dashboard/summary_widget.spec.ts` (created) — 4 API-level Playwright tests

### Frontend Tests Verified

- `web-frontend/test/unit/dashboard/components/SummaryWidget.spec.js` — 4/4 pass ✅

### Test Summary

- `_bmad-output/implementation-artifacts/tests/test-summary-4-5.md` (created)

### Coverage

All 4 ACs covered by test matrix (backend unit + frontend unit + E2E).
No gaps identified. No production code modified during QA pass.

## Senior Developer Review (AI)

**Reviewer:** claude-haiku-4-5 (Adversarial Review v3.0)
**Date:** 2026-06-12T22:54:00Z
**Outcome:** Approve — 0 CRITICAL issues, 1 HIGH issue fixed

### Findings

**HIGH severity (auto-fixed):**
1. File List incomplete — `e2e-tests/tests/dashboard/summary_widget.spec.ts` created but not documented (false claim of completeness)
2. File List incomplete — `_bmad-output/implementation-artifacts/tests/test-summary-4-5.md` created but not documented (false claim of completeness)

**Action taken:** File List updated to include both E2E and test-summary artifacts.

### Acceptance Criteria Validation

✅ AC #1: Non-regression — backend test `test_chart_widget_and_summary_widget_coexist` verified in place, all 49 dashboard widget tests passing
✅ AC #2: Backend coexistence test exists in `test_chart_widget_type.py` and passes
✅ AC #3: SummaryWidget renders result from data source (frontend tests 1–3, E2E test 1)
✅ AC #4: SummaryWidget store isolation confirmed (frontend test 4, E2E tests 2–4)

### Task Audit

✅ Task 1 (Backend coexistence): All [x] marks verified — test exists, suite passes, no re-implementation
✅ Task 2 (Frontend tests): All [x] marks verified — SummaryWidget.spec.js created with 4 tests, all pass, correct Vue Test Utils v2 pattern
✅ Task 3 (Non-regression check): All [x] marks verified — backend 136 tests, frontend 19 tests, zero regressions

### Code Quality Review

- No production code modified (as specified) ✓
- Test code follows project patterns (TestApp, Vitest, Playwright) ✓
- Vue Test Utils v2 `global.mocks` pattern correct ✓
- E2E tests use established baserowTest import pattern ✓
- Backend fixture calls properly structured ✓
- Mock structure correctly represents Vuex single-curry getters ✓

### Security Review

- No dependencies added ✓
- No API surface changes ✓
- No auth/permission changes ✓
- Tests properly isolate data sources (no cross-contamination) ✓

**Status decision:** 0 CRITICAL issues remaining → Story status advanced to **done**
