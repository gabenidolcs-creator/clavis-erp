import { TestApp } from '@baserow/test/helpers/testApp'
import { expect, test, describe, beforeEach, afterEach } from 'vitest'

import { RbacPermissionManagerType } from '@baserow/modules/core/permissionManagerTypes'

describe('RbacPermissionManagerType', () => {
  let testApp = null

  beforeEach(() => {
    testApp = new TestApp()
  })

  afterEach(() => {
    testApp.afterEach()
  })

  test('is registered in the permissionManager namespace', () => {
    const registry = testApp.getRegistry()
    const type = registry.get('permissionManager', 'rbac')

    // Avoid asserting on the instance directly: a failing matcher would serialize the
    // whole app object (which holds store getters from other modules) and obscure the
    // result. Compare plain strings instead.
    expect(type.constructor.name).toBe('RbacPermissionManagerType')
    expect(type.getType()).toBe('rbac')
    expect(RbacPermissionManagerType.getType()).toBe('rbac')
  })

  test('exposes the four fixed role tiers with translations', () => {
    const registry = testApp.getRegistry()
    const type = registry.get('permissionManager', 'rbac')
    const roles = type.getRolesTranslations()

    expect(Object.keys(roles).sort()).toEqual([
      'ADMIN',
      'COMMENTER',
      'EDITOR',
      'VIEWER',
    ])
    for (const role of Object.values(roles)) {
      expect(typeof role.name).toBe('string')
      expect(role.name.length).toBeGreaterThan(0)
      expect(typeof role.description).toBe('string')
    }
  })

  test('defers (returns null) so existing behavior is preserved', () => {
    const registry = testApp.getRegistry()
    const type = registry.get('permissionManager', 'rbac')

    // Story 1.2 stands up the role layer but does not tighten client enforcement.
    expect(type.hasPermission({}, 'workspace.update', {}, 1)).toBe(null)
  })
})
