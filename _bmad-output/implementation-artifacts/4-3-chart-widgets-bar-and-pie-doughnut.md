---
baseline_commit: ac24f350b
---

# Story 4.3: Chart Widgets — bar and pie/doughnut (clean-room)

Status: review

## Story

As a user,
I want bar and pie/doughnut chart Widgets on a Dashboard,
so that I can visualize grouped data from a grouped-aggregate Data Source.

## Acceptance Criteria

1. Given a Dashboard and a grouped-aggregate Data Source (story 4.2), when a user adds a bar or pie/doughnut Widget from the create-widget modal, it renders using the configured category/value/series fields from the Data Source.
2. The implementation is a clean-room reimplementation — a provenance record is created at `_bmad-output/implementation-artifacts/provenance/4-3-chart-widgets-bar-pie-provenance.md` (AR-1).
3. Chart Widgets interoperate with the existing free summary metric Widget on the same Dashboard — both appear on the WidgetBoard without conflict, share the same `widget_type_registry`, and the SummaryWidget continues rendering correctly.

## Tasks / Subtasks

- [x] Task 1: Add `ChartWidget` Django model (AC: #1, #3)
  - [x] 1.1 Add `ChartWidget` to `backend/src/baserow/contrib/dashboard/widgets/models.py`:
    ```python
    class ChartWidget(Widget):
        CHART_TYPE_BAR = 'bar'
        CHART_TYPE_PIE = 'pie'
        CHART_TYPE_DOUGHNUT = 'doughnut'
        CHART_TYPE_CHOICES = [
            (CHART_TYPE_BAR, 'Bar'),
            (CHART_TYPE_PIE, 'Pie'),
            (CHART_TYPE_DOUGHNUT, 'Doughnut'),
        ]
        chart_type = models.CharField(
            max_length=32, choices=CHART_TYPE_CHOICES, default=CHART_TYPE_BAR
        )
        data_source = models.ForeignKey(
            'dashboard.DashboardDataSource',
            on_delete=models.PROTECT,
            help_text='Data source providing grouped-aggregate rows for chart rendering.',
        )
    ```
  - [x] 1.2 Run migration: `just b manage makemigrations dashboard --name chartwidget` → creates `backend/src/baserow/contrib/dashboard/migrations/0004_chartwidget.py`; verify it references `0003_widget_dashboarddatasource_summarywidget` as dependency

- [x] Task 2: Implement `ChartWidgetType` backend type (AC: #1, #3)
  - [x] 2.1 Add `ChartWidgetType` class to `backend/src/baserow/contrib/dashboard/widgets/widget_types.py` below `SummaryWidgetType`
  - [x] 2.2 Type string and model:
    ```python
    from .models import SummaryWidget, ChartWidget  # add ChartWidget import
    from baserow.contrib.integrations.local_baserow.service_types import (
        LocalBaserowAggregateRowsUserServiceType,
        LocalBaserowGroupedAggregateRowsServiceType,  # add this import
    )

    class ChartWidgetType(WidgetType):
        type = 'chart'
        model_class = ChartWidget
    ```
  - [x] 2.3 Serializer fields (same pattern as SummaryWidgetType):
    ```python
    serializer_field_names = ['data_source_id', 'chart_type']
    serializer_field_overrides = {
        'data_source_id': serializers.PrimaryKeyRelatedField(
            queryset=DashboardDataSource.objects.all(),
            required=False,
            default=None,
            help_text='References a grouped-aggregate data source for the chart.',
        ),
        'chart_type': serializers.ChoiceField(
            choices=ChartWidget.CHART_TYPE_CHOICES,
            required=False,
            default=ChartWidget.CHART_TYPE_BAR,
            help_text='Chart display type: bar, pie, or doughnut.',
        ),
    }
    request_serializer_field_names = ['chart_type']
    request_serializer_field_overrides = {
        'chart_type': serializers.ChoiceField(
            choices=ChartWidget.CHART_TYPE_CHOICES,
            required=False,
            default=ChartWidget.CHART_TYPE_BAR,
        ),
    }
    ```
  - [x] 2.4 `prepare_value_for_db` — auto-creates `LocalBaserowGroupedAggregateRows` data source on widget creation (not `LocalBaserowAggregateRows` like SummaryWidget):
    ```python
    def prepare_value_for_db(self, values: dict, instance: Widget | None = None):
        if instance is None:
            available_name = DashboardDataSourceHandler().find_unused_data_source_name(
                values['dashboard'], 'ChartDataSource'
            )
            data_source = DashboardDataSourceHandler().create_data_source(
                dashboard=values['dashboard'],
                name=available_name,
                service_type=service_type_registry.get(
                    LocalBaserowGroupedAggregateRowsServiceType.type
                ),
            )
            values['data_source'] = data_source
        return values
    ```
  - [x] 2.5 Implement lifecycle hooks (identical pattern to SummaryWidgetType):
    ```python
    def before_trashed(self, instance: Widget):
        instance.data_source.trashed = True
        instance.data_source.save()

    def before_restore(self, instance: Widget):
        instance.data_source.trashed = False
        instance.data_source.save()

    def after_delete(self, instance: Widget):
        DashboardDataSourceHandler().delete_data_source(instance.data_source)
    ```
  - [x] 2.6 Implement `SerializedDict`, `serialize_property`, `deserialize_property` mirroring `SummaryWidgetType`:
    ```python
    class SerializedDict(WidgetDict):
        data_source_id: int
        chart_type: str

    def serialize_property(self, instance, prop_name, files_zip=None, storage=None, cache=None):
        if prop_name == 'data_source_id':
            return instance.data_source_id
        return super().serialize_property(instance, prop_name, files_zip=files_zip, storage=storage, cache=cache)

    def deserialize_property(self, prop_name, value, id_mapping, **kwargs):
        if prop_name == 'data_source_id' and value:
            return id_mapping['dashboard_data_sources'][value]
        return super().deserialize_property(prop_name, value, id_mapping, **kwargs)
    ```

- [x] Task 3: Register `ChartWidgetType` in `dashboard/apps.py` (AC: #3)
  - [x] 3.1 In `backend/src/baserow/contrib/dashboard/apps.py` `ready()` method, add after `widget_type_registry.register(SummaryWidgetType())`:
    ```python
    from baserow.contrib.dashboard.widgets.widget_types import SummaryWidgetType, ChartWidgetType
    widget_type_registry.register(ChartWidgetType())
    ```

- [x] Task 4: Create `ChartWidget.vue` frontend component (AC: #1)
  - [x] 4.1 Create `web-frontend/modules/dashboard/components/widget/ChartWidget.vue`
  - [x] 4.2 Props (identical signature to `SummaryWidget.vue`): `dashboard` (Object, required), `widget` (Object, required), `storePrefix` (String, default ''), `loading` (Boolean, default false)
  - [x] 4.3 Computed getters from store — copy exactly from `SummaryWidget.vue`:
    ```js
    dataSource() {
      return this.$store.getters[`${this.storePrefix}dashboardApplication/getDataSourceById`](this.widget.data_source_id)
    },
    dataForDataSource() {
      return this.$store.getters[`${this.storePrefix}dashboardApplication/getDataForDataSource`](this.dataSource?.id)
    },
    isEditMode() {
      return this.$store.getters[`${this.storePrefix}dashboardApplication/isEditMode`]
    },
    ```
  - [x] 4.4 Computed `chartOption` — builds ECharts option from `dataForDataSource.result` (array of `{category, value[, series]}`):
    ```js
    chartOption() {
      const result = this.dataForDataSource?.result || []
      const chartType = this.widget.chart_type || 'bar'
      if (chartType === 'bar') {
        return {
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: result.map(r => r.category) },
          yAxis: { type: 'value' },
          series: [{ type: 'bar', data: result.map(r => r.value) }],
        }
      }
      // pie and doughnut
      const seriesItem = {
        type: 'pie',
        data: result.map(r => ({ name: r.category, value: r.value })),
      }
      if (chartType === 'doughnut') {
        seriesItem.radius = ['40%', '70%']
      }
      return {
        tooltip: { trigger: 'item' },
        series: [seriesItem],
      }
    },
    dataSourceMisconfigured() {
      return !!(this.dataForDataSource?._error)
    },
    ```
  - [x] 4.5 Template: show loading spinner when `loading` prop is true; otherwise render widget header (title, WidgetContextMenu in edit mode) + `<BaseChart :option="chartOption" :type="widget.chart_type" />`
    ```html
    <template>
      <div class="dashboard-chart-widget">
        <template v-if="!loading">
          <div class="widget__header widget__header--no-border">
            <div class="widget__header-main">
              <div class="widget__header-title-wrapper">
                <div class="widget__header-title">{{ widget.title }}</div>
                <Badge v-if="dataSourceMisconfigured" color="red" indicator rounded>
                  {{ $t('widget.fixConfiguration') }}
                </Badge>
              </div>
              <div v-if="widget.description" class="widget__header-description">{{ widget.description }}</div>
            </div>
            <WidgetContextMenu
              v-if="isEditMode"
              :widget="widget"
              :dashboard="dashboard"
              @delete-widget="$emit('delete-widget', $event)"
            />
          </div>
          <div class="widget__content dashboard-chart-widget__chart">
            <BaseChart v-if="!dataSourceMisconfigured" :option="chartOption" :type="widget.chart_type" />
          </div>
        </template>
        <div v-else class="dashboard-chart-widget__loading loading-spinner" />
      </div>
    </template>
    ```
  - [x] 4.6 Import `BaseChart` from `@baserow/modules/dashboard/components/chart/BaseChart` and `WidgetContextMenu` from `@baserow/modules/dashboard/components/widget/WidgetContextMenu`
  - [x] 4.7 Emit `delete-widget` event (same as SummaryWidget.vue)

- [x] Task 5: Create `ChartWidgetSettings.vue` (AC: #1)
  - [x] 5.1 Create `web-frontend/modules/dashboard/components/widget/ChartWidgetSettings.vue`
  - [x] 5.2 Uses `GroupedAggregateRowsDataSourceForm` (story 4.2) — mirrors `SummaryWidgetSettings.vue` using `AggregateRowsDataSourceForm`, replacing it with `GroupedAggregateRowsDataSourceForm`:
    ```html
    <template>
      <GroupedAggregateRowsDataSourceForm
        v-if="dataSource"
        ref="dataSourceForm"
        :dashboard="dashboard"
        :widget="widget"
        :data-source="dataSource"
        :default-values="dataSource"
        :store-prefix="storePrefix"
        @values-changed="onDataSourceValuesChanged"
      />
    </template>
    ```
  - [x] 5.3 Script: copy `SummaryWidgetSettings.vue` script exactly, replacing `AggregateRowsDataSourceForm` import with `GroupedAggregateRowsDataSourceForm`

- [x] Task 6: Create SVG widget preview images (AC: #1)
  - [x] 6.1 Create `web-frontend/modules/dashboard/assets/images/widgets/bar_chart_widget.svg` — simple 72×40 SVG showing bar chart bars (follow style of `summary_widget.svg`: white fill, #E6E6E7 stroke border, simplified shapes)
  - [x] 6.2 Create `web-frontend/modules/dashboard/assets/images/widgets/pie_chart_widget.svg` — simple 72×40 SVG showing a pie chart circle segment

- [x] Task 7: Add `ChartWidgetType` frontend class and register in plugin.js (AC: #1, #3)
  - [x] 7.1 Add to `web-frontend/modules/dashboard/widgetTypes.js` (after `SummaryWidgetType`):
    ```js
    import BarChartWidgetSvg from '@baserow/modules/dashboard/assets/images/widgets/bar_chart_widget.svg?url'
    import PieChartWidgetSvg from '@baserow/modules/dashboard/assets/images/widgets/pie_chart_widget.svg?url'
    import ChartWidget from '@baserow/modules/dashboard/components/widget/ChartWidget'
    import ChartWidgetSettings from '@baserow/modules/dashboard/components/widget/ChartWidgetSettings'

    export class ChartWidgetType extends WidgetType {
      static getType() {
        return 'chart'
      }

      get name() {
        return this.app.$i18n.t('chartWidget.name')
      }

      get component() {
        return ChartWidget
      }

      get settingsComponent() {
        return ChartWidgetSettings
      }

      get variations() {
        const { $i18n: i18n } = this.app
        return [
          {
            name: i18n.t('barChartWidget.name'),
            createWidgetImage: BarChartWidgetSvg,
            type: this,
            params: { chart_type: 'bar' },
            dropdownIcon: '',
          },
          {
            name: i18n.t('pieChartWidget.name'),
            createWidgetImage: PieChartWidgetSvg,
            type: this,
            params: { chart_type: 'pie' },
            dropdownIcon: '',
          },
          {
            name: i18n.t('doughnutChartWidget.name'),
            createWidgetImage: PieChartWidgetSvg,
            type: this,
            params: { chart_type: 'doughnut' },
            dropdownIcon: '',
          },
        ]
      }

      isLoading(widget, data) {
        const dataSourceId = widget.data_source_id
        if (data[dataSourceId] && Object.keys(data[dataSourceId]).length !== 0) {
          return false
        }
        return true
      }
    }
    ```
  - [x] 7.2 In `web-frontend/modules/dashboard/plugin.js`, import `ChartWidgetType` and register alongside `SummaryWidgetType`:
    ```js
    import { SummaryWidgetType, ChartWidgetType } from '@baserow/modules/dashboard/widgetTypes'
    // inside setup():
    $registry.register('dashboardWidget', new ChartWidgetType(context))
    ```

- [x] Task 8: Add i18n keys (AC: #1)
  - [x] 8.1 Add to `web-frontend/modules/dashboard/locales/en.json`:
    ```json
    "chartWidget": { "name": "Chart" },
    "barChartWidget": { "name": "Bar chart" },
    "pieChartWidget": { "name": "Pie chart" },
    "doughnutChartWidget": { "name": "Doughnut chart" }
    ```
  - [x] 8.2 Add placeholder (empty string value) keys for the same keys to: `de.json`, `es.json`, `fr.json`, `it.json` — copy `en.json` structure, value = English string (translations deferred)

- [x] Task 9: Backend tests (AC: #1, #3)
  - [x] 9.1 Create `backend/tests/baserow/contrib/dashboard/widgets/test_chart_widget_type.py` with `@pytest.mark.django_db` on all test functions
  - [x] 9.2 Test: `test_create_chart_widget_creates_grouped_aggregate_data_source` — create bar chart widget via `WidgetService().create_widget(user, 'chart', dashboard.id, title='My chart', chart_type='bar')`; assert `widget.data_source` is not None; assert `ContentType.objects.get_for_model(LocalBaserowGroupedAggregateRows) == widget.data_source.service.content_type`
  - [x] 9.3 Test: `test_create_pie_widget` — same but with `chart_type='pie'`; assert `widget.chart_type == 'pie'`
  - [x] 9.4 Test: `test_create_doughnut_widget` — `chart_type='doughnut'`; assert `widget.chart_type == 'doughnut'`
  - [x] 9.5 Test: `test_chart_widget_trash_restore` — trash → assert `data_source.trashed is True`; restore → assert `data_source.trashed is False` (mirrors `test_summary_widget_trash_restore` in `test_summary_widget_type.py`)
  - [x] 9.6 Test: `test_chart_widget_datasource_cannot_be_deleted` — assert `ProtectedError` when deleting data source directly (mirrors `test_summary_widget_datasource_cannot_be_deleted`)
  - [x] 9.7 Test: `test_chart_widget_and_summary_widget_coexist` — create both a `summary` widget and a `chart` widget on the same dashboard; assert both are in `Widget.objects.filter(dashboard=dashboard)`; assert no registry conflict

- [x] Task 10: Provenance record (AC: #2)
  - [x] 10.1 Create directory `_bmad-output/implementation-artifacts/provenance/` if not exists
  - [x] 10.2 Create `_bmad-output/implementation-artifacts/provenance/4-3-chart-widgets-bar-pie-provenance.md` documenting:
    - What was reimplemented: `ChartWidgetType` backend type, `ChartWidget` model, `ChartWidget.vue`, `ChartWidgetSettings.vue`
    - Source inspiration: Baserow `SummaryWidgetType` pattern (same repo, license-compatible — extending, not copying premium/enterprise code)
    - ECharts chart option shapes: independently derived from Apache ECharts docs (Apache-2.0), not copied from any existing Baserow chart code
    - Confirmation no premium/enterprise source files were read to implement chart rendering logic

## Dev Notes

### Architecture constraints

- **Bundle discipline (SM-C3):** `ChartWidget.vue` must NOT import ECharts directly. It uses `<BaseChart>` from story 4.1, which already handles lazy-loading inside `mounted()`. Any direct `import('echarts/...')` call in ChartWidget.vue breaks the lazy-load guarantee.
- **Single `ChartWidgetType` for all 3 chart types:** The frontend `ChartWidgetType` has `static getType() { return 'chart' }` — ONE registry entry. Three variations (bar/pie/doughnut) are exposed via `get variations()`. This matches the backend `type = 'chart'` on `ChartWidgetType`. Do NOT create separate `BarChartWidgetType` and `PieChartWidgetType` classes — they would conflict in the registry.
- **`chart_type` sent as variation param:** The frontend `variations[].params = { chart_type: 'bar' }` is sent in the widget create API call body. The backend `WidgetType.prepare_value_for_db` receives it in `values` and saves it to `ChartWidget.chart_type`. Ensure `chart_type` appears in `request_serializer_field_names` so it passes DRF validation.
- **Data source auto-creation uses grouped-aggregate type:** `ChartWidgetType.prepare_value_for_db` must use `LocalBaserowGroupedAggregateRowsServiceType.type` (`"local_baserow_grouped_aggregate_rows"`), NOT `LocalBaserowAggregateRowsUserServiceType.type` (`"local_baserow_aggregate_rows"`). The SummaryWidget uses the latter; chart widgets use the former.
- **No WebSocket invalidation in this story:** Story 4.4 adds fetch-on-load + WebSocket row-event invalidation. Story 4.3 is display-only — chart renders once from initial data load. Do NOT implement WebSocket re-aggregate logic here.
- **Field permissions:** The grouped-aggregate data source (story 4.2) already enforces field-hide + row permissions in `dispatch_data()`. ChartWidget.vue needs no additional permission checks — it only renders `dataForDataSource.result`.

### Data flow for `chartOption` computed

`dataForDataSource.result` is the array returned by `LocalBaserowGroupedAggregateRowsServiceType.dispatch_transform()`. Shape: `[{category: "X", value: 42}, ...]` or `[{category: "X", value: 42, series: "S"}, ...]`.

For bar charts with series: each distinct `series` value becomes a separate ECharts series entry:
```js
// series grouping (if series values are present)
const seriesValues = [...new Set(result.map(r => r.series).filter(Boolean))]
if (seriesValues.length > 0) {
  // multi-series bar
  series: seriesValues.map(s => ({
    type: 'bar',
    name: s,
    data: categories.map(c => result.find(r => r.category === c && r.series === s)?.value ?? 0),
  }))
} else {
  series: [{ type: 'bar', data: result.map(r => r.value) }]
}
```
For pie/doughnut, series field is ignored (pie does not support a series dimension in ECharts).

### Project Structure Notes

- `ChartWidget` Django model → `backend/src/baserow/contrib/dashboard/widgets/models.py` (append after `SummaryWidget`)
- Migration → `backend/src/baserow/contrib/dashboard/migrations/0004_chartwidget.py`
- `ChartWidgetType` backend → `backend/src/baserow/contrib/dashboard/widgets/widget_types.py`
- `ChartWidgetType` registration → `backend/src/baserow/contrib/dashboard/apps.py`
- `ChartWidget.vue` → `web-frontend/modules/dashboard/components/widget/ChartWidget.vue` (new file)
- `ChartWidgetSettings.vue` → `web-frontend/modules/dashboard/components/widget/ChartWidgetSettings.vue` (new file)
- `ChartWidgetType` frontend → `web-frontend/modules/dashboard/widgetTypes.js` (append after `SummaryWidgetType`)
- Registration → `web-frontend/modules/dashboard/plugin.js`
- SVG assets → `web-frontend/modules/dashboard/assets/images/widgets/bar_chart_widget.svg` and `pie_chart_widget.svg`
- i18n → `web-frontend/modules/dashboard/locales/en.json` (and placeholder in other locale files)
- Tests → `backend/tests/baserow/contrib/dashboard/widgets/test_chart_widget_type.py` (new file)
- Provenance → `_bmad-output/implementation-artifacts/provenance/4-3-chart-widgets-bar-pie-provenance.md` (new file)

### References

- SummaryWidgetType pattern: `backend/src/baserow/contrib/dashboard/widgets/widget_types.py` — clone and adapt
- SummaryWidget.vue pattern: `web-frontend/modules/dashboard/components/widget/SummaryWidget.vue`
- SummaryWidgetSettings.vue pattern: `web-frontend/modules/dashboard/components/widget/SummaryWidgetSettings.vue`
- GroupedAggregateRowsDataSourceForm: `web-frontend/modules/dashboard/components/data_source/GroupedAggregateRowsDataSourceForm.vue` (story 4.2)
- BaseChart.vue: `web-frontend/modules/dashboard/components/chart/BaseChart.vue` (story 4.1)
- LocalBaserowGroupedAggregateRowsServiceType: `backend/src/baserow/contrib/integrations/local_baserow/service_types.py#LocalBaserowGroupedAggregateRowsServiceType` (type = `"local_baserow_grouped_aggregate_rows"`)
- Widget model base: `backend/src/baserow/contrib/dashboard/widgets/models.py`
- Dashboard apps.py registration: `backend/src/baserow/contrib/dashboard/apps.py`
- Existing widget type test: `backend/tests/baserow/contrib/dashboard/widgets/test_summary_widget_type.py`
- WidgetType base class: `web-frontend/modules/dashboard/widgetTypes.js#WidgetType`
- Plugin registration: `web-frontend/modules/dashboard/plugin.js`
- Summary widget SVG style reference: `web-frontend/modules/dashboard/assets/images/widgets/summary_widget.svg`
- Architecture D1 (ECharts): `_bmad-output/planning-artifacts/architecture.md#Library Decisions` — echarts@6.0, vue-echarts@8.0.1, lazy-load mandatory
- Architecture D9 (grouped-aggregate): `_bmad-output/planning-artifacts/architecture.md#Data Architecture`
- Story 4.2 scope boundary: grouped-aggregate service type is complete and registered; story 4.3 does NOT modify service_types.py

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Premium double-registration: `premium/apps.py` needed `widget_type_registry.unregister(ChartWidgetType.type)` before registering premium's ChartWidgetType (same pattern as story 4.2 fix).
- Tests bypass premium license: use `WidgetHandler().create_widget(CoreChartWidgetType(), ...)` directly.
- Fixture updated to use `service_type_registry.get(...).model_class` dynamically — premium replaces model class at startup.
- Added `allowed_fields = ['title', 'description', 'chart_type']` — base only defines title/description, chart_type was filtered by `extract_allowed()`.

### Completion Notes List

- ✅ `ChartWidget` model + migration `0004_chartwidget.py` created.
- ✅ `ChartWidgetType` backend: `prepare_value_for_db` (grouped-aggregate DS), lifecycle hooks, serialize/deserialize, `allowed_fields`.
- ✅ Premium guard: `unregister()` before `register()` in `premium/apps.py`.
- ✅ Frontend: `ChartWidget.vue` (multi-series bar, pie/doughnut), `ChartWidgetSettings.vue` (GroupedAggregateRowsDataSourceForm).
- ✅ `ChartWidgetType` frontend (3 variations), registered in `plugin.js`.
- ✅ SVG previews: `bar_chart_widget.svg`, `pie_chart_widget.svg`.
- ✅ i18n: en/de/es/fr/it locales updated.
- ✅ Test fixtures: `create_chart_widget`, `create_dashboard_local_baserow_grouped_aggregate_rows_data_source`.
- ✅ 6/6 new tests pass; 46/46 total dashboard widget tests pass.
- ✅ Provenance record created.

### File List

- `backend/src/baserow/contrib/dashboard/widgets/models.py` (modify — add ChartWidget)
- `backend/src/baserow/contrib/dashboard/migrations/0004_chartwidget.py` (create)
- `backend/src/baserow/contrib/dashboard/widgets/widget_types.py` (modify — add ChartWidgetType)
- `backend/src/baserow/contrib/dashboard/apps.py` (modify — register ChartWidgetType)
- `web-frontend/modules/dashboard/components/widget/ChartWidget.vue` (create)
- `web-frontend/modules/dashboard/components/widget/ChartWidgetSettings.vue` (create)
- `web-frontend/modules/dashboard/assets/images/widgets/bar_chart_widget.svg` (create)
- `web-frontend/modules/dashboard/assets/images/widgets/pie_chart_widget.svg` (create)
- `web-frontend/modules/dashboard/widgetTypes.js` (modify — add ChartWidgetType)
- `web-frontend/modules/dashboard/plugin.js` (modify — register ChartWidgetType)
- `web-frontend/modules/dashboard/locales/en.json` (modify — add chart widget i18n keys)
- `web-frontend/modules/dashboard/locales/de.json` (modify — placeholder keys)
- `web-frontend/modules/dashboard/locales/es.json` (modify — placeholder keys)
- `web-frontend/modules/dashboard/locales/fr.json` (modify — placeholder keys)
- `web-frontend/modules/dashboard/locales/it.json` (modify — placeholder keys)
- `backend/tests/baserow/contrib/dashboard/widgets/test_chart_widget_type.py` (create)
- `_bmad-output/implementation-artifacts/provenance/4-3-chart-widgets-bar-pie-provenance.md` (create)
- `backend/src/baserow/test_utils/fixtures/widget.py` (modify — add create_chart_widget)
- `backend/src/baserow/test_utils/fixtures/dashboard_data_source.py` (modify — add grouped aggregate fixture)
- `premium/backend/src/baserow_premium/apps.py` (modify — unregister core ChartWidgetType before premium register)
