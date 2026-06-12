<template>
  <div class="chart-base">
    <component
      :is="vchart"
      v-if="loaded"
      :option="option"
      :autoresize="autoresize"
      :theme="theme || undefined"
    />
  </div>
</template>

<script>
export default {
  name: 'BaseChart',
  props: {
    option: {
      type: Object,
      required: true,
    },
    // 'bar' | 'line' | 'pie' | 'doughnut' | 'scatter'
    // doughnut is a PieChart variant — callers set option.series[].radius = ['40%', '70%']
    type: {
      type: String,
      default: 'bar',
    },
    autoresize: {
      type: Boolean,
      default: true,
    },
    theme: {
      type: String,
      default: null,
    },
  },
  data() {
    return {
      loaded: false,
      vchart: null,
    }
  },
  async mounted() {
    // Lazy-load ECharts — do NOT import at module level (bundle budget ≤400KB gzip SM-C3)
    const { default: VChart } = await import('vue-echarts')
    const { use } = await import('echarts/core')
    const { BarChart, LineChart, PieChart, ScatterChart } = await import(
      'echarts/charts'
    )
    const {
      GridComponent,
      TooltipComponent,
      LegendComponent,
      TitleComponent,
    } = await import('echarts/components')
    const { CanvasRenderer } = await import('echarts/renderers')

    // use() must be called before VChart renders; calling after mount silently fails
    use([
      CanvasRenderer,
      BarChart,
      LineChart,
      PieChart,
      ScatterChart,
      GridComponent,
      TooltipComponent,
      LegendComponent,
      TitleComponent,
    ])

    this.vchart = VChart
    this.loaded = true
  },
}
</script>

<style lang="scss">
.chart-base {
  width: 100%;
  height: 100%;
}
</style>
