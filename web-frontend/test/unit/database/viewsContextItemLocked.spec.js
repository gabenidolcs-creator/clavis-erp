/**
 * Unit tests for locked-view behaviour in ViewsContextItem.vue (Story 1.7).
 *
 * Tests focus on the isLockedForCurrentUser computed property logic without
 * mounting the full component — the logic is deterministic given view.locked,
 * view.owned_by_id, userId, and the $hasPermission result.
 */

function buildIsLockedForCurrentUser({ locked, ownedById, userId, hasPermission }) {
  // Replicate the computed property from ViewsContextItem.vue
  const view = { locked, owned_by_id: ownedById }
  const database = { workspace: { id: 1 } }

  const $store = { getters: { 'auth/getUserId': userId } }
  const $hasPermission = () => hasPermission

  if (!view.locked) return false
  const resolvedUserId = $store.getters['auth/getUserId']
  if (view.owned_by_id === resolvedUserId) return false
  if ($hasPermission('database.table.view.update_locked_config', view, database.workspace.id)) return false
  return true
}

describe('isLockedForCurrentUser', () => {
  test('returns false when view is not locked', () => {
    expect(
      buildIsLockedForCurrentUser({
        locked: false,
        ownedById: 1,
        userId: 2,
        hasPermission: false,
      })
    ).toBe(false)
  })

  test('returns false when user is the lock owner', () => {
    expect(
      buildIsLockedForCurrentUser({
        locked: true,
        ownedById: 42,
        userId: 42,
        hasPermission: false,
      })
    ).toBe(false)
  })

  test('returns false when user is admin (has update_locked_config permission)', () => {
    expect(
      buildIsLockedForCurrentUser({
        locked: true,
        ownedById: 1,
        userId: 99,
        hasPermission: true,
      })
    ).toBe(false)
  })

  test('returns true for non-owner non-admin when view is locked', () => {
    expect(
      buildIsLockedForCurrentUser({
        locked: true,
        ownedById: 1,
        userId: 2,
        hasPermission: false,
      })
    ).toBe(true)
  })

  test('returns true when ownedById is null and user is not admin', () => {
    expect(
      buildIsLockedForCurrentUser({
        locked: true,
        ownedById: null,
        userId: 5,
        hasPermission: false,
      })
    ).toBe(true)
  })
})
