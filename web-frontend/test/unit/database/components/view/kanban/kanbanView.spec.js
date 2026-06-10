import { TestApp } from '@baserow/test/helpers/testApp'
import { KanbanViewType } from '@baserow/modules/database/viewTypes'
import { groupRowsBySingleSelect } from '@baserow/modules/database/components/view/kanban/KanbanView'

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
