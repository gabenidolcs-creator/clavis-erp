import bufferedRows from '@baserow/modules/database/store/view/bufferedRows'
import CalendarService from '@baserow/modules/database/services/view/calendar'
import { getRowMetadata } from '@baserow/modules/database/utils/row'

export function populateRow(row, metadata = {}) {
  row._ = {
    metadata: getRowMetadata(row, metadata),
    dragging: false,
  }
  return row
}

const calendarBufferedRows = bufferedRows({
  service: CalendarService,
  customPopulateRow: populateRow,
})

export const state = () => ({
  ...calendarBufferedRows.state(),
  // Ephemeral client-side display mode (`month` or `week`). Not persisted on
  // the view (AC #3 only requires the toggle to be available), so it lives in
  // the store rather than as a migration-backed column. Kept here — instead of
  // in component data — because the header and body components are siblings
  // rendered by the view shell and need to share it.
  displayMode: 'month',
})

export const mutations = {
  ...calendarBufferedRows.mutations,
  SET_DISPLAY_MODE(state, displayMode) {
    state.displayMode = displayMode
  },
}

export const actions = {
  ...calendarBufferedRows.actions,
  setDisplayMode({ commit }, displayMode) {
    commit('SET_DISPLAY_MODE', displayMode)
  },
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
  ...calendarBufferedRows.getters,
  getDisplayMode(state) {
    return state.displayMode
  },
}

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations,
}
