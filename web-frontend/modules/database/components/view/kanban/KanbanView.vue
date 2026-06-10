<template>
  <div class="kanban-view">
    <template v-if="singleSelectField">
      <div class="kanban-view__columns">
        <div
          v-for="column in columns"
          :key="column.id === null ? 'uncategorized' : column.id"
          class="kanban-view__column"
          @dragover="onDragOver($event)"
          @drop="onDrop(column, $event)"
        >
          <div class="kanban-view__column-header">
            <span
              v-if="column.id !== null"
              class="kanban-view__column-label"
              :class="'background-color--' + column.color"
            >
              {{ column.label }}
            </span>
            <span v-else class="kanban-view__column-label">
              {{ $t('kanbanView.uncategorized') }}
            </span>
            <span class="kanban-view__column-count">{{
              column.rows.length
            }}</span>
          </div>
          <div class="kanban-view__cards">
            <RowCard
              v-for="row in column.rows"
              :key="'card-' + row.id"
              :fields="cardFields"
              :row="row"
              :workspace-id="database.workspace.id"
              :cover-image-field="coverImageField"
              :draggable="canDrag"
              class="kanban-view__card"
              :class="{
                'kanban-view__card--draggable': canDrag,
                'kanban-view__card--dragging': row._ && row._.dragging,
              }"
              @click="rowClick(row)"
              @dragstart="onDragStart(row, $event)"
              @dragend="onDragEnd(row)"
            ></RowCard>
          </div>
        </div>
      </div>
    </template>
    <div v-else class="kanban-view__empty">
      <p class="kanban-view__empty-text">
        {{ $t('kanbanView.noSingleSelectField') }}
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

/**
 * Buckets the given rows into columns derived from the grouping single-select
 * field's options, in option order, with a trailing "Uncategorized" column for
 * rows whose grouping value is null. This is the only net-new concept compared
 * to the gallery view; everything else is the card-view structure.
 */
export function groupRowsBySingleSelect(rows, singleSelectField) {
  const fieldKey = `field_${singleSelectField.id}`
  const options = singleSelectField.select_options || []

  const columns = options.map((option) => ({
    id: option.id,
    label: option.value,
    color: option.color,
    rows: [],
  }))
  const uncategorized = { id: null, label: null, color: null, rows: [] }

  const columnById = {}
  columns.forEach((column) => {
    columnById[column.id] = column
  })

  for (const row of rows) {
    // Skip slots that have not been fetched yet (null placeholders).
    if (row === null || row === undefined) {
      continue
    }
    const value = row[fieldKey]
    const optionId = value === null || value === undefined ? null : value.id
    const column =
      optionId !== null && columnById[optionId] !== undefined
        ? columnById[optionId]
        : uncategorized
    column.rows.push(row)
  }

  return [...columns, uncategorized]
}

export default {
  name: 'KanbanView',
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
      // The card currently being dragged, or null when no drag is in progress.
      draggingRow: null,
    }
  },
  computed: {
    ...mapGetters({
      row: 'rowModalNavigation/getRow',
    }),
    allRows() {
      return this.$store.getters[this.storePrefix + 'view/kanban/getRows']
    },
    fieldOptions() {
      return this.$store.getters[
        this.storePrefix + 'view/kanban/getAllFieldOptions'
      ]
    },
    /**
     * The single-select field by which the board is grouped. Null when the view
     * has not been configured with a grouping field yet.
     */
    singleSelectField() {
      const fieldId = this.view.single_select_field
      if (!fieldId) {
        return null
      }
      return this.fields.find((field) => field.id === fieldId) || null
    },
    columns() {
      if (!this.singleSelectField) {
        return []
      }
      return groupRowsBySingleSelect(this.allRows, this.singleSelectField)
    },
    /**
     * Whether cards may be dragged between columns. Dragging mutates the
     * grouping single-select cell, so it is only offered when the view is not
     * read-only, a grouping field is configured, and that field is writable by
     * the current user. Field editability routes through the same
     * `canWriteFieldValues` predicate the grid/row editing path uses, so it
     * honours the Epic 1 field-permission layer. The server enforces the same
     * boundary regardless; disabling the UI just avoids an obvious no-op + the
     * rollback round-trip. (AC #4)
     */
    canDrag() {
      if (this.readOnly || !this.singleSelectField) {
        return false
      }
      return this.$registry
        .get('field', this.singleSelectField.type)
        .canWriteFieldValues(this.singleSelectField)
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
      const fieldId = this.view.card_cover_image_field
      return this.fields.find((field) => field.id === fieldId) || null
    },
    activeSearchTerm() {
      return this.$store.getters[
        `${this.storePrefix}view/kanban/getActiveSearchTerm`
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
          this.storePrefix + 'view/kanban/updateRowValue',
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
    /**
     * Begins dragging a card. Tracks the dragged row and flips its pre-seeded
     * `row._.dragging` flag (set in store/view/kanban.js `populateRow`) for the
     * drag visual state. When dragging is not permitted the drag is cancelled
     * so the card stays put. (AC #4)
     */
    onDragStart(row, event) {
      if (!this.canDrag) {
        if (event) {
          event.preventDefault()
        }
        return
      }
      this.draggingRow = row
      if (row._) {
        row._.dragging = true
      }
      if (event && event.dataTransfer) {
        event.dataTransfer.effectAllowed = 'move'
        // Some browsers require a payload for the drag to initiate.
        try {
          event.dataTransfer.setData('text/plain', String(row.id))
        } catch (e) {}
      }
    },
    onDragEnd(row) {
      if (row && row._) {
        row._.dragging = false
      }
      this.draggingRow = null
    },
    /**
     * `dragover` must call `preventDefault` for the element to be a valid drop
     * target. Only do so while a permitted drag is in progress — so a read-only
     * board (or any non-drag dragover) never claims the drop target. The
     * template intentionally binds `@dragover` WITHOUT the `.prevent` modifier;
     * an unconditional modifier would make every column a drop target and defeat
     * this guard.
     */
    onDragOver(event) {
      if (this.canDrag && this.draggingRow !== null && event) {
        event.preventDefault()
        if (event.dataTransfer) {
          event.dataTransfer.dropEffect = 'move'
        }
      }
    },
    /**
     * Drops the dragged card onto a column. Resolves the target option object
     * from the column (`null` for Uncategorized) and dispatches the existing
     * optimistic row-update path via `updateValue`. The card re-buckets
     * reactively because `columns` is derived from the store; rollback (on
     * failure) returns it. Dropping onto the card's own column is a no-op.
     * (AC #1, #3, #5)
     */
    onDrop(column, event) {
      if (event) {
        event.preventDefault()
      }
      const row = this.draggingRow
      this.draggingRow = null
      if (row && row._) {
        row._.dragging = false
      }
      if (!this.canDrag || row === null || row === undefined) {
        return
      }

      const field = this.singleSelectField
      const fieldKey = `field_${field.id}`
      const currentValue = row[fieldKey] === undefined ? null : row[fieldKey]
      const currentOptionId =
        currentValue === null || currentValue === undefined
          ? null
          : currentValue.id
      const targetOptionId = column.id

      // No-op guard (AC #5): dropping on the row's own column (both null counts
      // as equal) does not dispatch and does not flicker.
      if (currentOptionId === targetOptionId) {
        return
      }

      // Build the target value as the full option object (or null for
      // Uncategorized). SingleSelectFieldType.prepareValueForUpdate converts it
      // to the option id for the request, so we must NOT pre-convert it.
      let targetOption = null
      if (targetOptionId !== null) {
        const option = (field.select_options || []).find(
          (o) => o.id === targetOptionId
        )
        targetOption = option
          ? { id: option.id, value: option.value, color: option.color }
          : { id: column.id, value: column.label, color: column.color }
      }

      return this.updateValue({
        field,
        row,
        value: targetOption,
        oldValue: currentValue,
      })
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
            this.storePrefix + 'view/kanban/refreshRowFromBackend',
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
