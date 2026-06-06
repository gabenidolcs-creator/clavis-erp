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

  test('defers (returns null) — server is the authoritative source of truth', () => {
    const registry = testApp.getRegistry()
    const type = registry.get('permissionManager', 'rbac')

    // Story 1.3 enforces Viewer/Commenter denial SERVER-side (403). The client
    // deliberately keeps deferring (null) to avoid a second source of truth; it does
    // not mirror the deny. Even a mutating op resolves to null on the client.
    expect(type.hasPermission({}, 'workspace.update', {}, 1)).toBe(null)
    expect(
      type.hasPermission({}, 'database.table.create_row', {}, 1)
    ).toBe(null)
  })
})
