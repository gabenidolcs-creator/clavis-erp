<template>
  <div class="metric-element">
    <p v-if="displayValue !== null" class="metric-element__value">
      {{ displayValue }}
    </p>
    <p
      v-else-if="elementContent && elementContent._error"
      class="metric-element__error"
    >
      {{ $t('metricElement.dataSourceError') }}
    </p>
    <p v-else class="metric-element__empty">
      {{ $t('metricElement.noData') }}
    </p>
  </div>
</template>

<script>
export default {
  name: 'MetricElement',
  props: {
    element: { type: Object, required: true },
    builder: { type: Object, required: true },
    page: { type: Object, required: true },
    mode: { type: String, required: true },
  },
  computed: {
    elementContent() {
      return this.$store.getters['elementContent/getElementContent'](
        this.element
      )
    },
    misconfigured() {
      const content = this.elementContent
      return !!content?._error || !this.element.data_source_id
    },
    dataSource() {
      if (!this.element.data_source_id) return null
      return this.$store.getters['dataSource/getPageDataSourceById'](
        this.page,
        this.element.data_source_id
      )
    },
    displayValue() {
      if (this.misconfigured) return null
      const content = this.elementContent
      if (!this.dataSource || content?.result === undefined) return null
      try {
        return this.$registry
          .get('service', this.dataSource.type)
          .getResult(this.dataSource, content)
      } catch {
        return null
      }
    },
  },
}
</script>
