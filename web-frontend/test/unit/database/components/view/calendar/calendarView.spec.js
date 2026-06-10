import { vi } from 'vitest'
import { TestApp } from '@baserow/test/helpers/testApp'
import { CalendarViewType } from '@baserow/modules/database/viewTypes'
import CalendarView, {
  rowDateKey,
  buildCalendarDays,
  groupRowsByDate,
} from '@baserow/modules/database/components/view/calendar/CalendarView'
import CalendarViewHeader from '@baserow/modules/database/components/view/calendar/CalendarViewHeader'

describe('CalendarViewType', () => {
  let testApp

  beforeAll(() => {
    testApp = new TestApp()
  })

  afterEach(() => {
    testApp.afterEach()
  })

  test('getType returns calendar', () => {
    expect(CalendarViewType.getType()).toBe('calendar')
  })

  test('exposes the core name and icon', () => {
    // NOTE: in an open-core build that also loads the premium plugin, the
    // premium Calendar view registers later and overrides this core view in the
    // registry (premium takes precedence). The TestApp loads premium, so we
    // assert against the core class directly rather than the registry entry.
    const viewType = new CalendarViewType({ app: testApp.getApp() })
    expect(viewType.getType()).toBe('calendar')
    expect(viewType.getIconClass()).toBe('baserow-icon-calendar')
    // i18n is mocked in vitest.setup.ts so `t` echoes the translation key.
    expect(viewType.getName()).toBe('viewType.calendar')
  })

  test('the registry resolves a calendar view type', () => {
    const viewType = testApp.getApp().$registry.get('view', 'calendar')
    expect(viewType.getType()).toBe('calendar')
  })
})

// rowDateKey is the gate that decides whether a row is scheduled (placed on the
// grid) or shown in the unscheduled tray. It normalizes any date/datetime cell
// value to a `YYYY-MM-DD` key or null.
describe('rowDateKey', () => {
  test('normalizes a plain date string to a day key', () => {
    expect(rowDateKey('2026-06-10')).toBe('2026-06-10')
  })

  test('normalizes a datetime value to its day key', () => {
    expect(rowDateKey('2026-06-10T14:30:00Z')).toBe('2026-06-10')
  })

  test.each([null, undefined, ''])(
    'returns null for the empty value %s',
    (value) => {
      expect(rowDateKey(value)).toBe(null)
    }
  )

  test('returns null for an unparseable value', () => {
    expect(rowDateKey('not-a-date')).toBe(null)
  })
})

// buildCalendarDays is the only net-new positioning concept versus the kanban
// board: it lays out the ordered day cells for the grid in month or week mode.
describe('buildCalendarDays', () => {
  test('month mode lays out the full monthly grid and flags the in-period days', () => {
    const days = buildCalendarDays('2026-06-10', 'month', '2026-06-10')

    // Every day belonging to June is flagged in the current period; June has 30.
    const juneDays = days.filter((d) => d.key.startsWith('2026-06'))
    expect(juneDays.every((d) => d.inCurrentPeriod)).toBe(true)
    expect(days.filter((d) => d.inCurrentPeriod)).toHaveLength(30)

    // Leading/trailing days from the neighbouring months are not in-period.
    const outside = days.filter((d) => !d.key.startsWith('2026-06'))
    expect(outside.every((d) => !d.inCurrentPeriod)).toBe(true)

    // The reference day is present, labelled with its day-of-month, and today.
    const tenth = days.find((d) => d.key === '2026-06-10')
    expect(tenth).toBeDefined()
    expect(tenth.label).toBe(10)
    expect(tenth.isToday).toBe(true)
  })

  test('week mode lays out the ISO week containing the reference date', () => {
    const days = buildCalendarDays('2026-06-10', 'week', '2026-06-10')

    // ISO week = Monday..Sunday → 7 cells, all in-period.
    expect(days).toHaveLength(7)
    expect(days.every((d) => d.inCurrentPeriod)).toBe(true)
    // 2026-06-10 is a Wednesday; the week starts on Monday 2026-06-08.
    expect(days[0].key).toBe('2026-06-08')
    expect(days[6].key).toBe('2026-06-14')
    expect(days.map((d) => d.key)).toContain('2026-06-10')
  })

  test('isToday is only set for the matching todayKey', () => {
    const days = buildCalendarDays('2026-06-10', 'week', '2026-06-11')
    expect(days.filter((d) => d.isToday).map((d) => d.key)).toEqual([
      '2026-06-11',
    ])
  })
})

// groupRowsByDate buckets rows onto the visible day cells, sends undated rows to
// the unscheduled tray, and spans multi-day events across each of their days.
describe('groupRowsByDate', () => {
  const dateField = { id: 5 }
  const endDateField = { id: 6 }
  const days = [
    { key: '2026-06-10' },
    { key: '2026-06-11' },
    { key: '2026-06-12' },
  ]

  test('a dated row is bucketed on its day', () => {
    const row = { id: 1, field_5: '2026-06-11' }
    const { rowsByDay, unscheduled } = groupRowsByDate(
      [row],
      dateField,
      null,
      days
    )
    expect(rowsByDay['2026-06-11'].map((r) => r.id)).toEqual([1])
    expect(unscheduled).toHaveLength(0)
  })

  test('a row with no date value lands in the unscheduled tray', () => {
    const row = { id: 2, field_5: null }
    const { rowsByDay, unscheduled } = groupRowsByDate(
      [row],
      dateField,
      null,
      days
    )
    expect(unscheduled.map((r) => r.id)).toEqual([2])
    expect(Object.keys(rowsByDay)).toHaveLength(0)
  })

  test('a datetime value is bucketed on its calendar day', () => {
    const row = { id: 3, field_5: '2026-06-12T23:00:00Z' }
    const { rowsByDay } = groupRowsByDate([row], dateField, null, days)
    expect(rowsByDay['2026-06-12'].map((r) => r.id)).toEqual([3])
  })

  test('an end-date field spans the row across every visible day in range', () => {
    const row = { id: 4, field_5: '2026-06-10', field_6: '2026-06-12' }
    const { rowsByDay } = groupRowsByDate(
      [row],
      dateField,
      endDateField,
      days
    )
    expect(rowsByDay['2026-06-10'].map((r) => r.id)).toEqual([4])
    expect(rowsByDay['2026-06-11'].map((r) => r.id)).toEqual([4])
    expect(rowsByDay['2026-06-12'].map((r) => r.id)).toEqual([4])
  })

  test('an end date earlier than the start is ignored (single-day placement)', () => {
    const row = { id: 5, field_5: '2026-06-11', field_6: '2026-06-10' }
    const { rowsByDay } = groupRowsByDate(
      [row],
      dateField,
      endDateField,
      days
    )
    expect(rowsByDay['2026-06-11'].map((r) => r.id)).toEqual([5])
    expect(rowsByDay['2026-06-10']).toBeUndefined()
  })

  test('a scheduled row whose whole span is outside the grid is neither shown nor unscheduled', () => {
    const row = { id: 6, field_5: '2026-07-01' }
    const { rowsByDay, unscheduled } = groupRowsByDate(
      [row],
      dateField,
      null,
      days
    )
    expect(Object.keys(rowsByDay)).toHaveLength(0)
    expect(unscheduled).toHaveLength(0)
  })

  test('unfetched null row placeholders are skipped', () => {
    const row = { id: 7, field_5: '2026-06-10' }
    const { rowsByDay, unscheduled } = groupRowsByDate(
      [null, row],
      dateField,
      null,
      days
    )
    expect(rowsByDay['2026-06-10'].map((r) => r.id)).toEqual([7])
    expect(unscheduled).toHaveLength(0)
  })
})

// CalendarView field-resolution computeds. Driven against a minimal instance
// rather than a full mount: a full mount pulls in the `page/view/calendar`
// store, which in the open-core test build is the PREMIUM calendar store (it
// registers last and overrides core). Driving the computeds directly keeps the
// test in the core (clean-room) surface.
describe('CalendarView field-resolution computeds', () => {
  const dateField = { id: 5, name: 'Due', type: 'date' }
  const endField = { id: 6, name: 'End', type: 'date' }
  const textField = { id: 7, name: 'Name', type: 'text' }

  const makeVm = ({ fields, view = {} } = {}) => {
    const vm = { fields, view }
    for (const name of ['dateField', 'endDateField', 'coverImageField']) {
      Object.defineProperty(vm, name, { get: CalendarView.computed[name] })
    }
    return vm
  }

  test('dateField resolves view.date_field to the field object', () => {
    const vm = makeVm({
      fields: [dateField, textField],
      view: { date_field: 5 },
    })
    expect(vm.dateField).toBe(dateField)
  })

  test('dateField is null when unset or pointing at a missing field', () => {
    expect(
      makeVm({ fields: [dateField], view: { date_field: null } }).dateField
    ).toBe(null)
    expect(
      makeVm({ fields: [dateField], view: { date_field: 999 } }).dateField
    ).toBe(null)
  })

  test('endDateField resolves view.end_date_field to the field object', () => {
    const vm = makeVm({
      fields: [dateField, endField],
      view: { end_date_field: 6 },
    })
    expect(vm.endDateField).toBe(endField)
  })

  test('endDateField is null when unset', () => {
    expect(
      makeVm({ fields: [dateField], view: { end_date_field: null } })
        .endDateField
    ).toBe(null)
  })

  test('coverImageField is always null — the calendar card has no cover', () => {
    expect(makeVm({ fields: [dateField], view: {} }).coverImageField).toBe(null)
  })
})

// CalendarView.updateValue reuses the existing optimistic updateRowValue path
// of the calendar store. Driven at the method level (no mount).
describe('CalendarView.updateValue', () => {
  const dateField = { id: 5, type: 'date' }

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
      fields: [dateField],
      dispatched,
      $store: { dispatch: dispatch || recordingDispatch },
    }
    vm.updateValue = CalendarView.methods.updateValue.bind(vm)
    return vm
  }

  test('dispatches the calendar updateRowValue action with the moved value', async () => {
    const vm = makeVm()
    const row = { id: 10, field_5: '2026-06-10' }
    await vm.updateValue({
      field: dateField,
      row,
      value: '2026-06-12',
      oldValue: '2026-06-10',
    })

    expect(vm.dispatched).toHaveLength(1)
    expect(vm.dispatched[0].action).toBe('page/view/calendar/updateRowValue')
    expect(vm.dispatched[0].payload).toMatchObject({
      table: vm.table,
      view: vm.view,
      field: dateField,
      row,
      value: '2026-06-12',
      oldValue: '2026-06-10',
    })
  })

  test('a rejected server update is caught and surfaced via notifyIf', async () => {
    const notifyIf = vi.fn()
    const rejectingDispatch = () => Promise.reject({ handler: { notifyIf } })
    const vm = makeVm({ dispatch: rejectingDispatch })

    // Must not throw — the error is swallowed/surfaced, not propagated.
    await expect(
      vm.updateValue({
        field: dateField,
        row: { id: 10 },
        value: '2026-06-12',
        oldValue: '2026-06-10',
      })
    ).resolves.toBeUndefined()
    expect(notifyIf).toHaveBeenCalledWith('field')
  })
})

// CalendarViewHeader dispatches the positioning-field config via the GENERIC
// `view/update`, the display mode via the calendar store, and the field options
// via the calendar store actions (each guarded by readOnly OR a missing
// update_field_options permission). Driven at the method level (no mount).
describe('CalendarViewHeader dispatch', () => {
  const makeVm = ({ readOnly = false, hasPermission = true } = {}) => {
    const dispatched = []
    const vm = {
      readOnly,
      storePrefix: 'page/',
      view: { id: 5 },
      database: { workspace: { id: 9 } },
      dispatched,
      updatingDateField: false,
      updatingEndDateField: false,
      $refs: { dateFieldContext: { hide() {} } },
      $store: {
        dispatch: (action, payload) => {
          dispatched.push({ action, payload })
          return Promise.resolve()
        },
      },
      $hasPermission: () => hasPermission,
    }
    for (const name of [
      'updateDisplayMode',
      'updateDateField',
      'updateEndDateField',
      'updateAllFieldOptions',
      'updateFieldOptionsOfField',
      'orderFieldOptions',
    ]) {
      vm[name] = CalendarViewHeader.methods[name].bind(vm)
    }
    return vm
  }

  test('updateDateField dispatches the generic view/update with date_field (AC #3)', async () => {
    const vm = makeVm()
    await vm.updateDateField(5)

    expect(vm.dispatched).toHaveLength(1)
    expect(vm.dispatched[0].action).toBe('view/update')
    expect(vm.dispatched[0].payload).toMatchObject({
      view: vm.view,
      values: { date_field: 5 },
      readOnly: false,
    })
  })

  test('updateDateField passes null to clear the positioning field', async () => {
    const vm = makeVm()
    await vm.updateDateField(null)
    expect(vm.dispatched[0].payload.values).toEqual({ date_field: null })
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

  test('updateDisplayMode dispatches the calendar setDisplayMode action (AC #3)', () => {
    const vm = makeVm()
    vm.updateDisplayMode('week')

    expect(vm.dispatched).toHaveLength(1)
    expect(vm.dispatched[0].action).toBe('page/view/calendar/setDisplayMode')
    expect(vm.dispatched[0].payload).toBe('week')
  })

  test('updateFieldOptionsOfField dispatches the calendar store action with the guard (AC #5)', async () => {
    const vm = makeVm()
    const field = { id: 7 }
    await vm.updateFieldOptionsOfField({
      field,
      values: { hidden: true },
      oldValues: { hidden: false },
    })

    expect(vm.dispatched[0].action).toBe(
      'page/view/calendar/updateFieldOptionsOfField'
    )
    expect(vm.dispatched[0].payload).toMatchObject({
      field,
      values: { hidden: true },
      readOnly: false,
    })
  })

  test('orderFieldOptions dispatches the calendar reorder action (AC #5)', async () => {
    const vm = makeVm()
    await vm.orderFieldOptions({ order: [7, 5, 6] })

    expect(vm.dispatched[0].action).toBe(
      'page/view/calendar/updateFieldOptionsOrder'
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
