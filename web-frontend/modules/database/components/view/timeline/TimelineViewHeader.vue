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
          dateFieldsName || $t('timelineViewHeader.positionBy')
        }}</span>
      </a>
      <Context
        ref="dateFieldContext"
        class="timeline-view-header__date-context"
      >
        <div class="timeline-view-header__date-context-inner">
          <div class="timeline-view-header__date-section">
            <div class="timeline-view-header__date-label">
              {{ $t('timelineViewHeader.startDateField') }}
            </div>
            <ChooseDateField
              :database="database"
              :table="table"
              :view="view"
              :fields="fields"
              :read-only="readOnly"
              :loading="updatingStartDateField"
              :value="view.start_date_field"
              @input="updateStartDateField($event)"
            ></ChooseDateField>
          </div>
          <div class="timeline-view-header__date-section">
            <div class="timeline-view-header__date-label">
              {{ $t('timelineViewHeader.endDateField') }}
            </div>
            <ChooseDateField
              :database="database"
              :table="table"
              :view="view"
              :fields="fields"
              :read-only="readOnly"
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
        :model-value="timescale"
        type="button"
        :options="timescaleOptions"
        @input="updateTimescale($event)"
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
          $t('timelineViewHeader.customizeCards')
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
import { mapState } from 'vuex'

import { notifyIf } from '@baserow/modules/core/utils/error'
import ViewFieldsContext from '@baserow/modules/database/components/view/ViewFieldsContext'
import ViewSearch from '@baserow/modules/database/components/view/ViewSearch'
import ChooseDateField from '@baserow/modules/database/components/field/ChooseDateField'

export default {
  name: 'TimelineViewHeader',
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
      updatingStartDateField: false,
      updatingEndDateField: false,
    }
  },
  computed: {
    ...mapState({
      tableLoading: (state) => state.table.loading,
    }),
    fieldOptions() {
      return this.$store.getters[
        this.storePrefix + 'view/timeline/getAllFieldOptions'
      ]
    },
    timescale() {
      return this.view.timescale || 'month'
    },
    timescaleOptions() {
      const { $i18n: i18n } = this.app || this
      return [
        { label: i18n.t('timelineViewHeader.day'), value: 'day' },
        { label: i18n.t('timelineViewHeader.week'), value: 'week' },
        { label: i18n.t('timelineViewHeader.month'), value: 'month' },
      ]
    },
    dateFieldsName() {
      const startId = this.view.start_date_field
      const endId = this.view.end_date_field
      if (!startId || !endId) {
        return null
      }
      const start = this.fields.find((f) => f.id === startId)
      const end = this.fields.find((f) => f.id === endId)
      if (!start || !end) {
        return null
      }
      return `${start.name} → ${end.name}`
    },
  },
  methods: {
    /**
     * Persists the zoom level on the view through the generic `view/update`
     * action so it round-trips (AC #3). The persisted `timescale` column drives
     * the axis arithmetic in `TimelineView`.
     */
    async updateTimescale(timescale) {
      try {
        await this.$store.dispatch('view/update', {
          view: this.view,
          values: { timescale },
          readOnly: this.readOnly,
        })
      } catch (error) {
        notifyIf(error, 'view')
      }
    },
    async updateStartDateField(fieldId) {
      this.updatingStartDateField = true
      try {
        await this.$store.dispatch('view/update', {
          view: this.view,
          values: { start_date_field: fieldId },
          readOnly: this.readOnly,
        })
      } catch (error) {
        notifyIf(error, 'view')
      } finally {
        this.updatingStartDateField = false
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
          this.storePrefix + 'view/timeline/updateAllFieldOptions',
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
          this.storePrefix + 'view/timeline/updateFieldOptionsOfField',
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
          this.storePrefix + 'view/timeline/updateFieldOptionsOrder',
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
