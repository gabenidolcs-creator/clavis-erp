import { mountSuspended } from '@nuxt/test-utils/runtime'
import RecordReviewElement from '@baserow/modules/builder/components/elements/components/RecordReviewElement.vue'

const baseDataSource = {
  id: 7,
  type: 'local_baserow_list_rows',
  schema: {
    type: 'array',
    items: {
      properties: {
        field_1: { title: 'Name' },
        field_2: { title: 'Status' },
      },
    },
  },
}

const baseRows = [
  { field_1: 'Alice', field_2: 'Active' },
  { field_1: 'Bob', field_2: 'Inactive' },
  { field_1: 'Carol', field_2: 'Pending' },
]

const baseElement = {
  data_source_id: baseDataSource.id,
  _: { content: null },
}

const mountEl = (
  element = baseElement,
  getterContent = baseRows,
  dataSource = baseDataSource
) => {
  const mockGetDataSchema = vi.fn((ds) => ds.schema)
  const mockStore = {
    getters: {
      'elementContent/getElementContent': () => getterContent,
      'dataSource/getPageDataSourceById': () => dataSource,
    },
  }
  const mockRegistry = {
    get: vi.fn(() => ({ getDataSchema: mockGetDataSchema })),
  }
  return {
    wrapper: mountSuspended(RecordReviewElement, {
      props: {
        element,
        builder: { id: 1, theme: {} },
        page: { id: 1 },
        mode: 'public',
      },
      global: {
        mocks: {
          $store: mockStore,
          $registry: mockRegistry,
          $t: (key, params) => {
            if (key === 'recordReviewElement.rowCounter') {
              return `${params.current} of ${params.total}`
            }
            return key
          },
        },
      },
    }),
  }
}

describe('RecordReviewElement', () => {
  test('shows first row fields when elementContent has rows (AC 1, 6)', async () => {
    const { wrapper } = mountEl()
    const w = await wrapper
    expect(w.find('.record-review-element__fields').exists()).toBe(true)
    expect(w.find('.record-review-element__error').exists()).toBe(false)
    expect(w.find('.record-review-element__empty').exists()).toBe(false)
    const labels = w.findAll('.record-review-element__label')
    expect(labels[0].text()).toBe('Name')
    expect(labels[1].text()).toBe('Status')
  })

  test('shows error state when data_source_id is null (AC 4)', async () => {
    const element = { ...baseElement, data_source_id: null }
    const { wrapper } = mountEl(element, [])
    const w = await wrapper
    expect(w.find('.record-review-element__error').exists()).toBe(true)
    expect(w.find('.record-review-element__fields').exists()).toBe(false)
  })

  test('shows empty state when elementContent is empty array (AC 5)', async () => {
    const { wrapper } = mountEl(baseElement, [])
    const w = await wrapper
    expect(w.find('.record-review-element__empty').exists()).toBe(true)
    expect(w.find('.record-review-element__fields').exists()).toBe(false)
  })

  test('Previous button disabled on first row (AC 3)', async () => {
    const { wrapper } = mountEl()
    const w = await wrapper
    const buttons = w.findAll('button')
    const prevBtn = buttons[0]
    expect(prevBtn.attributes('disabled')).toBeDefined()
  })

  test('Next button disabled on last row (AC 2)', async () => {
    const { wrapper } = mountEl()
    const w = await wrapper
    // Advance to last row
    w.vm.currentIndex = baseRows.length - 1
    await w.vm.$nextTick()
    const buttons = w.findAll('button')
    const nextBtn = buttons[1]
    expect(nextBtn.attributes('disabled')).toBeDefined()
  })

  test('clicking Next increments currentIndex (AC 2)', async () => {
    const { wrapper } = mountEl()
    const w = await wrapper
    expect(w.vm.currentIndex).toBe(0)
    const buttons = w.findAll('button')
    await buttons[1].trigger('click')
    expect(w.vm.currentIndex).toBe(1)
  })

  test('clicking Previous decrements currentIndex (AC 3)', async () => {
    const { wrapper } = mountEl()
    const w = await wrapper
    w.vm.currentIndex = 1
    await w.vm.$nextTick()
    const buttons = w.findAll('button')
    await buttons[0].trigger('click')
    expect(w.vm.currentIndex).toBe(0)
  })

  test('row counter shows correct "N of M" text (AC 1)', async () => {
    const { wrapper } = mountEl()
    const w = await wrapper
    const counter = w.find('.record-review-element__counter')
    expect(counter.text()).toBe('1 of 3')
  })

  test('displayFields maps schema title to label and value to string (AC 6)', async () => {
    const { wrapper } = mountEl()
    const w = await wrapper
    const fields = w.vm.displayFields
    expect(fields).toHaveLength(2)
    expect(fields[0].label).toBe('Name')
    expect(fields[0].value).toBe('Alice')
    expect(fields[1].label).toBe('Status')
    expect(fields[1].value).toBe('Active')
  })

  test('shows error state when elementContent has _error (AC 4)', async () => {
    const { wrapper } = mountEl(baseElement, { _error: true })
    const w = await wrapper
    expect(w.find('.record-review-element__error').exists()).toBe(true)
  })

  test('watcher resets currentIndex to 0 when data_source_id changes (AC 2, 3)', async () => {
    const { wrapper } = mountEl()
    const w = await wrapper
    w.vm.currentIndex = 2
    await w.vm.$nextTick()
    expect(w.vm.currentIndex).toBe(2)
    await w.setProps({
      element: { ...baseElement, data_source_id: 99 },
    })
    await w.vm.$nextTick()
    expect(w.vm.currentIndex).toBe(0)
  })

  test('displayFields uses key as label fallback when schema has no title (AC 6)', async () => {
    const dsNoTitle = {
      ...baseDataSource,
      schema: {
        type: 'array',
        items: { properties: { field_1: {}, field_2: {} } },
      },
    }
    const { wrapper } = mountEl(baseElement, baseRows, dsNoTitle)
    const w = await wrapper
    const fields = w.vm.displayFields
    expect(fields[0].label).toBe('field_1')
    expect(fields[1].label).toBe('field_2')
  })

  test('displayFields shows em-dash for null values (AC 6)', async () => {
    const rowWithNull = [{ field_1: null, field_2: undefined }]
    const { wrapper } = mountEl(baseElement, rowWithNull)
    const w = await wrapper
    const fields = w.vm.displayFields
    expect(fields[0].value).toBe('—')
    expect(fields[1].value).toBe('—')
  })

  test('schemaProperties uses schema.properties when schema type is not array (AC 6)', async () => {
    const dsFlat = {
      ...baseDataSource,
      schema: {
        type: 'object',
        properties: { field_1: { title: 'FlatName' } },
      },
    }
    const rowFlat = [{ field_1: 'Test' }]
    const { wrapper } = mountEl(baseElement, rowFlat, dsFlat)
    const w = await wrapper
    const fields = w.vm.displayFields
    expect(fields[0].label).toBe('FlatName')
  })
})
