import MapService from '@baserow/modules/database/services/view/map'

export const state = () => ({
  pins: [],
  unresolvable: [],
  loading: false,
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
  // Placeholder for Story 3.14 — emitted by marker click in MapView.vue
  selectRow(_, rowId) {},
  // Required by BaseBufferedRowViewTypeMixin.afterFieldDeleted
  forceDeleteFieldOptions({ commit }, fieldId) {},
}

export const getters = {
  getPins: (state) => state.pins,
  getUnresolvable: (state) => state.unresolvable,
  isLoading: (state) => state.loading,
}

export default {
  namespaced: true,
  state,
  mutations,
  actions,
  getters,
}
