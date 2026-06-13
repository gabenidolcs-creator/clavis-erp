import { TestApp } from '@baserow/test/helpers/testApp'
import { expect, test, describe, beforeEach, afterEach } from 'vitest'

import {
  RbacPermissionManagerType,
  FieldPermissionManagerType,
} from '@baserow/modules/core/permissionManagerTypes'

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
      'INTERFACE_ONLY',
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
    expect(type.hasPermission({}, 'database.table.create_row', {}, 1)).toBe(
      null
    )
  })
})

describe('FieldPermissionManagerType', () => {
  let testApp = null

  beforeEach(() => {
    testApp = new TestApp()
  })

  afterEach(() => {
    testApp.afterEach()
  })

  test('is registered in the permissionManager namespace', () => {
    const registry = testApp.getRegistry()
    const type = registry.get('permissionManager', 'field_permissions')

    expect(type.constructor.name).toBe('FieldPermissionManagerType')
    expect(type.getType()).toBe('field_permissions')
    expect(FieldPermissionManagerType.getType()).toBe('field_permissions')
  })

  test('renders a restricted field read-only (false) for governed edit ops', () => {
    const registry = testApp.getRegistry()
    const type = registry.get('permissionManager', 'field_permissions')
    const permissions = { restricted_field_ids: [42] }

    expect(
      type.hasPermission(
        permissions,
        'database.table.field.write_values',
        { id: 42 },
        1
      )
    ).toBe(false)
    expect(
      type.hasPermission(
        permissions,
        'database.table.field.update',
        { id: 42 },
        1
      )
    ).toBe(false)
  })

  test('defers (null) for an unrestricted field', () => {
    const registry = testApp.getRegistry()
    const type = registry.get('permissionManager', 'field_permissions')
    const permissions = { restricted_field_ids: [42] }

    expect(
      type.hasPermission(
        permissions,
        'database.table.field.write_values',
        { id: 7 },
        1
      )
    ).toBe(null)
  })

  test('defers (null) for a non-governed operation on a restricted field', () => {
    const registry = testApp.getRegistry()
    const type = registry.get('permissionManager', 'field_permissions')
    const permissions = { restricted_field_ids: [42] }

    // Read is not a governed op — the field stays readable, server stays the SoT.
    expect(
      type.hasPermission(
        permissions,
        'database.table.field.read',
        { id: 42 },
        1
      )
    ).toBe(null)
  })

  test('defers (null) when no restricted_field_ids payload is present', () => {
    const registry = testApp.getRegistry()
    const type = registry.get('permissionManager', 'field_permissions')

    expect(
      type.hasPermission({}, 'database.table.field.write_values', { id: 42 }, 1)
    ).toBe(null)
  })

  // Story 1.5: hidden_field_ids hides a column entirely (false for read op).

  test('hides a field (false) for read op when hidden_field_ids contains it', () => {
    const registry = testApp.getRegistry()
    const type = registry.get('permissionManager', 'field_permissions')
    const permissions = { hidden_field_ids: [42] }

    expect(
      type.hasPermission(
        permissions,
        'database.table.field.read',
        { id: 42 },
        1
      )
    ).toBe(false)
  })

  test('defers (null) for read op on a field NOT in hidden_field_ids', () => {
    const registry = testApp.getRegistry()
    const type = registry.get('permissionManager', 'field_permissions')
    const permissions = { hidden_field_ids: [42] }

    expect(
      type.hasPermission(permissions, 'database.table.field.read', { id: 7 }, 1)
    ).toBe(null)
  })

  test('hidden field write op defers (null) — hidden alone does not block writes', () => {
    const registry = testApp.getRegistry()
    const type = registry.get('permissionManager', 'field_permissions')
    const permissions = { hidden_field_ids: [42] }

    expect(
      type.hasPermission(
        permissions,
        'database.table.field.write_values',
        { id: 42 },
        1
      )
    ).toBe(null)
  })

  test('restricted_field_ids and hidden_field_ids coexist independently', () => {
    const registry = testApp.getRegistry()
    const type = registry.get('permissionManager', 'field_permissions')
    const permissions = { restricted_field_ids: [10], hidden_field_ids: [20] }

    // Edit-restricted field is blocked for write, defers for read.
    expect(
      type.hasPermission(
        permissions,
        'database.table.field.write_values',
        { id: 10 },
        1
      )
    ).toBe(false)
    expect(
      type.hasPermission(
        permissions,
        'database.table.field.read',
        { id: 10 },
        1
      )
    ).toBe(null)

    // Hidden field is blocked for read, defers for write.
    expect(
      type.hasPermission(
        permissions,
        'database.table.field.read',
        { id: 20 },
        1
      )
    ).toBe(false)
    expect(
      type.hasPermission(
        permissions,
        'database.table.field.write_values',
        { id: 20 },
        1
      )
    ).toBe(null)
  })
})
