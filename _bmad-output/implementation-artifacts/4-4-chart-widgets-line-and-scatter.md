---
status: ready-for-dev
baseline_commit: eca28e86d8d62dc8d4ba24f62f89ecae4fb94a46
---
# Story 4.4: Chart Widgets — line and scatter

Status: ready-for-dev

## Story

As a user,
I want line and scatter chart Widgets on a Dashboard,
so that I can visualize trends and distributions that automatically reflect the latest data.

## Acceptance Criteria

1. **Given** a Dashboard and a grouped-aggregate Data Source, **When** a user adds a line Widget, **Then** it renders a line chart from the Data Source (category → x-axis, value → y-axis, optional series → multi-line).

2. **Given** a Dashboard and a grouped-aggregate Data Source, **When** a user adds a scatter Widget, **Then** it renders a scatter chart from the Data Source (category → x-axis label, value → y-value, dots per data point).

3. **Given** a Dashboard with a line or scatter Widget whose Data Source is bound to a Table, **When** rows in that Table are created, updated, or deleted via any path, **Then** the Widget's Data Source re-dispatches (debounced, no polling) and the chart updates without a full page reload — honoring AR-15 / NFR-1.

4. **Given** a Dashboard with up to 12 chart/metric Widgets over 100k-row Tables, **When** it loads, **Then** line and scatter charts lazy-load so an off-screen Widget does not block first paint — honoring NFR-2 (same guarantee as bar/pie from Story 4.3).

5. **Given** a Dashboard with the existing bar/pie/doughnut chart Widgets and metric Widgets from Stories 4.1–4.3, **When** line and scatter Widgets are added alongside them, **Then** all pre-existing Widgets continue to render and update correctly (no regression).

## Tasks / Subtasks

- [ ] Task 1 — Extend `ChartWidget` model and add migration (AC: 1, 2)
  - [ ] 1.1 Add `CHART_TYPE_LINE = "line"` and `CHART_TYPE_SCATTER = "scatter"` to `ChartWidget.CHART_TYPE_CHOICES` in `models.py`
  - [ ] 1.2 Create migration `0005_chartwidget_line_scatter.py` that alters the `chart_type` field's choices (data migration is not needed — choice additions are backward-compatible)
  - [ ] 1.3 Confirm `ChartWidgetType.request_serializer_field_names` already includes `chart_type` (no change needed if so); otherwise add it

- [ ] Task 2 — Add line and scatter ECharts rendering in `ChartWidget.vue` (AC: 1, 2, 4)
  - [ ] 2.1 In `chartOption` computed property, add a `line` branch: same x-axis/series grouping logic as `bar` but with `type: 'line'` in each ECharts series entry; include `smooth: false` default
  - [ ] 2.2 Add a `scatter` branch: `xAxis: { type: 'category', data: categories }`, `yAxis: { type: 'value' }`, `series: [{ type: 'scatter', data: result.map(r => r.value) }]`; series grouping: if `series` dimension present, produce one scatter series per series-value (same grouping pattern as bar)
  - [ ] 2.3 Do NOT import ECharts directly in `ChartWidget.vue` — all rendering goes through `<BaseChart>` from Story 4.1; `BaseChart.vue` already lazy-loads all ECharts modules inside `mounted()` (SM-C3 bundle discipline)

    ```js
    // chartOption computed — line branch (inside existing if/else chain)
    } else if (chartType === 'line' || chartType === 'scatter') {
      const categories = [...new Set(result.map((r) => r.category))]
      const seriesValues = [...new Set(result.map((r) => r.series).filter(Boolean))]
      const buildSeries = (type) =>
        seriesValues.length > 0
          ? seriesValues.map((s) => ({
              type,
              name: s,
              data: categories.map(
                (c) => result.find((r) => r.category === c && r.series === s)?.value ?? null
              ),
            }))
          : [{ type, data: result.map((r) => r.value) }]
      return {
        xAxis: { type: 'category', data: categories },
        yAxis: { type: 'value' },
        series: buildSeries(chartType),
        tooltip: { trigger: 'axis' },
        legend: seriesValues.length > 0 ? {} : undefined,
      }
    }
    ```

- [ ] Task 3 — Add frontend variations, SVG assets, and i18n (AC: 1, 2)
  - [ ] 3.1 Import `LineChartWidgetSvg` and `ScatterChartWidgetSvg` at top of `widgetTypes.js`
  - [ ] 3.2 Append two entries to `ChartWidgetType.get variations()`:
    ```js
    {
      name: i18n.t('lineChartWidget.name'),
      createWidgetImage: LineChartWidgetSvg,
      params: { chart_type: 'line' },
    },
    {
      name: i18n.t('scatterChartWidget.name'),
      createWidgetImage: ScatterChartWidgetSvg,
      params: { chart_type: 'scatter' },
    },
    ```
  - [ ] 3.3 Create `web-frontend/modules/dashboard/assets/images/widgets/line_chart_widget.svg` (simple polyline icon, same viewBox style as existing SVGs)
  - [ ] 3.4 Create `web-frontend/modules/dashboard/assets/images/widgets/scatter_chart_widget.svg` (scatter dots icon)
  - [ ] 3.5 Add keys to `en.json`:
    ```json
    "lineChartWidget": { "name": "Line" },
    "scatterChartWidget": { "name": "Scatter" }
    ```
  - [ ] 3.6 Add placeholder keys to `de.json`, `es.json`, `fr.json`, `it.json` (copy English values as temporary placeholders)

- [ ] Task 4 — WebSocket row-event invalidation (AC: 3)
  - [ ] 4.1 Add new store action `invalidateDataSourcesForTable` in `dashboardApplication.js`:
    ```js
    import debounce from 'lodash/debounce'
    // module-level map: tableId → debounced dispatch fn
    const tableInvalidationDebouncers = {}

    // action:
    invalidateDataSourcesForTable({ dispatch, state }, tableId) {
      if (!tableInvalidationDebouncers[tableId]) {
        tableInvalidationDebouncers[tableId] = debounce(async (id) => {
          const affected = state.dataSources.filter((ds) => ds.table_id === id)
          await Promise.all(affected.map((ds) => dispatch('dispatchDataSource', ds.id)))
          delete tableInvalidationDebouncers[id]
        }, 500)
      }
      tableInvalidationDebouncers[tableId](tableId)
    },
    ```
  - [ ] 4.2 Register `rows_created`, `rows_updated`, `rows_deleted` realtime events in `realtime.js`; each calls `store.dispatch('dashboardApplication/invalidateDataSourcesForTable', data.table_id)` when `data.table_id` matches any data source bound to the current dashboard (guard: `store.getters['dashboardApplication/getDashboardId']` must be set, meaning a dashboard is active):
    ```js
    ['rows_created', 'rows_updated', 'rows_deleted'].forEach((event) => {
      realtime.registerEvent(event, ({ store }, data) => {
        const dashboardId = store.getters['dashboardApplication/getDashboardId']
        if (!dashboardId) return
        const hasBound = store.state.dashboardApplication.dataSources.some(
          (ds) => ds.table_id === data.table_id
        )
        if (hasBound) {
          store.dispatch(
            'dashboardApplication/invalidateDataSourcesForTable',
            data.table_id
          )
        }
      })
    })
    ```
  - [ ] 4.3 Add getter `getDashboardId` to `dashboardApplication.js` store if not already present (check existing getters first):
    ```js
    getDashboardId(state) {
      return state.dashboardId
    },
    ```
  - [ ] 4.4 Confirm `state.dashboardId` is populated in `fetchInitial` (it should be via `commit('SET_DASHBOARD', ...)` or similar); trace through `pages/dashboard.vue` → store to confirm the ID is set before realtime subscription

- [ ] Task 5 — Backend and frontend tests (AC: 1, 2, 3, 5)
  - [ ] 5.1 In `test_chart_widget_type.py`, add `test_create_line_chart_widget` and `test_create_scatter_chart_widget` mirroring the existing bar/pie tests; verify `chart_type` saved correctly and data source type is `local_baserow_grouped_aggregate_rows`
  - [ ] 5.2 Add `test_line_scatter_chart_type_choices`: assert `ChartWidget.CHART_TYPE_CHOICES` contains `('line', 'Line')` and `('scatter', 'Scatter')`
  - [ ] 5.3 Add frontend unit test `web-frontend/test/unit/dashboard/realtime.spec.js` (or append to existing if file exists):
    - `rows_created` event with matching `table_id` → `invalidateDataSourcesForTable` dispatched
    - `rows_created` event with non-matching `table_id` → no dispatch
    - Rapid successive `rows_updated` events → debounced to single `dispatchDataSource` call
  - [ ] 5.4 Regression: run full `backend/tests/baserow/contrib/dashboard/` suite — all 46+ existing widget tests must still pass

## Dev Notes

### Architecture constraints

- **Bundle discipline (SM-C3):** `ChartWidget.vue` MUST NOT import any `echarts/*` module directly. All ECharts usage flows through `<BaseChart>` (`web-frontend/modules/dashboard/components/chart/BaseChart.vue`), which lazy-loads ECharts inside `mounted()`. Adding a direct import here breaks the lazy-load guarantee.
- **Single `ChartWidgetType` registry entry:** `ChartWidgetType.getType()` returns `'chart'` — one entry in the registry. Line and scatter are additional `variations`, NOT new classes. Do not create `LineChartWidgetType` or `ScatterChartWidgetType`.
- **`chart_type` in `request_serializer_field_names`:** Already set in Story 4.3's `ChartWidgetType`. The migration in Task 1.2 is a choices-only alteration; no column type change. Django `makemigrations` will produce an `AlterField` with the updated `choices` kwarg.
- **Debounce is module-level, not state-level:** `tableInvalidationDebouncers` map lives outside Vuex state (module scope in `dashboardApplication.js`) — same pattern as `debouncedWidgetUpdate` already in that file. This avoids Vuex reactivity overhead on the debounce handle.
- **Realtime subscription scope:** The dashboard page subscribes to `'dashboard'` channel for widget CRUD events. The `rows_created`/`rows_updated`/`rows_deleted` events come from the database table's realtime channel, which is always active for authenticated users. No new subscription call needed — just register the event handlers in `realtime.js`.
- **No new data source for line/scatter:** Line and scatter reuse `LocalBaserowGroupedAggregateRowsServiceType` (type = `"local_baserow_grouped_aggregate_rows"`) — same as bar/pie/doughnut. No changes to `service_types.py`.
- **Scatter x-axis:** ECharts `scatter` with `xAxis.type = 'category'` is valid and renders category labels on x with dots at the y-value. The data array format is identical to line: `[value, value, ...]` aligned to `xAxis.data` categories. This matches the `{category, value}` shape from `GroupedAggregateRowsServiceType.dispatch_transform()`.
- **Premium guard:** `premium/apps.py` already unregisters and re-registers `ChartWidgetType` to swap in the premium subclass. Since `CHART_TYPE_LINE` and `CHART_TYPE_SCATTER` are added to the base model, the premium subclass inherits them automatically — no changes needed in `premium/apps.py`.

### Data flow for WebSocket invalidation

```
Row event (rows_created / rows_updated / rows_deleted) fires on database realtime channel
  → data.table_id = N
  → realtime.js handler checks: is there a DashboardDataSource in state with table_id = N?
  → If yes: dispatch dashboardApplication/invalidateDataSourcesForTable(N)
  → Store action: debounce (500ms) → call dispatchDataSource for each matching data source
  → dispatchDataSource: POST /dashboard/data-sources/{id}/dispatch/ → updates state.data[id]
  → ChartWidget.vue: dataForDataSource computed re-evaluates → chartOption recomputes → BaseChart re-renders
```

No polling. No extra WebSocket channels. Debounce window: 500ms (absorbs burst row imports).

### Project Structure Notes

- `ChartWidget` model → `backend/src/baserow/contrib/dashboard/widgets/models.py` (modify — add `CHART_TYPE_LINE`, `CHART_TYPE_SCATTER` to choices)
- Migration → `backend/src/baserow/contrib/dashboard/migrations/0005_chartwidget_line_scatter.py` (create)
- `ChartWidget.vue` → `web-frontend/modules/dashboard/components/widget/ChartWidget.vue` (modify — add line/scatter branches to `chartOption`)
- `widgetTypes.js` → `web-frontend/modules/dashboard/widgetTypes.js` (modify — add 2 variations + SVG imports)
- SVG assets → `web-frontend/modules/dashboard/assets/images/widgets/line_chart_widget.svg` (create) and `scatter_chart_widget.svg` (create)
- i18n → `web-frontend/modules/dashboard/locales/en.json` (modify — add `lineChartWidget.name`, `scatterChartWidget.name`)
- i18n placeholder → `de.json`, `es.json`, `fr.json`, `it.json` (modify)
- Store → `web-frontend/modules/dashboard/store/dashboardApplication.js` (modify — add `invalidateDataSourcesForTable` action + `getDashboardId` getter if missing)
- Realtime handlers → `web-frontend/modules/dashboard/realtime.js` (modify — add `rows_created`, `rows_updated`, `rows_deleted` handlers)
- Tests → `backend/tests/baserow/contrib/dashboard/widgets/test_chart_widget_type.py` (modify — add line/scatter cases)
- Frontend tests → `web-frontend/test/unit/dashboard/realtime.spec.js` (create or modify — add row-event invalidation cases)

### References

- Story 4.3 ChartWidget.vue `chartOption` pattern: `web-frontend/modules/dashboard/components/widget/ChartWidget.vue`
- Story 4.3 `ChartWidgetType` variants: `web-frontend/modules/dashboard/widgetTypes.js#ChartWidgetType`
- ChartWidget model + choices: `backend/src/baserow/contrib/dashboard/widgets/models.py#ChartWidget`
- BaseChart.vue lazy-load contract: `web-frontend/modules/dashboard/components/chart/BaseChart.vue` (DO NOT bypass)
- Existing debounce pattern: `web-frontend/modules/dashboard/store/dashboardApplication.js` (L5–L122)
- Existing realtime event registration: `web-frontend/modules/dashboard/realtime.js`
- Dashboard page realtime subscribe/unsubscribe: `web-frontend/modules/dashboard/pages/dashboard.vue` (L94, L101)
- rows_created/rows_updated/rows_deleted event shape (`data.table_id`): `web-frontend/modules/database/realtime.js` (L173, L191, L230)
- Service type (data source): `backend/src/baserow/contrib/integrations/local_baserow/service_types.py#LocalBaserowGroupedAggregateRowsServiceType` (L1563)
- Architecture D1 (ECharts, lazy-load): `_bmad-output/planning-artifacts/architecture.md#Library Decisions`
- Architecture D11 (WebSocket row-event invalidation, no polling): `_bmad-output/planning-artifacts/architecture.md#API & Communication Patterns`
- Story 4.3 dev notes (ChartWidgetType patterns, premium guard, data source type): `_bmad-output/implementation-artifacts/4-3-chart-widgets-bar-and-pie-doughnut.md#Dev Notes`
- Existing widget tests: `backend/tests/baserow/contrib/dashboard/widgets/test_chart_widget_type.py`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List

- `backend/src/baserow/contrib/dashboard/widgets/models.py` (modify — add `CHART_TYPE_LINE`, `CHART_TYPE_SCATTER` to `ChartWidget.CHART_TYPE_CHOICES`)
- `backend/src/baserow/contrib/dashboard/migrations/0005_chartwidget_line_scatter.py` (create — `AlterField` on `chart_type` choices)
- `web-frontend/modules/dashboard/components/widget/ChartWidget.vue` (modify — add `line`/`scatter` branches to `chartOption` computed)
- `web-frontend/modules/dashboard/widgetTypes.js` (modify — add `line`/`scatter` variations + SVG imports)
- `web-frontend/modules/dashboard/assets/images/widgets/line_chart_widget.svg` (create)
- `web-frontend/modules/dashboard/assets/images/widgets/scatter_chart_widget.svg` (create)
- `web-frontend/modules/dashboard/locales/en.json` (modify — add `lineChartWidget.name`, `scatterChartWidget.name`)
- `web-frontend/modules/dashboard/locales/de.json` (modify — placeholder keys)
- `web-frontend/modules/dashboard/locales/es.json` (modify — placeholder keys)
- `web-frontend/modules/dashboard/locales/fr.json` (modify — placeholder keys)
- `web-frontend/modules/dashboard/locales/it.json` (modify — placeholder keys)
- `web-frontend/modules/dashboard/store/dashboardApplication.js` (modify — add `invalidateDataSourcesForTable` action + `getDashboardId` getter if missing)
- `web-frontend/modules/dashboard/realtime.js` (modify — register `rows_created`, `rows_updated`, `rows_deleted` handlers)
- `backend/tests/baserow/contrib/dashboard/widgets/test_chart_widget_type.py` (modify — add `test_create_line_chart_widget`, `test_create_scatter_chart_widget`, `test_line_scatter_chart_type_choices`)
- `web-frontend/test/unit/dashboard/realtime.spec.js` (create or modify — row-event invalidation unit tests)
