import { TestApp } from '@baserow/test/helpers/testApp'
import SummaryWidget from '@baserow/modules/dashboard/components/widget/SummaryWidget'

describe('SummaryWidget.vue', () => {
  let testApp = null

  beforeEach(() => {
    testApp = new TestApp()
  })

  afterEach(async () => {
    await testApp.afterEach()
  })

  function makeWrapper({ dataSourceId = 99, storeData = { result: 42 } } = {}) {
    const widget = {
      id: 1,
      data_source_id: dataSourceId,
      title: 'My metric',
      description: '',
    }
    return testApp.mount(SummaryWidget, {
      props: { widget, dashboard: { id: 10 }, loading: false },
      global: {
        mocks: {
          $store: {
            getters: {
              'dashboardApplication/getDataSourceById': (id) =>
                id === dataSourceId
                  ? { id: dataSourceId, type: 'local_baserow_aggregate_rows' }
                  : null,
              'dashboardApplication/getDataForDataSource': (id) =>
                id === dataSourceId ? storeData : null,
              'dashboardApplication/isEditMode': false,
            },
          },
          $registry: {
            get: (_ns, _type) => ({
              getResult: (_svc, data) => String(data.result),
            }),
          },
        },
      },
    })
  }

  it('renders result from data source', async () => {
    const wrapper = await makeWrapper({ storeData: { result: 42 } })
    expect(wrapper.find('.dashboard-summary-widget__summary').text()).toBe('42')
  })

  it('renders 0 when data source has no data', async () => {
    const dataSourceId = 99
    const wrapper = await testApp.mount(SummaryWidget, {
      props: {
        widget: { id: 1, data_source_id: dataSourceId, title: 'M', description: '' },
        dashboard: { id: 10 },
        loading: false,
      },
      global: {
        mocks: {
          $store: {
            getters: {
              'dashboardApplication/getDataSourceById': (id) =>
                id === dataSourceId
                  ? { id: dataSourceId, type: 'local_baserow_aggregate_rows' }
                  : null,
              'dashboardApplication/getDataForDataSource': (_id) => null,
              'dashboardApplication/isEditMode': false,
            },
          },
          $registry: {
            get: (_ns, _type) => ({
              getResult: (_svc, data) => String(data.result),
            }),
          },
        },
      },
    })
    expect(wrapper.find('.dashboard-summary-widget__summary').text()).toBe('0')
  })

  it('shows misconfigured badge when data has _error', async () => {
    const wrapper = await makeWrapper({ storeData: { _error: 'Something failed' } })
    const badge = wrapper.findComponent({ name: 'Badge' })
    expect(badge.exists()).toBe(true)
    expect(badge.props('color')).toBe('red')
  })

  it('coexistence: SummaryWidget reads only its own data source from shared store', async () => {
    const summarySourceId = 99
    const chartSourceId = 200
    const summaryData = { result: 77 }
    const chartData = { result: [10, 20, 30] }

    const wrapper = await testApp.mount(SummaryWidget, {
      props: {
        widget: {
          id: 1,
          data_source_id: summarySourceId,
          title: 'Summary',
          description: '',
        },
        dashboard: { id: 10 },
        loading: false,
      },
      global: {
        mocks: {
          $store: {
            getters: {
              'dashboardApplication/getDataSourceById': (id) => {
                if (id === summarySourceId) {
                  return { id: summarySourceId, type: 'local_baserow_aggregate_rows' }
                }
                if (id === chartSourceId) {
                  return {
                    id: chartSourceId,
                    type: 'local_baserow_grouped_aggregate_rows',
                  }
                }
                return null
              },
              'dashboardApplication/getDataForDataSource': (id) => {
                if (id === summarySourceId) return summaryData
                if (id === chartSourceId) return chartData
                return null
              },
              'dashboardApplication/isEditMode': false,
            },
          },
          $registry: {
            get: (_ns, _type) => ({
              getResult: (_svc, data) => String(data.result),
            }),
          },
        },
      },
    })

    // SummaryWidget must display its own result (77), not chart data
    expect(wrapper.find('.dashboard-summary-widget__summary').text()).toBe('77')
    // No error badge should appear
    expect(wrapper.findComponent({ name: 'Badge' }).exists()).toBe(false)
  })
})
