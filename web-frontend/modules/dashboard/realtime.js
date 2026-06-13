export const registerRealtimeEvents = (realtime) => {
  ;['rows_created', 'rows_updated', 'rows_deleted'].forEach((event) => {
    realtime.registerEvent(event, ({ store }, data) => {
      const dashboardId = store.getters['dashboardApplication/getDashboardId']
      if (!dashboardId) return
      const hasBound = store.state.dashboardApplication.dataSources.some(
        (ds) => ds.table_id === data.table_id
      )
      if (hasBound) {
        store.dispatch(
          'dashboardApplication/invalidateDataSourcesForTable',
          data.table_id
        )
      }
    })
  })
  realtime.registerEvent('widget_created', ({ store }, data) => {
    if (
      data.dashboard_id === store.getters['dashboardApplication/getDashboardId']
    ) {
      store.dispatch('dashboardApplication/handleNewWidgetCreated', data.widget)
    }
  })
  realtime.registerEvent('widget_updated', ({ store }, data) => {
    if (
      data.dashboard_id === store.getters['dashboardApplication/getDashboardId']
    ) {
      store.dispatch('dashboardApplication/handleWidgetUpdated', data.widget)
    }
  })
  realtime.registerEvent('widget_deleted', ({ store }, data) => {
    if (
      data.dashboard_id === store.getters['dashboardApplication/getDashboardId']
    ) {
      store.dispatch('dashboardApplication/handleWidgetDeleted', data.widget.id)
    }
  })
  realtime.registerEvent('data_source_updated', ({ store }, data) => {
    if (
      data.dashboard_id === store.getters['dashboardApplication/getDashboardId']
    ) {
      store.dispatch(
        'dashboardApplication/handleDataSourceUpdated',
        data.data_source
      )
    }
  })
}
