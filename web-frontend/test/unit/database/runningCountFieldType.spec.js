import { TestApp } from '@baserow/test/helpers/testApp'
import { RunningCountFieldType } from '@baserow/modules/database/fieldTypes'

describe('RunningCountFieldType', () => {
  let testApp

  beforeAll(() => {
    testApp = new TestApp()
  })

  afterEach(() => {
    testApp.afterEach()
  })

  test('getType returns running_count', () => {
    expect(RunningCountFieldType.getType()).toBe('running_count')
  })

  test('getIconClass returns iconoir-stats-up-square', () => {
    expect(RunningCountFieldType.getIconClass()).toBe('iconoir-stats-up-square')
  })

  test('toHumanReadableString returns number value', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'running_count')
    expect(fieldType.toHumanReadableString({}, 42)).toBe(42)
  })

  test('toHumanReadableString returns empty string for null', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'running_count')
    expect(fieldType.toHumanReadableString({}, null)).toBe('')
  })

  test('isReadOnlyField returns true', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'running_count')
    expect(fieldType.isReadOnlyField()).toBe(true)
  })

  test('shouldFetchDataWhenAdded returns true', () => {
    const fieldType = testApp.getApp().$registry.get('field', 'running_count')
    expect(fieldType.shouldFetchDataWhenAdded()).toBe(true)
  })
})
