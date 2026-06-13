import { TestApp } from '@baserow/test/helpers/testApp'
import { describe, test, expect, beforeEach, afterEach } from 'vitest'
import InterfaceCollaboratorPageGrants from '@baserow/modules/core/components/settings/members/InterfaceCollaboratorPageGrants'

const WORKSPACE = { id: 1, name: 'Test WS' }
const MEMBER = { id: 42, user_id: 42, name: 'Priya' }
const PAGE = { id: 10, name: 'Home', path: '/home', shared: false }

const GRANTS_URL = `/rbac/workspaces/${WORKSPACE.id}/interface-collaborators/${MEMBER.id}/page-grants/`

// Minimal app object matching what getAllOfWorkspace returns.
// We use SET_ITEMS mutation (state.items) which getAllOfWorkspace reads directly.
function makeAppItem() {
  return {
    id: 5,
    name: 'My App',
    type: 'builder',
    workspace: { id: WORKSPACE.id },
    pages: [PAGE],
    _: { type: { serialize: () => ({ type: 'builder' }) }, loading: false, selected: false },
  }
}

describe('InterfaceCollaboratorPageGrants.vue', () => {
  let testApp = null

  beforeEach(() => {
    testApp = new TestApp()
    // Seed the application store so getAllOfWorkspace returns our builder app.
    testApp.store.commit('application/SET_ITEMS', [makeAppItem()])
  })

  afterEach(() => {
    testApp.afterEach()
  })

  test('loads grants on mount — grantedPageIds empty when no grants', async () => {
    testApp.mock.onGet(GRANTS_URL).reply(200, [])

    const wrapper = await testApp.mount(InterfaceCollaboratorPageGrants, {
      propsData: { workspace: WORKSPACE, member: MEMBER },
    })
    await new Promise((r) => setTimeout(r, 50))

    expect(wrapper.vm.grantedPageIds.size).toBe(0)
    expect(wrapper.vm.loading).toBe(false)
  })

  test('page is checked when grant exists in API response', async () => {
    testApp.mock.onGet(GRANTS_URL).reply(200, [{ page_id: PAGE.id }])

    const wrapper = await testApp.mount(InterfaceCollaboratorPageGrants, {
      propsData: { workspace: WORKSPACE, member: MEMBER },
    })
    await new Promise((r) => setTimeout(r, 50))

    expect(wrapper.vm.isGranted(PAGE.id)).toBe(true)
  })

  test('toggleGrant calls POST and marks page as granted', async () => {
    testApp.mock.onGet(GRANTS_URL).reply(200, [])
    testApp.mock.onPost(GRANTS_URL).reply(200, { page_id: PAGE.id })

    const wrapper = await testApp.mount(InterfaceCollaboratorPageGrants, {
      propsData: { workspace: WORKSPACE, member: MEMBER },
    })
    await new Promise((r) => setTimeout(r, 50))

    await wrapper.vm.toggleGrant(PAGE)
    await new Promise((r) => setTimeout(r, 30))

    expect(wrapper.vm.isGranted(PAGE.id)).toBe(true)
  })

  test('toggleGrant calls DELETE and marks page as revoked', async () => {
    testApp.mock.onGet(GRANTS_URL).reply(200, [{ page_id: PAGE.id }])
    testApp.mock.onDelete(GRANTS_URL).reply(204)

    const wrapper = await testApp.mount(InterfaceCollaboratorPageGrants, {
      propsData: { workspace: WORKSPACE, member: MEMBER },
    })
    await new Promise((r) => setTimeout(r, 50))

    await wrapper.vm.toggleGrant(PAGE)
    await new Promise((r) => setTimeout(r, 30))

    expect(wrapper.vm.isGranted(PAGE.id)).toBe(false)
  })

  test('shows empty state when no builder apps', async () => {
    testApp.store.commit('application/SET_ITEMS', [])
    testApp.mock.onGet(GRANTS_URL).reply(200, [])

    const wrapper = await testApp.mount(InterfaceCollaboratorPageGrants, {
      propsData: { workspace: WORKSPACE, member: MEMBER },
    })
    await new Promise((r) => setTimeout(r, 50))

    expect(wrapper.vm.builderApps).toHaveLength(0)
  })
})
