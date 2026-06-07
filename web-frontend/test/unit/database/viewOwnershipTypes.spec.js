import {
  CollaborativeViewOwnershipType,
  PersonalViewOwnershipType,
} from '@baserow/modules/database/viewOwnershipTypes'

const mockApp = {
  $i18n: { t: (key) => key },
  $hasPermission: () => true,
}

describe('CollaborativeViewOwnershipType', () => {
  let type

  beforeEach(() => {
    type = new CollaborativeViewOwnershipType({ app: mockApp })
  })

  test('type is collaborative', () => {
    expect(type.getType()).toBe('collaborative')
  })

  test('getListViewTypeSort returns 50', () => {
    expect(type.getListViewTypeSort()).toBe(50)
  })

  test('serialize returns type and name', () => {
    const serialized = type.serialize()
    expect(serialized.type).toBe('collaborative')
    expect(typeof serialized.name).toBe('string')
  })
})

describe('PersonalViewOwnershipType', () => {
  let type

  beforeEach(() => {
    type = new PersonalViewOwnershipType({ app: mockApp })
  })

  test('type is personal', () => {
    expect(type.getType()).toBe('personal')
  })

  test('getListViewTypeSort returns 100', () => {
    expect(type.getListViewTypeSort()).toBe(100)
  })

  test('isCompatibleWithViewType returns true for all view types', () => {
    expect(type.isCompatibleWithViewType('grid')).toBe(true)
    expect(type.isCompatibleWithViewType('kanban')).toBe(true)
    expect(type.isCompatibleWithViewType('calendar')).toBe(true)
  })

  test('serialize returns type and name', () => {
    const serialized = type.serialize()
    expect(serialized.type).toBe('personal')
    expect(typeof serialized.name).toBe('string')
  })

  test('getIconClass returns eye-off icon', () => {
    expect(type.getIconClass()).toBe('iconoir-eye-off')
  })

  test('personal sort is higher than collaborative sort', () => {
    const collaborative = new CollaborativeViewOwnershipType({ app: mockApp })
    expect(type.getListViewTypeSort()).toBeGreaterThan(
      collaborative.getListViewTypeSort()
    )
  })
})
