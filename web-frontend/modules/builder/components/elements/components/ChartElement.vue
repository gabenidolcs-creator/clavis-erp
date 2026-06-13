<template>
  <div class="chart-element">
    <BaseChart
      v-if="!misconfigured && hasData"
      :option="chartOption"
      :type="element.chart_type"
    />
    <p v-else-if="misconfigured" class="chart-element__error">
      {{ $t('chartElement.dataSourceError') }}
    </p>
    <p v-else class="chart-element__empty">
      {{ $t('chartElement.noData') }}
    </p>
  </div>
</template>

<script>
import BaseChart from '@baserow/modules/dashboard/components/chart/BaseChart'

export default {
  name: 'ChartElement',
  components: { BaseChart },
  props: {
    element: { type: Object, required: true },
    builder: { type: Object, required: true },
    page: { type: Object, required: true },
    mode: { type: String, required: true },
  },
  computed: {
    elementContent() {
      return (
        this.$store.getters['elementContent/getElementContent'](this.element) ||
        []
      )
    },
    misconfigured() {
      const content = this.$store.getters['elementContent/getElementContent'](
        this.element
      )
      return !!content?._error
    },
    hasData() {
      return (
        Array.isArray(this.elementContent) && this.elementContent.length > 0
      )
    },
    chartOption() {
      const result = this.elementContent
      const chartType = this.element.chart_type || 'bar'

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
  },
}
</script>
