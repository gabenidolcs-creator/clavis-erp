<template>
  <ul v-if="!tableLoading" class="header__filter header__filter--full-width">
    <li class="header__filter-item">
      <a
        ref="dateFieldContextLink"
        class="header__filter-link"
        @click="
          $refs.dateFieldContext.toggle(
            $refs.dateFieldContextLink,
            'bottom',
            'left',
            4
          )
        "
      >
        <i class="header__filter-icon iconoir-calendar"></i>
        <span class="header__filter-name">{{
          dateFieldName || $t('calendarViewHeader.positionBy')
        }}</span>
      </a>
      <Context
        ref="dateFieldContext"
        class="calendar-view-header__date-context"
      >
        <div class="calendar-view-header__date-context-inner">
          <div class="calendar-view-header__date-section">
            <div class="calendar-view-header__date-label">
              {{ $t('calendarViewHeader.dateField') }}
            </div>
            <ChooseDateField
              :database="database"
              :table="table"
              :view="view"
              :fields="fields"
              :read-only="readOnly"
              :loading="updatingDateField"
              :value="view.date_field"
              @input="updateDateField($event)"
            ></ChooseDateField>
          </div>
          <div class="calendar-view-header__date-section">
            <div class="calendar-view-header__date-label">
              {{ $t('calendarViewHeader.endDateField') }}
            </div>
            <ChooseDateField
              :database="database"
              :table="table"
              :view="view"
              :fields="fields"
              :read-only="readOnly"
              :allow-empty="true"
              :loading="updatingEndDateField"
              :value="view.end_date_field"
              @input="updateEndDateField($event)"
            ></ChooseDateField>
          </div>
        </div>
      </Context>
    </li>
    <li class="header__filter-item">
      <RadioGroup
        :model-value="displayMode"
        type="button"
        :options="displayModeOptions"
        @input="updateDisplayMode($event)"
      ></RadioGroup>
    </li>
    <li class="header__filter-item">
      <a
        ref="customizeContextLink"
        class="header__filter-link"
        @click="
          $refs.customizeContext.toggle(
            $refs.customizeContextLink,
            'bottom',
            'left',
            4
          )
        "
      >
        <i class="header__filter-icon iconoir-settings"></i>
        <span class="header__filter-name">{{
          $t('calendarViewHeader.customizeCards')
        }}</span>
      </a>
      <ViewFieldsContext
        ref="customizeContext"
        :database="database"
        :view="view"
        :fields="fields"
        :field-options="fieldOptions"
        @update-all-field-options="updateAllFieldOptions"
        @update-field-options-of-field="updateFieldOptionsOfField"
        @update-order="orderFieldOptions"
      ></ViewFieldsContext>
    </li>
    <li class="header__filter-item header__filter-item--full-width">
      <ViewSearch
        :view="view"
        :fields="fields"
        :store-prefix="storePrefix"
        :always-hide-rows-not-matching-search="true"
        @refresh="$emit('refresh', $event)"
      ></ViewSearch>
    </li>
  </ul>
</template>

<script>
import { mapGetters, mapState } from 'vuex'

import { notifyIf } from '@baserow/modules/core/utils/error'
import ViewFieldsContext from '@baserow/modules/database/components/view/ViewFieldsContext'
import ViewSearch from '@baserow/modules/database/components/view/ViewSearch'
import ChooseDateField from '@baserow/modules/database/components/field/ChooseDateField'

export default {
  name: 'CalendarViewHeader',
  components: { ViewFieldsContext, ViewSearch, ChooseDateField },
  props: {
    database: {
      type: Object,
      required: true,
    },
    table: {
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
      required: true,
    },
    storePrefix: {
      type: String,
      required: true,
    },
  },
  emits: ['refresh'],
  data() {
    return {
      updatingDateField: false,
      updatingEndDateField: false,
    }
  },
  computed: {
    ...mapState({
      tableLoading: (state) => state.table.loading,
    }),
    ...mapGetters({}),
    fieldOptions() {
      return this.$store.getters[
        this.storePrefix + 'view/calendar/getAllFieldOptions'
      ]
    },
    displayMode() {
      return this.$store.getters[
        this.storePrefix + 'view/calendar/getDisplayMode'
      ]
    },
    displayModeOptions() {
      const { $i18n: i18n } = this.app || this
      return [
        { label: i18n.t('calendarViewHeader.month'), value: 'month' },
        { label: i18n.t('calendarViewHeader.week'), value: 'week' },
      ]
    },
    dateFieldName() {
      const fieldId = this.view.date_field
      if (!fieldId) {
        return null
      }
      const field = this.fields.find((f) => f.id === fieldId)
      return field ? field.name : null
    },
  },
  methods: {
    updateDisplayMode(mode) {
      this.$store.dispatch(
        this.storePrefix + 'view/calendar/setDisplayMode',
        mode
      )
    },
    async updateDateField(fieldId) {
      this.updatingDateField = true
      try {
        await this.$store.dispatch('view/update', {
          view: this.view,
          values: { date_field: fieldId },
          readOnly: this.readOnly,
        })
        this.$refs.dateFieldContext.hide()
      } catch (error) {
        notifyIf(error, 'view')
      } finally {
        this.updatingDateField = false
      }
    },
    async updateEndDateField(fieldId) {
      this.updatingEndDateField = true
      try {
        await this.$store.dispatch('view/update', {
          view: this.view,
          values: { end_date_field: fieldId },
          readOnly: this.readOnly,
        })
      } catch (error) {
        notifyIf(error, 'view')
      } finally {
        this.updatingEndDateField = false
      }
    },
    async updateAllFieldOptions({ newFieldOptions, oldFieldOptions }) {
      try {
        await this.$store.dispatch(
          this.storePrefix + 'view/calendar/updateAllFieldOptions',
          {
            newFieldOptions,
            oldFieldOptions,
            readOnly:
              this.readOnly ||
              !this.$hasPermission(
                'database.table.view.update_field_options',
                this.view,
                this.database.workspace.id
              ),
          }
        )
      } catch (error) {
        notifyIf(error, 'view')
      }
    },
    async updateFieldOptionsOfField({ field, values, oldValues }) {
      try {
        await this.$store.dispatch(
          this.storePrefix + 'view/calendar/updateFieldOptionsOfField',
          {
            field,
            values,
            oldValues,
            readOnly:
              this.readOnly ||
              !this.$hasPermission(
                'database.table.view.update_field_options',
                this.view,
                this.database.workspace.id
              ),
          }
        )
      } catch (error) {
        notifyIf(error, 'view')
      }
    },
    async orderFieldOptions({ order }) {
      try {
        await this.$store.dispatch(
          this.storePrefix + 'view/calendar/updateFieldOptionsOrder',
          {
            order,
            readOnly:
              this.readOnly ||
              !this.$hasPermission(
                'database.table.view.update_field_options',
                this.view,
                this.database.workspace.id
              ),
          }
        )
      } catch (error) {
        notifyIf(error, 'view')
      }
    },
  },
}
</script>
