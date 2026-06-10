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
        <div ref="rowsTrack" class="timeline-view__rows">
          <div
            v-for="row in scheduledRows"
            :key="'lane-' + row.id"
            class="timeline-view__row"
          >
            <div
              class="timeline-view__bar"
              :class="{
                'timeline-view__bar--draggable': canDragBars,
                'timeline-view__bar--dragging': row._.dragging,
              }"
              :style="barStyle(row)"
              @click="rowClick(row)"
              @mousedown="onBarMouseDown(row, 'move', $event)"
            >
              <div
                v-if="canDragBars"
                class="timeline-view__resize-handle timeline-view__resize-handle--start"
                @mousedown.stop.prevent="
                  onBarMouseDown(row, 'resize-start', $event)
                "
              ></div>
              <RowCard
                :fields="cardFields"
                :row="row"
                :workspace-id="database.workspace.id"
                :cover-image-field="coverImageField"
                class="timeline-view__card"
              ></RowCard>
              <div
                v-if="canDragBars"
                class="timeline-view__resize-handle timeline-view__resize-handle--end"
                @mousedown.stop.prevent="
                  onBarMouseDown(row, 'resize-end', $event)
                "
              ></div>
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

/**
 * Snaps a continuous horizontal pixel drag to a whole number of timescale
 * units. `axisWidthPx` is the pixel width of the bar track, `totalUnits` the
 * number of timescale units it spans, so `unitPx = axisWidthPx / totalUnits`
 * is the pixels-per-unit and `Math.round(deltaPx / unitPx)` is how many whole
 * units the cursor has travelled. Returns `0` (no-op) when either denominator
 * is non-positive so a missing track measurement never divides by zero. Kept
 * pure so the unit tests assert the maths without a DOM. (Story 3.7)
 */
export function pixelsToUnits(deltaPx, axisWidthPx, totalUnits) {
  if (axisWidthPx <= 0 || totalUnits <= 0) {
    return 0
  }
  const unitPx = axisWidthPx / totalUnits
  return Math.round(deltaPx / unitPx)
}

/**
 * The date-value builder for a move/resize: parses `oldValue` in the user's
 * local frame (the SAME frame `parseTimelineValue` positions bars in — never
 * `moment.utc`, so a shifted bar lands on the unit the user sees even across a
 * month/DST boundary), shifts it by `deltaUnits` of `unit`, then serialises it
 * back into the canonical store shape: a date-only field returns `YYYY-MM-DD`;
 * a datetime field returns a UTC ISO string preserving its original time-of-day
 * (only the date part moves). Returns `null` for an empty origin value (a
 * scheduled bar always has both dates, but guard anyway). The round-trip
 * invariant `parseTimelineValue(shiftDateValue(field, v, n, unit))` equals
 * `parseTimelineValue(v).add(n, unit)`. (Story 3.7, mirrors 3.5 dateValueForDay)
 */
export function shiftDateValue(field, oldValue, deltaUnits, unit) {
  const m = parseTimelineValue(oldValue)
  if (m === null) {
    return null
  }
  m.add(deltaUnits, unit)
  if (!field.date_include_time) {
    return m.format('YYYY-MM-DD')
  }
  return m.utc().format()
}

/**
 * Keeps a resize from inverting the bar by clamping `deltaUnits` so the dragged
 * endpoint never crosses the opposite one. The minimum bar is a single unit
 * (start and end snapped into the same unit), matching `barGeometry`'s
 * reversed-range → 1-unit clamp. `resize-start` may move the start right at most
 * onto the end's unit (positive delta clamped to the whole-unit span); dragging
 * it left to grow the bar is unbounded. `resize-end` is the mirror: it may move
 * the end left at most onto the start's unit (negative delta clamped to the
 * negated span); dragging right to grow is unbounded. Returns the clamped
 * integer delta (0 ⇒ the caller treats it as a no-op). (Story 3.7)
 */
export function clampResizeUnits(mode, oldStart, oldEnd, deltaUnits, unit) {
  const start = parseTimelineValue(oldStart)
  const end = parseTimelineValue(oldEnd)
  if (start === null || end === null) {
    return 0
  }
  const startSnap = moment(start).startOf(unit)
  const endSnap = moment(end).startOf(unit)
  // Whole units between start and end (>= 0 for a normal, non-reversed bar).
  const span = Math.max(0, endSnap.diff(startSnap, unit))
  if (mode === 'resize-start') {
    // New start at most onto the end's unit (delta <= span); growing left free.
    // `+ 0` normalises a `-0` result to `0`.
    return Math.min(deltaUnits, span) + 0
  }
  // resize-end: new end at most onto the start's unit (delta >= -span).
  return Math.max(deltaUnits, -span) + 0
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
      // While a pointer-drag is active this holds
      // `{ row, mode, startX, deltaUnits }` where
      // `mode ∈ { 'move', 'resize-start', 'resize-end' }`; `null` when idle.
      dragState: null,
      // Transient pixel offset applied to the dragged bar during a `move` for
      // visual feedback only — never written to the store. Cleared on release.
      dragVisualPx: 0,
      // Bar-track pixel width cached on `mousedown` (the px→unit denominator).
      axisWidthCache: 0,
      // Set true once a drag actually moves so the trailing `@click` does not
      // also open the row modal; consumed and cleared by `rowClick`.
      suppressClick: false,
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
    /**
     * Whether the bars expose a move/resize affordance. Mirrors
     * `KanbanView.canDrag` / Calendar `canDragDate`, but a timeline move writes
     * BOTH date cells so it requires BOTH `start_date_field` and
     * `end_date_field` to be present AND writable for the current user. A
     * read-only view, an unconfigured field, or either date field being
     * non-writable disables the affordance; Epic 1's field-permission layer
     * remains the authoritative server-side backstop. (AC #5)
     */
    canDragBars() {
      if (this.readOnly || !this.startDateField || !this.endDateField) {
        return false
      }
      return [this.startDateField, this.endDateField].every((field) =>
        this.$registry.get('field', field.type).canWriteFieldValues(field)
      )
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
  beforeUnmount() {
    // Leak guard: a drag in flight when the view unmounts would otherwise leave
    // the document-level listeners attached.
    window.removeEventListener('mousemove', this.onMouseMove)
    window.removeEventListener('mouseup', this.onMouseUp)
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
      const style = { left: `${left}%`, width: `${width}%` }
      // During an active `move` drag, translate the bar by the raw pixel delta
      // for live feedback. This is a local style only — the store value (and
      // therefore the committed position) is untouched until release.
      if (
        this.dragState &&
        this.dragState.mode === 'move' &&
        this.dragState.row &&
        this.dragState.row.id === row.id &&
        this.dragVisualPx !== 0
      ) {
        style.transform = `translateX(${this.dragVisualPx}px)`
      }
      return style
    },
    /**
     * The pixel width of the bar track — the denominator that converts a pixel
     * drag into whole timescale units. The axis and the rows share the same
     * horizontal extent; the rows track has zero horizontal padding.
     */
    axisWidthPx() {
      return this.$refs.rowsTrack?.clientWidth || 0
    },
    /**
     * Starts a pointer-drag on a bar. `mode` is `move` (bar body) or
     * `resize-start`/`resize-end` (an edge handle). Bails when the bars are not
     * draggable. Caches the track width, seeds `dragState`, flags the row as
     * dragging, and attaches the `document`-level move/up listeners so the drag
     * keeps tracking when the cursor leaves the bar. (AC #1, #2, #5)
     */
    onBarMouseDown(row, mode, event) {
      // Only a primary-button press starts a drag, and only when the bars are
      // draggable. A non-primary button or a non-draggable bar (read-only view
      // or a non-writable date field) attaches no listeners and prevents no
      // default — the click falls through to open the row as before.
      if (event.button !== 0 || !this.canDragBars) {
        return
      }
      // Suppress native text-selection/focus for the duration of a real drag
      // only (the bar's `@mousedown` carries no `.prevent` so a read-only bar's
      // default behaviour is untouched).
      event.preventDefault()
      this.axisWidthCache = this.axisWidthPx()
      this.dragState = { row, mode, startX: event.clientX, deltaUnits: 0 }
      this.dragVisualPx = 0
      this.suppressClick = false
      row._.dragging = true
      window.addEventListener('mousemove', this.onMouseMove)
      window.addEventListener('mouseup', this.onMouseUp)
    },
    /**
     * Tracks the cursor during a drag, converting the accumulated pixel delta
     * into whole timescale units. Stores the snapped `deltaUnits` on
     * `dragState` and (for a move) the raw pixel offset for the transient
     * visual. No request fires during the move. Once the drag actually moves a
     * unit, `suppressClick` is set so the trailing click does not open the row.
     */
    onMouseMove(event) {
      if (!this.dragState) {
        return
      }
      const deltaPx = event.clientX - this.dragState.startX
      const deltaUnits = pixelsToUnits(
        deltaPx,
        this.axisWidthCache,
        this.totalUnits
      )
      this.dragState.deltaUnits = deltaUnits
      if (this.dragState.mode === 'move') {
        this.dragVisualPx = deltaPx
      }
      if (deltaUnits !== 0) {
        this.suppressClick = true
      }
    },
    /**
     * Ends a drag: detaches the listeners, clears the drag state and the
     * transient offset, and commits when the cursor moved a non-zero number of
     * units. A zero-unit release (dropped where it started) is a no-op — no
     * request, no flicker (AC #1/#2). Re-checks `canDragBars` before committing
     * in case permission changed mid-drag. Move → atomic two-field commit;
     * resize → single-field commit.
     */
    onMouseUp() {
      window.removeEventListener('mousemove', this.onMouseMove)
      window.removeEventListener('mouseup', this.onMouseUp)
      const state = this.dragState
      this.dragState = null
      this.dragVisualPx = 0
      if (state && state.row) {
        state.row._.dragging = false
      }
      if (!state || !state.row || state.deltaUnits === 0) {
        return
      }
      if (!this.canDragBars) {
        return
      }
      if (state.mode === 'move') {
        this.onCommitMove(state.row, state.deltaUnits)
      } else {
        this.onCommitResize(state.row, state.mode, state.deltaUnits)
      }
    },
    /**
     * Commits a move: shifts BOTH date cells by the same delta (preserving the
     * span) and writes them in ONE `updateRowValues` (plural) dispatch so the
     * change is a single `batchUpdate` → one WebSocket broadcast (AC #3) → one
     * rollback unit (AC #4). The optimistic write re-positions the bar
     * reactively via the `barStyle` computed; a failure rolls both cells back
     * together and surfaces via `notifyIf`. (AC #1)
     */
    async onCommitMove(row, deltaUnits) {
      const unit = timelineUnit(this.timescale)
      const startField = this.startDateField
      const endField = this.endDateField
      const oldStart = row[`field_${startField.id}`]
      const oldEnd = row[`field_${endField.id}`]
      const newStart = shiftDateValue(startField, oldStart, deltaUnits, unit)
      const newEnd = shiftDateValue(endField, oldEnd, deltaUnits, unit)
      try {
        await this.$store.dispatch(
          this.storePrefix + 'view/timeline/updateRowValues',
          {
            table: this.table,
            view: this.view,
            fields: this.fields,
            row,
            values: { [startField.id]: newStart, [endField.id]: newEnd },
            oldValues: { [startField.id]: oldStart, [endField.id]: oldEnd },
          }
        )
      } catch (error) {
        notifyIf(error, 'field')
      }
    },
    /**
     * Commits a resize: clamps the delta so the bar never inverts (minimum
     * 1-unit bar), then writes ONLY the dragged endpoint through the existing
     * single-field `updateValue` path — the opposite cell is untouched (AC #2).
     * A clamp that collapses the move to zero units is a no-op.
     */
    async onCommitResize(row, mode, deltaUnits) {
      const unit = timelineUnit(this.timescale)
      const startField = this.startDateField
      const endField = this.endDateField
      const oldStart = row[`field_${startField.id}`]
      const oldEnd = row[`field_${endField.id}`]
      const clamped = clampResizeUnits(mode, oldStart, oldEnd, deltaUnits, unit)
      if (clamped === 0) {
        return
      }
      let field
      let value
      let oldValue
      if (mode === 'resize-start') {
        field = startField
        oldValue = oldStart
        value = shiftDateValue(startField, oldStart, clamped, unit)
      } else {
        field = endField
        oldValue = oldEnd
        value = shiftDateValue(endField, oldEnd, clamped, unit)
      }
      await this.updateValue({ field, row, value, oldValue })
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
      // A pointer-drag fires a trailing `click` after `mouseup`; if the drag
      // actually moved, swallow it so the modal does not open. A plain click
      // (no drag) leaves `suppressClick` false and opens the row as before.
      if (this.suppressClick) {
        this.suppressClick = false
        return
      }
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
