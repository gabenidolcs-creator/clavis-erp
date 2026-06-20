import { vi } from 'vitest'
import {
  LeftBorderColorViewDecoratorType,
  BackgroundColorViewDecoratorType,
} from '@baserow/modules/database/viewDecorators'
import { ConditionalColorValueProviderType } from '@baserow/modules/database/decoratorValueProviders'

vi.mock('@baserow/modules/database/utils/view', async (importOriginal) => {
  const actual = await importOriginal()
  return { ...actual, createFiltersTree: vi.fn() }
})

const { createFiltersTree } = await import(
  '@baserow/modules/database/utils/view'
)

const mockApp = {
  i18n: { t: (key) => key },
  $registry: {},
}

// ---------------------------------------------------------------------------
// LeftBorderColorViewDecoratorType
// ---------------------------------------------------------------------------

describe('LeftBorderColorViewDecoratorType', () => {
  let type

  beforeEach(() => {
    type = new LeftBorderColorViewDecoratorType({ app: mockApp })
  })

  test('getType returns left_border_color', () => {
    expect(type.getType()).toBe('left_border_color')
  })

  test('getPlace returns first_cell', () => {
    expect(type.getPlace()).toBe('first_cell')
  })

  test.each(['grid', 'gallery', 'kanban', 'calendar', 'timeline'])(
    'isCompatible returns true for %s view',
    (viewType) => {
      expect(type.isCompatible({ type: viewType })).toBe(true)
    }
  )

  test('isCompatible returns false for unknown view type', () => {
    expect(type.isCompatible({ type: 'form' })).toBe(false)
  })

  test('canAdd allows first decoration', () => {
    const [allowed] = type.canAdd({ view: { decorations: [] } })
    expect(allowed).toBe(true)
  })

  test('canAdd blocks duplicate decoration', () => {
    const view = {
      decorations: [{ type: 'left_border_color' }],
    }
    const [allowed] = type.canAdd({ view })
    expect(allowed).toBe(false)
  })

  test('getOrder returns 10', () => {
    expect(type.getOrder()).toBe(10)
  })
})

// ---------------------------------------------------------------------------
// BackgroundColorViewDecoratorType
// ---------------------------------------------------------------------------

describe('BackgroundColorViewDecoratorType', () => {
  let type

  beforeEach(() => {
    type = new BackgroundColorViewDecoratorType({ app: mockApp })
  })

  test('getType returns background_color', () => {
    expect(type.getType()).toBe('background_color')
  })

  test('getPlace returns wrapper', () => {
    expect(type.getPlace()).toBe('wrapper')
  })

  test.each(['grid', 'gallery', 'kanban', 'calendar', 'timeline'])(
    'isCompatible returns true for %s view',
    (viewType) => {
      expect(type.isCompatible({ type: viewType })).toBe(true)
    }
  )

  test('canAdd allows first decoration', () => {
    const [allowed] = type.canAdd({ view: { decorations: [] } })
    expect(allowed).toBe(true)
  })

  test('canAdd blocks duplicate decoration', () => {
    const view = {
      decorations: [{ type: 'background_color' }],
    }
    const [allowed] = type.canAdd({ view })
    expect(allowed).toBe(false)
  })

  test('getOrder returns 20', () => {
    expect(type.getOrder()).toBe(20)
  })
})

// ---------------------------------------------------------------------------
// ConditionalColorValueProviderType.getValue()
// ---------------------------------------------------------------------------

describe('ConditionalColorValueProviderType.getValue', () => {
  let provider
  const row = { id: 1, field_1: 'Trễ' }
  const fields = []

  beforeEach(() => {
    provider = new ConditionalColorValueProviderType({ app: mockApp })
    vi.clearAllMocks()
  })

  test('returns null when rules is empty', () => {
    expect(provider.getValue({ row, options: { rules: [] }, fields })).toBeNull()
  })

  test('returns null when options is null', () => {
    expect(provider.getValue({ row, options: null, fields })).toBeNull()
  })

  test('returns color of first matching rule', () => {
    createFiltersTree.mockReturnValue({ matches: () => true })
    const options = {
      rules: [
        { id: 'r1', color: '#FF0000', filters: [{ field: 1, type: 'equal', value: 'Trễ' }], filter_groups: [], filter_type: 'AND' },
      ],
    }
    expect(provider.getValue({ row, options, fields })).toBe('#FF0000')
  })

  test('skips non-matching rule and returns color of next matching rule', () => {
    createFiltersTree
      .mockReturnValueOnce({ matches: () => false })
      .mockReturnValueOnce({ matches: () => true })
    const options = {
      rules: [
        { id: 'r1', color: '#FF0000', filters: [{ field: 1, type: 'equal', value: 'Xong' }], filter_groups: [], filter_type: 'AND' },
        { id: 'r2', color: '#00FF00', filters: [{ field: 1, type: 'equal', value: 'Trễ' }], filter_groups: [], filter_type: 'AND' },
      ],
    }
    expect(provider.getValue({ row, options, fields })).toBe('#00FF00')
  })

  test('rule with no filters matches all rows', () => {
    const options = {
      rules: [
        { id: 'r1', color: '#0000FF', filters: [], filter_groups: [], filter_type: 'AND' },
      ],
    }
    expect(provider.getValue({ row, options, fields })).toBe('#0000FF')
    expect(createFiltersTree).not.toHaveBeenCalled()
  })

  test('returns null when no rule matches', () => {
    createFiltersTree.mockReturnValue({ matches: () => false })
    const options = {
      rules: [
        { id: 'r1', color: '#FF0000', filters: [{ field: 1, type: 'equal', value: 'Xong' }], filter_groups: [], filter_type: 'AND' },
      ],
    }
    expect(provider.getValue({ row, options, fields })).toBeNull()
  })

  test('first-match wins — does not evaluate subsequent rules', () => {
    createFiltersTree.mockReturnValue({ matches: () => true })
    const options = {
      rules: [
        { id: 'r1', color: '#FF0000', filters: [{ field: 1, type: 'equal', value: 'Trễ' }], filter_groups: [], filter_type: 'AND' },
        { id: 'r2', color: '#00FF00', filters: [{ field: 1, type: 'equal', value: 'Trễ' }], filter_groups: [], filter_type: 'AND' },
      ],
    }
    expect(provider.getValue({ row, options, fields })).toBe('#FF0000')
    expect(createFiltersTree).toHaveBeenCalledTimes(1)
  })

  test('skips malformed rule without crashing', () => {
    createFiltersTree.mockImplementation(() => {
      throw new Error('malformed')
    })
    const options = {
      rules: [
        { id: 'r1', color: '#FF0000', filters: [{ field: 1, type: 'bad' }], filter_groups: [], filter_type: 'AND' },
      ],
    }
    expect(() => provider.getValue({ row, options, fields })).not.toThrow()
    expect(provider.getValue({ row, options, fields })).toBeNull()
  })
})
