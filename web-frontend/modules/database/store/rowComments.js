const key = (tableId, rowId) => `${tableId}-${rowId}`

export const state = () => ({
  commentsByKey: {},
  loadingByKey: {},
})

export const mutations = {
  SET_LOADING(state, { tableId, rowId, loading }) {
    state.loadingByKey = {
      ...state.loadingByKey,
      [key(tableId, rowId)]: loading,
    }
  },
  SET_COMMENTS(state, { tableId, rowId, comments }) {
    state.commentsByKey = {
      ...state.commentsByKey,
      [key(tableId, rowId)]: comments,
    }
  },
  APPEND_COMMENT(state, { tableId, rowId, comment }) {
    const k = key(tableId, rowId)
    const existing = state.commentsByKey[k] || []
    state.commentsByKey = {
      ...state.commentsByKey,
      [k]: [...existing, comment],
    }
  },
  UPDATE_COMMENT(state, { tableId, rowId, comment }) {
    const k = key(tableId, rowId)
    const existing = state.commentsByKey[k] || []
    state.commentsByKey = {
      ...state.commentsByKey,
      [k]: existing.map((c) => (c.id === comment.id ? comment : c)),
    }
  },
  REMOVE_COMMENT(state, { tableId, rowId, commentId }) {
    const k = key(tableId, rowId)
    const existing = state.commentsByKey[k] || []
    state.commentsByKey = {
      ...state.commentsByKey,
      [k]: existing.filter((c) => c.id !== commentId),
    }
  },
}

export const actions = {
  async fetchComments({ commit }, { tableId, rowId }) {
    commit('SET_LOADING', { tableId, rowId, loading: true })
    try {
      const { data } = await this.$client.get(
        `/database/rows/table/${tableId}/${rowId}/comments/`
      )
      commit('SET_COMMENTS', { tableId, rowId, comments: data.results })
    } finally {
      commit('SET_LOADING', { tableId, rowId, loading: false })
    }
  },
  async createComment({ commit }, { tableId, rowId, message }) {
    const { data } = await this.$client.post(
      `/database/rows/table/${tableId}/${rowId}/comments/`,
      { message }
    )
    commit('APPEND_COMMENT', { tableId, rowId, comment: data })
    return data
  },
  async updateComment({ commit }, { tableId, rowId, commentId, message }) {
    const { data } = await this.$client.patch(
      `/database/rows/table/${tableId}/${rowId}/comments/${commentId}/`,
      { message }
    )
    commit('UPDATE_COMMENT', { tableId, rowId, comment: data })
    return data
  },
  async deleteComment({ commit }, { tableId, rowId, commentId }) {
    await this.$client.delete(
      `/database/rows/table/${tableId}/${rowId}/comments/${commentId}/`
    )
    commit('REMOVE_COMMENT', { tableId, rowId, commentId })
  },
  wsCommentCreated({ commit }, { tableId, rowId, comment }) {
    commit('APPEND_COMMENT', { tableId, rowId, comment })
  },
  wsCommentUpdated({ commit }, { tableId, rowId, comment }) {
    commit('UPDATE_COMMENT', { tableId, rowId, comment })
  },
  wsCommentDeleted({ commit }, { tableId, rowId, commentId }) {
    commit('REMOVE_COMMENT', { tableId, rowId, commentId })
  },
}

export const getters = {
  getComments: (state) => (tableId, rowId) => {
    return state.commentsByKey[key(tableId, rowId)] || []
  },
  isLoading: (state) => (tableId, rowId) => {
    return state.loadingByKey[key(tableId, rowId)] || false
  },
}

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations,
}
