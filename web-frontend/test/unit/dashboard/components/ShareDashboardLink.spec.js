import { TestApp } from '@baserow/test/helpers/testApp'
import ShareDashboardLink from '@baserow/modules/dashboard/components/ShareDashboardLink'

const mockEnableSharing = vi.fn().mockResolvedValue({ data: { public: true, slug: 'abc123' } })
const mockDisableSharing = vi.fn().mockResolvedValue({ data: { public: false, slug: 'abc123' } })
const mockRotateSlug = vi.fn().mockResolvedValue({ data: { public: true, slug: 'newslug99' } })

vi.mock('@baserow/modules/dashboard/services/share', () => ({
  default: () => ({
    enableSharing: mockEnableSharing,
    disableSharing: mockDisableSharing,
    rotateSlug: mockRotateSlug,
  }),
}))

describe('ShareDashboardLink.vue', () => {
  let testApp = null

  beforeEach(() => {
    testApp = new TestApp()
    vi.clearAllMocks()
  })

  afterEach(async () => {
    await testApp.afterEach()
  })

  function makeWrapper({
    dashboardPublic = true,
    slug = 'test-slug',
    canEdit = true,
  } = {}) {
    const dashboard = { id: 1, public: dashboardPublic, slug }
    return testApp.mount(ShareDashboardLink, {
      props: { dashboard, workspaceId: 10 },
      global: {
        mocks: {
          $config: { PUBLIC_WEB_FRONTEND_URL: 'https://example.com' },
          $hasPermission: () => canEdit,
          $client: {},
        },
      },
    })
  }

  it('renders share URL correctly when dashboard.public=true', async () => {
    const wrapper = await makeWrapper({ dashboardPublic: true, slug: 'test-slug' })
    const input = wrapper.find('input[readonly]')
    expect(input.exists()).toBe(true)
    expect(input.element.value).toBe(
      'https://example.com/public/dashboard/test-slug'
    )
  })

  it('does not show share URL when dashboard.public=false', async () => {
    const wrapper = await makeWrapper({ dashboardPublic: false })
    expect(wrapper.find('input[readonly]').exists()).toBe(false)
  })

  it('copy button is present when sharing enabled', async () => {
    const wrapper = await makeWrapper({ dashboardPublic: true })
    const buttons = wrapper.findAll('button')
    const copyBtn = buttons.find((b) => b.text().toLowerCase().includes('copy'))
    expect(copyBtn).toBeDefined()
  })

  it('toggle calls enableSharing when public=false', async () => {
    const wrapper = await makeWrapper({ dashboardPublic: false })
    // Call the method directly since SwitchInput is not globally registered in TestApp
    await wrapper.vm.toggleSharing()
    expect(mockEnableSharing).toHaveBeenCalledWith(1)
  })

  it('toggle calls disableSharing when public=true', async () => {
    const wrapper = await makeWrapper({ dashboardPublic: true })
    await wrapper.vm.toggleSharing()
    expect(mockDisableSharing).toHaveBeenCalledWith(1)
  })

  it('rotate button calls rotateSlug', async () => {
    const wrapper = await makeWrapper({ dashboardPublic: true })
    await wrapper.vm.rotateLink()
    expect(mockRotateSlug).toHaveBeenCalledWith(1)
  })

  it('edit controls absent when user lacks application.update permission', async () => {
    const wrapper = await makeWrapper({ dashboardPublic: true, canEdit: false })
    // No SwitchInput (edit toggle) and no rotate button when canEdit=false
    expect(wrapper.findComponent({ name: 'SwitchInput' }).exists()).toBe(false)
    expect(wrapper.find('.share-dashboard-link__rotate').exists()).toBe(false)
  })
})
