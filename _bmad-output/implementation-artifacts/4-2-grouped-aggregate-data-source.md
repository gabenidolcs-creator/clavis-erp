---
baseline_commit: f7edb58d5
---

# Story 4.2: Grouped-aggregate Data Source

Status: review

## Story

As a user,
I want a Data Source that groups Rows by a Field and aggregates a value per group,
so that charts have category/value data to render. `[B]`

## Acceptance Criteria

1. **Given** a Table, **when** a user configures a grouped-aggregate Data Source, **then** it returns (category, aggregated-value[, series]) tuples with a configurable group-by Field and aggregation (count/sum/avg/min/max), **and** it is registered in `service_type_registry` (AR-9) and reusable by Dashboard and App Builder.

2. **Given** the requesting principal, **when** the Data Source aggregates, **then** it honors field-hide and row permissions (Story 1.5) — it does not aggregate over Fields the principal cannot see (no inference leak, NFR-4).

## Tasks / Subtasks

- [x] Task 1 — Backend: Add `LocalBaserowGroupedAggregateRows` model (AC: #1 #2)
  - [x] In `backend/src/baserow/contrib/integrations/local_baserow/models.py`, add after `LocalBaserowAggregateRows` class:
    ```python
    class LocalBaserowGroupedAggregateRows(
        LocalBaserowViewService, LocalBaserowFilterableServiceMixin
    ):
        """Grouped-aggregate service — GROUP BY group_by_field, aggregate value_field."""

        AGGREGATION_CHOICES = [
            ("count", "Count"),
            ("sum", "Sum"),
            ("avg", "Average"),
            ("min", "Minimum"),
            ("max", "Maximum"),
        ]

        group_by_field = models.ForeignKey(
            "database.Field",
            help_text="The field to group by (provides categories).",
            null=True,
            on_delete=models.SET_NULL,
            related_name="grouped_aggregate_group_by",
        )
        value_field = models.ForeignKey(
            "database.Field",
            help_text="The field to aggregate. May be null for count aggregation.",
            null=True,
            blank=True,
            on_delete=models.SET_NULL,
            related_name="grouped_aggregate_value",
        )
        series_field = models.ForeignKey(
            "database.Field",
            help_text="Optional secondary group-by for multi-series charts.",
            null=True,
            blank=True,
            on_delete=models.SET_NULL,
            related_name="grouped_aggregate_series",
        )
        aggregation_type = models.CharField(
            default="count",
            max_length=16,
            choices=AGGREGATION_CHOICES,
            help_text="Aggregation function: count/sum/avg/min/max.",
        )
    ```
  - [x] Only `count` aggregation should work when `value_field` is null — validate in service type

- [x] Task 2 — Backend: Create migration (AC: #1)
  - [x] Run `just b manage makemigrations integrations --name localbaserowgroupedaggregaterows`
  - [x] Migration file goes to `backend/src/baserow/contrib/integrations/migrations/` — next number after `0027_*`
  - [x] Verify migration only contains the new `LocalBaserowGroupedAggregateRows` concrete table and its FK columns

- [x] Task 3 — Backend: Implement `LocalBaserowGroupedAggregateRowsServiceType` (AC: #1 #2)
  - [x] In `backend/src/baserow/contrib/integrations/local_baserow/service_types.py`, add new class after `LocalBaserowAggregateRowsUserServiceType`:
    - `type = "local_baserow_grouped_aggregate_rows"`
    - `model_class = LocalBaserowGroupedAggregateRows`
    - `dispatch_types = [DispatchTypes.DATA]`
    - `returns_list = True`
    - `allowed_fields`: `["group_by_field", "value_field", "series_field", "aggregation_type"]` (plus mixin fields + inherited)
    - `serializer_field_names`: `["group_by_field_id", "value_field_id", "series_field_id", "aggregation_type"]` (plus mixin names + inherited)
    - `serializer_field_overrides` for the three FK id fields (IntegerField, required/allow_null as needed)
    - Inherit from `LocalBaserowViewServiceType` + `LocalBaserowTableServiceFilterableMixin`
  - [x] `prepare_values()`:
    - Validate `group_by_field_id` → resolve to Field, ensure it belongs to the same table
    - Validate `value_field_id` → nullable, resolve to Field if provided, ensure same table
    - Validate `series_field_id` → nullable, resolve to Field if provided, ensure same table
    - Validate `aggregation_type` ∈ {count, sum, avg, min, max}
    - If `aggregation_type` ≠ `count` and `value_field` is None → raise `DRFValidationError`
    - Reset field FKs when `table` changes (mirror `LocalBaserowAggregateRowsUserServiceType.prepare_values` pattern)
  - [x] `resolve_service_formulas()`:
    - Check `service.group_by_field` is not None → raise `ServiceImproperlyConfiguredDispatchException("The group_by_field property is missing.")`
    - For non-count aggregations, check `service.value_field` is not None
    - **Permission check (AC #2 — critical):**
      ```python
      from baserow.contrib.database.fields.field_permission_handler import FieldPermissionHandler
      authorized_user = service.integration.authorized_user
      table = service.table
      hidden_ids = FieldPermissionHandler.get_hidden_field_ids(authorized_user, table)
      if service.group_by_field_id in hidden_ids:
          raise ServiceImproperlyConfiguredDispatchException(
              "The group_by_field is hidden from the authorized user (field permission)."
          )
      if service.value_field_id and service.value_field_id in hidden_ids:
          raise ServiceImproperlyConfiguredDispatchException(
              "The value_field is hidden from the authorized user (field permission)."
          )
      if service.series_field_id and service.series_field_id in hidden_ids:
          raise ServiceImproperlyConfiguredDispatchException(
              "The series_field is hidden from the authorized user (field permission)."
          )
      ```
    - Call `super().resolve_service_formulas(service, dispatch_context)` last
  - [x] `dispatch_data()`:
    - Build queryset via `self.build_queryset(service, table, dispatch_context, model=model)` — this already honors row permissions via view filters
    - Apply the GROUP BY aggregation using Django ORM:
      ```python
      from django.db.models import Count, Sum, Avg, Min, Max

      AGG_FUNCS = {"count": Count, "sum": Sum, "avg": Avg, "min": Min, "max": Max}

      group_by_db_col = service.group_by_field.specific.db_column
      agg_func_cls = AGG_FUNCS[service.aggregation_type]

      if service.aggregation_type == "count":
          agg_expr = agg_func_cls("id")
      else:
          value_db_col = service.value_field.specific.db_column
          agg_expr = agg_func_cls(value_db_col)

      qs = queryset.values(group_by_db_col)
      if service.series_field:
          series_db_col = service.series_field.specific.db_column
          qs = qs.values(group_by_db_col, series_db_col).annotate(value=agg_expr)
          results = [
              {"category": str(row[group_by_db_col]), "series": str(row[series_db_col]), "value": row["value"]}
              for row in qs
          ]
      else:
          qs = qs.annotate(value=agg_expr)
          results = [
              {"category": str(row[group_by_db_col]), "value": row["value"]}
              for row in qs
          ]
      return {"results": results, "service": service}
      ```
    - Handle `None` category values gracefully — convert to `""` or `"(empty)"`
  - [x] `dispatch_transform()`: `return DispatchResult(data={"results": data["results"]})`
  - [x] `generate_schema()`: return a JSON Schema with `type: array` items of `{category: string, value: number}` (plus optional `series: string`)

- [x] Task 4 — Backend: Register service type (AC: #1)
  - [x] In `backend/src/baserow/contrib/integrations/apps.py`:
    - Import `LocalBaserowGroupedAggregateRowsServiceType` from `local_baserow.service_types`
    - Add `service_type_registry.register(LocalBaserowGroupedAggregateRowsServiceType())` after the existing `AggregateRows` registration line (~line 39)

- [x] Task 5 — Frontend: Add `LocalBaserowGroupedAggregateRowsServiceType` class (AC: #1)
  - [x] In `web-frontend/modules/integrations/localBaserow/serviceTypes.js`, add after `LocalBaserowAggregateRowsServiceType`:
    ```js
    export class LocalBaserowGroupedAggregateRowsServiceType extends DataSourceLocalBaserowTableServiceType {
      static getType() {
        return 'local_baserow_grouped_aggregate_rows'
      }
      get name() {
        return this.app.$i18n.t('serviceType.localBaserowGroupedAggregateRows')
      }
      get description() {
        return this.app.$i18n.t('serviceType.localBaserowGroupedAggregateRowsDescription')
      }
      get formComponent() {
        return GroupedAggregateRowsDataSourceForm  // imported from dashboard module
      }
      get icon() {
        return 'iconoir-bar-chart-alt'
      }
      getOrder() { return 35 }
    }
    ```
  - [x] Import `GroupedAggregateRowsDataSourceForm` from the dashboard data_source components

- [x] Task 6 — Frontend: Register service type in plugin (AC: #1)
  - [x] In `web-frontend/modules/integrations/plugin.js`:
    - Import `LocalBaserowGroupedAggregateRowsServiceType`
    - Add `$registry.register('service', new LocalBaserowGroupedAggregateRowsServiceType(context))` alongside the existing service type registrations (~line 45)

- [x] Task 7 — Frontend: Create `GroupedAggregateRowsDataSourceForm.vue` (AC: #1)
  - [x] Create `web-frontend/modules/dashboard/components/data_source/GroupedAggregateRowsDataSourceForm.vue`
  - [x] Mirror structure of `AggregateRowsDataSourceForm.vue` — reuse `tableFields` mixin, same table/view dropdowns
  - [x] Form fields (in order):
    1. Table selector (same as existing form)
    2. View selector (optional, same as existing form)
    3. **Group-by field** — required; label `groupedAggregateRowsDataSourceForm.groupByFieldLabel`; all field types allowed (the GROUP BY is on the raw DB value)
    4. **Aggregation type** — required; label `...aggregationTypeLabel`; static choices: count/sum/avg/min/max (NOT `viewAggregationTypes` registry — these are our 5 fixed types)
    5. **Value field** — shown only when `values.aggregation_type !== 'count'`; required when visible; same field dropdown pattern
    6. **Series field** — optional; nullable; label `...seriesFieldLabel`; hidden behind a "Add series grouping" toggle or always shown with null option
  - [x] `allowedValues`: `['table_id', 'view_id', 'group_by_field_id', 'aggregation_type', 'value_field_id', 'series_field_id']`
  - [x] `values` defaults: `{ table_id: null, view_id: null, group_by_field_id: null, aggregation_type: 'count', value_field_id: null, series_field_id: null }`
  - [x] Vuelidate rules:
    - `table_id`: required + valid table id
    - `group_by_field_id`: required + valid field id
    - `aggregation_type`: required + in ['count','sum','avg','min','max']
    - `value_field_id`: required when `aggregation_type !== 'count'`
  - [x] When `table_id` changes: reset `group_by_field_id`, `value_field_id`, `series_field_id`, `view_id`
  - [x] When `aggregation_type` switches to `count`: set `value_field_id = null`

- [x] Task 8 — Backend: Write targeted tests (AC: #1 #2)
  - [x] Create `backend/tests/baserow/contrib/integrations/local_baserow/test_grouped_aggregate_rows_service_type.py`
  - [x] Use existing test patterns from `test_dashboard_data_source_handler.py` and `test_summary_widget_type.py`
  - [x] Required test cases:
    - `test_dispatch_count_aggregation` — count rows per group, verify results shape `[{category, value}]`
    - `test_dispatch_sum_aggregation` — sum a NumberField per group
    - `test_dispatch_avg_min_max` — test avg/min/max aggregation types
    - `test_dispatch_with_series_field` — results include `{category, series, value}` shape
    - `test_dispatch_honors_field_hide_on_group_by_field` — setup FieldPermission with readable_by_role=ADMIN, dispatch as MEMBER → raises `ServiceImproperlyConfiguredDispatchException`
    - `test_dispatch_honors_field_hide_on_value_field` — hidden value field raises exception
    - `test_dispatch_count_does_not_require_value_field` — count aggregation with `value_field=None` succeeds
    - `test_resolve_formulas_raises_when_group_by_missing` — no group_by_field → exception
    - `test_resolve_formulas_raises_when_value_field_missing_for_sum` — sum without value_field → exception
    - `test_generate_schema_without_series` — schema has `{category, value}` properties
    - `test_generate_schema_with_series` — schema has `{category, series, value}` properties
  - [x] Run: `just b test backend/tests/baserow/contrib/integrations/local_baserow/test_grouped_aggregate_rows_service_type.py`

## Dev Notes

### Architecture Reference

- **D9 (architecture.md §Data Architecture):** "new **service-type** registered in `service_type_registry`, returning (category, aggregated-value[, series]) via SQL `GROUP BY` with configurable group-by field + aggregation (count/sum/avg/min/max). Honors requesting principal's field-hide + row permissions (no aggregation over hidden fields). Reused by Dashboard charts (FR-15) and App Builder chart elements (FR-22)."
- **This story is Bucket B greenfield** — no premium/enterprise source to copy from. All new code lives in `contrib/integrations/local_baserow/` following the existing `LocalBaserowAggregateRows` / `LocalBaserowListRows` pattern.
- **Reuse by Dashboard AND App Builder** — the service type is registered once in `service_type_registry`; both FR-15 (story 4.3) and FR-22 (story 5.1) will reference `"local_baserow_grouped_aggregate_rows"` when they create their data sources.

### Permission Enforcement — Critical (AC #2, NFR-4)

The permission check is NOT just for row access — it guards **field-level visibility** too:

- `FieldPermissionHandler.get_hidden_field_ids(authorized_user, table)` → set of field IDs hidden from the authorized user
- Source: `backend/src/baserow/contrib/database/fields/field_permission_handler.py:44`
- The authorized user is `service.integration.authorized_user` (same pattern used in `build_queryset()` at `local_baserow/service_types.py:288`)
- If ANY of `group_by_field`, `value_field`, or `series_field` is in `hidden_ids` → raise `ServiceImproperlyConfiguredDispatchException` (not a 403 — the dispatch error surfaces as a widget error state, not an auth error)
- Row permissions are automatically honored via `build_queryset()` → `get_table_queryset()` which applies view filters routed through the permission chain

**Why this is different from `LocalBaserowAggregateRowsUserServiceType`:**
The existing aggregate service has no field-hide check. Story 4.2 is the first service that explicitly checks `hidden_field_ids` because chart aggregations can leak the existence and distribution of hidden field values (inference attack, NFR-4).

### Model Inheritance Pattern

The `LocalBaserowGroupedAggregateRows` model must inherit from BOTH:
1. `LocalBaserowViewService` — gives access to `table`, `view`, integration FK, and `build_queryset()` plumbing
2. `LocalBaserowFilterableServiceMixin` — adds `filters` M2M so the data source can be scoped to matching rows (mirrors the existing `LocalBaserowListRows` and `LocalBaserowAggregateRows` pattern)

Do NOT inherit from `SearchableServiceMixin` — the grouped aggregate is not a row search.

Source models:
- `LocalBaserowViewService` at `local_baserow/models.py:42`
- `LocalBaserowFilterableServiceMixin` at `local_baserow/models.py:49`
- `LocalBaserowAggregateRows` at `local_baserow/models.py:108` — reference only for FK pattern

### Service Type Inheritance Pattern

```python
class LocalBaserowGroupedAggregateRowsServiceType(
    LocalBaserowTableServiceFilterableMixin,
    LocalBaserowViewServiceType,   # provides table/view/build_queryset
):
    type = "local_baserow_grouped_aggregate_rows"
    model_class = LocalBaserowGroupedAggregateRows
    dispatch_types = [DispatchTypes.DATA]
    returns_list = True            # multiple (category, value) records
```

Mirror how `LocalBaserowAggregateRowsUserServiceType` inherits `LocalBaserowTableServiceFilterableMixin` and `LocalBaserowViewServiceType`. Source: `local_baserow/service_types.py:1184`.

### Django ORM GROUP BY Pattern

Use `.values(col).annotate(value=Agg(col2))` to produce the GROUP BY:

```python
# Get the model for this service's table
model = self.get_table_model(service)  # from LocalBaserowViewServiceType
queryset = self.build_queryset(service, table, dispatch_context, model=model)

group_col = service.group_by_field.specific.db_column  # e.g. "field_42"
qs = queryset.values(group_col).annotate(value=Count("id"))
# → [{"field_42": "Marketing", "value": 7}, ...]
```

**Important:** Use `.specific.db_column` to get the actual DB column name (e.g. `field_42`). Do NOT use `.name` or `id` directly as DB column. See `local_baserow/service_types.py:1505` for `model._meta.get_field(field.db_column)` pattern.

**Null categories:** Django groups NULL values together. Represent them as `""` in the output so the frontend can display them without crashing.

### Migration File

Next migration number is `0028`. Run:
```bash
just b manage makemigrations integrations --name localbaserowgroupedaggregaterows
```
The migration will add the `localbaserowgroupedaggregaterows` concrete table with 4 FK columns + `aggregation_type` CharField.

If `just b manage makemigrations` produces `0028_*` but the squash numbering has gaps, do not manually renumber — let Django assign.

### Frontend Service Type Location

The new `LocalBaserowGroupedAggregateRowsServiceType` class belongs in:
- `web-frontend/modules/integrations/localBaserow/serviceTypes.js` (add after `LocalBaserowAggregateRowsServiceType` at line ~421)
- Register in `web-frontend/modules/integrations/plugin.js` (add alongside line ~45)

The `formComponent` references `GroupedAggregateRowsDataSourceForm` from the dashboard module. This creates a cross-module import from `integrations` → `dashboard`. Check if this pattern is already used for `AggregateRowsDataSourceForm.vue` (it is — `AggregateRowsDataSourceForm.vue` lives in `modules/dashboard/` but is referenced from `modules/integrations/localBaserow/serviceTypes.js`). Follow the same import path pattern.

**Do NOT** register the grouped aggregate service type in `modules/dashboard/module.js` — the integrations module is the correct registration point, consistent with all other service types.

### i18n Keys Needed

Add to the appropriate locale files (likely `web-frontend/modules/integrations/locales/en.json` and/or `dashboard/locales/en.json`):
- `serviceType.localBaserowGroupedAggregateRows`: "Grouped Aggregate"
- `serviceType.localBaserowGroupedAggregateRowsDescription`: "Groups rows by a field and aggregates a value per group."
- `groupedAggregateRowsDataSourceForm.data`: "Data"
- `groupedAggregateRowsDataSourceForm.groupByFieldLabel`: "Group by"
- `groupedAggregateRowsDataSourceForm.aggregationTypeLabel`: "Aggregation"
- `groupedAggregateRowsDataSourceForm.valueFieldLabel`: "Value field"
- `groupedAggregateRowsDataSourceForm.seriesFieldLabel`: "Series field (optional)"
- `groupedAggregateRowsDataSourceForm.sourceFieldLabel`: "Table"
- `groupedAggregateRowsDataSourceForm.viewFieldLabel`: "Filter by view"
- `groupedAggregateRowsDataSourceForm.notSelected`: "Not selected"
- `groupedAggregateRowsDataSourceForm.aggregationTypes.count`: "Count"
- `groupedAggregateRowsDataSourceForm.aggregationTypes.sum`: "Sum"
- `groupedAggregateRowsDataSourceForm.aggregationTypes.avg`: "Average"
- `groupedAggregateRowsDataSourceForm.aggregationTypes.min`: "Minimum"
- `groupedAggregateRowsDataSourceForm.aggregationTypes.max`: "Maximum"

### Story 4.1 Context (Previous Story Learnings)

- `BaseChart.vue` now exists at `web-frontend/modules/dashboard/components/chart/BaseChart.vue`. Story 4.2 does NOT use it — this story is pure data plumbing with no chart rendering.
- `echarts@6.0.0` and `vue-echarts@8.0.1` are already installed. No new JS dependencies needed for this story.
- Story 4.2 is backend-heavy and a thin frontend form. The chart rendering wiring (widget types registering with this service type) is deferred to story 4.3.

### Scope Boundaries (What NOT to Build)

- **Do NOT** create Dashboard widget types for charts — that is story 4.3
- **Do NOT** register chart widget types in `widgetTypes.js` — story 4.3
- **Do NOT** build the App Builder chart element — story 5.1
- **Do NOT** wire the service type to any widget component here — story 4.3 does `SummaryWidgetType` style wiring for the chart widget
- **Do NOT** add WebSocket invalidation / debounce re-aggregate — that is story 4.4 (D11)
- The `GroupedAggregateRowsDataSourceForm.vue` is standalone; it does not need to be registered in any widget type in this story

### Testing Pattern Reference

- `backend/tests/baserow/contrib/dashboard/widgets/test_summary_widget_type.py` — best reference for widget + data source test patterns
- `backend/tests/baserow/contrib/dashboard/data_sources/test_dashboard_data_source_handler.py` — reference for service dispatch + permission tests
- Use `data_fixture` conftest fixtures for creating Table, Field, User, RoleAssignment, FieldPermission
- `FieldPermission.objects.create(field=field, readable_by_role="member")` pattern (Story 1.5, from `field_permission_handler.py`)
- Run with: `just b test backend/tests/baserow/contrib/integrations/local_baserow/test_grouped_aggregate_rows_service_type.py`

### Project Structure Notes

- Model lives in `backend/src/baserow/contrib/integrations/local_baserow/models.py` [UPDATE]
- Service type lives in `backend/src/baserow/contrib/integrations/local_baserow/service_types.py` [UPDATE]
- Migration lives in `backend/src/baserow/contrib/integrations/migrations/0028_*.py` [NEW]
- Registration in `backend/src/baserow/contrib/integrations/apps.py` [UPDATE]
- Frontend service type class in `web-frontend/modules/integrations/localBaserow/serviceTypes.js` [UPDATE]
- Frontend plugin registration in `web-frontend/modules/integrations/plugin.js` [UPDATE]
- Frontend form component in `web-frontend/modules/dashboard/components/data_source/GroupedAggregateRowsDataSourceForm.vue` [NEW]
- Backend tests in `backend/tests/baserow/contrib/integrations/local_baserow/test_grouped_aggregate_rows_service_type.py` [NEW]
- No `premium/` or `enterprise/` touches (Bucket B greenfield)
- Architecture §Component-to-Location Map confirms: `contrib/dashboard/data_sources/ [B] FR-14 grouped-aggregate Data Source (service-type)` — however the actual service type class follows the existing convention of living next to other LocalBaserow service types

### References

- [Source: _bmad-output/planning-artifacts/epics.md §Story 4.2 — Grouped-aggregate Data Source L722-738]
- [Source: _bmad-output/planning-artifacts/architecture.md §Data Architecture — D9]
- [Source: _bmad-output/planning-artifacts/architecture.md §Core Architectural Decisions — Fixed by brownfield foundation (service_type_registry)]
- [Source: _bmad-output/planning-artifacts/architecture.md §Component-to-Location Map — contrib/dashboard/data_sources/]
- [Source: backend/src/baserow/contrib/integrations/local_baserow/models.py:108 — LocalBaserowAggregateRows model pattern]
- [Source: backend/src/baserow/contrib/integrations/local_baserow/service_types.py:1184 — LocalBaserowAggregateRowsUserServiceType — inheritance + dispatch pattern]
- [Source: backend/src/baserow/contrib/integrations/local_baserow/service_types.py:274 — build_queryset pattern (authorized_user, row permission)]
- [Source: backend/src/baserow/core/field_permissions/permission_manager.py — FieldPermissionManagerType.filter_queryset + _hidden_field_ids]
- [Source: backend/src/baserow/contrib/database/fields/field_permission_handler.py:44 — FieldPermissionHandler.get_hidden_field_ids]
- [Source: backend/src/baserow/contrib/integrations/apps.py:27-39 — service type registration point]
- [Source: web-frontend/modules/integrations/localBaserow/serviceTypes.js:323 — LocalBaserowAggregateRowsServiceType frontend pattern]
- [Source: web-frontend/modules/integrations/plugin.js:41-45 — service type registration in plugin]
- [Source: web-frontend/modules/dashboard/components/data_source/AggregateRowsDataSourceForm.vue — form component pattern to mirror]
- [Source: _bmad-output/implementation-artifacts/4-1-charting-foundation-shared-lazy-loaded.md — previous story learnings]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- GROUP BY returned count=1 for all groups due to default `ordering = ["order", "id"]` on GeneratedTableModel. Fixed by calling `.order_by()` before `.values().annotate()`.
- FieldPermission tests did not raise because `FieldPermissionManagerType._hidden_field_ids` defers when user has no `RoleAssignment` (`role is None`). Fixed by calling `RbacHandler().assign_role(user, workspace, "EDITOR")` to give an explicit sub-ADMIN role.
- `test_generate_schema_*` tests errored due to missing `@pytest.mark.django_db` decorator (data_fixture requires DB access even for schema-only tests).
- Migration `makemigrations` in non-OSS mode clashes with `premium/baserow_premium` which also defines `LocalBaserowGroupedAggregateRows` (empty body, uses `SeparateDatabaseAndState`). Used `BASEROW_OSS_ONLY=1` env to generate clean migration.

### Completion Notes List

- All 8 tasks implemented and verified. 11/11 backend tests pass.
- The 3 pre-existing failures (`test_can_dispatch_interesting_table`, `test_local_baserow_table_service_generate_schema_with_interesting_test_table`) are unrelated to story 4.2 — they fail on baseline commit too (missing field type in `construct_all_possible_field_kwargs`).
- `GroupedAggregateRowsDataSourceForm.vue` is standalone; no widget type wiring (story 4.3 scope).
- Premium's `LocalBaserowGroupedAggregateRows` (in `premium/backend`) uses `SeparateDatabaseAndState(database_operations=[])` — it expects core migration 0028 to create the DB table, which it does.

### File List

**New files:**
- `backend/src/baserow/contrib/integrations/migrations/0028_localbaserowgroupedaggregaterows.py`
- `backend/tests/baserow/contrib/integrations/local_baserow/test_grouped_aggregate_rows_service_type.py`
- `web-frontend/modules/dashboard/components/data_source/GroupedAggregateRowsDataSourceForm.vue`

**Modified files:**
- `backend/src/baserow/contrib/integrations/local_baserow/models.py` — added `LocalBaserowGroupedAggregateRows` model
- `backend/src/baserow/contrib/integrations/local_baserow/service_types.py` — added `LocalBaserowGroupedAggregateRowsServiceType`
- `backend/src/baserow/contrib/integrations/apps.py` — registered service type
- `backend/src/baserow/test_utils/fixtures/service.py` — added fixture method
- `web-frontend/modules/integrations/localBaserow/serviceTypes.js` — added `LocalBaserowGroupedAggregateRowsServiceType` class
- `web-frontend/modules/integrations/plugin.js` — registered service type
- `web-frontend/modules/dashboard/locales/en.json` — added `groupedAggregateRowsDataSourceForm` i18n section
- `web-frontend/modules/integrations/locales/en.json` — added `serviceType.localBaserowGroupedAggregateRows*` keys

### Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-06-12 | Implemented story 4.2 — all 8 tasks complete, 11/11 tests pass | claude-sonnet-4-6 |
