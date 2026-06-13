import { mountSuspended } from '@nuxt/test-utils/runtime'
import ViewEmbedElement from '@baserow/modules/builder/components/elements/components/ViewEmbedElement.vue'
import CalendarView from '@baserow/modules/database/components/view/calendar/CalendarView'
import TimelineView from '@baserow/modules/database/components/view/timeline/TimelineView'

const kanbanView = {
  id: 10,
  table_id: 2,
  name: 'My Kanban',
  type: 'kanban',
  single_select_field: 5,
}

const calendarView = {
  id: 11,
  table_id: 2,
  name: 'My Calendar',
  type: 'calendar',
  date_field: 6,
}

const timelineView = {
  id: 12,
  table_id: 2,
  name: 'My Timeline',
  type: 'timeline',
  start_date_field: 7,
  end_date_field: 8,
}

const baseFields = [{ id: 1, name: 'Name', type: 'text' }]

const makeBuilder = (views = [kanbanView]) => ({
  id: 1,
  theme: {},
  integrations: [
    {
      context_data: {
        databases: [
          {
            id: 100,
            name: 'DB',
            tables: [{ id: 2, database_id: 100, name: 'Table' }],
            views,
          },
        ],
      },
    },
  ],
})

const mountEl = (
  viewId,
  viewResponse = kanbanView,
  fieldsResponse = baseFields,
  builder = makeBuilder()
) => {
  const element = { id: 99, view_id: viewId }
  const mockClient = {
    database: {
      views: { get: vi.fn().mockResolvedValue({ data: viewResponse }) },
      fields: { fetchAll: vi.fn().mockResolvedValue({ data: fieldsResponse }) },
    },
  }
  return {
    wrapper: mountSuspended(ViewEmbedElement, {
      props: {
        element,
        builder,
        page: { id: 1 },
        mode: 'public',
      },
      global: {
        mocks: { $client: mockClient },
      },
    }),
    mockClient,
  }
}

describe('ViewEmbedElement', () => {
  test('renders KanbanView when view type is kanban and single_select_field is set', async () => {
    const { wrapper } = mountEl(kanbanView.id, kanbanView)
    const w = await wrapper
    await w.vm.$nextTick()
    // Not misconfigured — kanban has single_select_field
    expect(w.vm.misconfigured).toBe(false)
    expect(w.find('.view-embed-element__misconfigured').exists()).toBe(false)
    expect(w.find('.view-embed-element__error').exists()).toBe(false)
  })

  test('shows misconfigured state when Kanban view has no single_select_field', async () => {
    const brokenKanban = { ...kanbanView, single_select_field: null }
    const { wrapper } = mountEl(kanbanView.id, brokenKanban)
    const w = await wrapper
    await w.vm.$nextTick()
    expect(w.vm.misconfigured).toBe(true)
    expect(w.find('.view-embed-element__misconfigured').exists()).toBe(true)
  })

  test('shows misconfigured state when Calendar view has no date_field', async () => {
    const brokenCalendar = { ...calendarView, date_field: null }
    const { wrapper } = mountEl(
      calendarView.id,
      brokenCalendar,
      baseFields,
      makeBuilder([calendarView])
    )
    const w = await wrapper
    await w.vm.$nextTick()
    expect(w.vm.misconfigured).toBe(true)
    expect(w.find('.view-embed-element__misconfigured').exists()).toBe(true)
  })

  test('shows misconfigured state when Timeline view missing start_date_field', async () => {
    const brokenTimeline = { ...timelineView, start_date_field: null }
    const { wrapper } = mountEl(
      timelineView.id,
      brokenTimeline,
      baseFields,
      makeBuilder([timelineView])
    )
    const w = await wrapper
    await w.vm.$nextTick()
    expect(w.vm.misconfigured).toBe(true)
    expect(w.find('.view-embed-element__misconfigured').exists()).toBe(true)
  })

  test('storePrefix uses unique embed/<element.id>/ per instance', async () => {
    const { wrapper } = mountEl(kanbanView.id, kanbanView)
    const w = await wrapper
    expect(w.vm.storePrefix).toBe('embed/99/')
  })

  test('view_id null shows no-configuration state (viewMeta not found)', async () => {
    const { wrapper } = mountEl(null, kanbanView)
    const w = await wrapper
    await w.vm.$nextTick()
    expect(w.vm.viewMeta).toBeUndefined()
    expect(w.find('.view-embed-element__misconfigured').exists()).toBe(true)
  })

  test('shows misconfigured state when Timeline view missing end_date_field (AC 3)', async () => {
    const brokenTimeline = { ...timelineView, end_date_field: null }
    const { wrapper } = mountEl(
      timelineView.id,
      brokenTimeline,
      baseFields,
      makeBuilder([timelineView])
    )
    const w = await wrapper
    await w.vm.$nextTick()
    expect(w.vm.misconfigured).toBe(true)
    expect(w.find('.view-embed-element__misconfigured').exists()).toBe(true)
  })

  test('viewComponent delegates to CalendarView for calendar type (AC 1)', async () => {
    const { wrapper } = mountEl(
      calendarView.id,
      calendarView,
      baseFields,
      makeBuilder([calendarView])
    )
    const w = await wrapper
    await w.vm.$nextTick()
    expect(w.vm.viewComponent).toBe(CalendarView)
    expect(w.vm.misconfigured).toBe(false)
  })

  test('viewComponent delegates to TimelineView for timeline type (AC 1)', async () => {
    const { wrapper } = mountEl(
      timelineView.id,
      timelineView,
      baseFields,
      makeBuilder([timelineView])
    )
    const w = await wrapper
    await w.vm.$nextTick()
    expect(w.vm.viewComponent).toBe(TimelineView)
    expect(w.vm.misconfigured).toBe(false)
  })
})
