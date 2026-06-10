<template>
  <div ref="cell" class="grid-view__cell active">
    <div v-if="value" class="grid-field-barcode">
      <qrcode-vue
        v-if="field.barcode_type === 'qr'"
        :value="String(value)"
        :size="32"
        render-as="svg"
      />
      <svg v-else ref="code128Svg" class="grid-field-barcode__code128" />
    </div>
  </div>
</template>

<script>
import gridField from '@baserow/modules/database/mixins/gridField'
import QrcodeVue from 'qrcode.vue'
import JsBarcode from 'jsbarcode'

export default {
  name: 'GridViewFieldBarcode',
  components: { QrcodeVue },
  mixins: [gridField],
  watch: {
    value: {
      immediate: true,
      handler(val) {
        this.$nextTick(() => this._renderCode128(val))
      },
    },
    'field.barcode_type': {
      handler() {
        this.$nextTick(() => this._renderCode128(this.value))
      },
    },
  },
  methods: {
    _renderCode128(val) {
      if (!val || this.field.barcode_type !== 'code128') return
      if (!this.$refs.code128Svg) return
      try {
        JsBarcode(this.$refs.code128Svg, String(val), {
          format: 'CODE128',
          width: 1,
          height: 40,
          displayValue: false,
          margin: 0,
        })
      } catch (e) {
        // Invalid Code128 characters — clear SVG (AC #5)
        this.$refs.code128Svg.innerHTML = ''
      }
    },
  },
}
</script>
