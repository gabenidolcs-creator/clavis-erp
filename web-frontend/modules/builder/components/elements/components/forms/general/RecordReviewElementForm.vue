<template>
  <form @submit.prevent>
    <FormGroup
      :label="$t('recordReviewElementForm.dataSource')"
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
  name: 'RecordReviewElementForm',
  components: { DataSourceDropdown },
  mixins: [elementForm],
  data() {
    return {
      allowedValues: ['data_source_id'],
      values: {
        data_source_id: null,
      },
    }
  },
}
</script>
