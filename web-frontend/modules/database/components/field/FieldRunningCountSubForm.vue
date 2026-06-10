<script>
import form from '@baserow/modules/core/mixins/form'
import fieldSubForm from '@baserow/modules/database/mixins/fieldSubForm'

export default {
  name: 'FieldRunningCountSubForm',
  mixins: [form, fieldSubForm],
  setup() {
    return () => null
  },
  data() {
    return {
      allowedValues: [],
      values: {},
    }
  },
}
</script>
