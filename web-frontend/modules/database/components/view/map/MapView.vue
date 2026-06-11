<template>
  <div class="map-view">
    <div v-if="!hasLocationSource" class="map-view__no-source">
      <p>{{ $t('mapView.noLocationSource') }}</p>
    </div>
    <template v-else>
      <div class="map-view__main">
        <div ref="mapHost" class="map-view__host"></div>
      </div>
      <div v-if="unresolvable.length > 0" class="map-view__unresolvable">
        <div class="map-view__unresolvable-header">
          {{ $t('mapView.couldNotLocate') }}
          <span class="map-view__unresolvable-count">{{
            unresolvable.length
          }}</span>
        </div>
        <ul class="map-view__unresolvable-list">
          <li
            v-for="item in unresolvable"
            :key="item.row_id"
            class="map-view__unresolvable-item"
          >
            {{ $t('mapView.row') }} {{ item.row_id }}
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>

<script>
const TILE_URL =
  'https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png'

export default {
  name: 'MapView',
  props: {
    database: {
      type: Object,
      required: true,
    },
    table: {
      type: Object,
      required: true,
    },
    view: {
      type: Object,
      required: true,
    },
    fields: {
      type: Array,
      required: true,
    },
    readOnly: {
      type: Boolean,
      required: true,
    },
    storePrefix: {
      type: String,
      required: true,
    },
  },
  emits: ['refresh'],
  data() {
    return {
      mapInstance: null,
      loading: false,
    }
  },
  computed: {
    hasLocationSource() {
      return (
        this.view.address_field != null ||
        (this.view.lat_field != null && this.view.lng_field != null)
      )
    },
    pins() {
      return this.$store.getters[this.storePrefix + 'view/map/getPins']
    },
    unresolvable() {
      return this.$store.getters[this.storePrefix + 'view/map/getUnresolvable']
    },
  },
  watch: {
    'view.address_field'() {
      this.fetchRows()
    },
    'view.lat_field'() {
      this.fetchRows()
    },
    'view.lng_field'() {
      this.fetchRows()
    },
  },
  async mounted() {
    if (this.hasLocationSource) {
      await this.fetchRows()
      await this.initMap()
    }
  },
  beforeUnmount() {
    if (this.mapInstance) {
      this.mapInstance.remove()
      this.mapInstance = null
    }
  },
  methods: {
    async fetchRows() {
      await this.$store.dispatch(this.storePrefix + 'view/map/fetchRows', {
        viewId: this.view.id,
      })
    },
    async initMap() {
      // Lazy-load MapLibre GL JS — do NOT import at module level (bundle budget)
      const maplibregl = await import('maplibre-gl')
      await import('maplibre-gl/dist/maplibre-gl.css')

      if (!this.$refs.mapHost) return

      this.mapInstance = new maplibregl.default.Map({
        container: this.$refs.mapHost,
        style: {
          version: 8,
          sources: {
            osm: {
              type: 'raster',
              tiles: [TILE_URL],
              tileSize: 256,
            },
          },
          layers: [
            {
              id: 'osm',
              type: 'raster',
              source: 'osm',
            },
          ],
        },
        center: [0, 20],
        zoom: 2,
      })

      this.mapInstance.on('load', () => {
        this.renderPins()
      })
    },
    renderPins() {
      if (!this.mapInstance) return
      // Remove existing markers (simple approach for Story 3.13)
      const existingMarkers = this._markers || []
      existingMarkers.forEach((m) => m.remove())
      this._markers = []

      this.pins.forEach((pin) => {
        import('maplibre-gl').then((maplibregl) => {
          const marker = new maplibregl.default.Marker()
            .setLngLat([pin.lng, pin.lat])
            .addTo(this.mapInstance)
          marker.getElement().addEventListener('click', () => {
            this.$store.dispatch(
              this.storePrefix + 'view/map/selectRow',
              pin.row_id
            )
          })
          this._markers.push(marker)
        })
      })
    },
  },
}
</script>
