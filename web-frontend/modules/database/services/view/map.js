export default (client) => ({
  fetchRows(viewId) {
    return client.get(`/database/views/map/${viewId}/rows/`)
  },
})
