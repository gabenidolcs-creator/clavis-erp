<template>
  <div>
    <slot v-if="canCreateDateField || dateFields.length > 0"></slot>
    <div v-else class="warning">
      {{ $t('chooseDateField.warningWhenNothingToChooseOrCreate') }}
    </div>

    <RadioGroup
      :model-value="value"
      vertical-layout
      :options="dateFieldsOptions"
      :disabled="loading || readOnly"
      @input="$emit('input', $event)"
    >
    </RadioGroup>

    <div v-if="canCreateDateField" class="margin-top-2">
      <span ref="createFieldContextLink">
        <ButtonText
          icon="iconoir-plus"
          class="choose-select-field__link margin-right-auto"
          @click="$refs.createFieldContext.toggle($refs.createFieldContextLink)"
        >
          {{ $t('chooseDateField.addDateField') }}
        </ButtonText></span
      >

      <CreateFieldContext
        ref="createFieldContext"
        :table="table"
        :view="view"
        :forced-type="dateFieldType"
        :all-fields-in-table="fields"
        :database="database"
        @field-created="$event.callback()"
      ></CreateFieldContext>
    </div>
  </div>
</template>

<script>
import CreateFieldContext from '@baserow/modules/database/components/field/CreateFieldContext'

export default {
  name: 'ChooseDateField',
  components: { CreateFieldContext },
  props: {
    table: {
      type: Object,
      required: true,
    },
    database: {
      type: Object,
      required: true,
    },
    view: {
      type: Object,
      required: true,
    },
    fields: {
      type: Array,
      required: true,
    },
    readOnly: {
      type: Boolean,
      required: false,
      default: false,
    },
    // Allows an empty option so the chooser can also clear the optional end
    // date field.
    allowEmpty: {
      type: Boolean,
      required: false,
      default: false,
    },
    value: {
      required: true,
      validator() {
        return true
      },
    },
    loading: {
      type: Boolean,
      required: false,
      default: false,
    },
  },
  emits: ['input'],

  computed: {
    canCreateDateField() {
      return (
        !this.readOnly &&
        this.$hasPermission(
          'database.table.create_field',
          this.table,
          this.database.workspace.id
        )
      )
    },
    dateFieldType() {
      return 'date'
    },
    /**
     * Only fields that can represent a date can position rows on the calendar.
     * The capability is read from the field type registry so date-like formula
     * fields are included alongside plain date fields, matching the backend
     * `can_represent_date` check.
     */
    dateFields() {
      return this.fields.filter((field) => {
        const fieldType = this.$registry.get('field', field.type)
        return fieldType.canRepresentDate(field)
      })
    },
    dateFieldsOptions() {
      const options = this.dateFields.map((dateField) => {
        return {
          label: dateField.name,
          value: dateField.id,
        }
      })
      if (this.allowEmpty) {
        options.unshift({
          label: this.$t('chooseDateField.none'),
          value: null,
        })
      }
      return options
    },
  },
}
</script>
