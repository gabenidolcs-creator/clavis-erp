export default (client) => {
  return {
    enableSharing(dashboardId) {
      return client.post(`/dashboard/${dashboardId}/share/enable/`)
    },
    disableSharing(dashboardId) {
      return client.post(`/dashboard/${dashboardId}/share/disable/`)
    },
    rotateSlug(dashboardId) {
      return client.post(`/dashboard/${dashboardId}/share/rotate-slug/`)
    },
  }
}
