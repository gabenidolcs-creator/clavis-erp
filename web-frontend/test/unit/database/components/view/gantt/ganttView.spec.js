import { vi } from 'vitest'
import { TestApp } from '@baserow/test/helpers/testApp'
import { GanttViewType } from '@baserow/modules/database/viewTypes'
import GanttView, {
  ganttViewMode,
} from '@baserow/modules/database/components/view/gantt/GanttView'
import GanttViewHeader from '@baserow/modules/database/components/view/gantt/GanttViewHeader'
import * as ganttStore from '@baserow/modules/database/store/view/gantt'

describe('GanttViewType', () => {
  let testApp

  beforeAll(() => {
    testApp = new TestApp()
  })

  afterEach(() => {
    testApp.afterEach()
  })

  test('getType returns gantt', () => {
    expect(GanttViewType.getType()).toBe('gantt')
  })

  test('exposes the core name and icon', () => {
    // Gantt has no premium twin, so the core class IS the registry entry.
    const viewType = new GanttViewType({ app: testApp.getApp() })
    expect(viewType.getType()).toBe('gantt')
    expect(viewType.getIconClass()).toBe('baserow-icon-gantt')
    // i18n is mocked in vitest.setup.ts so `t` echoes the translation key.
    expect(viewType.getName()).toBe('viewType.gantt')
  })
})

// ganttViewMode maps the persisted zoom level to the Frappe Gantt `view_mode`
// name (capitalised); an unknown value falls back to Month, mirroring the
// backend column default. (AC #4)
describe('ganttViewMode', () => {
  test.each([
    ['day', 'Day'],
    ['week', 'Week'],
    ['month', 'Month'],
  ])('maps %s to %s', (timescale, mode) => {
    expect(ganttViewMode(timescale)).toBe(mode)
  })

  test('falls back to Month for an unknown timescale', () => {
    expect(ganttViewMode('century')).toBe('Month')
    expect(ganttViewMode(undefined)).toBe('Month')
  })
})

// Field-resolution + zoom computeds. Driven against a minimal instance rather
// than a full mount (a full mount pulls in the page/view/gantt store and the
// lazy Frappe Gantt lib). Keeps the test on pure component logic.
describe('GanttView field-resolution computeds', () => {
  const startField = { id: 5, name: 'Start', type: 'date' }
  const endField = { id: 6, name: 'End', type: 'date' }
  const textField = { id: 7, name: 'Name', type: 'text' }

  const makeVm = ({ fields, view = {} } = {}) => {
    const vm = { fields, view }
    for (const name of [
      'startDateField',
      'endDateField',
      'timescale',
      'viewMode',
      'coverImageField',
    ]) {
      Object.defineProperty(vm, name, {
        get: GanttView.computed[name],
      })
    }
    return vm
  }

  test('startDateField resolves view.start_date_field to the field object', () => {
    const vm = makeVm({
      fields: [startField, textField],
      view: { start_date_field: 5 },
    })
    expect(vm.startDateField).toBe(startField)
  })

  test('startDateField is null when unset or pointing at a missing field', () => {
    expect(
      makeVm({ fields: [startField], view: { start_date_field: null } })
        .startDateField
    ).toBe(null)
    expect(
      makeVm({ fields: [startField], view: { start_date_field: 999 } })
        .startDateField
    ).toBe(null)
  })

  test('endDateField resolves view.end_date_field to the field object', () => {
    const vm = makeVm({
      fields: [startField, endField],
      view: { end_date_field: 6 },
    })
    expect(vm.endDateField).toBe(endField)
  })

  test('timescale defaults to month when unset', () => {
    expect(makeVm({ fields: [], view: {} }).timescale).toBe('month')
    expect(makeVm({ fields: [], view: { timescale: 'week' } }).timescale).toBe(
      'week'
    )
  })

  test('viewMode reflects the persisted timescale (AC #4)', () => {
    expect(makeVm({ fields: [], view: { timescale: 'day' } }).viewMode).toBe(
      'Day'
    )
    expect(makeVm({ fields: [], view: {} }).viewMode).toBe('Month')
  })

  test('coverImageField is always null — the gantt tray card has no cover', () => {
    expect(makeVm({ fields: [startField], view: {} }).coverImageField).toBe(
      null
    )
  })
})

// partitioned/scheduledRows/unscheduledRows reuse the shared Timeline partition:
// a row is SCHEDULED (a bar) only when BOTH start AND end are present; otherwise
// it lands in the unscheduled tray. (AC #2)
describe('GanttView scheduled/unscheduled partition (AC #2)', () => {
  const startField = { id: 5, type: 'date' }
  const endField = { id: 6, type: 'date' }

  const makeVm = ({ allRows, startDateField, endDateField }) => {
    const vm = { allRows, startDateField, endDateField }
    for (const name of ['partitioned', 'scheduledRows', 'unscheduledRows']) {
      Object.defineProperty(vm, name, {
        get: GanttView.computed[name],
      })
    }
    return vm
  }

  test('a row with both start and end is scheduled', () => {
    const vm = makeVm({
      allRows: [{ id: 1, field_5: '2026-06-10', field_6: '2026-06-12' }],
      startDateField: startField,
      endDateField: endField,
    })
    expect(vm.scheduledRows.map((r) => r.id)).toEqual([1])
    expect(vm.unscheduledRows).toHaveLength(0)
  })

  test('a row missing either endpoint goes to the tray', () => {
    const vm = makeVm({
      allRows: [
        { id: 2, field_5: '2026-06-10', field_6: null },
        { id: 3, field_5: null, field_6: '2026-06-12' },
      ],
      startDateField: startField,
      endDateField: endField,
    })
    expect(vm.scheduledRows).toHaveLength(0)
    expect(vm.unscheduledRows.map((r) => r.id)).toEqual([2, 3])
  })

  test('both partitions are empty until both date fields are configured', () => {
    const vm = makeVm({
      allRows: [{ id: 1, field_5: '2026-06-10', field_6: '2026-06-12' }],
      startDateField: startField,
      endDateField: null,
    })
    expect(vm.scheduledRows).toHaveLength(0)
    expect(vm.unscheduledRows).toHaveLength(0)
  })
})

// ganttTasks is the render keystone: each scheduled row becomes a Frappe Gantt
// task with `start`/`end` serialised to `YYYY-MM-DD` (no day drift), `progress`
// 0, and `dependencies` the empty 3.9 seam. (AC #2, #3)
describe('GanttView.ganttTasks mapping (AC #2, #3)', () => {
  const startField = { id: 5, type: 'date' }
  const endField = { id: 6, type: 'date' }
  const primaryField = { id: 9, type: 'text', primary: true }

  const makeVm = ({ allRows }) => {
    const vm = {
      allRows,
      // No edges in the mapping fixtures → every task's `dependencies` is ''.
      dependencies: [],
      startDateField: startField,
      endDateField: endField,
      primaryField,
      $registry: {
        get: () => ({
          toHumanReadableString: (field, value) => String(value ?? ''),
        }),
      },
    }
    for (const name of [
      'partitioned',
      'scheduledRows',
      'unscheduledRows',
      'ganttTasks',
    ]) {
      Object.defineProperty(vm, name, {
        get: GanttView.computed[name],
      })
    }
    vm.rowName = GanttView.methods.rowName.bind(vm)
    vm.dependenciesForRow = GanttView.methods.dependenciesForRow.bind(vm)
    return vm
  }

  test('maps a scheduled row to a task with YYYY-MM-DD dates and no day drift', () => {
    const vm = makeVm({
      allRows: [
        {
          id: 1,
          field_5: '2026-06-10',
          field_6: '2026-06-12',
          field_9: 'Plan',
        },
      ],
    })
    expect(vm.ganttTasks).toEqual([
      {
        id: '1',
        name: 'Plan',
        start: '2026-06-10',
        end: '2026-06-12',
        progress: 0,
        dependencies: '',
      },
    ])
  })

  test('the task id is the row id as a string', () => {
    const vm = makeVm({
      allRows: [
        { id: 42, field_5: '2026-06-10', field_6: '2026-06-12', field_9: 'X' },
      ],
    })
    expect(vm.ganttTasks[0].id).toBe('42')
  })

  test('unscheduled rows contribute no tasks', () => {
    const vm = makeVm({
      allRows: [
        { id: 1, field_5: '2026-06-10', field_6: null, field_9: 'Half' },
      ],
    })
    expect(vm.ganttTasks).toHaveLength(0)
  })
})

// dependenciesForRow is the now-live Story 3.9 seam: for a row it returns the
// comma-separated predecessor ids of every edge whose successor IS that row, in
// the order Frappe Gantt draws arrows from. (AC #1, AC #3)
describe('GanttView.dependenciesForRow (Story 3.9 seam, AC #1/#3)', () => {
  const bind = (dependencies) =>
    GanttView.methods.dependenciesForRow.bind({ dependencies })

  test('returns the predecessor ids for edges ending at the row', () => {
    const dependenciesForRow = bind([
      { predecessor_row_id: 1, successor_row_id: 3 },
      { predecessor_row_id: 2, successor_row_id: 3 },
      { predecessor_row_id: 9, successor_row_id: 4 },
    ])
    expect(dependenciesForRow({ id: 3 })).toBe('1,2')
    expect(dependenciesForRow({ id: 4 })).toBe('9')
  })

  test('returns an empty string when the row has no predecessors', () => {
    expect(bind([])({ id: 1 })).toBe('')
    expect(
      bind([{ predecessor_row_id: 1, successor_row_id: 2 }])({ id: 1 })
    ).toBe('')
  })
})

// The predecessor picker (Story 3.9 draw affordance) dispatches the store's
// optimistic create/delete actions with the right row ids, is guarded by
// `canEditDependencies`, and translates a cycle rejection into a clear toast.
describe('GanttView predecessor-picker affordance (Story 3.9, AC #1/#2)', () => {
  const makeVm = ({ canEdit = true, dispatch } = {}) => {
    const dispatched = []
    const recording = (action, payload) => {
      dispatched.push({ action, payload })
      return Promise.resolve()
    }
    const vm = {
      canEditDependencies: canEdit,
      openRow: { id: 3 },
      storePrefix: 'page/',
      view: { id: 2 },
      dispatched,
      $store: { dispatch: dispatch || recording },
      $t: (key) => key,
    }
    vm.addPredecessor = GanttView.methods.addPredecessor.bind(vm)
    vm.removeDependency = GanttView.methods.removeDependency.bind(vm)
    return vm
  }

  test('addPredecessor dispatches createDependency with predecessor→open row ids', async () => {
    const vm = makeVm()
    await vm.addPredecessor(1)
    expect(vm.dispatched).toHaveLength(1)
    expect(vm.dispatched[0].action).toBe('page/view/gantt/createDependency')
    expect(vm.dispatched[0].payload).toEqual({
      viewId: 2,
      predecessorRowId: 1,
      successorRowId: 3,
    })
  })

  test('addPredecessor is a no-op when editing is not allowed', async () => {
    const vm = makeVm({ canEdit: false })
    await vm.addPredecessor(1)
    expect(vm.dispatched).toHaveLength(0)
  })

  test('a cycle rejection surfaces a clear toast and does not rethrow', async () => {
    const toasts = []
    const dispatch = (action, payload) => {
      if (action === 'toast/error') {
        toasts.push(payload)
        return Promise.resolve()
      }
      return Promise.reject({
        handler: { code: 'ERROR_TASK_DEPENDENCY_CYCLE' },
      })
    }
    const vm = makeVm({ dispatch })
    await expect(vm.addPredecessor(1)).resolves.toBeUndefined()
    expect(toasts).toHaveLength(1)
    expect(toasts[0].title).toBe('ganttView.cycleRejectedTitle')
  })

  test('removeDependency dispatches deleteDependency with the edge id', async () => {
    const vm = makeVm()
    await vm.removeDependency({ id: 77 })
    expect(vm.dispatched[0].action).toBe('page/view/gantt/deleteDependency')
    expect(vm.dispatched[0].payload).toEqual({ viewId: 2, dependencyId: 77 })
  })

  test('removeDependency is a no-op when editing is not allowed', async () => {
    const vm = makeVm({ canEdit: false })
    await vm.removeDependency({ id: 77 })
    expect(vm.dispatched).toHaveLength(0)
  })
})

// The gantt store's createDependency action optimistically adds the edge and
// rolls it back on a cycle 400; deleteDependency removes optimistically and
// restores on failure. (Story 3.9, AC #1/#2)
describe('gantt store dependency actions (Story 3.9, AC #1/#2)', () => {
  const makeCtx = (initial = []) => {
    const s = { ...ganttStore.state(), dependencies: [...initial] }
    const commit = (name, payload) => ganttStore.mutations[name](s, payload)
    const getters = {
      getDependencies: s.dependencies,
    }
    // getDependencies must reflect the live array; redefine as a getter.
    Object.defineProperty(getters, 'getDependencies', {
      get: () => s.dependencies,
    })
    return { s, ctx: { commit, getters } }
  }

  test('createDependency persists the server edge on success', async () => {
    const { s, ctx } = makeCtx()
    const client = {
      post: () =>
        Promise.resolve({
          data: {
            id: 5,
            predecessor_row_id: 1,
            successor_row_id: 2,
            dependency_type: 'FS',
          },
        }),
    }
    await ganttStore.actions.createDependency.call({ $client: client }, ctx, {
      viewId: 2,
      predecessorRowId: 1,
      successorRowId: 2,
    })
    expect(s.dependencies).toEqual([
      {
        id: 5,
        predecessor_row_id: 1,
        successor_row_id: 2,
        dependency_type: 'FS',
      },
    ])
  })

  test('createDependency rolls back the optimistic edge on a cycle 400', async () => {
    const { s, ctx } = makeCtx()
    const client = {
      post: () =>
        Promise.reject({ handler: { code: 'ERROR_TASK_DEPENDENCY_CYCLE' } }),
    }
    await expect(
      ganttStore.actions.createDependency.call({ $client: client }, ctx, {
        viewId: 2,
        predecessorRowId: 1,
        successorRowId: 2,
      })
    ).rejects.toBeDefined()
    // The optimistic edge (temp id -1) is gone; state is unchanged.
    expect(s.dependencies).toEqual([])
  })

  test('deleteDependency restores the edge when the server delete fails', async () => {
    const edge = {
      id: 9,
      predecessor_row_id: 1,
      successor_row_id: 2,
      dependency_type: 'FS',
    }
    const { s, ctx } = makeCtx([edge])
    const client = { delete: () => Promise.reject(new Error('boom')) }
    await expect(
      ganttStore.actions.deleteDependency.call({ $client: client }, ctx, {
        viewId: 2,
        dependencyId: 9,
      })
    ).rejects.toBeDefined()
    expect(s.dependencies).toEqual([edge])
  })
})

// openTaskRow resolves a clicked task back to its row by id and reuses the
// standard row-modal path; an unknown id is a safe no-op.
describe('GanttView.openTaskRow', () => {
  const makeVm = ({ allRows }) => {
    const rowClick = vi.fn()
    const vm = { allRows, rowClick }
    vm.openTaskRow = GanttView.methods.openTaskRow.bind(vm)
    return vm
  }

  test('resolves the task id (string) to the row and opens it', () => {
    const row = { id: 7 }
    const vm = makeVm({ allRows: [row, { id: 8 }] })
    vm.openTaskRow({ id: '7' })
    expect(vm.rowClick).toHaveBeenCalledWith(row)
  })

  test('an unknown task id is a no-op', () => {
    const vm = makeVm({ allRows: [{ id: 8 }] })
    vm.openTaskRow({ id: '999' })
    expect(vm.rowClick).not.toHaveBeenCalled()
  })
})

// GanttView.updateValue reuses the optimistic updateRowValue path of the gantt
// store. Driven at the method level (no mount).
describe('GanttView.updateValue', () => {
  const startField = { id: 5, type: 'date' }

  const makeVm = ({ dispatch = null } = {}) => {
    const dispatched = []
    const recordingDispatch = (action, payload) => {
      dispatched.push({ action, payload })
      return Promise.resolve()
    }
    const vm = {
      storePrefix: 'page/',
      table: { id: 1 },
      view: { id: 2 },
      fields: [startField],
      dispatched,
      $store: { dispatch: dispatch || recordingDispatch },
    }
    vm.updateValue = GanttView.methods.updateValue.bind(vm)
    return vm
  }

  test('dispatches the gantt updateRowValue action', async () => {
    const vm = makeVm()
    const row = { id: 10, field_5: '2026-06-10' }
    await vm.updateValue({
      field: startField,
      row,
      value: '2026-06-12',
      oldValue: '2026-06-10',
    })

    expect(vm.dispatched).toHaveLength(1)
    expect(vm.dispatched[0].action).toBe('page/view/gantt/updateRowValue')
    expect(vm.dispatched[0].payload).toMatchObject({
      table: vm.table,
      view: vm.view,
      field: startField,
      row,
      value: '2026-06-12',
      oldValue: '2026-06-10',
    })
  })

  test('a rejected server update is caught and surfaced via notifyIf', async () => {
    const notifyIf = vi.fn()
    const rejectingDispatch = () => Promise.reject({ handler: { notifyIf } })
    const vm = makeVm({ dispatch: rejectingDispatch })

    await expect(
      vm.updateValue({
        field: startField,
        row: { id: 10 },
        value: '2026-06-12',
        oldValue: '2026-06-10',
      })
    ).resolves.toBeUndefined()
    expect(notifyIf).toHaveBeenCalledWith('field')
  })
})

// GanttViewHeader dispatches the start/end positioning fields and the zoom level
// via the GENERIC `view/update` (so timescale round-trips, AC #4), and the field
// options via the gantt store actions (each guarded by readOnly OR a missing
// update_field_options permission). Driven at the method level.
describe('GanttViewHeader dispatch', () => {
  const makeVm = ({ readOnly = false, hasPermission = true } = {}) => {
    const dispatched = []
    const vm = {
      readOnly,
      storePrefix: 'page/',
      view: { id: 5 },
      database: { workspace: { id: 9 } },
      dispatched,
      updatingStartDateField: false,
      updatingEndDateField: false,
      $store: {
        dispatch: (action, payload) => {
          dispatched.push({ action, payload })
          return Promise.resolve()
        },
      },
      $hasPermission: () => hasPermission,
    }
    for (const name of [
      'updateTimescale',
      'updateStartDateField',
      'updateEndDateField',
      'updateAllFieldOptions',
      'updateFieldOptionsOfField',
      'orderFieldOptions',
    ]) {
      vm[name] = GanttViewHeader.methods[name].bind(vm)
    }
    return vm
  }

  test('updateStartDateField dispatches the generic view/update with start_date_field (AC #1)', async () => {
    const vm = makeVm()
    await vm.updateStartDateField(5)

    expect(vm.dispatched).toHaveLength(1)
    expect(vm.dispatched[0].action).toBe('view/update')
    expect(vm.dispatched[0].payload).toMatchObject({
      view: vm.view,
      values: { start_date_field: 5 },
      readOnly: false,
    })
  })

  test('updateEndDateField dispatches the generic view/update with end_date_field (AC #1)', async () => {
    const vm = makeVm()
    await vm.updateEndDateField(6)

    expect(vm.dispatched[0].action).toBe('view/update')
    expect(vm.dispatched[0].payload).toMatchObject({
      values: { end_date_field: 6 },
      readOnly: false,
    })
  })

  test('updateTimescale dispatches the generic view/update so the zoom persists (AC #4)', async () => {
    const vm = makeVm()
    await vm.updateTimescale('week')

    expect(vm.dispatched).toHaveLength(1)
    expect(vm.dispatched[0].action).toBe('view/update')
    expect(vm.dispatched[0].payload).toMatchObject({
      view: vm.view,
      values: { timescale: 'week' },
      readOnly: false,
    })
  })

  test('updateFieldOptionsOfField dispatches the gantt store action with the guard (AC #5)', async () => {
    const vm = makeVm()
    const field = { id: 7 }
    await vm.updateFieldOptionsOfField({
      field,
      values: { hidden: true },
      oldValues: { hidden: false },
    })

    expect(vm.dispatched[0].action).toBe(
      'page/view/gantt/updateFieldOptionsOfField'
    )
    expect(vm.dispatched[0].payload).toMatchObject({
      field,
      values: { hidden: true },
      readOnly: false,
    })
  })

  test('orderFieldOptions dispatches the gantt reorder action (AC #5)', async () => {
    const vm = makeVm()
    await vm.orderFieldOptions({ order: [7, 5, 6] })

    expect(vm.dispatched[0].action).toBe(
      'page/view/gantt/updateFieldOptionsOrder'
    )
    expect(vm.dispatched[0].payload).toMatchObject({
      order: [7, 5, 6],
      readOnly: false,
    })
  })

  test('field-option dispatches carry readOnly=true when the view is read-only (AC #5)', async () => {
    const vm = makeVm({ readOnly: true })
    await vm.updateFieldOptionsOfField({
      field: { id: 7 },
      values: { hidden: true },
      oldValues: { hidden: false },
    })
    expect(vm.dispatched[0].payload.readOnly).toBe(true)
  })

  test('field-option dispatches carry readOnly=true when the update permission is missing (AC #5)', async () => {
    const vm = makeVm({ hasPermission: false })
    await vm.orderFieldOptions({ order: [5, 6] })
    expect(vm.dispatched[0].payload.readOnly).toBe(true)
  })
})

// Story 3.10: dragging a bar (the predecessor) computes whole-day deltas, and
// branches on whether any direct FS successor would be pushed. No violation →
// write the predecessor alone, silently. Violation → ask the backend for the
// read-only preview and prompt; nothing is written until the author confirms.
// (AC #1, #2, #4, #5)
describe('GanttView cascade reschedule on drag (Story 3.10)', () => {
  const startField = { id: 5, type: 'date', date_include_time: false }
  const endField = { id: 6, type: 'date', date_include_time: false }

  const makeVm = ({
    allRows,
    dependencies = [],
    dispatch = null,
    canDrag = true,
  } = {}) => {
    const dispatched = []
    const recording = (action, payload) => {
      dispatched.push({ action, payload })
      if (action.endsWith('previewCascade')) {
        return Promise.resolve({
          cascade_count: 1,
          affected_successors: [{ row_id: 2 }],
        })
      }
      return Promise.resolve()
    }
    const modal = { show: vi.fn(), hide: vi.fn() }
    const refreshGantt = vi.fn()
    const vm = {
      readOnly: false,
      storePrefix: 'page/',
      table: { id: 1 },
      view: { id: 2 },
      fields: [startField, endField],
      allRows,
      dependencies,
      startDateField: startField,
      endDateField: endField,
      pendingCascade: null,
      cascadeResolved: true,
      dispatched,
      $store: { dispatch: dispatch || recording },
      $registry: {
        get: () => ({ canWriteFieldValues: () => canDrag }),
      },
      $refs: { rescheduleModal: modal },
      refreshGantt,
    }
    Object.defineProperty(vm, 'canDragBars', {
      get: GanttView.computed.canDragBars,
    })
    for (const name of [
      'onBarDateChange',
      'commitPredecessorOnly',
      'confirmCascade',
      'declineCascade',
      'onRescheduleModalHidden',
    ]) {
      vm[name] = GanttView.methods[name].bind(vm)
    }
    return vm
  }

  test('canDragBars is true only when not read-only and both fields are writable', () => {
    expect(makeVm({ allRows: [] }).canDragBars).toBe(true)
    expect(makeVm({ allRows: [], canDrag: false }).canDragBars).toBe(false)
    const ro = makeVm({ allRows: [] })
    ro.readOnly = true
    expect(ro.canDragBars).toBe(false)
  })

  test('a move that violates no successor writes the predecessor alone, no prompt (AC #4)', async () => {
    const vm = makeVm({
      allRows: [
        { id: 1, field_5: '2026-06-10', field_6: '2026-06-12' },
        // Successor starts AFTER the predecessor's new finish → not pushed.
        { id: 2, field_5: '2026-06-20', field_6: '2026-06-21' },
      ],
      dependencies: [{ predecessor_row_id: 1, successor_row_id: 2 }],
    })
    await vm.onBarDateChange(
      { id: '1' },
      new Date('2026-06-15'),
      new Date('2026-06-17')
    )
    expect(vm.dispatched).toHaveLength(1)
    expect(vm.dispatched[0].action).toBe('page/view/gantt/updateRowValues')
    expect(vm.dispatched[0].payload.values).toEqual({
      field_5: '2026-06-15',
      field_6: '2026-06-17',
    })
    expect(vm.dispatched[0].payload.oldValues).toEqual({
      field_5: '2026-06-10',
      field_6: '2026-06-12',
    })
    expect(vm.$refs.rescheduleModal.show).not.toHaveBeenCalled()
    expect(vm.pendingCascade).toBe(null)
  })

  test('a move that pushes a successor previews and prompts WITHOUT writing (AC #1)', async () => {
    const vm = makeVm({
      allRows: [
        { id: 1, field_5: '2026-06-10', field_6: '2026-06-12' },
        // Successor starts BEFORE the predecessor's new finish → pushed.
        { id: 2, field_5: '2026-06-13', field_6: '2026-06-14' },
      ],
      dependencies: [{ predecessor_row_id: 1, successor_row_id: 2 }],
    })
    await vm.onBarDateChange(
      { id: '1' },
      new Date('2026-06-15'),
      new Date('2026-06-17')
    )
    expect(vm.dispatched).toHaveLength(1)
    expect(vm.dispatched[0].action).toBe('page/view/gantt/previewCascade')
    expect(vm.dispatched[0].payload).toEqual({
      viewId: 2,
      predecessorRowId: 1,
      newStart: '2026-06-15',
      newEnd: '2026-06-17',
    })
    expect(vm.$refs.rescheduleModal.show).toHaveBeenCalled()
    expect(vm.cascadeResolved).toBe(false)
    expect(vm.pendingCascade.preview.cascade_count).toBe(1)
    // Nothing committed yet.
    expect(
      vm.dispatched.some((d) => d.action.endsWith('updateRowValues'))
    ).toBe(false)
    expect(vm.dispatched.some((d) => d.action.endsWith('applyCascade'))).toBe(
      false
    )
  })

  test('a day-granular no-op snaps the bar back and writes nothing', async () => {
    const vm = makeVm({
      allRows: [{ id: 1, field_5: '2026-06-10', field_6: '2026-06-12' }],
    })
    await vm.onBarDateChange(
      { id: '1' },
      new Date('2026-06-10'),
      new Date('2026-06-12')
    )
    expect(vm.dispatched).toHaveLength(0)
    expect(vm.refreshGantt).toHaveBeenCalled()
  })

  test('onBarDateChange is a no-op when bars are not draggable (AC #5)', async () => {
    const vm = makeVm({
      allRows: [{ id: 1, field_5: '2026-06-10', field_6: '2026-06-12' }],
      canDrag: false,
    })
    await vm.onBarDateChange(
      { id: '1' },
      new Date('2026-06-15'),
      new Date('2026-06-17')
    )
    expect(vm.dispatched).toHaveLength(0)
  })

  test('confirmCascade commits the cascade and clears the prompt (AC #2)', async () => {
    const vm = makeVm({ allRows: [] })
    vm.pendingCascade = {
      row: { id: 1 },
      values: {},
      oldValues: {},
      newStart: '2026-06-15',
      newEnd: '2026-06-17',
      preview: { cascade_count: 1 },
    }
    vm.cascadeResolved = false
    await vm.confirmCascade()
    expect(vm.dispatched[0].action).toBe('page/view/gantt/applyCascade')
    expect(vm.dispatched[0].payload).toEqual({
      viewId: 2,
      predecessorRowId: 1,
      newStart: '2026-06-15',
      newEnd: '2026-06-17',
    })
    expect(vm.$refs.rescheduleModal.hide).toHaveBeenCalled()
    expect(vm.cascadeResolved).toBe(true)
    expect(vm.pendingCascade).toBe(null)
  })

  test('declineCascade writes only the predecessor and refetches edges (AC #4)', async () => {
    const vm = makeVm({ allRows: [] })
    vm.pendingCascade = {
      row: { id: 1 },
      values: { field_5: '2026-06-15', field_6: '2026-06-17' },
      oldValues: { field_5: '2026-06-10', field_6: '2026-06-12' },
      newStart: '2026-06-15',
      newEnd: '2026-06-17',
      preview: { cascade_count: 1 },
    }
    vm.cascadeResolved = false
    await vm.declineCascade()
    expect(vm.dispatched[0].action).toBe('page/view/gantt/updateRowValues')
    expect(vm.dispatched[0].payload.values).toEqual({
      field_5: '2026-06-15',
      field_6: '2026-06-17',
    })
    expect(vm.dispatched[1].action).toBe('page/view/gantt/fetchDependencies')
    expect(vm.$refs.rescheduleModal.hide).toHaveBeenCalled()
    expect(vm.pendingCascade).toBe(null)
  })

  test('dismissing the prompt without a choice reverts the optimistic bar (AC #5)', () => {
    const vm = makeVm({ allRows: [] })
    vm.pendingCascade = { row: { id: 1 } }
    vm.cascadeResolved = false
    vm.onRescheduleModalHidden()
    expect(vm.refreshGantt).toHaveBeenCalled()
    expect(vm.pendingCascade).toBe(null)
    expect(vm.cascadeResolved).toBe(true)
  })

  test('a resolved hide (after confirm/decline) does not double-revert', () => {
    const vm = makeVm({ allRows: [] })
    vm.cascadeResolved = true
    vm.onRescheduleModalHidden()
    expect(vm.refreshGantt).not.toHaveBeenCalled()
  })
})

// markViolatedConnectors (AC #3): for each edge flagged `violated`, find the lib
// arrow keyed by data-from/data-to and tag it; clears stale tags first.
describe('GanttView.markViolatedConnectors (AC #3)', () => {
  test('tags the connector of a violated edge by its from/to row ids', () => {
    const arrow = { classList: { add: vi.fn(), remove: vi.fn() } }
    const host = {
      querySelectorAll: vi.fn(() => []),
      querySelector: vi.fn(() => arrow),
    }
    const vm = {
      $refs: { ganttHost: host },
      dependencies: [
        { predecessor_row_id: 1, successor_row_id: 2, violated: true },
        { predecessor_row_id: 3, successor_row_id: 4, violated: false },
      ],
    }
    GanttView.methods.markViolatedConnectors.call(vm)
    expect(host.querySelector).toHaveBeenCalledWith(
      '.arrow[data-from="1"][data-to="2"]'
    )
    expect(host.querySelector).toHaveBeenCalledTimes(1)
    expect(arrow.classList.add).toHaveBeenCalledWith(
      'gantt-view__arrow--violated'
    )
  })

  test('is a safe no-op when the host is not mounted', () => {
    const vm = { $refs: {}, dependencies: [{ violated: true }] }
    expect(() =>
      GanttView.methods.markViolatedConnectors.call(vm)
    ).not.toThrow()
  })
})
