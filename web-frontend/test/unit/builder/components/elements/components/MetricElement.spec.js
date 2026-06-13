import { mountSuspended } from '@nuxt/test-utils/runtime'
import MetricElement from '@baserow/modules/builder/components/elements/components/MetricElement.vue'

const baseDataSource = { id: 5, type: 'local_baserow_aggregate_rows' }

const baseElement = {
  data_source_id: baseDataSource.id,
  _: { content: null, hasNextPage: false },
}

const mountEl = (element = baseElement, getterContent = null, dataSource = baseDataSource) => {
  const mockGetResult = vi.fn((ds, content) => String(content.result))
  const mockStore = {
    getters: {
      'elementContent/getElementContent': () => getterContent,
      'dataSource/getPageDataSourceById': () => dataSource,
    },
  }
  const mockRegistry = {
    get: vi.fn(() => ({ getResult: mockGetResult })),
  }
  return {
    wrapper: mountSuspended(MetricElement, {
      props: {
        element,
        builder: { id: 1, theme: {} },
        page: { id: 1 },
        mode: 'public',
      },
      global: {
        mocks: { $store: mockStore, $registry: mockRegistry },
      },
    }),
    mockGetResult,
    mockRegistry,
  }
}

describe('MetricElement', () => {
  test('renders value when content has result and dataSource is set', async () => {
    const content = { result: 42 }
    const { wrapper } = mountEl(baseElement, content)
    const w = await wrapper
    expect(w.find('.metric-element__value').exists()).toBe(true)
    expect(w.find('.metric-element__value').text()).toBe('42')
    expect(w.find('.metric-element__error').exists()).toBe(false)
    expect(w.find('.metric-element__empty').exists()).toBe(false)
  })

  test('renders error state when content has _error', async () => {
    const { wrapper } = mountEl(baseElement, { _error: 'some error' })
    const w = await wrapper
    expect(w.find('.metric-element__error').exists()).toBe(true)
    expect(w.find('.metric-element__value').exists()).toBe(false)
  })

  test('renders empty state when data_source_id is null (not configured)', async () => {
    const element = { ...baseElement, data_source_id: null }
    const { wrapper } = mountEl(element, null, null)
    const w = await wrapper
    expect(w.find('.metric-element__empty').exists()).toBe(true)
    expect(w.find('.metric-element__value').exists()).toBe(false)
  })

  test('renders empty state when dataSource not found in store (data_source_id set but store returns null)', async () => {
    const { wrapper } = mountEl(baseElement, { result: 99 }, null)
    const w = await wrapper
    expect(w.find('.metric-element__value').exists()).toBe(false)
    expect(w.find('.metric-element__empty').exists()).toBe(true)
  })

  test('displayValue is null when data_source_id is null', async () => {
    const element = { ...baseElement, data_source_id: null }
    const { wrapper } = mountEl(element, { result: 100 }, null)
    const w = await wrapper
    expect(w.vm.misconfigured).toBe(true)
    expect(w.vm.displayValue).toBeNull()
  })

  test('calls getResult with correct args', async () => {
    const content = { result: 99 }
    const { wrapper, mockGetResult } = mountEl(baseElement, content)
    await wrapper
    expect(mockGetResult).toHaveBeenCalledWith(baseDataSource, content)
  })
})
