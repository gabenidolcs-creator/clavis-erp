import { vi } from 'vitest'
import { TestApp } from '@baserow/test/helpers/testApp'
import { KanbanViewType } from '@baserow/modules/database/viewTypes'
import KanbanView, {
  groupRowsBySingleSelect,
} from '@baserow/modules/database/components/view/kanban/KanbanView'

describe('KanbanViewType', () => {
  let testApp

  beforeAll(() => {
    testApp = new TestApp()
  })

  afterEach(() => {
    testApp.afterEach()
  })

  test('getType returns kanban', () => {
    expect(KanbanViewType.getType()).toBe('kanban')
  })

  test('exposes the core name and icon', () => {
    // NOTE: in an open-core build that also loads the premium plugin, the
    // premium Kanban view registers later and overrides this core view in the
    // registry (premium takes precedence). The TestApp loads premium, so we
    // assert against the core class directly rather than the registry entry.
    const viewType = new KanbanViewType({ app: testApp.getApp() })
    expect(viewType.getType()).toBe('kanban')
    expect(viewType.getIconClass()).toBe('baserow-icon-kanban')
    // i18n is mocked in vitest.setup.ts so `t` echoes the translation key.
    expect(viewType.getName()).toBe('viewType.kanban')
  })

  test('the registry resolves a kanban view type', () => {
    const viewType = testApp.getApp().$registry.get('view', 'kanban')
    expect(viewType.getType()).toBe('kanban')
  })
})

describe('groupRowsBySingleSelect', () => {
  // A single-select field with two options in a defined order. Cell values on a
  // row are objects of the shape { id, value, color } or null.
  const singleSelectField = {
    id: 7,
    type: 'single_select',
    select_options: [
      { id: 1, value: 'To do', color: 'blue' },
      { id: 2, value: 'Done', color: 'green' },
    ],
  }

  test('buckets rows into one column per option in option order plus Uncategorized', () => {
    const rows = [
      { id: 10, field_7: { id: 2, value: 'Done', color: 'green' } },
      { id: 11, field_7: { id: 1, value: 'To do', color: 'blue' } },
      { id: 12, field_7: { id: 2, value: 'Done', color: 'green' } },
    ]

    const columns = groupRowsBySingleSelect(rows, singleSelectField)

    // Two option columns (in option order) plus the trailing Uncategorized column.
    expect(columns).toHaveLength(3)
    expect(columns[0].id).toBe(1)
    expect(columns[0].label).toBe('To do')
    expect(columns[0].rows.map((r) => r.id)).toEqual([11])
    expect(columns[1].id).toBe(2)
    expect(columns[1].label).toBe('Done')
    expect(columns[1].rows.map((r) => r.id)).toEqual([10, 12])
    // Trailing Uncategorized column for null values.
    expect(columns[2].id).toBe(null)
    expect(columns[2].rows).toHaveLength(0)
  })

  test('a row with a null grouping value lands in the Uncategorized column', () => {
    const rows = [
      { id: 20, field_7: null },
      { id: 21, field_7: { id: 1, value: 'To do', color: 'blue' } },
    ]

    const columns = groupRowsBySingleSelect(rows, singleSelectField)
    const uncategorized = columns[columns.length - 1]

    expect(uncategorized.id).toBe(null)
    expect(uncategorized.rows.map((r) => r.id)).toEqual([20])
  })

  test('rows referencing a deleted/unknown option fall into Uncategorized', () => {
    const rows = [{ id: 30, field_7: { id: 999, value: 'Gone', color: 'red' } }]

    const columns = groupRowsBySingleSelect(rows, singleSelectField)
    const uncategorized = columns[columns.length - 1]

    expect(uncategorized.rows.map((r) => r.id)).toEqual([30])
  })

  test('unfetched null row placeholders are skipped', () => {
    const rows = [
      null,
      { id: 40, field_7: { id: 1, value: 'To do', color: 'blue' } },
    ]

    const columns = groupRowsBySingleSelect(rows, singleSelectField)

    expect(columns[0].rows.map((r) => r.id)).toEqual([40])
    expect(columns[columns.length - 1].rows).toHaveLength(0)
  })
})

// Story 3.2 — dragging a card between columns. The drop reuses the EXISTING
// optimistic `updateRowValue` path; these tests assert the drop dispatches the
// right value, the no-op/readOnly/permission guards, and that a rejected update
// is swallowed (surfaced) by `updateValue`.
//
// These exercise the component's real `canDrag` computed and drag methods
// against a minimal instance rather than a full mount. A full mount pulls in the
// `page/view/kanban` store, which in the open-core test build is the PREMIUM
// kanban store (it registers last and overrides core) with a different
// `fetchInitial` signature — so a real mount cannot drive the free-core view.
// Driving the methods directly keeps the test in the core (clean-room) surface.
describe('KanbanView card drag-and-drop', () => {
  const singleSelectField = {
    id: 2,
    type: 'single_select',
    select_options: [
      { id: 1, value: 'To do', color: 'blue' },
      { id: 2, value: 'Done', color: 'green' },
    ],
  }
  const toDoColumn = { id: 1, label: 'To do', color: 'blue', rows: [] }
  const doneColumn = { id: 2, label: 'Done', color: 'green', rows: [] }
  const uncategorizedColumn = { id: null, label: null, color: null, rows: [] }

  const aRow = (id, value) => ({ id, field_2: value, _: { dragging: false } })

  // Builds a minimal instance binding the component's real methods + the live
  // `canDrag` getter. `dispatch` defaults to recording calls into `dispatched`.
  const makeVm = ({
    readOnly = false,
    canWrite = true,
    field = singleSelectField,
    dispatch = null,
  } = {}) => {
    const dispatched = []
    const recordingDispatch = (action, payload) => {
      dispatched.push({ action, payload })
      return Promise.resolve()
    }
    const vm = {
      readOnly,
      singleSelectField: field,
      storePrefix: 'page/',
      table: { id: 1 },
      view: {},
      fields: field ? [field] : [],
      draggingRow: null,
      dispatched,
      $store: { dispatch: dispatch || recordingDispatch },
      $registry: {
        get: () => ({
          canWriteFieldValues: () => canWrite,
          isReadOnlyField: () => !canWrite,
        }),
      },
    }
    Object.defineProperty(vm, 'canDrag', {
      get: KanbanView.computed.canDrag,
    })
    vm.updateValue = KanbanView.methods.updateValue.bind(vm)
    vm.onDragStart = KanbanView.methods.onDragStart.bind(vm)
    vm.onDragEnd = KanbanView.methods.onDragEnd.bind(vm)
    vm.onDragOver = KanbanView.methods.onDragOver.bind(vm)
    vm.onDrop = KanbanView.methods.onDrop.bind(vm)
    return vm
  }

  test('canDrag is true only when editable, not read-only, and a grouping field is set (AC #4)', () => {
    expect(makeVm().canDrag).toBe(true)
    expect(makeVm({ readOnly: true }).canDrag).toBe(false)
    expect(makeVm({ canWrite: false }).canDrag).toBe(false)
    expect(makeVm({ field: null }).canDrag).toBe(false)
  })

  test('onDragStart/onDragEnd toggle the row dragging flag and track the dragged row', () => {
    const vm = makeVm()
    const row = aRow(10, { id: 1, value: 'To do', color: 'blue' })
    vm.onDragStart(row, { dataTransfer: { setData() {} } })
    expect(row._.dragging).toBe(true)
    expect(vm.draggingRow).toBe(row)
    vm.onDragEnd(row)
    expect(row._.dragging).toBe(false)
    expect(vm.draggingRow).toBe(null)
  })

  test('a disabled drag (read-only) is cancelled in onDragStart and never tracks a row (AC #4)', () => {
    const vm = makeVm({ readOnly: true })
    const row = aRow(10, { id: 1, value: 'To do', color: 'blue' })
    const event = { preventDefault: vi.fn(), dataTransfer: { setData() {} } }
    vm.onDragStart(row, event)
    expect(event.preventDefault).toHaveBeenCalled()
    expect(vm.draggingRow).toBe(null)
    expect(row._.dragging).toBe(false)
  })

  test('onDragStart is cancelled when the grouping field is not editable (AC #4)', () => {
    const vm = makeVm({ canWrite: false })
    const row = aRow(10, { id: 1, value: 'To do', color: 'blue' })
    const event = { preventDefault: vi.fn(), dataTransfer: { setData() {} } }
    vm.onDragStart(row, event)
    expect(event.preventDefault).toHaveBeenCalled()
    expect(vm.draggingRow).toBe(null)
    expect(row._.dragging).toBe(false)
  })

  test('onDragOver only prevents default while a permitted drag is in progress (valid drop target)', () => {
    // A valid HTML5 drop target requires `dragover` to call preventDefault, but
    // only when a draggable drag is actually in flight.
    const vm = makeVm()
    vm.draggingRow = aRow(10, { id: 1, value: 'To do', color: 'blue' })
    const overEvent = { preventDefault: vi.fn(), dataTransfer: {} }
    vm.onDragOver(overEvent)
    expect(overEvent.preventDefault).toHaveBeenCalled()
    // The drop affordance is advertised as a move so the cursor reflects it.
    // The template binds @dragover WITHOUT `.prevent` so this guard is the sole
    // authority on whether the column is a valid drop target.
    expect(overEvent.dataTransfer.dropEffect).toBe('move')

    // No drag in progress: do not claim the drop target.
    vm.draggingRow = null
    const idleEvent = { preventDefault: vi.fn() }
    vm.onDragOver(idleEvent)
    expect(idleEvent.preventDefault).not.toHaveBeenCalled()

    // Drag in progress but dragging not permitted (read-only): not a drop target.
    const ro = makeVm({ readOnly: true })
    ro.draggingRow = aRow(10, { id: 1, value: 'To do', color: 'blue' })
    const roEvent = { preventDefault: vi.fn() }
    ro.onDragOver(roEvent)
    expect(roEvent.preventDefault).not.toHaveBeenCalled()
  })

  test('dropping a card on a different column dispatches updateRowValue once with the target option (AC #1)', async () => {
    const vm = makeVm()
    const row = aRow(10, { id: 1, value: 'To do', color: 'blue' }) // "To do"
    vm.draggingRow = row

    await vm.onDrop(doneColumn)

    expect(vm.dispatched).toHaveLength(1)
    expect(vm.dispatched[0].action).toBe('page/view/kanban/updateRowValue')
    expect(vm.dispatched[0].payload).toMatchObject({
      field: singleSelectField,
      row,
      value: { id: 2, value: 'Done', color: 'green' },
      oldValue: { id: 1, value: 'To do', color: 'blue' },
    })
  })

  test('dropping a card on the Uncategorized column passes value null (AC #1)', async () => {
    const vm = makeVm()
    const row = aRow(10, { id: 1, value: 'To do', color: 'blue' })
    vm.draggingRow = row

    await vm.onDrop(uncategorizedColumn)

    expect(vm.dispatched).toHaveLength(1)
    expect(vm.dispatched[0].payload).toMatchObject({
      value: null,
      oldValue: { id: 1, value: 'To do', color: 'blue' },
    })
  })

  test('dropping a card on its own column is a no-op (AC #5)', async () => {
    const vm = makeVm()
    const row = aRow(10, { id: 1, value: 'To do', color: 'blue' }) // "To do"
    vm.draggingRow = row

    await vm.onDrop(toDoColumn) // same column

    expect(vm.dispatched).toHaveLength(0)
  })

  test('an Uncategorized card dropped back on Uncategorized is a no-op (both null equal, AC #5)', async () => {
    const vm = makeVm()
    const row = aRow(12, null) // currently Uncategorized
    vm.draggingRow = row

    await vm.onDrop(uncategorizedColumn)

    expect(vm.dispatched).toHaveLength(0)
  })

  test('when readOnly, a drop dispatches nothing (AC #4)', async () => {
    const vm = makeVm({ readOnly: true })
    const row = aRow(10, { id: 1, value: 'To do', color: 'blue' })
    vm.draggingRow = row

    await vm.onDrop(doneColumn)

    expect(vm.dispatched).toHaveLength(0)
  })

  test('when the grouping field is not editable, a drop dispatches nothing (AC #4)', async () => {
    const vm = makeVm({ canWrite: false })
    const row = aRow(10, { id: 1, value: 'To do', color: 'blue' })
    vm.draggingRow = row

    await vm.onDrop(doneColumn)

    expect(vm.dispatched).toHaveLength(0)
  })

  test('when no grouping field is configured, a drop dispatches nothing (AC #4)', async () => {
    // canDrag is false when singleSelectField is null, so onDrop short-circuits
    // before resolving any field key — proving drag is a no-op on an
    // unconfigured board.
    const vm = makeVm({ field: null })
    const row = aRow(10, { id: 1, value: 'To do', color: 'blue' })
    vm.draggingRow = row

    await vm.onDrop(doneColumn)

    expect(vm.dispatched).toHaveLength(0)
  })

  test('a drop with no drag in progress is a safe no-op', async () => {
    // Defensive: a stray `drop` event with no tracked row (draggingRow === null)
    // must not throw or dispatch.
    const vm = makeVm()
    vm.draggingRow = null

    // The guard short-circuits synchronously (returns undefined, no promise) and
    // must not throw or dispatch.
    expect(() => vm.onDrop(doneColumn)).not.toThrow()
    expect(vm.onDrop(doneColumn)).toBeUndefined()
    expect(vm.dispatched).toHaveLength(0)
  })

  test('a rejected server update is caught and surfaced via notifyIf (AC #3)', async () => {
    const notifyIf = vi.fn()
    // bufferedRows re-throws the original error after rolling back; updateValue
    // catches it and routes it to notifyIf. A Baserow error carries a `.handler`
    // whose notifyIf surfaces the toast.
    const rejectingDispatch = () => Promise.reject({ handler: { notifyIf } })
    const vm = makeVm({ dispatch: rejectingDispatch })
    const row = aRow(10, { id: 1, value: 'To do', color: 'blue' })
    vm.draggingRow = row

    // Must not throw — the error is swallowed/surfaced, not propagated.
    await expect(vm.onDrop(doneColumn)).resolves.toBeUndefined()
    expect(notifyIf).toHaveBeenCalledWith('field')
  })

  test('after a rejected drop the dragged row grouping value is left unchanged (rollback, AC #3)', async () => {
    // onDrop/updateValue never mutate the row cell directly — the optimistic
    // commit and its rollback live in bufferedRows. So on rejection the row
    // object the component holds must be exactly its origin value; the store is
    // the single source of truth for the optimistic move + snap-back. This
    // guards against the anti-pattern of the component splicing the value itself
    // (which would desync from rollback).
    const origin = { id: 1, value: 'To do', color: 'blue' }
    const rejectingDispatch = () =>
      Promise.reject({ handler: { notifyIf() {} } })
    const vm = makeVm({ dispatch: rejectingDispatch })
    const row = aRow(10, origin)
    vm.draggingRow = row

    await vm.onDrop(doneColumn)

    // The component left the cell to the store; it is still the origin option.
    expect(row.field_2).toEqual(origin)
  })
})
