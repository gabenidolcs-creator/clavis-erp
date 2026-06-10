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
  </div>
</template>

<script>
import { mapGetters } from 'vuex'

import { notifyIf } from '@baserow/modules/core/utils/error'
import {
  sortFieldsByOrderAndIdFunction,
  filterVisibleFieldsFunction,
  filterHiddenFieldsFunction,
} from '@baserow/modules/database/utils/view'
import RowCard from '@baserow/modules/database/components/card/RowCard'
import RowEditModal from '@baserow/modules/database/components/row/RowEditModal'
import viewHelpers from '@baserow/modules/database/mixins/viewHelpers'
import { populateRow } from '@baserow/modules/database/store/view/grid'
import { clone } from '@baserow/modules/core/utils/object'
// Reuse the core MIT Timeline (Story 3.6) pure partition + date-parse helpers
// instead of forking a second copy — the scheduled/tray split and the
// user-timezone date parsing are identical, only the bar layer differs.
import {
  partitionTimelineRows,
  rowDateRange,
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
      // The live Frappe Gantt instance, created lazily in `mounted`. `null`
      // until the lib has loaded and the host element exists.
      ganttInstance: null,
      // Set in `beforeUnmount` so the async lib loader bails instead of
      // rendering into a host that is about to be (or already is) detached.
      isUnmounting: false,
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
        return {
          id: String(row.id),
          name: this.rowName(row),
          start: start.format('YYYY-MM-DD'),
          end: end.format('YYYY-MM-DD'),
          progress: 0,
          dependencies: this.dependenciesForRow(row),
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
        // Render-only (AC #5): every editing affordance is disabled. The drag/
        // resize write path is Story 3.10's scope, so `on_date_change`/
        // `on_progress_change` stay unwired here.
        readonly: true,
        infinite_padding: false,
        popup_on: 'click',
        // Returning `false` suppresses the lib's own popup; the side effect
        // opens the Baserow row modal instead (mirrors Timeline's `rowClick`).
        popup: ({ task }) => {
          this.openTaskRow(task)
          return false
        },
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
     * single dead document listener each time. It is render-only and harmless in
     * 3.8; Story 3.10 (which wires the drag write path) should pin a lib version
     * with a teardown hook or patch this out then.
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
