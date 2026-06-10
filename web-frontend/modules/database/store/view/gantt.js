import bufferedRows from '@baserow/modules/database/store/view/bufferedRows'
import GanttService from '@baserow/modules/database/services/view/gantt'
import { getRowMetadata } from '@baserow/modules/database/utils/row'

export function populateRow(row, metadata = {}) {
  // The gantt view is render-only (Story 3.8): unlike the timeline store there
  // is no `dragging` pre-seed because no drag/resize write path exists here
  // (that is Story 3.10's scope).
  row._ = {
    metadata: getRowMetadata(row, metadata),
  }
  return row
}

const ganttBufferedRows = bufferedRows({
  service: GanttService,
  customPopulateRow: populateRow,
})

export const state = () => ({
  ...ganttBufferedRows.state(),
})

export const mutations = {
  ...ganttBufferedRows.mutations,
}

export const actions = {
  ...ganttBufferedRows.actions,
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
  ...ganttBufferedRows.getters,
}

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations,
}
