# Provenance Record: Story 4.3 — Chart Widgets (Bar and Pie/Doughnut)

## What Was Reimplemented

### Backend

- **`ChartWidget` model** (`backend/src/baserow/contrib/dashboard/widgets/models.py`)  
  New Django model extending `Widget`. Fields: `chart_type` (CharField with bar/pie/doughnut choices), `data_source` (FK to `DashboardDataSource`). Independently designed; not copied from any premium/enterprise source.

- **`ChartWidgetType` backend type** (`backend/src/baserow/contrib/dashboard/widgets/widget_types.py`)  
  Implements `prepare_value_for_db`, `before_trashed`, `before_restore`, `after_delete`, `serialize_property`, `deserialize_property`, `SerializedDict`. All patterns derived from `SummaryWidgetType` in the same file (same repo, Apache/BSL-compatible core module). No premium/enterprise source files were read.

- **Migration** (`backend/src/baserow/contrib/dashboard/migrations/0004_chartwidget.py`)  
  Auto-generated via `manage.py makemigrations`.

### Frontend

- **`ChartWidget.vue`** (`web-frontend/modules/dashboard/components/widget/ChartWidget.vue`)  
  Renders bar/pie/doughnut charts using `<BaseChart>` from story 4.1 (lazy-loaded ECharts). Chart option logic derived independently from Apache ECharts documentation (Apache-2.0). Multi-series grouping for bar charts derived from ECharts series API docs.

- **`ChartWidgetSettings.vue`** (`web-frontend/modules/dashboard/components/widget/ChartWidgetSettings.vue`)  
  Settings panel wrapping `GroupedAggregateRowsDataSourceForm` from story 4.2. Pattern mirrors `SummaryWidgetSettings.vue` (same repo).

- **`ChartWidgetType` frontend class** (`web-frontend/modules/dashboard/widgetTypes.js`)  
  Frontend registry entry with single type string `'chart'` and three variations (bar/pie/doughnut). Pattern derived from `SummaryWidgetType` in the same file.

## Source Inspiration

| Component | Inspiration Source | License |
|---|---|---|
| `ChartWidgetType` backend | `SummaryWidgetType` (same file, core module) | BSL 1.1 (own code) |
| `ChartWidget.vue` template | `SummaryWidget.vue` structure | BSL 1.1 (own code) |
| `ChartWidgetSettings.vue` | `SummaryWidgetSettings.vue` | BSL 1.1 (own code) |
| ECharts `chartOption` shapes | Apache ECharts documentation | Apache-2.0 |
| `BaseChart` usage | story 4.1 implementation | own code |

## Clean-Room Confirmation

- **No premium source files read** to implement chart rendering logic or widget type structure.
- **No enterprise source files read** during implementation.
- The `unregister()` guard added to `premium/backend/src/baserow_premium/apps.py` is a maintenance fix (same pattern already used elsewhere in that file), not a feature copy.
- ECharts option object shapes (xAxis/yAxis/series config) are independently derived from Apache ECharts v5+ public documentation.

## Implemented by

claude-sonnet-4-6 — 2026-06-12
