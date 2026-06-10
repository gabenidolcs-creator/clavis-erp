import { vi } from 'vitest'
import { TestApp } from '@baserow/test/helpers/testApp'
import { KanbanViewType } from '@baserow/modules/database/viewTypes'
import KanbanView, {
  groupRowsBySingleSelect,
} from '@baserow/modules/database/components/view/kanban/KanbanView'
import KanbanViewHeader from '@baserow/modules/database/components/view/kanban/KanbanViewHeader'

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

// Story 3.3 — card appearance. The card-face field selection (`hidden`/`order`
// field options) and the cover image were inherited from the Gallery-derived
// core Kanban view in Story 3.1. These tests pin the EXISTING behavior:
// `cardFields`/`hiddenFields`/`coverImageField` computeds drive what `RowCard`
// renders. Driven against a minimal instance for the same reason as the drag
// tests above — a full mount pulls in the premium kanban store (registers last,
// overrides core) and would leave the free-core surface / clean room.
describe('KanbanView card appearance computeds', () => {
  const textField = { id: 11, name: 'Name', type: 'text', primary: true }
  const statusField = { id: 12, name: 'Status', type: 'single_select' }
  const notesField = { id: 13, name: 'Notes', type: 'long_text' }
  const coverField = { id: 14, name: 'Cover', type: 'file' }

  // Binds the real `cardFields`/`hiddenFields`/`coverImageField` computeds to a
  // minimal instance. `fieldOptions` is supplied directly (it is itself a
  // store-backed computed in the component; the appearance computeds only read
  // `this.fieldOptions`).
  const makeVm = ({ fields, fieldOptions, view = {} } = {}) => {
    const vm = { fields, fieldOptions, view }
    for (const name of ['cardFields', 'hiddenFields', 'coverImageField']) {
      Object.defineProperty(vm, name, { get: KanbanView.computed[name] })
    }
    return vm
  }

  test('cardFields excludes hidden fields and orders by option order then id (AC #1)', () => {
    const vm = makeVm({
      fields: [textField, statusField, notesField],
      fieldOptions: {
        11: { hidden: false, order: 2 },
        12: { hidden: false, order: 1 },
        13: { hidden: true, order: 3 },
      },
    })

    // notesField (13) is hidden → excluded. status (order 1) before name (order 2).
    expect(vm.cardFields.map((f) => f.id)).toEqual([12, 11])
  })

  test('a field without a field option is treated as hidden (AC #1)', () => {
    const vm = makeVm({
      fields: [textField, statusField],
      fieldOptions: { 11: { hidden: false, order: 0 } },
    })

    expect(vm.cardFields.map((f) => f.id)).toEqual([11])
    expect(vm.hiddenFields.map((f) => f.id)).toEqual([12])
  })

  test('hiddenFields is the complement of cardFields (AC #1)', () => {
    const vm = makeVm({
      fields: [textField, statusField, notesField],
      fieldOptions: {
        11: { hidden: false, order: 0 },
        12: { hidden: true, order: 1 },
        13: { hidden: true, order: 2 },
      },
    })

    expect(vm.cardFields.map((f) => f.id)).toEqual([11])
    expect(vm.hiddenFields.map((f) => f.id)).toEqual([12, 13])
  })

  test('coverImageField resolves view.card_cover_image_field to the field object (AC #1)', () => {
    const vm = makeVm({
      fields: [textField, coverField],
      fieldOptions: {},
      view: { card_cover_image_field: 14 },
    })

    expect(vm.coverImageField).toBe(coverField)
  })

  test('coverImageField is null when unset or pointing at a missing field (AC #1)', () => {
    expect(
      makeVm({
        fields: [textField, coverField],
        fieldOptions: {},
        view: { card_cover_image_field: null },
      }).coverImageField
    ).toBe(null)

    expect(
      makeVm({
        fields: [textField],
        fieldOptions: {},
        view: { card_cover_image_field: 999 },
      }).coverImageField
    ).toBe(null)
  })
})

// Story 3.3 — the "Customize cards" header (already wired in 3.1) dispatches the
// two distinct persistence paths: the cover image via the GENERIC `view/update`
// and the field options (hidden/order) via the kanban store actions. Each is
// guarded by readOnly OR a missing update_field_options permission. Driven at
// the method level (no mount) to stay on the free-core surface.
describe('KanbanViewHeader card-appearance dispatch', () => {
  const makeVm = ({ readOnly = false, hasPermission = true } = {}) => {
    const dispatched = []
    const vm = {
      readOnly,
      storePrefix: 'page/',
      view: { id: 5 },
      database: { workspace: { id: 9 } },
      dispatched,
      $store: {
        dispatch: (action, payload) => {
          dispatched.push({ action, payload })
          return Promise.resolve()
        },
      },
      $hasPermission: () => hasPermission,
    }
    for (const name of [
      'updateCoverImageField',
      'updateFieldOptionsOfField',
      'orderFieldOptions',
      'updateAllFieldOptions',
    ]) {
      vm[name] = KanbanViewHeader.methods[name].bind(vm)
    }
    return vm
  }

  test('updateCoverImageField dispatches the generic view/update with card_cover_image_field (AC #2)', async () => {
    const vm = makeVm()
    await vm.updateCoverImageField(14)

    expect(vm.dispatched).toHaveLength(1)
    expect(vm.dispatched[0].action).toBe('view/update')
    expect(vm.dispatched[0].payload).toMatchObject({
      view: vm.view,
      values: { card_cover_image_field: 14 },
      readOnly: false,
    })
  })

  test('updateCoverImageField passes null to clear the cover (AC #2)', async () => {
    const vm = makeVm()
    await vm.updateCoverImageField(null)

    expect(vm.dispatched[0].payload.values).toEqual({
      card_cover_image_field: null,
    })
  })

  test('updateFieldOptionsOfField dispatches the kanban store action with the readOnly/permission guard (AC #2)', async () => {
    const vm = makeVm()
    const field = { id: 12 }
    await vm.updateFieldOptionsOfField({
      field,
      values: { hidden: true },
      oldValues: { hidden: false },
    })

    expect(vm.dispatched).toHaveLength(1)
    expect(vm.dispatched[0].action).toBe(
      'page/view/kanban/updateFieldOptionsOfField'
    )
    expect(vm.dispatched[0].payload).toMatchObject({
      field,
      values: { hidden: true },
      readOnly: false,
    })
  })

  test('orderFieldOptions dispatches the kanban store reorder action (AC #2)', async () => {
    const vm = makeVm()
    await vm.orderFieldOptions({ order: [12, 11, 13] })

    expect(vm.dispatched[0].action).toBe(
      'page/view/kanban/updateFieldOptionsOrder'
    )
    expect(vm.dispatched[0].payload).toMatchObject({
      order: [12, 11, 13],
      readOnly: false,
    })
  })

  test('field-option dispatches carry readOnly=true when the view is read-only (AC #2)', async () => {
    const vm = makeVm({ readOnly: true })
    await vm.updateFieldOptionsOfField({
      field: { id: 12 },
      values: { hidden: true },
      oldValues: { hidden: false },
    })

    expect(vm.dispatched[0].payload.readOnly).toBe(true)
  })

  test('field-option dispatches carry readOnly=true when the update permission is missing (AC #2)', async () => {
    const vm = makeVm({ hasPermission: false })
    await vm.orderFieldOptions({ order: [11, 12] })

    expect(vm.dispatched[0].payload.readOnly).toBe(true)
  })
})
