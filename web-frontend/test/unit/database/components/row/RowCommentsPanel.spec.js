import { vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createStore } from 'vuex'
import RowCommentsPanel from '@baserow/modules/database/components/row/RowCommentsPanel'
import rowCommentsStore from '@baserow/modules/database/store/rowComments'

const SIMPLE_MESSAGE = {
  type: 'doc',
  content: [{ type: 'paragraph', content: [{ type: 'text', text: 'hello' }] }],
}

const mockComment = (overrides = {}) => ({
  id: 1,
  author: { id: 10, name: 'Alice' },
  message: SIMPLE_MESSAGE,
  created_on: '2026-06-12T00:00:00Z',
  updated_on: '2026-06-12T00:00:00Z',
  ...overrides,
})

function createTestStore(comments = []) {
  const store = createStore({
    modules: {
      rowComments: rowCommentsStore,
      auth: {
        namespaced: true,
        getters: {
          getUserId: () => 10,
        },
      },
    },
  })
  if (comments.length) {
    store.commit('rowComments/SET_COMMENTS', {
      tableId: 1,
      rowId: 42,
      comments,
    })
  }
  return store
}

function mountPanel(store, propsData = {}) {
  return mount(RowCommentsPanel, {
    global: {
      plugins: [store],
      stubs: {
        RichTextEditor: {
          template: '<div class="rich-text-editor-stub"></div>',
          props: ['modelValue', 'editable', 'mentionableUsers', 'placeholder'],
          emits: ['update:modelValue', 'shift-enter'],
        },
        RowCommentItem: {
          template: '<div class="row-comment-item-stub">{{ comment.id }}</div>',
          props: ['comment', 'currentUserId', 'isAdmin', 'readOnly', 'mentionableUsers'],
          emits: ['update', 'delete'],
        },
      },
      mocks: {
        $t: (key) => key,
        $store: store,
      },
    },
    propsData: {
      table: { id: 1 },
      row: { id: 42 },
      readOnly: false,
      mentionableUsers: [],
      isAdmin: false,
      ...propsData,
    },
  })
}

describe('RowCommentsPanel', () => {
  test('renders comment list when comments exist', async () => {
    const store = createTestStore([mockComment(), mockComment({ id: 2 })])
    store.dispatch = vi.fn().mockResolvedValue(undefined)
    const wrapper = mountPanel(store)
    await wrapper.vm.$nextTick()
    const items = wrapper.findAll('.row-comment-item-stub')
    expect(items.length).toBe(2)
  })

  test('shows empty state when no comments', async () => {
    const store = createTestStore([])
    store.dispatch = vi.fn().mockResolvedValue(undefined)
    const wrapper = mountPanel(store)
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('rowComments.noComments')
  })

  test('hides compose area when readOnly=true', async () => {
    const store = createTestStore([])
    store.dispatch = vi.fn().mockResolvedValue(undefined)
    const wrapper = mountPanel(store, { readOnly: true })
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.row-comments-panel__compose').exists()).toBe(false)
  })

  test('shows compose area for Commenter (readOnly=false)', async () => {
    const store = createTestStore([])
    store.dispatch = vi.fn().mockResolvedValue(undefined)
    const wrapper = mountPanel(store, { readOnly: false })
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.row-comments-panel__compose').exists()).toBe(true)
  })

  test('submit button calls createComment store action', async () => {
    const store = createTestStore([])
    const dispatchSpy = vi.spyOn(store, 'dispatch').mockResolvedValue(undefined)
    const wrapper = mountPanel(store, { readOnly: false })
    await wrapper.vm.$nextTick()

    // Manually set hasContent to true by simulating non-empty message
    wrapper.vm.newMessage = SIMPLE_MESSAGE
    await wrapper.vm.$nextTick()

    const submitBtn = wrapper.find('button.button--primary')
    await submitBtn.trigger('click')
    await wrapper.vm.$nextTick()

    expect(dispatchSpy).toHaveBeenCalledWith(
      'rowComments/createComment',
      expect.objectContaining({
        tableId: 1,
        rowId: 42,
        message: SIMPLE_MESSAGE,
      })
    )
  })

  test('fetchSubscriptionStatus dispatched on mount', async () => {
    const store = createTestStore([])
    const dispatchSpy = vi.spyOn(store, 'dispatch').mockResolvedValue(undefined)
    mountPanel(store)
    expect(dispatchSpy).toHaveBeenCalledWith(
      'rowComments/fetchSubscriptionStatus',
      { tableId: 1, rowId: 42 }
    )
  })

  test('subscribe button shows when not subscribed', async () => {
    const store = createTestStore([])
    store.dispatch = vi.fn().mockResolvedValue(undefined)
    const wrapper = mountPanel(store)
    await wrapper.vm.$nextTick()
    const btns = wrapper.findAll('button')
    const subscribeBtn = btns.find((b) => b.text() === 'rowComments.subscribe')
    expect(subscribeBtn).toBeTruthy()
  })

  test('unsubscribe button shows when subscribed', async () => {
    const store = createTestStore([])
    store.dispatch = vi.fn().mockResolvedValue(undefined)
    store.commit('rowComments/SET_SUBSCRIBED', { tableId: 1, rowId: 42, subscribed: true })
    const wrapper = mountPanel(store)
    await wrapper.vm.$nextTick()
    const btns = wrapper.findAll('button')
    const unsubscribeBtn = btns.find((b) => b.text() === 'rowComments.unsubscribe')
    expect(unsubscribeBtn).toBeTruthy()
  })

  test('subscribe button click dispatches subscribe action', async () => {
    const store = createTestStore([])
    const dispatchSpy = vi.spyOn(store, 'dispatch').mockResolvedValue(undefined)
    const wrapper = mountPanel(store)
    await wrapper.vm.$nextTick()
    const btns = wrapper.findAll('button')
    const subscribeBtn = btns.find((b) => b.text() === 'rowComments.subscribe')
    await subscribeBtn.trigger('click')
    expect(dispatchSpy).toHaveBeenCalledWith(
      'rowComments/subscribe',
      { tableId: 1, rowId: 42 }
    )
  })

  test('unsubscribe button click dispatches unsubscribe action', async () => {
    const store = createTestStore([])
    const dispatchSpy = vi.spyOn(store, 'dispatch').mockResolvedValue(undefined)
    store.commit('rowComments/SET_SUBSCRIBED', { tableId: 1, rowId: 42, subscribed: true })
    const wrapper = mountPanel(store)
    await wrapper.vm.$nextTick()
    const btns = wrapper.findAll('button')
    const unsubscribeBtn = btns.find((b) => b.text() === 'rowComments.unsubscribe')
    await unsubscribeBtn.trigger('click')
    expect(dispatchSpy).toHaveBeenCalledWith(
      'rowComments/unsubscribe',
      { tableId: 1, rowId: 42 }
    )
  })
})
