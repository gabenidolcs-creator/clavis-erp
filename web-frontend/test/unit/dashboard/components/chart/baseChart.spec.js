import { h } from 'vue'
import { TestApp } from '@baserow/test/helpers/testApp'
import { expect } from 'vitest'
import flushPromises from 'flush-promises'

import BaseChart from '@baserow/modules/dashboard/components/chart/BaseChart.vue'
import { use as echartsUse } from 'echarts/core'

const MockVChart = {
  name: 'VChart',
  props: ['option', 'autoresize', 'theme'],
  render() {
    return h('div', { class: 'vchart-stub' })
  },
}

vi.mock('vue-echarts', () => ({ default: MockVChart }))
vi.mock('echarts/core', () => ({ use: vi.fn() }))
vi.mock('echarts/charts', () => ({
  BarChart: {},
  LineChart: {},
  PieChart: {},
  ScatterChart: {},
}))
vi.mock('echarts/components', () => ({
  GridComponent: {},
  TooltipComponent: {},
  LegendComponent: {},
  TitleComponent: {},
}))
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }))

describe('BaseChart.vue', () => {
  let testApp = null

  beforeEach(() => {
    testApp = new TestApp()
    vi.clearAllMocks()
  })

  afterEach(async () => {
    await testApp.afterEach()
  })

  test('data() initialises with loaded=false and vchart=null before mount', () => {
    const initialData = BaseChart.data.call({})
    expect(initialData.loaded).toBe(false)
    expect(initialData.vchart).toBeNull()
  })

  test('loaded switches to true after dynamic imports resolve on mount', async () => {
    const wrapper = await testApp.mount(BaseChart, {
      props: { option: { series: [] } },
    })
    await flushPromises()
    expect(wrapper.vm.loaded).toBe(true)
    expect(wrapper.vm.vchart).not.toBeNull()
  })

  test('passes option prop to VChart unchanged', async () => {
    const option = { series: [{ type: 'bar', data: [1, 2, 3] }] }
    const wrapper = await testApp.mount(BaseChart, { props: { option } })
    await flushPromises()
    const vchartWrapper = wrapper.findComponent({ name: 'VChart' })
    expect(vchartWrapper.exists()).toBe(true)
    expect(vchartWrapper.props('option')).toBe(option)
  })

  test('passes autoresize prop through to VChart', async () => {
    const wrapper = await testApp.mount(BaseChart, {
      props: { option: {}, autoresize: false },
    })
    await flushPromises()
    const vchartWrapper = wrapper.findComponent({ name: 'VChart' })
    expect(vchartWrapper.props('autoresize')).toBe(false)
  })

  test('default props: type=bar, autoresize=true, theme=null', () => {
    expect(BaseChart.props.type.default).toBe('bar')
    expect(BaseChart.props.autoresize.default).toBe(true)
    expect(BaseChart.props.theme.default).toBeNull()
  })

  test('chart-base root element has correct class', async () => {
    const wrapper = await testApp.mount(BaseChart, {
      props: { option: {} },
    })
    expect(wrapper.find('.chart-base').exists()).toBe(true)
  })

  test('VChart receives updated option when prop changes reactively', async () => {
    const option = { series: [{ type: 'bar', data: [1, 2] }] }
    const wrapper = await testApp.mount(BaseChart, { props: { option } })
    await flushPromises()
    const updatedOption = { series: [{ type: 'line', data: [3, 4] }] }
    await wrapper.setProps({ option: updatedOption })
    const vchartWrapper = wrapper.findComponent({ name: 'VChart' })
    expect(vchartWrapper.props('option')).toEqual(updatedOption)
  })

  test('theme null converts to undefined for VChart', async () => {
    const wrapper = await testApp.mount(BaseChart, {
      props: { option: {}, theme: null },
    })
    await flushPromises()
    const vchartWrapper = wrapper.findComponent({ name: 'VChart' })
    expect(vchartWrapper.props('theme')).toBeUndefined()
  })

  test('theme prop passed through to VChart when non-null', async () => {
    const wrapper = await testApp.mount(BaseChart, {
      props: { option: {}, theme: 'dark' },
    })
    await flushPromises()
    const vchartWrapper = wrapper.findComponent({ name: 'VChart' })
    expect(vchartWrapper.props('theme')).toBe('dark')
  })

  test('echarts use() called during mounted with all required components', async () => {
    await testApp.mount(BaseChart, { props: { option: {} } })
    await flushPromises()
    expect(echartsUse).toHaveBeenCalledOnce()
    const [registeredComponents] = echartsUse.mock.calls[0]
    expect(registeredComponents).toHaveLength(9)
  })
})
