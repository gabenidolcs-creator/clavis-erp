export function createKanbanView(
  mock,
  application,
  table,
  {
    viewType = 'kanban',
    viewId = 1,
    filters = [],
    sortings = [],
    decorations = [],
    singleSelectField = null,
    cardCoverImageField = null,
  }
) {
  const tableId = table.id
  const kanbanView = {
    id: viewId,
    table_id: tableId,
    name: `mock_view_${viewId}`,
    order: 0,
    type: viewType,
    table: {
      id: tableId,
      name: table.name,
      order: 0,
      database_id: application.id,
    },
    filter_type: 'AND',
    filters_disabled: false,
    ownership_type: 'collaborative',
    filters,
    sortings,
    decorations,
    single_select_field: singleSelectField,
    card_cover_image_field: cardCoverImageField,
  }
  mock.onGet(`/database/views/table/${tableId}/`).reply(200, [kanbanView])
  return kanbanView
}

export function createKanbanRows(mock, view, fields, rows = []) {
  const fieldOptions = {}
  for (let i = 1; i < fields.length; i++) {
    fieldOptions[i] = {
      hidden: false,
      order: i,
    }
  }
  mock.onGet(`/database/views/kanban/${view.id}/`).reply(200, {
    count: rows.length,
    results: rows,
    field_options: fieldOptions,
  })
}
