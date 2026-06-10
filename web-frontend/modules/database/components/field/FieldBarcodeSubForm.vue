<template>
  <div>
    <FormGroup
      small-label
      :label="$t('fieldBarcodeSubForm.typeLabel')"
      class="margin-bottom-2"
    >
      <Dropdown
        v-model="values.barcode_type"
        :show-search="false"
        :fixed-items="true"
      >
        <DropdownItem name="QR Code" value="qr" />
        <DropdownItem name="Code 128" value="code128" />
      </Dropdown>
    </FormGroup>
    <FieldTextSubForm :default-values="defaultValues" />
  </div>
</template>

<script>
import form from '@baserow/modules/core/mixins/form'
import fieldSubForm from '@baserow/modules/database/mixins/fieldSubForm'
import FieldTextSubForm from '@baserow/modules/database/components/field/FieldTextSubForm'

export default {
  name: 'FieldBarcodeSubForm',
  components: { FieldTextSubForm },
  mixins: [form, fieldSubForm],
  data() {
    return {
      allowedValues: ['barcode_type'],
      values: {
        barcode_type: 'qr',
      },
    }
  },
}
</script>
