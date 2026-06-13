<template>
  <form @submit.prevent>
    <FormGroup
      :label="$t('chartElementForm.chartType')"
      class="margin-bottom-2"
      small-label
      required
    >
      <Dropdown v-model="values.chart_type" :show-search="false">
        <DropdownItem
          v-for="ct in chartTypes"
          :key="ct.value"
          :name="ct.label"
          :value="ct.value"
        />
      </Dropdown>
    </FormGroup>
    <FormGroup
      :label="$t('chartElementForm.dataSource')"
      small-label
      class="margin-bottom-2"
    >
      <DataSourceDropdown v-model="values.data_source_id" small />
    </FormGroup>
  </form>
</template>

<script>
import elementForm from '@baserow/modules/builder/mixins/elementForm'
import DataSourceDropdown from '@baserow/modules/builder/components/dataSource/DataSourceDropdown'

export default {
  name: 'ChartElementForm',
  components: { DataSourceDropdown },
  mixins: [elementForm],
  data() {
    return {
      allowedValues: ['chart_type', 'data_source_id'],
      values: {
        chart_type: 'bar',
        data_source_id: null,
      },
    }
  },
  computed: {
    chartTypes() {
      return [
        { value: 'bar', label: this.$t('chartElementForm.bar') },
        { value: 'line', label: this.$t('chartElementForm.line') },
        { value: 'pie', label: this.$t('chartElementForm.pie') },
        { value: 'doughnut', label: this.$t('chartElementForm.doughnut') },
        { value: 'scatter', label: this.$t('chartElementForm.scatter') },
      ]
    },
  },
}
</script>
