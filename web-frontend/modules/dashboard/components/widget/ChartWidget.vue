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
          <div v-if="widget.description" class="widget__header-description">
            {{ widget.description }}
          </div>
        </div>
        <WidgetContextMenu
          v-if="isEditMode"
          :widget="widget"
          :dashboard="dashboard"
          @delete-widget="$emit('delete-widget', $event)"
        />
      </div>
      <div class="widget__content dashboard-chart-widget__chart">
        <BaseChart
          v-if="!dataSourceMisconfigured"
          :option="chartOption"
          :type="widget.chart_type"
        />
      </div>
    </template>
    <div v-else class="dashboard-chart-widget__loading loading-spinner" />
  </div>
</template>

<script>
import BaseChart from '@baserow/modules/dashboard/components/chart/BaseChart'
import WidgetContextMenu from '@baserow/modules/dashboard/components/widget/WidgetContextMenu'

export default {
  name: 'ChartWidget',
  components: { BaseChart, WidgetContextMenu },
  props: {
    dashboard: {
      type: Object,
      required: true,
    },
    widget: {
      type: Object,
      required: true,
    },
    storePrefix: {
      type: String,
      required: false,
      default: '',
    },
    loading: {
      type: Boolean,
      required: false,
      default: false,
    },
  },
  emits: ['delete-widget'],
  computed: {
    dataSource() {
      return this.$store.getters[
        `${this.storePrefix}dashboardApplication/getDataSourceById`
      ](this.widget.data_source_id)
    },
    dataForDataSource() {
      return this.$store.getters[
        `${this.storePrefix}dashboardApplication/getDataForDataSource`
      ](this.dataSource?.id)
    },
    isEditMode() {
      return this.$store.getters[
        `${this.storePrefix}dashboardApplication/isEditMode`
      ]
    },
    chartOption() {
      const result = this.dataForDataSource?.result || []
      const chartType = this.widget.chart_type || 'bar'
      if (chartType === 'bar') {
        const categories = [...new Set(result.map((r) => r.category))]
        const seriesValues = [
          ...new Set(result.map((r) => r.series).filter(Boolean)),
        ]
        if (seriesValues.length > 0) {
          return {
            tooltip: { trigger: 'axis' },
            legend: {},
            xAxis: { type: 'category', data: categories },
            yAxis: { type: 'value' },
            series: seriesValues.map((s) => ({
              type: 'bar',
              name: s,
              data: categories.map(
                (c) =>
                  result.find((r) => r.category === c && r.series === s)
                    ?.value ?? 0
              ),
            })),
          }
        }
        return {
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: result.map((r) => r.category) },
          yAxis: { type: 'value' },
          series: [{ type: 'bar', data: result.map((r) => r.value) }],
        }
      }
      // line and scatter
      if (chartType === 'line' || chartType === 'scatter') {
        const categories = [...new Set(result.map((r) => r.category))]
        const seriesValues = [
          ...new Set(result.map((r) => r.series).filter(Boolean)),
        ]
        const buildSeries = (type) =>
          seriesValues.length > 0
            ? seriesValues.map((s) => ({
                type,
                name: s,
                data: categories.map(
                  (c) =>
                    result.find((r) => r.category === c && r.series === s)
                      ?.value ?? null
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
      // pie and doughnut
      const seriesItem = {
        type: 'pie',
        data: result.map((r) => ({ name: r.category, value: r.value })),
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
      return !!this.dataForDataSource?._error
    },
  },
}
</script>
