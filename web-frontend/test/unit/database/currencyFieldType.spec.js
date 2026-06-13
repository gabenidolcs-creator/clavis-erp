import { TestApp } from '@baserow/test/helpers/testApp'
import { CurrencyFieldType } from '@baserow/modules/database/fieldTypes'
import FieldCurrencySubForm from '@baserow/modules/database/components/field/FieldCurrencySubForm'

describe('CurrencyFieldType', () => {
  let testApp

  beforeAll(() => {
    testApp = new TestApp()
  })

  afterEach(() => {
    testApp.afterEach()
  })

  test('getType returns currency', () => {
    expect(CurrencyFieldType.getType()).toBe('currency')
  })

  test('toHumanReadableString prepends symbol', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'currency')
    const field = {
      currency_symbol: '£',
      number_decimal_places: 2,
      number_negative: false,
      number_separator: 'NO_FORMATTING',
      number_prefix: '',
      number_suffix: '',
    }
    const result = fieldType.toHumanReadableString(field, '9.99')
    expect(result).toBe('£9.99')
  })

  test('toHumanReadableString returns empty string for null', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'currency')
    const field = {
      currency_symbol: '$',
      number_decimal_places: 2,
      number_negative: false,
      number_separator: 'NO_FORMATTING',
      number_prefix: '',
      number_suffix: '',
    }
    expect(fieldType.toHumanReadableString(field, null)).toBe('')
    expect(fieldType.toHumanReadableString(field, undefined)).toBe('')
    expect(fieldType.toHumanReadableString(field, '')).toBe('')
  })

  test('toHumanReadableString uses default symbol when currency_symbol is empty', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'currency')
    const field = {
      currency_symbol: '',
      number_decimal_places: 0,
      number_negative: false,
      number_separator: 'NO_FORMATTING',
      number_prefix: '',
      number_suffix: '',
    }
    const result = fieldType.toHumanReadableString(field, '42')
    expect(result).toBe('$42')
  })

  test('toHumanReadableString applies thousand separator', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'currency')
    const field = {
      currency_symbol: '£',
      number_decimal_places: 2,
      number_negative: true,
      number_separator: 'COMMA_PERIOD',
      number_prefix: '',
      number_suffix: '',
    }
    const result = fieldType.toHumanReadableString(field, '1234.56')
    expect(result).toBe('£1,234.56')
  })

  test('getName returns fieldType.currency i18n key', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'currency')
    expect(fieldType.getName()).toBe('fieldType.currency')
  })

  test('getFormComponent returns FieldCurrencySubForm', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'currency')
    const component = fieldType.getFormComponent()
    expect(component).toBeDefined()
    expect(component.name || component.__name).toBe('FieldCurrencySubForm')
  })

  test('toHumanReadableString pads decimal places on whole numbers', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'currency')
    const field = {
      currency_symbol: '$',
      number_decimal_places: 2,
      number_negative: false,
      number_separator: 'NO_FORMATTING',
      number_prefix: '',
      number_suffix: '',
    }
    const result = fieldType.toHumanReadableString(field, '9')
    expect(result).toBe('$9.00')
  })
})
