import { describe, it, expect, vi, beforeEach } from 'vitest'
import { registerRealtimeEvents } from '@baserow/modules/dashboard/realtime'
import { actions } from '@baserow/modules/dashboard/store/dashboardApplication'

function makeStore({ dashboardId = 1, dataSources = [] } = {}) {
  return {
    getters: {
      'dashboardApplication/getDashboardId': dashboardId,
    },
    state: {
      dashboardApplication: { dataSources },
    },
    dispatch: vi.fn().mockResolvedValue(undefined),
  }
}

function makeRealtime() {
  const handlers = {}
  return {
    registerEvent: vi.fn((event, handler) => {
      handlers[event] = handler
    }),
    trigger(event, store, data) {
      if (handlers[event]) handlers[event]({ store }, data)
    },
  }
}

describe('dashboard realtime row-event invalidation', () => {
  let realtime

  beforeEach(() => {
    realtime = makeRealtime()
    registerRealtimeEvents(realtime)
  })

  it('registers rows_created, rows_updated, rows_deleted handlers', () => {
    const names = realtime.registerEvent.mock.calls.map((c) => c[0])
    expect(names).toContain('rows_created')
    expect(names).toContain('rows_updated')
    expect(names).toContain('rows_deleted')
  })

  it('rows_created with matching table_id dispatches invalidateDataSourcesForTable', () => {
    const store = makeStore({
      dashboardId: 1,
      dataSources: [{ id: 10, table_id: 42 }],
    })
    realtime.trigger('rows_created', store, { table_id: 42 })
    expect(store.dispatch).toHaveBeenCalledWith(
      'dashboardApplication/invalidateDataSourcesForTable',
      42
    )
  })

  it('rows_created with non-matching table_id does not dispatch', () => {
    const store = makeStore({
      dashboardId: 1,
      dataSources: [{ id: 10, table_id: 42 }],
    })
    realtime.trigger('rows_created', store, { table_id: 99 })
    expect(store.dispatch).not.toHaveBeenCalled()
  })

  it('does not dispatch when no dashboard is active (dashboardId null)', () => {
    const store = makeStore({
      dashboardId: null,
      dataSources: [{ id: 10, table_id: 42 }],
    })
    realtime.trigger('rows_created', store, { table_id: 42 })
    expect(store.dispatch).not.toHaveBeenCalled()
  })
})

describe('dashboardApplication store: invalidateDataSourcesForTable debounce', () => {
  it('rapid successive calls debounce to a single dispatchDataSource call', async () => {
    const dispatchMock = vi.fn().mockResolvedValue(undefined)
    const context = {
      dispatch: dispatchMock,
      state: { dataSources: [{ id: 10, table_id: 5 }] },
    }

    // Call three times in rapid succession
    actions.invalidateDataSourcesForTable(context, 5)
    actions.invalidateDataSourcesForTable(context, 5)
    actions.invalidateDataSourcesForTable(context, 5)

    // Before debounce fires: dispatchDataSource not called yet
    expect(dispatchMock).not.toHaveBeenCalledWith('dispatchDataSource', 10)

    // Wait for debounce (500ms) + buffer
    await new Promise((resolve) => setTimeout(resolve, 600))

    const dsCalls = dispatchMock.mock.calls.filter(
      (c) => c[0] === 'dispatchDataSource'
    )
    expect(dsCalls.length).toBe(1)
    expect(dsCalls[0][1]).toBe(10)
  })
})
