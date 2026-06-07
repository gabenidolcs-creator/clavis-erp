<template>
  <div>
    <FormGroup
      small-label
      :label="$t('fieldCurrencySubForm.symbolLabel')"
      class="margin-bottom-2"
    >
      <FormInput
        v-model="v$.values.currency_symbol.$model"
        :error="fieldHasErrors('currency_symbol')"
        type="text"
        :placeholder="$t('fieldCurrencySubForm.symbolPlaceholder')"
        @blur="v$.values.currency_symbol.$touch"
      ></FormInput>
    </FormGroup>
    <FieldNumberSubForm
      :default-values="defaultValues"
      :allow-set-number-negative="true"
    />
  </div>
</template>

<script>
import { useVuelidate } from '@vuelidate/core'
import { maxLength } from '@vuelidate/validators'
import form from '@baserow/modules/core/mixins/form'
import fieldSubForm from '@baserow/modules/database/mixins/fieldSubForm'
import FieldNumberSubForm from '@baserow/modules/database/components/field/FieldNumberSubForm'

export default {
  name: 'FieldCurrencySubForm',
  components: { FieldNumberSubForm },
  mixins: [form, fieldSubForm],
  setup() {
    return { v$: useVuelidate({ $lazy: true }) }
  },
  data() {
    return {
      allowedValues: ['currency_symbol'],
      values: {
        currency_symbol: '$',
      },
    }
  },
  validations() {
    return {
      values: {
        currency_symbol: { maxLength: maxLength(10) },
      },
    }
  },
}
</script>
