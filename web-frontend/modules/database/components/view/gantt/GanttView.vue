<template>
  <div class="gantt-view">
    <template v-if="startDateField && endDateField">
      <div class="gantt-view__main">
        <div ref="ganttHost" class="gantt-view__host"></div>
      </div>
      <!--
        Story 3.9 draw affordance. Frappe Gantt is `readonly` (no lib draw
        handle — drag is 3.10), so the explicit predecessor picker is the v1
        way to draw an edge. It targets the currently-open task row and lists
        every existing predecessor (removable) plus the other scheduled rows as
        candidates. Selecting a candidate creates a `predecessor → open row`
        edge through the store's optimistic action.
      -->
      <div v-if="openRow" class="gantt-view__dependencies">
        <div class="gantt-view__dependencies-header">
          {{ $t('ganttView.predecessorsTitle') }}
        </div>
        <ul
          v-if="openRowPredecessors.length"
          class="gantt-view__dependencies-list"
        >
          <li
            v-for="item in openRowPredecessors"
            :key="item.dependency.id"
            class="gantt-view__dependencies-item"
          >
            <span class="gantt-view__dependencies-name">{{ item.name }}</span>
            <a
              v-if="canEditDependencies"
              class="gantt-view__dependencies-remove"
              @click="removeDependency(item.dependency)"
            >
              <i class="iconoir-cancel"></i>
            </a>
          </li>
        </ul>
        <p v-else class="gantt-view__dependencies-empty">
          {{ $t('ganttView.noPredecessors') }}
        </p>
        <Dropdown
          v-if="canEditDependencies && availablePredecessorRows.length"
          :value="null"
          class="gantt-view__dependencies-add"
          :show-search="true"
          @input="addPredecessor($event)"
        >
          <DropdownItem
            v-for="candidate in availablePredecessorRows"
            :key="candidate.id"
            :name="rowName(candidate)"
            :value="candidate.id"
          ></DropdownItem>
        </Dropdown>
      </div>
      <div v-if="unscheduledRows.length > 0" class="gantt-view__unscheduled">
        <div class="gantt-view__unscheduled-header">
          {{ $t('ganttView.unscheduled') }}
          <span class="gantt-view__unscheduled-count">{{
            unscheduledRows.length
          }}</span>
        </div>
        <div class="gantt-view__unscheduled-cards">
          <RowCard
            v-for="row in unscheduledRows"
            :key="'unscheduled-' + row.id"
            :fields="cardFields"
            :row="row"
            :workspace-id="database.workspace.id"
            :cover-image-field="coverImageField"
            class="gantt-view__card gantt-view__card--tray"
            @click="rowClick(row)"
          ></RowCard>
        </div>
      </div>
    </template>
    <div v-else class="gantt-view__empty">
      <p class="gantt-view__empty-text">
        {{ $t('ganttView.noDateFields') }}
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
    <Modal ref="rescheduleModal" @hidden="onRescheduleModalHidden">
      <h2 class="box__title">{{ $t('ganttView.rescheduleTitle') }}</h2>
      <p>
        {{
          $t('ganttView.rescheduleMessage', {
            count: pendingCascade ? pendingCascade.preview.cascade_count : 0,
          })
        }}
      </p>
      <div class="actions actions--right">
        <button
          class="button button--ghost"
          type="button"
          @click="declineCascade"
        >
          {{ $t('ganttView.rescheduleDecline') }}
        </button>
        <button class="button" type="button" @click="confirmCascade">
          {{ $t('ganttView.rescheduleConfirm') }}
        </button>
      </div>
    </Modal>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'

import moment from '@baserow/modules/core/moment'
import { notifyIf } from '@baserow/modules/core/utils/error'
import {
  sortFieldsByOrderAndIdFunction,
  filterVisibleFieldsFunction,
  filterHiddenFieldsFunction,
} from '@baserow/modules/database/utils/view'
import Modal from '@baserow/modules/core/components/Modal'
import RowCard from '@baserow/modules/database/components/card/RowCard'
import RowEditModal from '@baserow/modules/database/components/row/RowEditModal'
import viewHelpers from '@baserow/modules/database/mixins/viewHelpers'
import { populateRow } from '@baserow/modules/database/store/view/grid'
import { clone } from '@baserow/modules/core/utils/object'
// Reuse the core MIT Timeline (Story 3.6/3.7) pure partition + date-parse +
// date-shift helpers instead of forking a second copy — the scheduled/tray
// split, the user-timezone date parsing, and the whole-day shift discipline
// (date-only → `YYYY-MM-DD`, datetime → preserve `HH:mm`) are identical, only
// the bar layer differs. The cascade backend mirrors the same semantics.
import {
  partitionTimelineRows,
  rowDateRange,
  shiftDateValue,
} from '@baserow/modules/database/components/view/timeline/TimelineView'

// Lazy, cached-promise loaders mirroring `excel.js` so the heavy Frappe Gantt
// renderer (and its CSS) never lands on the landing-route bundle — it is only
// fetched the first time a Gantt view actually mounts. (NFR / SM-C3 lazy-load)
let ganttLibPromise
export const loadGantt = () => (ganttLibPromise ??= import('frappe-gantt'))
// The library's CSS lives at `frappe-gantt/dist/frappe-gantt.css`, but the
// package's `exports` map only exposes the `.` entry, so that subpath is
// unresolvable by Vite (Nuxt build + Vitest alike). We lazily import a vendored
// verbatim copy instead — it still lands only on the async Gantt chunk.
let ganttCssPromise
const loadGanttCss = () =>
  (ganttCssPromise ??= import('./frappe-gantt.vendor.css'))

// Maps the persisted `timescale` choice to the Frappe Gantt `view_mode` name
// (its accepted values are capitalised). Defaults to `Month` for any unknown
// value, mirroring the backend column default.
const VIEW_MODE_BY_TIMESCALE = {
  day: 'Day',
  week: 'Week',
  month: 'Month',
}

/**
 * Resolves a `timescale` choice (`day`/`week`/`month`) to the Frappe Gantt
 * `view_mode` name, defaulting to `Month` for any unknown value.
 */
export function ganttViewMode(timescale) {
  return VIEW_MODE_BY_TIMESCALE[timescale] || 'Month'
}

export default {
  name: 'GanttView',
  components: { RowCard, RowEditModal, Modal },
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
      // The live Frappe Gantt instance, created lazily in `mounted`. `null`
      // until the lib has loaded and the host element exists.
      ganttInstance: null,
      // Set in `beforeUnmount` so the async lib loader bails instead of
      // rendering into a host that is about to be (or already is) detached.
      isUnmounting: false,
      // Story 3.10 / AC #1: the in-flight cascade awaiting the author's
      // confirm/decline. Holds the moved predecessor, its computed new
      // start/end values + old values (for a predecessor-only write or a
      // revert), and the read-only preview payload (affected successors +
      // transitive count) used to populate the prompt. `null` when no prompt
      // is open.
      pendingCascade: null,
      // Guards `onRescheduleModalHidden`: a confirm/decline sets this so a
      // dismiss (escape/click-away) after a choice does not double-revert,
      // while an undecided dismiss rolls the optimistic bar back. (AC #5)
      cascadeResolved: true,
    }
  },
  computed: {
    ...mapGetters({
      row: 'rowModalNavigation/getRow',
    }),
    allRows() {
      return this.$store.getters[this.storePrefix + 'view/gantt/getRows']
    },
    fieldOptions() {
      return this.$store.getters[
        this.storePrefix + 'view/gantt/getAllFieldOptions'
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
    viewMode() {
      return ganttViewMode(this.timescale)
    },
    /**
     * The primary field of the table, used to label each Gantt bar. Falls back
     * to the first field when no field is flagged primary.
     */
    primaryField() {
      return (
        this.fields.find((field) => field.primary) || this.fields[0] || null
      )
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
    /**
     * Maps each scheduled row to a Frappe Gantt task. `start`/`end` are parsed
     * in the user's timezone (via the shared Timeline `rowDateRange`, never
     * `moment.utc`) and serialised to `YYYY-MM-DD` so a date-only value never
     * drifts a day. `progress` is 0 (no progress field in v1) and
     * `dependencies` is the 3.9 seam (see `dependenciesForRow`). (AC #2)
     */
    ganttTasks() {
      return this.scheduledRows.map((row) => {
        const { start, end } = rowDateRange(
          row,
          this.startDateField,
          this.endDateField
        )
        const isMilestone = start.format('YYYY-MM-DD') === end.format('YYYY-MM-DD')
        const classes = []
        if (isMilestone) classes.push('gantt-view__milestone')
        if (this.criticalTaskIds.includes(row.id)) classes.push('gantt-view__critical')
        if (this.conflictTaskIds.includes(row.id)) classes.push('gantt-view__conflict')
        return {
          id: String(row.id),
          name: this.rowName(row),
          start: start.format('YYYY-MM-DD'),
          end: end.format('YYYY-MM-DD'),
          progress: 0,
          dependencies: this.dependenciesForRow(row),
          custom_class: classes.join(' '),
        }
      })
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
      // Gantt reuses the row card for the tray; it has no dedicated cover field
      // of its own, so cards render without a cover image.
      return null
    },
    activeSearchTerm() {
      return this.$store.getters[
        `${this.storePrefix}view/gantt/getActiveSearchTerm`
      ]
    },
    /**
     * The table's `TaskDependency` edges from the store. `ganttTasks` reads
     * these via `dependenciesForRow`, so this computed sits in that reactive
     * chain and the existing `ganttTasks` watch repaints the connectors when an
     * edge is added or removed. (Story 3.9 AC #1)
     */
    dependencies() {
      return this.$store.getters[
        `${this.storePrefix}view/gantt/getDependencies`
      ]
    },
    criticalTaskIds() {
      return this.$store.getters[`${this.storePrefix}view/gantt/criticalTaskIds`]
    },
    conflictTaskIds() {
      return this.$store.getters[`${this.storePrefix}view/gantt/conflictTaskIds`]
    },
    /**
     * The row whose modal is currently open (the picker target), or null.
     */
    openRow() {
      return this.row
    },
    /**
     * Editing edges follows the same permission gate as editing a row value:
     * not read-only and the principal can update rows in this table/view.
     */
    canEditDependencies() {
      return (
        !this.readOnly &&
        (this.$hasPermission(
          'database.table.update_row',
          this.table,
          this.database.workspace.id
        ) ||
          this.$hasPermission(
            'database.table.view.update_row',
            this.view,
            this.database.workspace.id
          ))
      )
    },
    /**
     * The open row's predecessors as `{ dependency, name }` items, resolved
     * from the edges whose `successor_row_id` is the open row.
     */
    openRowPredecessors() {
      if (!this.openRow) {
        return []
      }
      return this.dependencies
        .filter((edge) => edge.successor_row_id === this.openRow.id)
        .map((edge) => {
          const predecessor = this.allRows.find(
            (r) => r.id === edge.predecessor_row_id
          )
          return {
            dependency: edge,
            name: predecessor
              ? this.rowName(predecessor)
              : `#${edge.predecessor_row_id}`,
          }
        })
    },
    /**
     * Candidate predecessors for the open row: every other scheduled row that
     * is not already a predecessor and is not the open row itself. The backend
     * is the cycle authority, so non-immediate cycles are still offered here and
     * rejected on create with a clear error.
     */
    availablePredecessorRows() {
      if (!this.openRow) {
        return []
      }
      const existing = new Set(
        this.openRowPredecessors.map(
          (item) => item.dependency.predecessor_row_id
        )
      )
      return this.scheduledRows.filter(
        (r) => r.id !== this.openRow.id && !existing.has(r.id)
      )
    },
    /**
     * Whether bars may be dragged/resized. Mirrors Timeline's `canDragBars`:
     * not read-only, both date fields set, and the principal can write values
     * to BOTH the start and end fields (a field-level permission, distinct from
     * the row-level edge gate `canEditDependencies`). When false the lib is
     * mounted `readonly` and no `on_date_change` fires. (AC #5)
     */
    canDragBars() {
      return (
        !this.readOnly &&
        !!this.startDateField &&
        !!this.endDateField &&
        [this.startDateField, this.endDateField].every((field) =>
          this.$registry.get('field', field.type).canWriteFieldValues(field)
        )
      )
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
    // Re-render the bars whenever the task set changes (rows added/removed,
    // dates edited, dependency edges resolved). The instance is reused and
    // refreshed rather than recreated.
    ganttTasks() {
      this.refreshGantt()
    },
    // Story 3.11: repaint critical-path / conflict classes whenever the CPM
    // result arrays change (no full gantt rebuild needed — DOM-only pass).
    criticalTaskIds() {
      this.$nextTick(() => this.markCriticalPath())
    },
    conflictTaskIds() {
      this.$nextTick(() => this.markCriticalPath())
    },
    // Switching zoom re-renders through the lib's own `change_view_mode`.
    viewMode(mode) {
      if (this.ganttInstance) {
        this.ganttInstance.change_view_mode(mode)
      }
    },
    // The host appears/disappears when the date fields are (un)configured; build
    // the instance the first time both are set.
    startDateField() {
      this.$nextTick(() => this.ensureGantt())
    },
    endDateField() {
      this.$nextTick(() => this.ensureGantt())
    },
  },
  mounted() {
    if (this.row !== null) {
      this.populateAndEditRow(this.row)
    }
    this.ensureGantt()
  },
  beforeUnmount() {
    // Leak guard: drop the instance and clear the host so the lib's internal
    // listeners and SVG are released when the view unmounts (mirrors the 3.7
    // `beforeUnmount` cleanup discipline). The flag also short-circuits any
    // in-flight `ensureGantt` lib load so it does not render into a dead host.
    this.isUnmounting = true
    this.destroyGantt()
  },
  methods: {
    /**
     * The label for a bar: the primary field value rendered through its field
     * type's human-readable formatter. Empty string when unresolved.
     */
    rowName(row) {
      const field = this.primaryField
      if (!field) {
        return ''
      }
      const value = row[`field_${field.id}`]
      const fieldType = this.$registry.get('field', field.type)
      return fieldType.toHumanReadableString(field, value) || ''
    },
    /**
     * The dependency edges for a row's task, as the comma-separated predecessor
     * id string Frappe Gantt expects. STORY 3.9 SEAM (now live): every edge
     * whose `successor_row_id` is this row contributes its `predecessor_row_id`
     * to the string the lib draws arrows from. Empty string when the row has no
     * predecessors. The render call shape is untouched. (AC #1, AC #3)
     */
    dependenciesForRow(row) {
      return this.dependencies
        .filter((edge) => edge.successor_row_id === row.id)
        .map((edge) => edge.predecessor_row_id)
        .join(',')
    },
    /**
     * Draws a `predecessor → open row` edge through the store's optimistic
     * action. A cycle/exists rejection rolls back the optimistic edge in the
     * store; here we translate the structured error into a clear toast naming
     * the cause. Guarded by `canEditDependencies` so a read-only/insufficient-
     * permission principal cannot mutate edges.
     */
    async addPredecessor(predecessorRowId) {
      if (!this.canEditDependencies || !this.openRow) {
        return
      }
      try {
        await this.$store.dispatch(
          this.storePrefix + 'view/gantt/createDependency',
          {
            viewId: this.view.id,
            predecessorRowId,
            successorRowId: this.openRow.id,
          }
        )
      } catch (error) {
        if (
          error.handler &&
          error.handler.code === 'ERROR_TASK_DEPENDENCY_CYCLE'
        ) {
          this.$store.dispatch('toast/error', {
            title: this.$t('ganttView.cycleRejectedTitle'),
            message: this.$t('ganttView.cycleRejectedMessage'),
          })
        } else {
          notifyIf(error, 'view')
        }
      }
    },
    /**
     * Removes an edge through the store's optimistic delete (restored on
     * failure). Guarded by `canEditDependencies`.
     */
    async removeDependency(dependency) {
      if (!this.canEditDependencies) {
        return
      }
      try {
        await this.$store.dispatch(
          this.storePrefix + 'view/gantt/deleteDependency',
          {
            viewId: this.view.id,
            dependencyId: dependency.id,
          }
        )
      } catch (error) {
        notifyIf(error, 'view')
      }
    },
    /**
     * Lazily builds the Frappe Gantt instance once both date fields are set and
     * the host element exists. Loads the lib + CSS on demand (never at module
     * top level). Idempotent: a no-op when an instance already exists.
     */
    async ensureGantt() {
      if (
        this.ganttInstance ||
        !this.startDateField ||
        !this.endDateField ||
        !this.$refs.ganttHost
      ) {
        return
      }
      const [{ default: Gantt }] = await Promise.all([
        loadGantt(),
        loadGanttCss(),
      ])
      // The component may have unmounted (or the host vanished) while the lib
      // was loading; bail rather than render into a detached node.
      if (this.isUnmounting || !this.$refs.ganttHost) {
        return
      }
      this.ganttInstance = new Gantt(this.$refs.ganttHost, this.ganttTasks, {
        view_mode: this.viewMode,
        date_format: 'YYYY-MM-DD',
        // Story 3.10: bars are draggable/resizable when the principal may write
        // both date fields (`canDragBars`); otherwise the view stays render-only
        // exactly as in 3.8. `readonly_progress` is always on — there is no
        // progress field in v1, so the progress handle must never appear even
        // when dates are editable. `on_date_change` fires once on pointer
        // release with the moved bar's new start/end Date objects. (AC #5)
        readonly: !this.canDragBars,
        readonly_progress: true,
        on_date_change: (task, start, end) =>
          this.onBarDateChange(task, start, end),
        infinite_padding: false,
        popup_on: 'click',
        // Returning `false` suppresses the lib's own popup; the side effect
        // opens the Baserow row modal instead (mirrors Timeline's `rowClick`).
        popup: ({ task }) => {
          this.openTaskRow(task)
          return false
        },
      })
      this.$nextTick(() => {
        this.markViolatedConnectors()
        this.markCriticalPath()
      })
    },
    /**
     * Re-renders the existing instance with the current task set, building it
     * first if it does not yet exist.
     */
    refreshGantt() {
      if (!this.ganttInstance) {
        this.ensureGantt()
        return
      }
      this.ganttInstance.refresh(this.ganttTasks)
      this.$nextTick(() => {
        this.markViolatedConnectors()
        this.markCriticalPath()
      })
    },
    /**
     * Tears down the instance and empties the host node so the per-instance SVG
     * and the bar-level listeners (which live on the host's children) are
     * released across unmount.
     *
     * Known limitation: Frappe Gantt 1.2.2 exposes no `destroy()` and attaches
     * one anonymous `document` `mouseup` listener per instance in
     * `bind_bar_events` (not gated by the `readonly` option), which cannot be
     * removed without a lib reference. Re-opening a Gantt view therefore leaks a
     * single dead document listener each time. Story 3.10 wires the drag write
     * path on top of the same lib version, so the pre-existing leak is unchanged
     * — not worsened: the write path adds no listeners of its own, it only reads
     * the lib's `on_date_change` callback. A future lib bump with a teardown
     * hook should remove the listener; until then this empties the host so the
     * SVG and the bar-level (child) listeners are released on unmount.
     */
    destroyGantt() {
      this.ganttInstance = null
      const host = this.$refs.ganttHost
      if (host) {
        host.replaceChildren()
      }
    },
    /**
     * Opens the row modal for a clicked Gantt task. `task.id` is the row id as a
     * string; resolve it back to the row and reuse the standard modal path.
     */
    openTaskRow(task) {
      const row = this.allRows.find((r) => String(r.id) === String(task.id))
      if (row) {
        this.rowClick(row)
      }
    },
    /**
     * Story 3.10 / AC #1, #2, #4, #5. Fires once on bar drag/resize release.
     * Translates the lib's new start/end `Date`s into whole-day deltas, shifts
     * the two date-field values through the shared Timeline `shiftDateValue`
     * (date-only → `YYYY-MM-DD`, datetime → preserve `HH:mm`), then decides:
     *
     *   - no direct FS successor would be pushed → write the predecessor alone
     *     immediately, no prompt (AC #4: a move that violates nothing is silent);
     *   - at least one successor would start before the predecessor's new finish
     *     → ask the backend for the read-only cascade preview and open the
     *     confirm prompt. Nothing is written until the author confirms (AC #1).
     */
    async onBarDateChange(task, start, end) {
      if (!this.canDragBars) {
        return
      }
      const row = this.allRows.find((r) => String(r.id) === String(task.id))
      if (!row) {
        return
      }
      const { start: oldStart, end: oldEnd } = rowDateRange(
        row,
        this.startDateField,
        this.endDateField
      )
      const startDelta = moment(start)
        .startOf('day')
        .diff(oldStart.clone().startOf('day'), 'days')
      const endDelta = moment(end)
        .startOf('day')
        .diff(oldEnd.clone().startOf('day'), 'days')
      // Day-granular no-op (a click, or a sub-day jiggle the bars can't show):
      // snap back to the authoritative positions and do nothing.
      if (startDelta === 0 && endDelta === 0) {
        this.refreshGantt()
        return
      }
      const oldStartValue = row[`field_${this.startDateField.id}`]
      const oldEndValue = row[`field_${this.endDateField.id}`]
      const newStartValue = shiftDateValue(
        this.startDateField,
        oldStartValue,
        startDelta,
        'days'
      )
      const newEndValue = shiftDateValue(
        this.endDateField,
        oldEndValue,
        endDelta,
        'days'
      )
      const oldValues = {
        [`field_${this.startDateField.id}`]: oldStartValue,
        [`field_${this.endDateField.id}`]: oldEndValue,
      }
      const values = {
        [`field_${this.startDateField.id}`]: newStartValue,
        [`field_${this.endDateField.id}`]: newEndValue,
      }
      // A direct FS successor is pushed when its start falls before the
      // predecessor's NEW finish. Moving a predecessor earlier never violates,
      // so this naturally prompts only on forward moves.
      const newFinish = oldEnd.clone().add(endDelta, 'days')
      const wouldViolate = this.dependencies
        .filter((edge) => edge.predecessor_row_id === row.id)
        .some((edge) => {
          const successor = this.allRows.find(
            (r) => r.id === edge.successor_row_id
          )
          if (!successor) {
            return false
          }
          const { start: successorStart } = rowDateRange(
            successor,
            this.startDateField,
            this.endDateField
          )
          return successorStart.isBefore(newFinish)
        })
      if (!wouldViolate) {
        await this.commitPredecessorOnly(row, values, oldValues)
        return
      }
      try {
        const preview = await this.$store.dispatch(
          this.storePrefix + 'view/gantt/previewCascade',
          {
            viewId: this.view.id,
            predecessorRowId: row.id,
            newStart: newStartValue,
            newEnd: newEndValue,
          }
        )
        this.cascadeResolved = false
        this.pendingCascade = {
          row,
          values,
          oldValues,
          newStart: newStartValue,
          newEnd: newEndValue,
          preview,
        }
        this.$refs.rescheduleModal.show()
      } catch (error) {
        notifyIf(error, 'view')
        this.refreshGantt()
      }
    },
    /**
     * Writes only the dragged predecessor's two date values, in a single
     * undoable step, through the buffered-rows store. On failure the optimistic
     * bar is rolled back to the store's authoritative position (AC #5).
     */
    async commitPredecessorOnly(row, values, oldValues) {
      try {
        await this.$store.dispatch(
          this.storePrefix + 'view/gantt/updateRowValues',
          {
            table: this.table,
            view: this.view,
            fields: this.fields,
            row,
            values,
            oldValues,
          }
        )
      } catch (error) {
        notifyIf(error, 'field')
        this.refreshGantt()
      }
    },
    /**
     * AC #2: the author confirmed the cascade. Commit it — the backend shifts
     * the predecessor + every transitive dependent atomically in one undoable
     * step and broadcasts one batch update, so the buffered-rows handler
     * repositions every bar. On error roll the optimistic bar back. (AC #5)
     */
    async confirmCascade() {
      const pending = this.pendingCascade
      if (!pending) {
        return
      }
      this.cascadeResolved = true
      this.$refs.rescheduleModal.hide()
      try {
        await this.$store.dispatch(
          this.storePrefix + 'view/gantt/applyCascade',
          {
            viewId: this.view.id,
            predecessorRowId: pending.row.id,
            newStart: pending.newStart,
            newEnd: pending.newEnd,
          }
        )
      } catch (error) {
        notifyIf(error, 'view')
        this.refreshGantt()
      } finally {
        this.pendingCascade = null
      }
    },
    /**
     * AC #4: the author declined the cascade — move the predecessor alone and
     * leave the dependents in place. The now-violated FS edges are re-derived on
     * the next dependency fetch and styled by `markViolatedConnectors`.
     */
    async declineCascade() {
      const pending = this.pendingCascade
      if (!pending) {
        return
      }
      this.cascadeResolved = true
      this.$refs.rescheduleModal.hide()
      await this.commitPredecessorOnly(
        pending.row,
        pending.values,
        pending.oldValues
      )
      await this.$store.dispatch(
        this.storePrefix + 'view/gantt/fetchDependencies',
        {
          viewId: this.view.id,
        }
      )
      this.pendingCascade = null
    },
    /**
     * The prompt was dismissed (escape / click-away) without a choice: treat it
     * as a cancel and snap the optimistic bar back to its authoritative
     * position, writing nothing. (AC #5)
     */
    onRescheduleModalHidden() {
      if (!this.cascadeResolved) {
        this.cascadeResolved = true
        this.pendingCascade = null
        this.refreshGantt()
      }
    },
    /**
     * AC #3: tag the SVG connectors of FS edges flagged `violated` (a dependent
     * that starts before its predecessor finishes) so the stylesheet can render
     * them in the warning treatment. Frappe Gantt keys each arrow with
     * `data-from`/`data-to` = the predecessor/successor task ids, so each edge
     * maps to exactly one connector. Re-applied after every (re)render.
     */
    markViolatedConnectors() {
      const host = this.$refs.ganttHost
      if (!host) {
        return
      }
      host
        .querySelectorAll('.arrow.gantt-view__arrow--violated')
        .forEach((arrow) =>
          arrow.classList.remove('gantt-view__arrow--violated')
        )
      this.dependencies
        .filter((edge) => edge.violated)
        .forEach((edge) => {
          const arrow = host.querySelector(
            `.arrow[data-from="${edge.predecessor_row_id}"][data-to="${edge.successor_row_id}"]`
          )
          if (arrow) {
            arrow.classList.add('gantt-view__arrow--violated')
          }
        })
    },
    /**
     * Story 3.11 / AC #2 & #3. Post-render DOM pass that adds/removes
     * `gantt-view__critical` and `gantt-view__conflict` classes on `.bar-wrapper`
     * elements so the stylesheet can repaint critical-path bars and conflict bars.
     * Mirrors `markViolatedConnectors` in structure. Called from `refreshGantt`
     * and `ensureGantt` via `$nextTick`, and from dedicated watchers on the two
     * CPM id arrays so changes take effect without a full gantt rebuild.
     */
    markCriticalPath() {
      const host = this.$refs.ganttHost
      if (!host) {
        return
      }
      // Clear previous state.
      host
        .querySelectorAll('.bar-wrapper.gantt-view__critical')
        .forEach((el) => el.classList.remove('gantt-view__critical'))
      host
        .querySelectorAll('.bar-wrapper.gantt-view__conflict')
        .forEach((el) => el.classList.remove('gantt-view__conflict'))
      this.criticalTaskIds.forEach((id) => {
        const bar = host.querySelector(`.bar-wrapper[data-id="${id}"]`)
        if (bar) bar.classList.add('gantt-view__critical')
      })
      this.conflictTaskIds.forEach((id) => {
        const bar = host.querySelector(`.bar-wrapper[data-id="${id}"]`)
        if (bar) bar.classList.add('gantt-view__conflict')
      })
    },
    async updateValue({ field, row, value, oldValue }) {
      try {
        await this.$store.dispatch(
          this.storePrefix + 'view/gantt/updateRowValue',
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
            this.storePrefix + 'view/gantt/refreshRowFromBackend',
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
