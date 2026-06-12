<template>
  <form @submit.prevent>
    <FormSection
      :title="$t('groupedAggregateRowsDataSourceForm.data')"
      class="margin-bottom-2"
    >
      <FormGroup
        :label="$t('groupedAggregateRowsDataSourceForm.sourceFieldLabel')"
        class="margin-bottom-2"
        small-label
        required
        horizontal
        horizontal-narrow
      >
        <Dropdown
          v-model="computedTableId"
          :show-search="true"
          fixed-items
          :error="fieldHasErrors('table_id')"
        >
          <DropdownSection
            v-for="database in databases"
            :key="database.id"
            :title="`${database.name} (${database.id})`"
          >
            <DropdownItem
              v-for="table in database.tables"
              :key="table.id"
              :name="table.name"
              :value="table.id"
              :indented="true"
            >
              {{ table.name }}
            </DropdownItem>
          </DropdownSection>
        </Dropdown>
      </FormGroup>
      <FormGroup
        v-if="values.table_id && !fieldHasErrors('table_id')"
        :label="$t('groupedAggregateRowsDataSourceForm.viewFieldLabel')"
        class="margin-bottom-2"
        small-label
        horizontal
        horizontal-narrow
      >
        <Dropdown
          v-model="v$.values.view_id.$model"
          :show-search="false"
          fixed-items
          :disabled="fieldsLoading"
        >
          <DropdownItem
            :name="$t('groupedAggregateRowsDataSourceForm.notSelected')"
            :value="null"
            >{{ $t('groupedAggregateRowsDataSourceForm.notSelected') }}</DropdownItem
          >
          <DropdownItem
            v-for="view in tableViews"
            :key="view.id"
            :name="view.name"
            :value="view.id"
          >
            {{ view.name }}
          </DropdownItem>
        </Dropdown>
      </FormGroup>
      <FormGroup
        v-if="values.table_id && !fieldHasErrors('table_id')"
        class="margin-bottom-2"
        small-label
        :label="$t('groupedAggregateRowsDataSourceForm.groupByFieldLabel')"
        required
        horizontal
        horizontal-narrow
      >
        <Dropdown
          v-model="v$.values.group_by_field_id.$model"
          :disabled="tableFields.length === 0 || fieldsLoading"
          :error="fieldHasErrors('group_by_field_id')"
        >
          <DropdownItem
            v-for="field in tableFields"
            :key="field.id"
            :name="field.name"
            :value="field.id"
            :icon="fieldIconClass(field)"
          />
        </Dropdown>
      </FormGroup>
      <FormGroup
        v-if="values.table_id && !fieldHasErrors('table_id')"
        class="margin-bottom-2"
        small-label
        :label="$t('groupedAggregateRowsDataSourceForm.aggregationTypeLabel')"
        required
        horizontal
        horizontal-narrow
      >
        <Dropdown
          v-model="v$.values.aggregation_type.$model"
          :error="fieldHasErrors('aggregation_type')"
          :disabled="fieldsLoading"
        >
          <DropdownItem
            v-for="(label, key) in aggregationTypeChoices"
            :key="key"
            :name="label"
            :value="key"
          />
        </Dropdown>
      </FormGroup>
      <FormGroup
        v-if="values.table_id && !fieldHasErrors('table_id') && values.aggregation_type !== 'count'"
        class="margin-bottom-2"
        small-label
        :label="$t('groupedAggregateRowsDataSourceForm.valueFieldLabel')"
        required
        horizontal
        horizontal-narrow
      >
        <Dropdown
          v-model="v$.values.value_field_id.$model"
          :disabled="tableFields.length === 0 || fieldsLoading"
          :error="fieldHasErrors('value_field_id')"
        >
          <DropdownItem
            v-for="field in tableFields"
            :key="field.id"
            :name="field.name"
            :value="field.id"
            :icon="fieldIconClass(field)"
          />
        </Dropdown>
      </FormGroup>
      <FormGroup
        v-if="values.table_id && !fieldHasErrors('table_id')"
        class="margin-bottom-2"
        small-label
        :label="$t('groupedAggregateRowsDataSourceForm.seriesFieldLabel')"
        horizontal
        horizontal-narrow
      >
        <Dropdown
          v-model="v$.values.series_field_id.$model"
          :disabled="tableFields.length === 0 || fieldsLoading"
        >
          <DropdownItem
            :name="$t('groupedAggregateRowsDataSourceForm.notSelected')"
            :value="null"
          >
            {{ $t('groupedAggregateRowsDataSourceForm.notSelected') }}
          </DropdownItem>
          <DropdownItem
            v-for="field in tableFields"
            :key="field.id"
            :name="field.name"
            :value="field.id"
            :icon="fieldIconClass(field)"
          />
        </Dropdown>
      </FormGroup>
    </FormSection>
  </form>
</template>

<script>
import { useVuelidate } from '@vuelidate/core'
import form from '@baserow/modules/core/mixins/form'
import { required } from '@vuelidate/validators'
import tableFields from '@baserow/modules/database/mixins/tableFields'

const AGGREGATION_TYPES = ['count', 'sum', 'avg', 'min', 'max']

const includes = (array) => (value) => array.includes(value)

const requiredIfNotCount = (aggregationType) => (value) => {
  if (aggregationType === 'count') return true
  return value !== null && value !== undefined
}

export default {
  name: 'GroupedAggregateRowsDataSourceForm',
  mixins: [form, tableFields],
  props: {
    dashboard: {
      type: Object,
      required: true,
    },
    widget: {
      type: Object,
      required: true,
    },
    dataSource: {
      type: Object,
      required: true,
    },
    storePrefix: {
      type: String,
      required: false,
      default: '',
    },
  },
  setup() {
    return { v$: useVuelidate({ $lazy: true }) }
  },
  data() {
    return {
      allowedValues: [
        'table_id',
        'view_id',
        'group_by_field_id',
        'aggregation_type',
        'value_field_id',
        'series_field_id',
      ],
      values: {
        table_id: null,
        view_id: null,
        group_by_field_id: null,
        aggregation_type: 'count',
        value_field_id: null,
        series_field_id: null,
      },
      tableLoading: false,
      skipFirstValuesEmit: true,
      tableIdHasChanged: false,
    }
  },
  computed: {
    computedTableId: {
      get() {
        return this.v$.values.table_id.$model
      },
      set(tableId) {
        if (tableId !== this.v$.values.table_id.$model) {
          this.v$.values.table_id.$model = tableId
          this.tableIdHasChanged = true
          this.v$.values.view_id.$model = null
          this.v$.values.group_by_field_id.$model = null
          this.v$.values.value_field_id.$model = null
          this.v$.values.series_field_id.$model = null
        }
      },
    },
    integration() {
      return this.$store.getters[
        `${this.storePrefix}dashboardApplication/getIntegrationById`
      ](this.dataSource.integration_id)
    },
    databases() {
      return this.integration.context_data.databases
    },
    databaseSelected() {
      return this.databases.find((database) =>
        database.tables.some((table) => table.id === this.values.table_id)
      )
    },
    tables() {
      return this.databases.map((database) => database.tables).flat()
    },
    tableIds() {
      return this.tables.map((table) => table.id)
    },
    tableFieldIds() {
      return this.tableFields.map((field) => field.id)
    },
    tableViews() {
      return (
        this.databaseSelected?.views.filter(
          (view) => view.table_id === this.values.table_id
        ) || []
      )
    },
    aggregationTypeChoices() {
      return {
        count: this.$t('groupedAggregateRowsDataSourceForm.aggregationTypes.count'),
        sum: this.$t('groupedAggregateRowsDataSourceForm.aggregationTypes.sum'),
        avg: this.$t('groupedAggregateRowsDataSourceForm.aggregationTypes.avg'),
        min: this.$t('groupedAggregateRowsDataSourceForm.aggregationTypes.min'),
        max: this.$t('groupedAggregateRowsDataSourceForm.aggregationTypes.max'),
      }
    },
  },
  watch: {
    dataSource: {
      async handler() {
        this.setEmitValues(false)
        await this.reset(true)
        this.v$.$touch()
        await this.$nextTick()
        this.setEmitValues(true)
      },
      deep: true,
    },
    fieldsLoading(loading) {
      if (this.tableIdHasChanged && !loading) {
        this.tableIdHasChanged = false
      }
    },
    'values.aggregation_type'(newType) {
      if (newType === 'count') {
        this.v$.values.value_field_id.$model = null
      }
    },
  },
  mounted() {
    this.v$.$validate()
  },
  validations() {
    return {
      values: {
        table_id: {
          required,
          isValidTableId: (value) => includes(this.tableIds)(value),
        },
        view_id: {},
        group_by_field_id: {
          required,
          isValidFieldId: (value) => includes(this.tableFieldIds)(value),
        },
        aggregation_type: {
          required,
          isValidType: (value) => includes(AGGREGATION_TYPES)(value),
        },
        value_field_id: {
          requiredIfNotCount: requiredIfNotCount(this.values.aggregation_type),
        },
        series_field_id: {},
      },
    }
  },
  methods: {
    getTableId() {
      return this.values.table_id
    },
    fieldIconClass(field) {
      const fieldType = this.$registry.get('field', field.type)
      return fieldType.iconClass
    },
  },
}
</script>
