import { TestApp } from '@baserow/test/helpers/testApp'
import { CurrencyFieldType } from '@baserow/modules/database/fieldTypes'

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
})
