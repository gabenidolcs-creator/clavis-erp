# Test Automation Summary — Story 4.2: Grouped-aggregate Data Source

## Generated Tests

### Backend Unit Tests (pytest)

File: `backend/tests/baserow/contrib/integrations/local_baserow/test_grouped_aggregate_rows_service_type.py`

- [x] `test_dispatch_count_aggregation` — count rows per group, results shape `[{category, value}]`
- [x] `test_dispatch_sum_aggregation` — sum NumberField per group
- [x] `test_dispatch_avg_min_max` — avg/min/max aggregation types
- [x] `test_dispatch_with_series_field` — results include `{category, series, value}` shape
- [x] `test_dispatch_honors_field_hide_on_group_by_field` — group_by hidden → `ServiceImproperlyConfiguredDispatchException`
- [x] `test_dispatch_honors_field_hide_on_value_field` — value_field hidden → exception
- [x] `test_dispatch_count_does_not_require_value_field` — count with `value_field=None` succeeds
- [x] `test_resolve_formulas_raises_when_group_by_missing` — no group_by_field → exception
- [x] `test_resolve_formulas_raises_when_value_field_missing_for_sum` — sum without value_field → exception
- [x] `test_generate_schema_without_series` — schema has `{category, value}` only
- [x] `test_generate_schema_with_series` — schema has `{category, series, value}`
- [x] **[GAP FILLED]** `test_dispatch_honors_field_hide_on_series_field` — series_field hidden → exception (AC #2 completeness)
- [x] **[GAP FILLED]** `test_dispatch_null_category_becomes_empty_string` — NULL group-by value → `""` in output
- [x] **[GAP FILLED]** `test_prepare_values_raises_when_non_count_has_no_value_field` — `prepare_values()` DRFValidationError path

**Total backend tests: 14/14 pass**

Run command:
```bash
DATABASE_URL="postgresql://..." PYTHONPATH="tests:../premium/backend/tests:../enterprise/backend/tests:src:../premium/backend/src:../enterprise/backend/src" uv run --active pytest -c pytest.ini tests/baserow/contrib/integrations/local_baserow/test_grouped_aggregate_rows_service_type.py -v
```

### E2E Tests (Playwright)

File: `e2e-tests/tests/database/grouped_aggregate_data_source.spec.ts`

> **Note:** Requires Docker e2e stack (no local Nuxt server). Run via `e2e-tests/run-e2e-tests-locally.sh`.

- [x] `Service type is registered — data source can be created via API` — creates dashboard + integration + data source, verifies type/fields
- [x] `Dispatch returns (category, value) tuples for count aggregation` — seeds A×2/B×1, verifies dispatch result shape and values
- [x] `Dispatch with series_field returns (category, series, value) tuples` — 3 rows with 2 dims, verifies all 3 keys present
- [x] `NULL category value is returned as empty string` — NULL row → `""` in results, not `"null"` or crash

**E2E note:** Chart widget rendering is deferred to Story 4.3. These tests cover API-level registration and dispatch only.

## Bug Fixed

**`premium/backend/src/baserow_premium/apps.py`** — premium's `LocalBaserowGroupedAggregateRowsUserServiceType` did not unregister the core OSS service type before registering the premium version, causing `InstanceTypeAlreadyRegistered` in non-OSS-only test runs.

Fix: added `service_type_registry.unregister(LocalBaserowGroupedAggregateRowsUserServiceType.type)` before the `register()` call, following the existing pattern at line 25 (`PremiumBuilderApplicationType`).

## Coverage

| Layer | AC Covered |
|---|---|
| Backend dispatch (count/sum/avg/min/max) | AC #1 |
| Backend series field dispatch | AC #1 |
| Backend field-hide permission (group_by, value, series) | AC #2 |
| Backend schema generation | AC #1 |
| Backend prepare_values validation | AC #1 |
| Null category → `""` coercion | AC #1 (data quality) |
| E2E API: service type registered | AC #1 |
| E2E API: dispatch shape | AC #1 |
| E2E API: series shape | AC #1 |
| E2E API: null category string | AC #1 (data quality) |

## Files Changed

**New:**
- `e2e-tests/tests/database/grouped_aggregate_data_source.spec.ts`

**Modified:**
- `backend/tests/baserow/contrib/integrations/local_baserow/test_grouped_aggregate_rows_service_type.py` — 3 gap-filling tests added (14 total, was 11)
- `premium/backend/src/baserow_premium/apps.py` — unregister before register to fix `InstanceTypeAlreadyRegistered` in test runs
