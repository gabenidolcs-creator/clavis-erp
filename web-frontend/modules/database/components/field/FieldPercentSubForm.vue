<template>
  <FieldNumberSubForm
    :default-values="defaultValues"
    :allow-set-number-negative="true"
  />
</template>

<script>
import form from '@baserow/modules/core/mixins/form'
import fieldSubForm from '@baserow/modules/database/mixins/fieldSubForm'
import FieldNumberSubForm from '@baserow/modules/database/components/field/FieldNumberSubForm'

export default {
  name: 'FieldPercentSubForm',
  components: { FieldNumberSubForm },
  mixins: [form, fieldSubForm],
  data() {
    return {
      allowedValues: [],
      values: {},
    }
  },
}
</script>
