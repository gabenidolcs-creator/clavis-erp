<template>
  <ul v-if="!tableLoading" class="header__filter header__filter--full-width">
    <li class="header__filter-item">
      <a
        ref="locationContextLink"
        class="header__filter-link"
        @click="
          $refs.locationContext.toggle(
            $refs.locationContextLink,
            'bottom',
            'left',
            4
          )
        "
      >
        <i class="header__filter-icon iconoir-maps"></i>
        <span class="header__filter-name">{{
          locationSourceName || $t('mapViewHeader.chooseLocation')
        }}</span>
      </a>
      <Context ref="locationContext" class="map-view-header__location-context">
        <div class="map-view-header__location-inner">
          <div class="map-view-header__section">
            <div class="map-view-header__label">
              {{ $t('mapViewHeader.addressField') }}
            </div>
            <Dropdown
              :value="view.address_field"
              :show-search="true"
              :disabled="readOnly || updatingField"
              small
              @input="updateAddressField($event)"
            >
              <DropdownItem :value="null" :name="$t('mapViewHeader.none')" />
              <DropdownItem
                v-for="field in textFields"
                :key="field.id"
                :value="field.id"
                :name="field.name"
              />
            </Dropdown>
          </div>
          <div class="map-view-header__divider">
            {{ $t('mapViewHeader.or') }}
          </div>
          <div class="map-view-header__section">
            <div class="map-view-header__label">
              {{ $t('mapViewHeader.latField') }}
            </div>
            <Dropdown
              :value="view.lat_field"
              :show-search="true"
              :disabled="readOnly || updatingField"
              small
              @input="updateLatField($event)"
            >
              <DropdownItem :value="null" :name="$t('mapViewHeader.none')" />
              <DropdownItem
                v-for="field in numericFields"
                :key="field.id"
                :value="field.id"
                :name="field.name"
              />
            </Dropdown>
          </div>
          <div class="map-view-header__section">
            <div class="map-view-header__label">
              {{ $t('mapViewHeader.lngField') }}
            </div>
            <Dropdown
              :value="view.lng_field"
              :show-search="true"
              :disabled="readOnly || updatingField"
              small
              @input="updateLngField($event)"
            >
              <DropdownItem :value="null" :name="$t('mapViewHeader.none')" />
              <DropdownItem
                v-for="field in numericFields"
                :key="field.id"
                :value="field.id"
                :name="field.name"
              />
            </Dropdown>
          </div>
        </div>
      </Context>
    </li>
  </ul>
</template>

<script>
export default {
  name: 'MapViewHeader',
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
      updatingField: false,
    }
  },
  computed: {
    tableLoading() {
      return this.$store.getters['table/getLoading']
    },
    textFields() {
      return this.fields.filter((f) => ['text', 'long_text'].includes(f.type))
    },
    numericFields() {
      return this.fields.filter((f) => f.type === 'number')
    },
    locationSourceName() {
      if (this.view.address_field) {
        const field = this.fields.find((f) => f.id === this.view.address_field)
        return field ? field.name : null
      }
      if (this.view.lat_field && this.view.lng_field) {
        const lat = this.fields.find((f) => f.id === this.view.lat_field)
        const lng = this.fields.find((f) => f.id === this.view.lng_field)
        return lat && lng ? `${lat.name} / ${lng.name}` : null
      }
      return null
    },
  },
  methods: {
    async updateAddressField(fieldId) {
      if (this.updatingField) return
      this.updatingField = true
      try {
        await this.$store.dispatch('view/update', {
          view: this.view,
          values: {
            address_field: fieldId,
            // Selecting address mode clears lat/lng pair
            lat_field: null,
            lng_field: null,
          },
        })
        this.$emit('refresh')
      } finally {
        this.updatingField = false
      }
    },
    async updateLatField(fieldId) {
      if (this.updatingField) return
      this.updatingField = true
      try {
        await this.$store.dispatch('view/update', {
          view: this.view,
          values: {
            lat_field: fieldId,
            // Selecting lat/lng pair mode clears address
            address_field: null,
          },
        })
        this.$emit('refresh')
      } finally {
        this.updatingField = false
      }
    },
    async updateLngField(fieldId) {
      if (this.updatingField) return
      this.updatingField = true
      try {
        await this.$store.dispatch('view/update', {
          view: this.view,
          values: {
            lng_field: fieldId,
            // Selecting lat/lng pair mode clears address
            address_field: null,
          },
        })
        this.$emit('refresh')
      } finally {
        this.updatingField = false
      }
    },
  },
}
</script>
