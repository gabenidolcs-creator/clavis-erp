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
    /**
     * Story 3.10 / AC #1: read-only cascade preview. Returns the transitive set
     * of dependent successors that would shift if the predecessor moved to
     * `newStart`/`newEnd`, plus the count — WITHOUT writing anything, so the UI
     * can prompt the user before committing.
     */
    rescheduleCascadePreview(viewId, { predecessorRowId, newStart, newEnd }) {
      return client.post(
        `/database/views/gantt/${viewId}/reschedule/preview/`,
        {
          predecessor_row_id: predecessorRowId,
          new_start: newStart,
          new_end: newEnd,
        }
      )
    },
    /**
     * Story 3.10 / AC #2: commit the cascade. The backend recomputes under a
     * table-scoped lock and shifts the predecessor + every transitive dependent
     * atomically in ONE undoable step.
     */
    rescheduleCascadeApply(viewId, { predecessorRowId, newStart, newEnd }) {
      return client.post(`/database/views/gantt/${viewId}/reschedule/apply/`, {
        predecessor_row_id: predecessorRowId,
        new_start: newStart,
        new_end: newEnd,
      })
    },
  }
}
