<template>
  <div class="calendar-view">
    <template v-if="dateField">
      <div class="calendar-view__main">
        <div class="calendar-view__weekdays">
          <div
            v-for="weekDay in weekDays"
            :key="weekDay"
            class="calendar-view__weekday"
          >
            {{ weekDay }}
          </div>
        </div>
        <div
          class="calendar-view__grid"
          :class="`calendar-view__grid--${displayMode}`"
        >
          <div
            v-for="day in days"
            :key="day.key"
            class="calendar-view__day"
            :class="{
              'calendar-view__day--outside': !day.inCurrentPeriod,
              'calendar-view__day--today': day.isToday,
            }"
          >
            <div class="calendar-view__day-header">
              <span class="calendar-view__day-number">{{ day.label }}</span>
            </div>
            <div class="calendar-view__day-cards">
              <RowCard
                v-for="row in rowsByDay[day.key] || []"
                :key="'card-' + day.key + '-' + row.id"
                :fields="cardFields"
                :row="row"
                :workspace-id="database.workspace.id"
                :cover-image-field="coverImageField"
                class="calendar-view__card"
                @click="rowClick(row)"
              ></RowCard>
            </div>
          </div>
        </div>
      </div>
      <div v-if="unscheduledRows.length > 0" class="calendar-view__unscheduled">
        <div class="calendar-view__unscheduled-header">
          {{ $t('calendarView.unscheduled') }}
          <span class="calendar-view__unscheduled-count">{{
            unscheduledRows.length
          }}</span>
        </div>
        <div class="calendar-view__unscheduled-cards">
          <RowCard
            v-for="row in unscheduledRows"
            :key="'unscheduled-' + row.id"
            :fields="cardFields"
            :row="row"
            :workspace-id="database.workspace.id"
            :cover-image-field="coverImageField"
            class="calendar-view__card"
            @click="rowClick(row)"
          ></RowCard>
        </div>
      </div>
    </template>
    <div v-else class="calendar-view__empty">
      <p class="calendar-view__empty-text">
        {{ $t('calendarView.noDateField') }}
      </p>
    </div>
    <RowEditModal
      ref="rowEditModal"
      enable-navigation
      :database="database"
      :table="table"
      :view="view"
      :all-fields-in-table="fields"
      :primary-is-sortable="true"
      :visible-fields="cardFields"
      :hidden-fields="hiddenFields"
      :rows="allRows"
      :read-only="
        readOnly ||
        (!$hasPermission(
          'database.table.update_row',
          table,
          database.workspace.id
        ) &&
          !$hasPermission(
            'database.table.view.update_row',
            view,
            database.workspace.id
          ))
      "
      :show-hidden-fields="showHiddenFieldsInRowModal"
      @hidden="$emit('selected-row', undefined)"
      @toggle-hidden-fields-visibility="
        showHiddenFieldsInRowModal = !showHiddenFieldsInRowModal
      "
      @update="updateValue"
      @order-fields="orderFields"
      @toggle-field-visibility="toggleFieldVisibility"
      @field-updated="$emit('refresh', $event)"
      @field-deleted="$emit('refresh')"
      @field-created="showFieldCreated"
      @field-created-callback-done="afterFieldCreatedUpdateFieldOptions"
      @navigate-previous="$emit('navigate-previous', $event, activeSearchTerm)"
      @navigate-next="$emit('navigate-next', $event, activeSearchTerm)"
      @refresh-row="refreshRow"
    >
    </RowEditModal>
  </div>
</template>

<script>
import moment from '@baserow/modules/core/moment'
import { mapGetters } from 'vuex'

import { notifyIf } from '@baserow/modules/core/utils/error'
import {
  sortFieldsByOrderAndIdFunction,
  filterVisibleFieldsFunction,
  filterHiddenFieldsFunction,
} from '@baserow/modules/database/utils/view'
import {
  weekDaysShort,
  getMonthlyTimestamps,
  getUserTimeZone,
} from '@baserow/modules/core/utils/date'
import RowCard from '@baserow/modules/database/components/card/RowCard'
import RowEditModal from '@baserow/modules/database/components/row/RowEditModal'
import viewHelpers from '@baserow/modules/database/mixins/viewHelpers'
import { populateRow } from '@baserow/modules/database/store/view/grid'
import { clone } from '@baserow/modules/core/utils/object'

/**
 * Normalizes a raw date/datetime cell value to a `YYYY-MM-DD` day key, or
 * `null` when the value is empty or unparseable. This is what decides whether a
 * row is scheduled (placed on the grid) or shown in the unscheduled tray.
 */
export function rowDateKey(value) {
  if (value === null || value === undefined || value === '') {
    return null
  }
  const parsed = moment(value)
  if (!parsed.isValid()) {
    return null
  }
  return parsed.format('YYYY-MM-DD')
}

/**
 * Builds the ordered list of day cells for the calendar grid. In `month` mode
 * the range is the full monthly grid (leading/trailing days of the
 * surrounding weeks) derived from the shared `getMonthlyTimestamps` helper. In
 * `week` mode the range is the ISO week (Monday–Sunday) containing the
 * reference date. Each cell carries its `YYYY-MM-DD` key, the day-of-month
 * label, whether it belongs to the period being viewed, and whether it is
 * today. This is the only net-new concept compared to the kanban board.
 */
export function buildCalendarDays(referenceDate, mode, todayKey) {
  const reference = moment(referenceDate)
  let cursor
  let end
  let inPeriod

  if (mode === 'week') {
    cursor = moment(reference).startOf('isoWeek')
    end = moment(reference).endOf('isoWeek')
    inPeriod = () => true
  } else {
    const { fromTimestamp, toTimestamp } = getMonthlyTimestamps(reference)
    cursor = moment(fromTimestamp)
    // `toTimestamp` is exclusive (first day of the following row block).
    end = moment(toTimestamp).subtract(1, 'day')
    const referenceMonth = reference.month()
    inPeriod = (day) => day.month() === referenceMonth
  }

  const days = []
  const day = moment(cursor)
  while (day.isSameOrBefore(end, 'day')) {
    const key = day.format('YYYY-MM-DD')
    days.push({
      key,
      label: day.date(),
      inCurrentPeriod: inPeriod(day),
      isToday: key === todayKey,
    })
    day.add(1, 'day')
  }
  return days
}

/**
 * Buckets rows onto the visible day cells. A row with no (or an unparseable)
 * date value is returned in `unscheduled`. When an end-date field is configured
 * and holds a later date, the row spans every day cell between its start and
 * end (inclusive) that is visible in the current grid, so multi-day events show
 * on each of their days.
 */
export function groupRowsByDate(rows, dateField, endDateField, days) {
  const rowsByDay = {}
  const unscheduled = []
  const visibleKeys = new Set(days.map((d) => d.key))
  const startKey = `field_${dateField.id}`
  const endKey = endDateField ? `field_${endDateField.id}` : null

  for (const row of rows) {
    if (row === null || row === undefined) {
      continue
    }
    const start = rowDateKey(row[startKey])
    if (start === null) {
      unscheduled.push(row)
      continue
    }

    let end = start
    if (endKey !== null) {
      const rawEnd = rowDateKey(row[endKey])
      if (rawEnd !== null && rawEnd > start) {
        end = rawEnd
      }
    }

    const cursor = moment(start)
    const last = moment(end)
    let placed = false
    while (cursor.isSameOrBefore(last, 'day')) {
      const key = cursor.format('YYYY-MM-DD')
      if (visibleKeys.has(key)) {
        if (rowsByDay[key] === undefined) {
          rowsByDay[key] = []
        }
        rowsByDay[key].push(row)
        placed = true
      }
      cursor.add(1, 'day')
    }

    // A scheduled row whose whole span falls outside the visible grid is not an
    // unscheduled row; it simply is not shown this period.
    if (!placed) {
      continue
    }
  }

  return { rowsByDay, unscheduled }
}

export default {
  name: 'CalendarView',
  components: { RowCard, RowEditModal },
  mixins: [viewHelpers],
  props: {
    fields: {
      type: Array,
      required: true,
    },
    view: {
      type: Object,
      required: true,
    },
    table: {
      type: Object,
      required: true,
    },
    database: {
      type: Object,
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
  emits: ['navigate-next', 'navigate-previous', 'refresh', 'selected-row'],
  data() {
    return {
      showHiddenFieldsInRowModal: false,
      // The date the grid is centred on. Defaults to today in the user's
      // timezone.
      referenceDate: moment.tz(getUserTimeZone()).format('YYYY-MM-DD'),
    }
  },
  computed: {
    ...mapGetters({
      row: 'rowModalNavigation/getRow',
    }),
    allRows() {
      return this.$store.getters[this.storePrefix + 'view/calendar/getRows']
    },
    fieldOptions() {
      return this.$store.getters[
        this.storePrefix + 'view/calendar/getAllFieldOptions'
      ]
    },
    /**
     * The date field by which rows are positioned. Null when the view has not
     * been configured with a date field yet.
     */
    dateField() {
      const fieldId = this.view.date_field
      if (!fieldId) {
        return null
      }
      return this.fields.find((field) => field.id === fieldId) || null
    },
    endDateField() {
      const fieldId = this.view.end_date_field
      if (!fieldId) {
        return null
      }
      return this.fields.find((field) => field.id === fieldId) || null
    },
    todayKey() {
      return moment.tz(getUserTimeZone()).format('YYYY-MM-DD')
    },
    displayMode() {
      return this.$store.getters[
        this.storePrefix + 'view/calendar/getDisplayMode'
      ]
    },
    weekDays() {
      return weekDaysShort()
    },
    days() {
      return buildCalendarDays(
        this.referenceDate,
        this.displayMode,
        this.todayKey
      )
    },
    grouped() {
      if (!this.dateField) {
        return { rowsByDay: {}, unscheduled: [] }
      }
      return groupRowsByDate(
        this.allRows,
        this.dateField,
        this.endDateField,
        this.days
      )
    },
    rowsByDay() {
      return this.grouped.rowsByDay
    },
    unscheduledRows() {
      return this.grouped.unscheduled
    },
    /**
     * Returns the visible field objects in the right order.
     */
    cardFields() {
      const fieldOptions = this.fieldOptions
      return this.fields
        .filter(filterVisibleFieldsFunction(fieldOptions))
        .sort(sortFieldsByOrderAndIdFunction(fieldOptions))
    },
    hiddenFields() {
      const fieldOptions = this.fieldOptions
      return this.fields
        .filter(filterHiddenFieldsFunction(fieldOptions))
        .sort(sortFieldsByOrderAndIdFunction(fieldOptions))
    },
    coverImageField() {
      // Calendar reuses the row card; it has no dedicated cover field of its
      // own, so cards render without a cover image.
      return null
    },
    activeSearchTerm() {
      return this.$store.getters[
        `${this.storePrefix}view/calendar/getActiveSearchTerm`
      ]
    },
  },
  watch: {
    row: {
      deep: true,
      handler(row, oldRow) {
        if (this.$refs.rowEditModal) {
          if (
            (oldRow === null && row !== null) ||
            (oldRow && row && oldRow.id !== row.id)
          ) {
            this.populateAndEditRow(row)
          } else if (oldRow !== null && row === null) {
            this.$refs.rowEditModal.hide(false)
          }
        }
      },
    },
  },
  mounted() {
    if (this.row !== null) {
      this.populateAndEditRow(this.row)
    }
  },
  methods: {
    async updateValue({ field, row, value, oldValue }) {
      try {
        await this.$store.dispatch(
          this.storePrefix + 'view/calendar/updateRowValue',
          {
            table: this.table,
            view: this.view,
            fields: this.fields,
            row,
            field,
            value,
            oldValue,
          }
        )
      } catch (error) {
        notifyIf(error, 'field')
      }
    },
    rowClick(row) {
      this.$refs.rowEditModal.show(row.id)
      this.$emit('selected-row', row)
    },
    refreshRow(row) {
      if (this.refreshingRow) {
        return
      }
      this.refreshingRow = true

      this.$nextTick(async () => {
        try {
          await this.$store.dispatch(
            this.storePrefix + 'view/calendar/refreshRowFromBackend',
            { table: this.table, row }
          )
        } catch (error) {
          notifyIf(error, 'row')
        } finally {
          this.refreshingRow = false
        }
      })
    },
    showFieldCreated({ fetchNeeded, ...context }) {
      this.fieldCreated({ fetchNeeded, ...context })
      this.showHiddenFieldsInRowModal = true
    },
    populateAndEditRow(row) {
      const rowClone = populateRow(clone(row))
      this.$refs.rowEditModal.show(row.id, rowClone)
    },
  },
}
</script>
