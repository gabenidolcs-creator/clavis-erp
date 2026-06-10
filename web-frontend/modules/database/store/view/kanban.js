import bufferedRows from '@baserow/modules/database/store/view/bufferedRows'
import KanbanService from '@baserow/modules/database/services/view/kanban'
import { getRowMetadata } from '@baserow/modules/database/utils/row'

export function populateRow(row, metadata = {}) {
  row._ = {
    metadata: getRowMetadata(row, metadata),
    dragging: false,
  }
  return row
}

const kanbanBufferedRows = bufferedRows({
  service: KanbanService,
  customPopulateRow: populateRow,
})

export const state = () => ({
  ...kanbanBufferedRows.state(),
})

export const mutations = {
  ...kanbanBufferedRows.mutations,
}

export const actions = {
  ...kanbanBufferedRows.actions,
  async fetchInitial(
    { dispatch },
    { viewId, fields, adhocFiltering, adhocSorting }
  ) {
    const data = await dispatch('fetchInitialRows', {
      viewId,
      fields,
      initialRowArguments: { includeFieldOptions: true },
      adhocFiltering,
      adhocSorting,
    })
    await dispatch('forceUpdateAllFieldOptions', data.field_options)
  },
}

export const getters = {
  ...kanbanBufferedRows.getters,
}

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations,
}
