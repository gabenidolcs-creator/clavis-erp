import { vi } from 'vitest'
import moment from '@baserow/modules/core/moment'
import { TestApp } from '@baserow/test/helpers/testApp'
import { TimelineViewType } from '@baserow/modules/database/viewTypes'
import TimelineView, {
  timelineUnit,
  parseTimelineValue,
  partitionTimelineRows,
  computeAxisRange,
  axisUnitCount,
  computeTicks,
  barGeometry,
} from '@baserow/modules/database/components/view/timeline/TimelineView'
import TimelineViewHeader from '@baserow/modules/database/components/view/timeline/TimelineViewHeader'

describe('TimelineViewType', () => {
  let testApp

  beforeAll(() => {
    testApp = new TestApp()
  })

  afterEach(() => {
    testApp.afterEach()
  })

  test('getType returns timeline', () => {
    expect(TimelineViewType.getType()).toBe('timeline')
  })

  test('exposes the core name and icon', () => {
    // NOTE: in an open-core build that also loads the premium plugin, the
    // premium Timeline view registers later and overrides this core view in the
    // registry (premium takes precedence). The TestApp loads premium, so we
    // assert against the core class directly rather than the registry entry.
    const viewType = new TimelineViewType({ app: testApp.getApp() })
    expect(viewType.getType()).toBe('timeline')
    expect(viewType.getIconClass()).toBe('baserow-icon-timeline')
    // i18n is mocked in vitest.setup.ts so `t` echoes the translation key.
    expect(viewType.getName()).toBe('viewType.timeline')
  })
})

// timelineUnit maps the persisted zoom level to the moment unit all axis/bar
// arithmetic uses; an unknown value falls back to month.
describe('timelineUnit', () => {
  test.each([
    ['day', 'day'],
    ['week', 'isoWeek'],
    ['month', 'month'],
  ])('maps %s to %s', (timescale, unit) => {
    expect(timelineUnit(timescale)).toBe(unit)
  })

  test('falls back to month for an unknown timescale', () => {
    expect(timelineUnit('century')).toBe('month')
    expect(timelineUnit(undefined)).toBe('month')
  })
})

// parseTimelineValue is the gate that decides whether a date cell contributes a
// (parseable) moment or is treated as missing.
describe('parseTimelineValue', () => {
  test('parses a plain date string', () => {
    expect(parseTimelineValue('2026-06-10').isValid()).toBe(true)
  })

  test('parses a datetime string', () => {
    expect(parseTimelineValue('2026-06-10T14:30:00Z').isValid()).toBe(true)
  })

  test.each([null, undefined, ''])('returns null for empty value %s', (v) => {
    expect(parseTimelineValue(v)).toBe(null)
  })

  test('returns null for an unparseable value', () => {
    expect(parseTimelineValue('not-a-date')).toBe(null)
  })
})

// partitionTimelineRows is the net-new partition versus the calendar: a row is
// SCHEDULED (a bar) only when BOTH start AND end are present; missing either
// sends it to the unscheduled tray. (AC #2 / #4)
describe('partitionTimelineRows', () => {
  const startField = { id: 5 }
  const endField = { id: 6 }

  test('a row with both start and end is scheduled', () => {
    const row = { id: 1, field_5: '2026-06-10', field_6: '2026-06-12' }
    const { scheduled, unscheduled } = partitionTimelineRows(
      [row],
      startField,
      endField
    )
    expect(scheduled.map((r) => r.id)).toEqual([1])
    expect(unscheduled).toHaveLength(0)
  })

  test('a row missing the end value goes to the tray (AC #4)', () => {
    const row = { id: 2, field_5: '2026-06-10', field_6: null }
    const { scheduled, unscheduled } = partitionTimelineRows(
      [row],
      startField,
      endField
    )
    expect(scheduled).toHaveLength(0)
    expect(unscheduled.map((r) => r.id)).toEqual([2])
  })

  test('a row missing the start value goes to the tray (AC #4)', () => {
    const row = { id: 3, field_5: null, field_6: '2026-06-12' }
    const { scheduled, unscheduled } = partitionTimelineRows(
      [row],
      startField,
      endField
    )
    expect(scheduled).toHaveLength(0)
    expect(unscheduled.map((r) => r.id)).toEqual([3])
  })

  test('a row missing both values goes to the tray', () => {
    const row = { id: 4, field_5: null, field_6: null }
    const { scheduled, unscheduled } = partitionTimelineRows(
      [row],
      startField,
      endField
    )
    expect(scheduled).toHaveLength(0)
    expect(unscheduled.map((r) => r.id)).toEqual([4])
  })

  test('unfetched null row placeholders are skipped entirely', () => {
    const row = { id: 5, field_5: '2026-06-10', field_6: '2026-06-12' }
    const { scheduled, unscheduled } = partitionTimelineRows(
      [null, row],
      startField,
      endField
    )
    expect(scheduled.map((r) => r.id)).toEqual([5])
    expect(unscheduled).toHaveLength(0)
  })
})

// computeAxisRange / axisUnitCount / computeTicks build the horizontal axis from
// the scheduled rows, snapped to the timescale unit. (AC #3)
describe('computeAxisRange', () => {
  const startField = { id: 5 }
  const endField = { id: 6 }

  test('spans min(start)..max(end) snapped to month boundaries', () => {
    const rows = [
      { id: 1, field_5: '2026-01-15', field_6: '2026-01-20' },
      { id: 2, field_5: '2026-02-10', field_6: '2026-03-05' },
    ]
    const { rangeStart, rangeEnd } = computeAxisRange(
      rows,
      startField,
      endField,
      'month',
      moment('2026-06-10')
    )
    expect(rangeStart.format('YYYY-MM-DD')).toBe('2026-01-01')
    expect(rangeEnd.format('YYYY-MM-DD')).toBe('2026-03-31')
    expect(axisUnitCount(rangeStart, rangeEnd, 'month')).toBe(3)
  })

  test('a reversed row does not widen the range past its start', () => {
    const rows = [{ id: 1, field_5: '2026-02-10', field_6: '2026-01-01' }]
    const { rangeStart, rangeEnd } = computeAxisRange(
      rows,
      startField,
      endField,
      'month',
      moment('2026-06-10')
    )
    expect(rangeStart.format('YYYY-MM')).toBe('2026-02')
    expect(rangeEnd.format('YYYY-MM')).toBe('2026-02')
  })

  test('falls back to a window around today when no rows are scheduled', () => {
    const { rangeStart, rangeEnd } = computeAxisRange(
      [],
      startField,
      endField,
      'month',
      moment('2026-06-10')
    )
    expect(rangeStart.format('YYYY-MM-DD')).toBe('2026-06-01')
    expect(rangeEnd.format('YYYY-MM-DD')).toBe('2026-06-30')
  })

  test('day timescale produces one tick per day', () => {
    const rows = [{ id: 1, field_5: '2026-06-10', field_6: '2026-06-14' }]
    const { rangeStart, rangeEnd } = computeAxisRange(
      rows,
      startField,
      endField,
      'day',
      moment('2026-06-10')
    )
    expect(axisUnitCount(rangeStart, rangeEnd, 'day')).toBe(5)
    expect(computeTicks(rangeStart, rangeEnd, 'day')).toHaveLength(5)
  })
})

describe('computeTicks', () => {
  test('ticks are evenly spaced and cover the full axis', () => {
    const rangeStart = moment('2026-01-01')
    const rangeEnd = moment('2026-03-31')
    const ticks = computeTicks(rangeStart, rangeEnd, 'month')
    expect(ticks).toHaveLength(3)
    expect(ticks[0].left).toBeCloseTo(0)
    expect(ticks[1].left).toBeCloseTo(100 / 3)
    expect(ticks[2].left).toBeCloseTo(200 / 3)
    expect(ticks.every((t) => t.width === 100 / 3)).toBe(true)
  })
})

// barGeometry is the net-new positioning keystone: it maps a row's start..end
// onto the axis as { left, width } percentages. Kept pure so it is unit-tested
// directly and reused by Story 3.7's drag/resize maths. (AC #2)
describe('barGeometry', () => {
  test('a single-unit row at the range start is a full-width bar (total = 1)', () => {
    const { left, width } = barGeometry(
      moment('2026-06-10'),
      moment('2026-06-10'),
      moment('2026-06-01'),
      1,
      'month'
    )
    expect(left).toBeCloseTo(0)
    expect(width).toBeCloseTo(100)
  })

  test('a multi-unit row spans width ≈ span / total', () => {
    // 2026-06-10 .. 2026-06-12 over a 5-day axis starting 2026-06-10.
    const { left, width } = barGeometry(
      moment('2026-06-10'),
      moment('2026-06-12'),
      moment('2026-06-10'),
      5,
      'day'
    )
    expect(left).toBeCloseTo(0)
    expect(width).toBeCloseTo(60) // 3 of 5 days
  })

  test('the bar is offset by the units between range start and its start', () => {
    const { left, width } = barGeometry(
      moment('2026-06-12'),
      moment('2026-06-12'),
      moment('2026-06-10'),
      5,
      'day'
    )
    expect(left).toBeCloseTo(40) // 2 of 5 days
    expect(width).toBeCloseTo(20) // 1 of 5 days
  })

  test('end < start clamps to a 1-unit bar without throwing', () => {
    let result
    expect(() => {
      result = barGeometry(
        moment('2026-06-12'),
        moment('2026-06-10'),
        moment('2026-06-10'),
        5,
        'day'
      )
    }).not.toThrow()
    expect(result.width).toBeCloseTo(20) // clamped to 1 of 5 days
  })

  test('a null end clamps to a 1-unit bar', () => {
    const { width } = barGeometry(
      moment('2026-06-10'),
      null,
      moment('2026-06-10'),
      5,
      'day'
    )
    expect(width).toBeCloseTo(20)
  })
})

// Field-resolution computeds. Driven against a minimal instance rather than a
// full mount: a full mount pulls in the `page/view/timeline` store, which in the
// open-core test build is the PREMIUM timeline store (it registers last and
// overrides core). Driving the computeds directly keeps the test in the core
// (clean-room) surface.
describe('TimelineView field-resolution computeds', () => {
  const startField = { id: 5, name: 'Start', type: 'date' }
  const endField = { id: 6, name: 'End', type: 'date' }
  const textField = { id: 7, name: 'Name', type: 'text' }

  const makeVm = ({ fields, view = {} } = {}) => {
    const vm = { fields, view }
    for (const name of [
      'startDateField',
      'endDateField',
      'timescale',
      'coverImageField',
    ]) {
      Object.defineProperty(vm, name, {
        get: TimelineView.computed[name],
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

  test('coverImageField is always null — the timeline card has no cover', () => {
    expect(makeVm({ fields: [startField], view: {} }).coverImageField).toBe(
      null
    )
  })
})

// TimelineView.updateValue reuses the existing optimistic updateRowValue path of
// the timeline store. Driven at the method level (no mount).
describe('TimelineView.updateValue', () => {
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
    vm.updateValue = TimelineView.methods.updateValue.bind(vm)
    return vm
  }

  test('dispatches the timeline updateRowValue action', async () => {
    const vm = makeVm()
    const row = { id: 10, field_5: '2026-06-10' }
    await vm.updateValue({
      field: startField,
      row,
      value: '2026-06-12',
      oldValue: '2026-06-10',
    })

    expect(vm.dispatched).toHaveLength(1)
    expect(vm.dispatched[0].action).toBe('page/view/timeline/updateRowValue')
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

// TimelineViewHeader dispatches the start/end positioning fields and the zoom
// level via the GENERIC `view/update` (so timescale round-trips, AC #3), and the
// field options via the timeline store actions (each guarded by readOnly OR a
// missing update_field_options permission). Driven at the method level.
describe('TimelineViewHeader dispatch', () => {
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
      vm[name] = TimelineViewHeader.methods[name].bind(vm)
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

  test('updateTimescale dispatches the generic view/update so the zoom persists (AC #3)', async () => {
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

  test('updateFieldOptionsOfField dispatches the timeline store action with the guard (AC #5)', async () => {
    const vm = makeVm()
    const field = { id: 7 }
    await vm.updateFieldOptionsOfField({
      field,
      values: { hidden: true },
      oldValues: { hidden: false },
    })

    expect(vm.dispatched[0].action).toBe(
      'page/view/timeline/updateFieldOptionsOfField'
    )
    expect(vm.dispatched[0].payload).toMatchObject({
      field,
      values: { hidden: true },
      readOnly: false,
    })
  })

  test('orderFieldOptions dispatches the timeline reorder action (AC #5)', async () => {
    const vm = makeVm()
    await vm.orderFieldOptions({ order: [7, 5, 6] })

    expect(vm.dispatched[0].action).toBe(
      'page/view/timeline/updateFieldOptionsOrder'
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
