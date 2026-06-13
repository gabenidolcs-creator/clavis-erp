export default (client) => {
  return {
    getPublicDashboard(slug) {
      return client.get(`/dashboard/public/${slug}/`)
    },
    dispatchPublicDataSource(slug, dataSourceId) {
      return client.get(`/dashboard/public/${slug}/dispatch/${dataSourceId}/`)
    },
  }
}
