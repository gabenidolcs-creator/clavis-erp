import { TestApp } from '@baserow/test/helpers/testApp'
import { BarcodeFieldType } from '@baserow/modules/database/fieldTypes'

describe('BarcodeFieldType', () => {
  let testApp

  beforeAll(() => {
    testApp = new TestApp()
  })

  afterEach(() => {
    testApp.afterEach()
  })

  test('getType returns barcode', () => {
    expect(BarcodeFieldType.getType()).toBe('barcode')
  })

  test('getIconClass returns iconoir-barcode', () => {
    expect(BarcodeFieldType.getIconClass()).toBe('iconoir-barcode')
  })

  test('toHumanReadableString returns value as string', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'barcode')
    const field = { barcode_type: 'qr' }
    expect(fieldType.toHumanReadableString(field, 'ABC-123')).toBe('ABC-123')
  })

  test('toHumanReadableString returns empty string for null', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'barcode')
    const field = { barcode_type: 'qr' }
    expect(fieldType.toHumanReadableString(field, null)).toBe('')
  })

  test('toHumanReadableString returns empty string for undefined', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'barcode')
    const field = { barcode_type: 'qr' }
    expect(fieldType.toHumanReadableString(field, undefined)).toBe('')
  })

  test('toHumanReadableString returns empty string for empty string (AC #4)', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'barcode')
    const field = { barcode_type: 'qr' }
    expect(fieldType.toHumanReadableString(field, '')).toBe('')
  })
})
