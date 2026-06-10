import bufferedRowService from '@baserow/modules/database/services/view/bufferedRows'

/**
 * The Gantt view service is the buffered-rows service (Story 3.8) extended with
 * the Story 3.9 `TaskDependency` edge endpoints. The rows service is preserved
 * verbatim (spread) so the store's `bufferedRows` wiring keeps working; the
 * three dependency calls map 1:1 onto the thin DRF views over
 * `TaskDependencyHandler`.
 */
export default (client) => {
  const service = bufferedRowService(client, 'gantt')
  return {
    ...service,
    fetchDependencies(viewId) {
      return client.get(`/database/views/gantt/${viewId}/dependencies/`)
    },
    createDependency(viewId, predecessorRowId, successorRowId) {
      return client.post(`/database/views/gantt/${viewId}/dependencies/`, {
        predecessor_row_id: predecessorRowId,
        successor_row_id: successorRowId,
      })
    },
    deleteDependency(viewId, dependencyId) {
      return client.delete(
        `/database/views/gantt/${viewId}/dependencies/${dependencyId}/`
      )
    },
  }
}
