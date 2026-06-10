<template>
  <div class="timeline-view">
    <template v-if="startDateField && endDateField">
      <div class="timeline-view__main">
        <div class="timeline-view__axis">
          <div
            v-for="tick in ticks"
            :key="tick.key"
            class="timeline-view__tick"
            :style="{ left: tick.left + '%', width: tick.width + '%' }"
          >
            <span class="timeline-view__tick-label">{{ tick.label }}</span>
          </div>
        </div>
        <div class="timeline-view__rows">
          <div
            v-for="row in scheduledRows"
            :key="'lane-' + row.id"
            class="timeline-view__row"
          >
            <div
              class="timeline-view__bar"
              :style="barStyle(row)"
              @click="rowClick(row)"
            >
              <RowCard
                :fields="cardFields"
                :row="row"
                :workspace-id="database.workspace.id"
                :cover-image-field="coverImageField"
                class="timeline-view__card"
              ></RowCard>
            </div>
          </div>
        </div>
      </div>
      <div v-if="unscheduledRows.length > 0" class="timeline-view__unscheduled">
        <div class="timeline-view__unscheduled-header">
          {{ $t('timelineView.unscheduled') }}
          <span class="timeline-view__unscheduled-count">{{
            unscheduledRows.length
          }}</span>
        </div>
        <div class="timeline-view__unscheduled-cards">
          <RowCard
            v-for="row in unscheduledRows"
            :key="'unscheduled-' + row.id"
            :fields="cardFields"
            :row="row"
            :workspace-id="database.workspace.id"
            :cover-image-field="coverImageField"
            class="timeline-view__card timeline-view__card--tray"
            @click="rowClick(row)"
          ></RowCard>
        </div>
      </div>
    </template>
    <div v-else class="timeline-view__empty">
      <p class="timeline-view__empty-text">
        {{ $t('timelineView.noDateFields') }}
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
  getUserTimeZone,
  getCapitalizedMonthName,
} from '@baserow/modules/core/utils/date'
import RowCard from '@baserow/modules/database/components/card/RowCard'
import RowEditModal from '@baserow/modules/database/components/row/RowEditModal'
import viewHelpers from '@baserow/modules/database/mixins/viewHelpers'
import { populateRow } from '@baserow/modules/database/store/view/grid'
import { clone } from '@baserow/modules/core/utils/object'

// Maps the persisted `timescale` choice to the moment unit used for all axis
// and bar arithmetic. ISO week is used for `week` so weeks start on Monday,
// matching the calendar grid.
const UNIT_BY_TIMESCALE = {
  day: 'day',
  week: 'isoWeek',
  month: 'month',
}

/**
 * Resolves a `timescale` choice (`day`/`week`/`month`) to its moment unit,
 * defaulting to `month` for any unknown value.
 */
export function timelineUnit(timescale) {
  return UNIT_BY_TIMESCALE[timescale] || 'month'
}

/**
 * Parses a raw date/datetime cell value into a moment in the user's timezone,
 * or `null` when empty/unparseable. Positioning is always done in the user's
 * local frame (never `moment.utc`) so a bar lands on the day the user sees,
 * mirroring the calendar's `rowDateKey` choice.
 */
export function parseTimelineValue(value) {
  if (value === null || value === undefined || value === '') {
    return null
  }
  const parsed = moment.tz(value, getUserTimeZone())
  return parsed.isValid() ? parsed : null
}

/**
 * Returns the parsed `{ start, end }` moments for a row given the configured
 * start and end date fields. Either side is `null` when its cell is empty or
 * unparseable.
 */
export function rowDateRange(row, startDateField, endDateField) {
  const start = startDateField
    ? parseTimelineValue(row[`field_${startDateField.id}`])
    : null
  const end = endDateField
    ? parseTimelineValue(row[`field_${endDateField.id}`])
    : null
  return { start, end }
}

/**
 * Partitions rows into `scheduled` (renderable as a bar) and `unscheduled`
 * (shown in the tray). A row is scheduled ONLY when BOTH its start and end
 * date values are present and parseable (AC #2). A row missing either value is
 * not a malformed bar — it goes to the tray (AC #4). This is the delta from the
 * calendar, which partitioned on a single date field.
 */
export function partitionTimelineRows(rows, startDateField, endDateField) {
  const scheduled = []
  const unscheduled = []
  for (const row of rows) {
    if (row === null || row === undefined) {
      continue
    }
    const { start, end } = rowDateRange(row, startDateField, endDateField)
    if (start !== null && end !== null) {
      scheduled.push(row)
    } else {
      unscheduled.push(row)
    }
  }
  return { scheduled, unscheduled }
}

/**
 * Computes the inclusive axis range `[rangeStart, rangeEnd]` (both moments) for
 * a set of scheduled rows, snapped outward to the timescale unit boundaries
 * (`startOf`/`endOf` of `day`/`isoWeek`/`month`). When there are no scheduled
 * rows it falls back to a sensible window around `today`. An end that precedes
 * its start is clamped to the start so a reversed row never widens the range.
 */
export function computeAxisRange(
  scheduledRows,
  startDateField,
  endDateField,
  timescale,
  today
) {
  const unit = timelineUnit(timescale)
  let min = null
  let max = null

  for (const row of scheduledRows) {
    const { start, end } = rowDateRange(row, startDateField, endDateField)
    if (start === null || end === null) {
      continue
    }
    // Clamp a reversed row so it spans a single unit at its start.
    const effectiveEnd = end.isBefore(start) ? moment(start) : end
    if (min === null || start.isBefore(min)) {
      min = moment(start)
    }
    if (max === null || effectiveEnd.isAfter(max)) {
      max = moment(effectiveEnd)
    }
  }

  if (min === null || max === null) {
    // Empty fallback: a small window centred on today.
    const base = today ? moment(today) : moment.tz(getUserTimeZone())
    min = moment(base)
    max = moment(base)
  }

  return {
    rangeStart: min.startOf(unit),
    rangeEnd: max.endOf(unit),
  }
}

/**
 * The number of whole timescale units spanned by `[rangeStart, rangeEnd]`
 * inclusive. Always at least 1 so downstream fraction maths never divides by
 * zero.
 */
export function axisUnitCount(rangeStart, rangeEnd, timescale) {
  const unit = timelineUnit(timescale)
  const startSnap = moment(rangeStart).startOf(unit)
  const endSnap = moment(rangeEnd).startOf(unit)
  return Math.max(1, endSnap.diff(startSnap, unit) + 1)
}

/**
 * Builds the axis ticks (one per timescale unit) as `{ key, label, left, width }`
 * where `left`/`width` are percentages of the full axis. Labels are the day +
 * short month for `day`, the ISO-week start date for `week`, and the
 * capitalised month name for `month`.
 */
export function computeTicks(rangeStart, rangeEnd, timescale) {
  const unit = timelineUnit(timescale)
  const total = axisUnitCount(rangeStart, rangeEnd, timescale)
  const width = 100 / total
  const ticks = []
  const cursor = moment(rangeStart).startOf(unit)
  for (let i = 0; i < total; i++) {
    let label
    if (timescale === 'day') {
      label = cursor.format('D MMM')
    } else if (timescale === 'week') {
      label = cursor.format('D MMM')
    } else {
      label = getCapitalizedMonthName(cursor)
    }
    ticks.push({
      key: cursor.format('YYYY-MM-DD'),
      label,
      left: i * width,
      width,
    })
    cursor.add(1, unit)
  }
  return ticks
}

/**
 * Pure bar geometry: maps a row's `[start, end]` onto the axis as
 * `{ left, width }` percentages. `offsetUnits` is how many whole units the bar
 * starts after `rangeStart`; `spanUnits` is the inclusive unit count of the bar
 * (so a single-unit row is `1`). A reversed row (`end < start`) is clamped to a
 * 1-unit bar rather than throwing. Kept pure (no `this`) so Task 7 can assert
 * the arithmetic directly and Story 3.7 can reuse it for drag/resize maths.
 */
export function barGeometry(start, end, rangeStart, totalUnits, timescale) {
  const unit = timelineUnit(timescale)
  const startSnap = moment(start).startOf(unit)
  const rangeSnap = moment(rangeStart).startOf(unit)
  const offsetUnits = Math.max(0, startSnap.diff(rangeSnap, unit))

  let spanUnits
  if (end === null || end === undefined || moment(end).isBefore(start)) {
    spanUnits = 1
  } else {
    const endSnap = moment(end).startOf(unit)
    spanUnits = Math.max(1, endSnap.diff(startSnap, unit) + 1)
  }

  const total = Math.max(1, totalUnits)
  return {
    left: (offsetUnits / total) * 100,
    width: (spanUnits / total) * 100,
  }
}

export default {
  name: 'TimelineView',
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
    }
  },
  computed: {
    ...mapGetters({
      row: 'rowModalNavigation/getRow',
    }),
    allRows() {
      return this.$store.getters[this.storePrefix + 'view/timeline/getRows']
    },
    fieldOptions() {
      return this.$store.getters[
        this.storePrefix + 'view/timeline/getAllFieldOptions'
      ]
    },
    /**
     * The field whose value positions the left edge of each bar. Null until the
     * view has been configured with a start date field.
     */
    startDateField() {
      const fieldId = this.view.start_date_field
      if (!fieldId) {
        return null
      }
      return this.fields.find((field) => field.id === fieldId) || null
    },
    /**
     * The field whose value positions the right edge of each bar. Null until
     * the view has been configured with an end date field.
     */
    endDateField() {
      const fieldId = this.view.end_date_field
      if (!fieldId) {
        return null
      }
      return this.fields.find((field) => field.id === fieldId) || null
    },
    timescale() {
      return this.view.timescale || 'month'
    },
    today() {
      return moment.tz(getUserTimeZone())
    },
    partitioned() {
      if (!this.startDateField || !this.endDateField) {
        return { scheduled: [], unscheduled: [] }
      }
      return partitionTimelineRows(
        this.allRows,
        this.startDateField,
        this.endDateField
      )
    },
    scheduledRows() {
      return this.partitioned.scheduled
    },
    unscheduledRows() {
      return this.partitioned.unscheduled
    },
    axisRange() {
      return computeAxisRange(
        this.scheduledRows,
        this.startDateField,
        this.endDateField,
        this.timescale,
        this.today
      )
    },
    totalUnits() {
      return axisUnitCount(
        this.axisRange.rangeStart,
        this.axisRange.rangeEnd,
        this.timescale
      )
    },
    ticks() {
      return computeTicks(
        this.axisRange.rangeStart,
        this.axisRange.rangeEnd,
        this.timescale
      )
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
      // Timeline reuses the row card; it has no dedicated cover field of its
      // own, so cards render without a cover image.
      return null
    },
    activeSearchTerm() {
      return this.$store.getters[
        `${this.storePrefix}view/timeline/getActiveSearchTerm`
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
    /**
     * The inline style positioning a row's bar on the axis. Delegates to the
     * pure `barGeometry` helper so the arithmetic stays unit-testable.
     */
    barStyle(row) {
      const { start, end } = rowDateRange(
        row,
        this.startDateField,
        this.endDateField
      )
      const { left, width } = barGeometry(
        start,
        end,
        this.axisRange.rangeStart,
        this.totalUnits,
        this.timescale
      )
      return { left: `${left}%`, width: `${width}%` }
    },
    async updateValue({ field, row, value, oldValue }) {
      try {
        await this.$store.dispatch(
          this.storePrefix + 'view/timeline/updateRowValue',
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
            this.storePrefix + 'view/timeline/refreshRowFromBackend',
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
