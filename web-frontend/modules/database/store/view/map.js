import MapService from '@baserow/modules/database/services/view/map'

export const state = () => ({
  pins: [],
  unresolvable: [],
  loading: false,
  selectedRowId: null,
})

export const mutations = {
  SET_PINS(state, pins) {
    state.pins = pins
  },
  SET_UNRESOLVABLE(state, unresolvable) {
    state.unresolvable = unresolvable
  },
  SET_LOADING(state, loading) {
    state.loading = loading
  },
  UPDATE_PIN(state, { rowId, lat, lng }) {
    // Remove from unresolvable if it was there
    state.unresolvable = state.unresolvable.filter((u) => u.row_id !== rowId)
    // Replace existing pin or add new one
    const idx = state.pins.findIndex((p) => p.row_id === rowId)
    if (idx !== -1) {
      state.pins.splice(idx, 1, { row_id: rowId, lat, lng })
    } else {
      state.pins.push({ row_id: rowId, lat, lng })
    }
  },
  SET_SELECTED_ROW_ID(state, id) {
    state.selectedRowId = id
  },
}

export const actions = {
  async fetchRows({ commit }, { viewId }) {
    commit('SET_LOADING', true)
    try {
      const { data } = await MapService(this.$client).fetchRows(viewId)
      commit('SET_PINS', data.pins || [])
      commit('SET_UNRESOLVABLE', data.unresolvable || [])
    } finally {
      commit('SET_LOADING', false)
    }
  },
  selectRow({ commit }, rowId) {
    commit('SET_SELECTED_ROW_ID', rowId)
  },
  pinUpdated({ commit }, { rowId, lat, lng }) {
    commit('UPDATE_PIN', { rowId, lat, lng })
  },
  // Required by BaseBufferedRowViewTypeMixin.afterFieldDeleted
  forceDeleteFieldOptions({ commit }, fieldId) {},
}

export const getters = {
  getPins: (state) => state.pins,
  getUnresolvable: (state) => state.unresolvable,
  isLoading: (state) => state.loading,
  getSelectedRowId: (state) => state.selectedRowId,
}

export default {
  namespaced: true,
  state,
  mutations,
  actions,
  getters,
}
