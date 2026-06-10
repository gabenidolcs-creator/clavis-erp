import { TestApp } from '@baserow/test/helpers/testApp'
import { PercentFieldType } from '@baserow/modules/database/fieldTypes'

describe('PercentFieldType', () => {
  let testApp

  beforeAll(() => {
    testApp = new TestApp()
  })

  afterEach(() => {
    testApp.afterEach()
  })

  test('getType returns percent', () => {
    expect(PercentFieldType.getType()).toBe('percent')
  })

  test('toHumanReadableString appends % suffix', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'percent')
    const field = {
      number_decimal_places: 1,
      number_negative: false,
      number_separator: 'NO_FORMATTING',
      number_prefix: '',
      number_suffix: '',
    }
    const result = fieldType.toHumanReadableString(field, '9.9')
    expect(result).toBe('9.9%')
  })

  test('toHumanReadableString returns empty string for null', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'percent')
    const field = {
      number_decimal_places: 1,
      number_negative: false,
      number_separator: 'NO_FORMATTING',
      number_prefix: '',
      number_suffix: '',
    }
    expect(fieldType.toHumanReadableString(field, null)).toBe('')
    expect(fieldType.toHumanReadableString(field, undefined)).toBe('')
    expect(fieldType.toHumanReadableString(field, '')).toBe('')
  })

  test('toHumanReadableString uses number_suffix % even if field has empty suffix', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'percent')
    const field = {
      number_decimal_places: 0,
      number_negative: false,
      number_separator: 'NO_FORMATTING',
      number_prefix: 'ignore',
      number_suffix: '',
    }
    const result = fieldType.toHumanReadableString(field, '50')
    expect(result).toBe('50%')
  })

  test('toHumanReadableString applies decimal places', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'percent')
    const field = {
      number_decimal_places: 2,
      number_negative: false,
      number_separator: 'NO_FORMATTING',
      number_prefix: '',
      number_suffix: '',
    }
    const result = fieldType.toHumanReadableString(field, '50')
    expect(result).toBe('50.00%')
  })

  test('getName returns fieldType.percent i18n key', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'percent')
    expect(fieldType.getName()).toBe('fieldType.percent')
  })

  test('getFormComponent returns FieldPercentSubForm', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'percent')
    const component = fieldType.getFormComponent()
    expect(component).toBeDefined()
    expect(component.name || component.__name).toBe('FieldPercentSubForm')
  })

  test('toHumanReadableString applies thousand separator', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'percent')
    const field = {
      number_decimal_places: 2,
      number_negative: true,
      number_separator: 'COMMA_PERIOD',
      number_prefix: '',
      number_suffix: '',
    }
    const result = fieldType.toHumanReadableString(field, '1234.56')
    expect(result).toBe('1,234.56%')
  })

  test('getIconClass returns iconoir-percentage', () => {
    expect(PercentFieldType.getIconClass()).toBe('iconoir-percentage')
  })
})
