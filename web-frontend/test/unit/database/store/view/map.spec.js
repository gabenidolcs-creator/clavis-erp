import mapStore from '@baserow/modules/database/store/view/map'
import { TestApp } from '@baserow/test/helpers/testApp'

describe('Map view store', () => {
  let testApp = null
  let store = null

  beforeEach(() => {
    testApp = new TestApp()
    store = testApp.createStore({
      modules: {
        map: { ...mapStore, namespaced: true },
      },
    })
  })

  afterEach(() => {
    testApp.afterEach()
  })

  describe('pinUpdated', () => {
    test('adds new pin when row_id not in pins', async () => {
      await store.commit('map/SET_PINS', [])
      await store.commit('map/SET_UNRESOLVABLE', [])

      await store.dispatch('map/pinUpdated', { rowId: 5, lat: 10.0, lng: 20.0 })

      expect(store.getters['map/getPins']).toHaveLength(1)
      expect(store.getters['map/getPins'][0]).toEqual({
        row_id: 5,
        lat: 10.0,
        lng: 20.0,
      })
    })

    test('replaces existing pin when row_id already in pins', async () => {
      await store.commit('map/SET_PINS', [{ row_id: 5, lat: 1.0, lng: 2.0 }])

      await store.dispatch('map/pinUpdated', { rowId: 5, lat: 10.0, lng: 20.0 })

      expect(store.getters['map/getPins']).toHaveLength(1)
      expect(store.getters['map/getPins'][0].lat).toBe(10.0)
      expect(store.getters['map/getPins'][0].lng).toBe(20.0)
    })

    test('removes row from unresolvable when pin is resolved', async () => {
      await store.commit('map/SET_PINS', [])
      await store.commit('map/SET_UNRESOLVABLE', [
        { row_id: 3, address: 'somewhere' },
        { row_id: 9, address: 'elsewhere' },
      ])

      await store.dispatch('map/pinUpdated', { rowId: 3, lat: 5.0, lng: 6.0 })

      const unresolvable = store.getters['map/getUnresolvable']
      expect(unresolvable).toHaveLength(1)
      expect(unresolvable[0].row_id).toBe(9)
      expect(store.getters['map/getPins']).toHaveLength(1)
    })

    test('unresolvable unchanged when updated row was not there', async () => {
      await store.commit('map/SET_PINS', [{ row_id: 1, lat: 0.0, lng: 0.0 }])
      await store.commit('map/SET_UNRESOLVABLE', [
        { row_id: 7, address: 'abc' },
      ])

      await store.dispatch('map/pinUpdated', { rowId: 99, lat: 1.0, lng: 2.0 })

      expect(store.getters['map/getUnresolvable']).toHaveLength(1)
    })
  })

  describe('selectRow', () => {
    test('sets selectedRowId in state', async () => {
      expect(store.getters['map/getSelectedRowId']).toBeNull()
      await store.dispatch('map/selectRow', 42)
      expect(store.getters['map/getSelectedRowId']).toBe(42)
    })

    test('can clear selectedRowId to null', async () => {
      await store.dispatch('map/selectRow', 42)
      await store.dispatch('map/selectRow', null)
      expect(store.getters['map/getSelectedRowId']).toBeNull()
    })
  })

  describe('fetchRows', () => {
    test('loads pins and unresolvable from API response', async () => {
      testApp.mock.onGet('/database/views/map/1/rows/').reply(200, {
        pins: [{ row_id: 1, lat: 10.0, lng: 20.0 }],
        unresolvable: [{ row_id: 2, address: 'unknown' }],
      })

      await store.dispatch('map/fetchRows', { viewId: 1 })

      expect(store.getters['map/getPins']).toHaveLength(1)
      expect(store.getters['map/getPins'][0]).toEqual({
        row_id: 1,
        lat: 10.0,
        lng: 20.0,
      })
      expect(store.getters['map/getUnresolvable']).toHaveLength(1)
      expect(store.getters['map/getUnresolvable'][0].row_id).toBe(2)
    })

    test('resets loading to false after successful fetch', async () => {
      testApp.mock
        .onGet('/database/views/map/2/rows/')
        .reply(200, { pins: [], unresolvable: [] })

      await store.dispatch('map/fetchRows', { viewId: 2 })

      expect(store.getters['map/isLoading']).toBe(false)
    })

    test('resets loading to false on API error', async () => {
      testApp.mock.onGet('/database/views/map/3/rows/').reply(500)

      await expect(
        store.dispatch('map/fetchRows', { viewId: 3 })
      ).rejects.toThrow()

      expect(store.getters['map/isLoading']).toBe(false)
    })

    test('handles empty pins and unresolvable fields in response', async () => {
      testApp.mock.onGet('/database/views/map/4/rows/').reply(200, {})

      await store.dispatch('map/fetchRows', { viewId: 4 })

      expect(store.getters['map/getPins']).toEqual([])
      expect(store.getters['map/getUnresolvable']).toEqual([])
    })
  })
})
