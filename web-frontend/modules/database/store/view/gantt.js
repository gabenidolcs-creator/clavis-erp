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
  // Story 3.9: the table's `TaskDependency` edges, the source for the Gantt
  // connector strings. An edge is `{ id, table, predecessor_row_id,
  // successor_row_id, dependency_type }`.
  dependencies: [],
})

export const mutations = {
  ...ganttBufferedRows.mutations,
  SET_DEPENDENCIES(state, dependencies) {
    state.dependencies = dependencies
  },
  ADD_DEPENDENCY(state, dependency) {
    state.dependencies.push(dependency)
  },
  REMOVE_DEPENDENCY(state, dependencyId) {
    state.dependencies = state.dependencies.filter(
      (dependency) => dependency.id !== dependencyId
    )
  },
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
    await dispatch('fetchDependencies', { viewId })
  },
  /**
   * Loads every `TaskDependency` edge for the view's table; the connectors are
   * a property of the table, shared across its Gantt views.
   */
  async fetchDependencies({ commit }, { viewId }) {
    const { data } = await GanttService(this.$client).fetchDependencies(viewId)
    commit('SET_DEPENDENCIES', data)
  },
  /**
   * Optimistically adds a `predecessor → successor` edge, then reconciles with
   * the server. On a cycle/exists 400 the optimistic edge is rolled back and
   * the error re-thrown so the caller can surface a clear message. The
   * optimistic row carries a temporary negative id, swapped for the real edge
   * once persisted.
   */
  async createDependency(
    { commit, getters },
    { viewId, predecessorRowId, successorRowId }
  ) {
    const optimistic = {
      id: -1,
      predecessor_row_id: predecessorRowId,
      successor_row_id: successorRowId,
      dependency_type: 'FS',
    }
    commit('ADD_DEPENDENCY', optimistic)
    try {
      const { data } = await GanttService(this.$client).createDependency(
        viewId,
        predecessorRowId,
        successorRowId
      )
      commit('REMOVE_DEPENDENCY', -1)
      commit('ADD_DEPENDENCY', data)
      return data
    } catch (error) {
      commit('REMOVE_DEPENDENCY', -1)
      throw error
    }
  },
  /**
   * Optimistically removes an edge, restoring it if the server delete fails.
   */
  async deleteDependency({ commit, getters }, { viewId, dependencyId }) {
    const existing = getters.getDependencies.find(
      (dependency) => dependency.id === dependencyId
    )
    commit('REMOVE_DEPENDENCY', dependencyId)
    try {
      await GanttService(this.$client).deleteDependency(viewId, dependencyId)
    } catch (error) {
      if (existing !== undefined) {
        commit('ADD_DEPENDENCY', existing)
      }
      throw error
    }
  },
  /**
   * Real-time reconciliation: apply a `task_dependency_created` /
   * `task_dependency_deleted` event from another session to the local edge set
   * (idempotent — ignores an edge id already present).
   */
  dependencyCreated({ commit, getters }, { dependency }) {
    const exists = getters.getDependencies.some((d) => d.id === dependency.id)
    if (!exists) {
      commit('ADD_DEPENDENCY', dependency)
    }
  },
  dependencyDeleted({ commit }, { dependencyId }) {
    commit('REMOVE_DEPENDENCY', dependencyId)
  },
}

export const getters = {
  ...ganttBufferedRows.getters,
  getDependencies(state) {
    return state.dependencies
  },
}

export default {
  namespaced: true,
  state,
  getters,
  actions,
  mutations,
}
