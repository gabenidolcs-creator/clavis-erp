import { TestApp } from '@baserow/test/helpers/testApp'
import { AutonumberFieldType } from '@baserow/modules/database/fieldTypes'

describe('AutonumberFieldType', () => {
  let testApp

  beforeAll(() => {
    testApp = new TestApp()
  })

  afterEach(() => {
    testApp.afterEach()
  })

  test('getType returns autonumber', () => {
    expect(AutonumberFieldType.getType()).toBe('autonumber')
  })

  test('getIconClass returns iconoir-numbered-list-left', () => {
    expect(AutonumberFieldType.getIconClass()).toBe(
      'iconoir-numbered-list-left'
    )
  })

  test('isReadOnlyField returns true', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'autonumber')
    expect(fieldType.isReadOnlyField()).toBe(true)
  })

  test('shouldFetchDataWhenAdded returns true', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'autonumber')
    expect(fieldType.shouldFetchDataWhenAdded()).toBe(true)
  })

  test('toHumanReadableString returns number value', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'autonumber')
    expect(fieldType.toHumanReadableString({}, 42)).toBe(42)
  })

  test('toHumanReadableString returns empty string for null', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'autonumber')
    expect(fieldType.toHumanReadableString({}, null)).toBe('')
  })
})
