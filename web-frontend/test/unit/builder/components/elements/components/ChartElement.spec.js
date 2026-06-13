import { h } from 'vue'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import ChartElement from '@baserow/modules/builder/components/elements/components/ChartElement.vue'

// Mock BaseChart to avoid lazy-loading ECharts in tests
vi.mock('@baserow/modules/dashboard/components/chart/BaseChart', () => ({
  default: {
    name: 'BaseChart',
    props: ['option', 'type'],
    render() {
      return h('div', { class: 'base-chart-stub' })
    },
  },
}))

const baseElement = {
  chart_type: 'bar',
  data_source_id: null,
  _: { content: [], hasNextPage: false },
}

const mountEl = (element = baseElement, getterContent = []) => {
  const mockStore = {
    getters: {
      'elementContent/getElementContent': () => getterContent,
    },
  }
  return mountSuspended(ChartElement, {
    props: {
      element,
      builder: { id: 1, theme: {} },
      page: { id: 1 },
      mode: 'public',
    },
    global: {
      mocks: { $store: mockStore },
    },
  })
}

describe('ChartElement', () => {
  test('renders BaseChart when content is non-empty and no error', async () => {
    const content = [{ category: 'A', value: 10, series: null }]
    const wrapper = await mountEl(baseElement, content)
    expect(wrapper.find('.base-chart-stub').exists()).toBe(true)
    expect(wrapper.find('.chart-element__error').exists()).toBe(false)
    expect(wrapper.find('.chart-element__empty').exists()).toBe(false)
  })

  test('renders error state when content has _error', async () => {
    const wrapper = await mountEl(baseElement, { _error: 'some error' })
    expect(wrapper.find('.chart-element__error').exists()).toBe(true)
    expect(wrapper.find('.base-chart-stub').exists()).toBe(false)
  })

  test('renders empty state when content is empty array', async () => {
    const wrapper = await mountEl(baseElement, [])
    expect(wrapper.find('.chart-element__empty').exists()).toBe(true)
    expect(wrapper.find('.base-chart-stub').exists()).toBe(false)
  })

  test('chartOption computed returns correct ECharts option for bar type', async () => {
    const content = [
      { category: 'Q1', value: 100, series: null },
      { category: 'Q2', value: 200, series: null },
    ]
    const wrapper = await mountEl(
      { ...baseElement, chart_type: 'bar' },
      content
    )
    const option = wrapper.vm.chartOption
    expect(option.xAxis.type).toBe('category')
    expect(option.xAxis.data).toEqual(['Q1', 'Q2'])
    expect(option.series[0].type).toBe('bar')
    expect(option.series[0].data).toEqual([100, 200])
  })

  test('chartOption sets radius for doughnut type', async () => {
    const content = [
      { category: 'A', value: 50, series: null },
      { category: 'B', value: 50, series: null },
    ]
    const wrapper = await mountEl(
      { ...baseElement, chart_type: 'doughnut' },
      content
    )
    const option = wrapper.vm.chartOption
    expect(option.series[0].type).toBe('pie')
    expect(option.series[0].radius).toEqual(['40%', '70%'])
  })
})
