<template>
  <form @submit.prevent>
    <FormRow class="margin-bottom-2">
      <FormGroup
        :label="$t('viewEmbedElementForm.databaseLabel')"
        small-label
        required
      >
        <Dropdown v-model="databaseSelectedId" :show-search="false" fixed-items>
          <DropdownItem
            v-for="database in databases"
            :key="database.id"
            :name="database.name"
            :value="database.id"
          >
            {{ database.name }}
          </DropdownItem>
        </Dropdown>
      </FormGroup>
      <FormGroup
        :label="$t('viewEmbedElementForm.viewLabel')"
        small-label
        required
      >
        <Dropdown
          v-model="values.view_id"
          :show-search="false"
          :disabled="databaseSelectedId === null"
          fixed-items
        >
          <DropdownItem
            v-for="view in eligibleViews"
            :key="view.id"
            :name="view.name"
            :value="view.id"
          >
            {{ view.name }}
          </DropdownItem>
        </Dropdown>
      </FormGroup>
    </FormRow>
  </form>
</template>

<script>
import elementForm from '@baserow/modules/builder/mixins/elementForm'

const EMBED_VIEW_TYPES = ['kanban', 'calendar', 'timeline']

export default {
  name: 'ViewEmbedElementForm',
  mixins: [elementForm],
  data() {
    return {
      allowedValues: ['view_id'],
      values: {
        view_id: null,
      },
      databaseSelectedId: null,
    }
  },
  computed: {
    databases() {
      return this.builder.integrations?.[0]?.context_data?.databases || []
    },
    databaseSelected() {
      return this.databases.find((db) => db.id === this.databaseSelectedId)
    },
    eligibleViews() {
      return (this.databaseSelected?.views || []).filter((v) =>
        EMBED_VIEW_TYPES.includes(v.type)
      )
    },
  },
  watch: {
    'values.view_id': {
      handler(viewId) {
        if (viewId && this.databaseSelectedId === null) {
          const db = this.databases.find((d) =>
            d.views.some((v) => v.id === viewId)
          )
          if (db) this.databaseSelectedId = db.id
        }
      },
      immediate: true,
    },
  },
}
</script>
