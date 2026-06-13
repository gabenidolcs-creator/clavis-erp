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
    <RowEditModal
      ref="rowEditModal"
      :database="database"
      :table="table"
      :view="view"
      :all-fields-in-table="fields"
      :rows="[]"
      :read-only="readOnly"
      @hidden="$emit('selected-row', undefined)"
      @update="$emit('refresh')"
      @field-updated="$emit('refresh', $event)"
      @field-deleted="$emit('refresh')"
    />
  </div>
</template>

<script>
import RowEditModal from '@baserow/modules/database/components/row/RowEditModal'

const TILE_URL = 'https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png'

export default {
  name: 'MapView',
  components: { RowEditModal },
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
  emits: ['refresh', 'selected-row'],
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
    pins() {
      this._updatePinsSource()
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
        this._initPinsSource()
      })
    },
    _initPinsSource() {
      this.mapInstance.addSource('pins', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
        cluster: true,
        clusterMaxZoom: 14,
        clusterRadius: 50,
      })

      this.mapInstance.addLayer({
        id: 'clusters',
        type: 'circle',
        source: 'pins',
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': '#1a73e8',
          'circle-radius': [
            'step',
            ['get', 'point_count'],
            20,
            100,
            30,
            750,
            40,
          ],
        },
      })

      this.mapInstance.addLayer({
        id: 'cluster-count',
        type: 'symbol',
        source: 'pins',
        filter: ['has', 'point_count'],
        layout: {
          'text-field': '{point_count_abbreviated}',
          'text-size': 12,
        },
        paint: { 'text-color': '#ffffff' },
      })

      this.mapInstance.addLayer({
        id: 'unclustered-point',
        type: 'circle',
        source: 'pins',
        filter: ['!', ['has', 'point_count']],
        paint: { 'circle-color': '#e53935', 'circle-radius': 8 },
      })

      this.mapInstance.on('click', 'clusters', (e) => {
        const feat = e.features[0]
        const clusterId = feat.properties.cluster_id
        this.mapInstance
          .getSource('pins')
          .getClusterExpansionZoom(clusterId, (err, zoom) => {
            if (err) return
            this.mapInstance.easeTo({
              center: feat.geometry.coordinates,
              zoom,
            })
          })
      })

      this.mapInstance.on('click', 'unclustered-point', (e) => {
        const rowId = e.features[0].properties.row_id
        this.$refs.rowEditModal.show(rowId)
      })

      this.mapInstance.on('mouseenter', 'clusters', () => {
        this.mapInstance.getCanvas().style.cursor = 'pointer'
      })
      this.mapInstance.on('mouseleave', 'clusters', () => {
        this.mapInstance.getCanvas().style.cursor = ''
      })
      this.mapInstance.on('mouseenter', 'unclustered-point', () => {
        this.mapInstance.getCanvas().style.cursor = 'pointer'
      })
      this.mapInstance.on('mouseleave', 'unclustered-point', () => {
        this.mapInstance.getCanvas().style.cursor = ''
      })

      this._updatePinsSource()
    },
    _updatePinsSource() {
      const source = this.mapInstance?.getSource('pins')
      if (!source) return
      source.setData({
        type: 'FeatureCollection',
        features: this.pins.map((pin) => ({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [pin.lng, pin.lat] },
          properties: { row_id: pin.row_id },
        })),
      })
    },
  },
}
</script>
