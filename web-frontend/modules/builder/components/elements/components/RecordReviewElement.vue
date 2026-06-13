<template>
  <div class="record-review-element">
    <p v-if="misconfigured" class="record-review-element__error">
      {{ $t('recordReviewElement.dataSourceError') }}
    </p>
    <p v-else-if="totalRows === 0" class="record-review-element__empty">
      {{ $t('recordReviewElement.noData') }}
    </p>
    <template v-else>
      <div class="record-review-element__fields">
        <div
          v-for="field in displayFields"
          :key="field.label"
          class="record-review-element__field"
        >
          <span class="record-review-element__label">{{ field.label }}</span>
          <span class="record-review-element__value">{{ field.value }}</span>
        </div>
      </div>
      <div class="record-review-element__nav">
        <button :disabled="!canPrev" @click="prev">
          {{ $t('recordReviewElement.previous') }}
        </button>
        <span class="record-review-element__counter">{{ rowCounterLabel }}</span>
        <button :disabled="!canNext" @click="next">
          {{ $t('recordReviewElement.next') }}
        </button>
      </div>
    </template>
  </div>
</template>

<script>
export default {
  name: 'RecordReviewElement',
  props: {
    element: { type: Object, required: true },
    builder: { type: Object, required: true },
    page: { type: Object, required: true },
    mode: { type: String, required: true },
  },
  data() {
    return {
      currentIndex: 0,
    }
  },
  computed: {
    elementContent() {
      const content = this.$store.getters['elementContent/getElementContent'](
        this.element
      )
      return Array.isArray(content) ? content : []
    },
    dataSource() {
      if (!this.element.data_source_id) return null
      return this.$store.getters['dataSource/getPageDataSourceById'](
        this.page,
        this.element.data_source_id
      )
    },
    misconfigured() {
      const raw = this.$store.getters['elementContent/getElementContent'](
        this.element
      )
      return !this.element.data_source_id || !!raw?._error
    },
    rows() {
      return this.elementContent
    },
    totalRows() {
      return this.rows.length
    },
    currentRow() {
      return this.rows[this.currentIndex] || null
    },
    canPrev() {
      return this.currentIndex > 0
    },
    canNext() {
      return this.currentIndex < this.totalRows - 1
    },
    schemaProperties() {
      if (!this.dataSource) return {}
      const serviceType = this.$registry.get('service', this.dataSource.type)
      const schema = serviceType.getDataSchema(this.dataSource)
      if (!schema) return {}
      return schema.type === 'array'
        ? schema.items?.properties || {}
        : schema.properties || {}
    },
    displayFields() {
      if (!this.currentRow) return []
      return Object.entries(this.currentRow).map(([key, value]) => {
        const schemaProp = this.schemaProperties[key]
        return {
          label: schemaProp?.title || key,
          value:
            value !== null && value !== undefined ? String(value) : '—',
        }
      })
    },
    rowCounterLabel() {
      return this.$t('recordReviewElement.rowCounter', {
        current: this.currentIndex + 1,
        total: this.totalRows,
      })
    },
  },
  watch: {
    'element.data_source_id'() {
      this.currentIndex = 0
    },
  },
  methods: {
    prev() {
      if (this.canPrev) this.currentIndex--
    },
    next() {
      if (this.canNext) this.currentIndex++
    },
  },
}
</script>
