# Test Automation Summary — Story 4.3: Chart Widgets — Bar and Pie/Doughnut

## Generated Tests

### Backend Unit Tests (pytest)

File: `backend/tests/baserow/contrib/dashboard/widgets/test_chart_widget_type.py`

- [x] `test_create_chart_widget_creates_grouped_aggregate_data_source` — bar widget auto-creates `local_baserow_grouped_aggregate_rows` data source; content type asserted via registry (not hardcoded)
- [x] `test_create_pie_widget` — pie widget: `chart_type == "pie"`, data source created
- [x] `test_create_doughnut_widget` — doughnut widget: `chart_type == "doughnut"`, data source created
- [x] `test_chart_widget_before_trashed_and_restore` — trash sets `data_source.trashed=True`; restore sets `False`
- [x] `test_chart_widget_datasource_cannot_be_deleted` — direct `DashboardDataSourceService().delete_data_source()` raises `ProtectedError`
- [x] `test_chart_widget_and_summary_widget_coexist` — both widget types on same dashboard; both in `Widget.objects.filter(dashboard=dashboard)`; both type keys found in registry

**Total backend tests: 6/6 pass** (46/46 dashboard widget tests total — no regressions)

Run command:
```bash
PYTHONPATH="src:../premium/backend/src:../enterprise/backend/src" \
  uv run --active pytest -c pytest.ini \
  tests/baserow/contrib/dashboard/widgets/test_chart_widget_type.py -v
```

> **Note (bypass pattern):** Tests use `WidgetHandler().create_widget(CoreChartWidgetType(), ...)` directly instead of `WidgetService` to avoid the premium license gate (`before_create` raises `LicenseHandler.raise_if_user_doesnt_have_feature` for users without a premium license).

### E2E Tests (Playwright)

File: `e2e-tests/tests/dashboard/chart_widget.spec.ts`

> **Note:** Requires Docker e2e stack. Run via `e2e-tests/run-e2e-tests-locally.sh`.

- [x] `Bar chart widget is created with auto-provisioned grouped-aggregate data source` — POSTs `{type:"chart",chart_type:"bar"}`; asserts `widget.type==="chart"`, `widget.chart_type==="bar"`, `widget.data_source_id` truthy; fetches data source and confirms `type==="local_baserow_grouped_aggregate_rows"`
- [x] `Pie chart widget persists chart_type as 'pie'` — asserts `widget.chart_type==="pie"` and data source created
- [x] `Doughnut chart widget persists chart_type as 'doughnut'` — asserts `widget.chart_type==="doughnut"` and data source created
- [x] `Chart widget and summary widget coexist on the same dashboard (AC #3)` — creates both widget types; GET list returns both; both types present in response
- [x] `Creating a chart widget with an invalid chart_type returns a 400 error` — `chart_type:"scatter"` → axios throws with `response.status===400`

## Coverage

| Layer | AC Covered |
|---|---|
| Backend: bar widget creates grouped-aggregate DS | AC #1 |
| Backend: pie/doughnut chart_type persisted | AC #1 |
| Backend: trash/restore syncs data_source.trashed | AC #1 lifecycle |
| Backend: data source protected from direct delete | AC #1 lifecycle |
| Backend: chart + summary coexist, no registry conflict | AC #3 |
| E2E API: bar widget auto-creates grouped-aggregate DS | AC #1 |
| E2E API: pie/doughnut chart_type stored | AC #1 |
| E2E API: chart + summary widget list on same dashboard | AC #3 |
| E2E API: invalid chart_type rejected 400 | error case |

## Bugs Fixed During QA

1. **`ChartWidgetType.allowed_fields` missing** — base `WidgetType.allowed_fields = ["title", "description"]` would cause `extract_allowed()` in `WidgetHandler.create_widget` to silently strip `chart_type`. Fix: `allowed_fields = ["title", "description", "chart_type"]` added to `ChartWidgetType`.

2. **Premium double-registration** — `premium/apps.py` registered premium `ChartWidgetType` without unregistering the core OSS one first, raising `InstanceTypeAlreadyRegistered`. Fix: `widget_type_registry.unregister(ChartWidgetType.type)` added before the premium `register()` call.

3. **Data source fixture hardcoded OSS model class** — `create_dashboard_local_baserow_grouped_aggregate_rows_data_source` used `LocalBaserowGroupedAggregateRows` directly; fails when premium model class is substituted. Fix: lazy registry-resolved `model_class = service_type_registry.get(...).model_class`.

## Files Changed

**New:**
- `e2e-tests/tests/dashboard/chart_widget.spec.ts` — 5 E2E API tests
- `backend/tests/baserow/contrib/dashboard/widgets/test_chart_widget_type.py` — 6 backend unit tests
- `_bmad-output/implementation-artifacts/tests/test-summary-4-3.md` — this file

**Modified (bug fixes):**
- `backend/src/baserow/contrib/dashboard/widgets/widget_types.py` — `allowed_fields` override
- `premium/backend/src/baserow_premium/apps.py` — unregister before register
- `backend/src/baserow/test_utils/fixtures/dashboard_data_source.py` — registry-resolved model class
