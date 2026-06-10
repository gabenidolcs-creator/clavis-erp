import bufferedRows from '@baserow/modules/database/store/view/bufferedRows'
import TimelineService from '@baserow/modules/database/services/view/timeline'
import { getRowMetadata } from '@baserow/modules/database/utils/row'

export function populateRow(row, metadata = {}) {
  row._ = {
    metadata: getRowMetadata(row, metadata),
    // Pre-seeded for Story 3.7 (drag/resize); unused by 3.6 itself but kept
    // here so the per-row flag exists on every buffered row, mirroring how the
    // calendar store pre-seeded `dragging` in 3.4 for 3.5.
    dragging: false,
  }
  return row
}

const timelineBufferedRows = bufferedRows({
  service: TimelineService,
  customPopulateRow: populateRow,
})

export const state = () => ({
  ...timelineBufferedRows.state(),
})

export const mutations = {
  ...timelineBufferedRows.mutations,
}

export const actions = {
  ...timelineBufferedRows.actions,
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
  ...timelineBufferedRows.getters,
}

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations,
}
