<template>
  <div class="view-embed-element">
    <div v-if="loading" class="view-embed-element__loading">
      {{ $t('viewEmbedElement.loading') }}
    </div>
    <div v-else-if="fetchError" class="view-embed-element__error">
      {{ $t('viewEmbedElement.fetchError') }}
    </div>
    <div v-else-if="!viewMeta" class="view-embed-element__misconfigured">
      {{ $t('viewEmbedElement.notConfigured') }}
    </div>
    <div v-else-if="misconfigured" class="view-embed-element__misconfigured">
      {{ $t('viewEmbedElement.notConfigured') }}
    </div>
    <component
      :is="viewComponent"
      v-else-if="
        viewComponent &&
        resolvedView &&
        tableMeta &&
        databaseMeta &&
        resolvedFields
      "
      :view="resolvedView"
      :table="tableMeta"
      :database="databaseMeta"
      :fields="resolvedFields"
      :read-only="true"
      :store-prefix="storePrefix"
    />
  </div>
</template>

<script>
import KanbanView from '@baserow/modules/database/components/view/kanban/KanbanView'
import CalendarView from '@baserow/modules/database/components/view/calendar/CalendarView'
import TimelineView from '@baserow/modules/database/components/view/timeline/TimelineView'

const VIEW_COMPONENTS = {
  kanban: KanbanView,
  calendar: CalendarView,
  timeline: TimelineView,
}

export default {
  name: 'ViewEmbedElement',
  props: {
    element: { type: Object, required: true },
    builder: { type: Object, required: true },
    page: { type: Object, required: true },
    mode: { type: String, required: true },
  },
  data() {
    return {
      loading: false,
      fetchError: false,
      resolvedView: null,
      resolvedFields: null,
    }
  },
  computed: {
    integration() {
      return this.builder.integrations?.[0]
    },
    databases() {
      return this.integration?.context_data?.databases || []
    },
    viewMeta() {
      return this.databases
        .flatMap((db) => db.views)
        .find((v) => v.id === this.element.view_id)
    },
    tableMeta() {
      if (!this.viewMeta) return null
      return this.databases
        .flatMap((db) => db.tables)
        .find((t) => t.id === this.viewMeta.table_id)
    },
    databaseMeta() {
      if (!this.viewMeta) return null
      return this.databases.find((db) =>
        db.views.some((v) => v.id === this.viewMeta.id)
      )
    },
    viewComponent() {
      return VIEW_COMPONENTS[this.viewMeta?.type] || null
    },
    storePrefix() {
      return 'embed/' + this.element.id + '/'
    },
    misconfigured() {
      if (!this.resolvedView || !this.viewMeta) return false
      const type = this.viewMeta.type
      if (type === 'kanban') return !this.resolvedView.single_select_field
      if (type === 'calendar') return !this.resolvedView.date_field
      if (type === 'timeline')
        return (
          !this.resolvedView.start_date_field ||
          !this.resolvedView.end_date_field
        )
      return false
    },
  },
  watch: {
    'element.view_id': {
      handler(viewId) {
        if (viewId) {
          this.fetchViewData(viewId)
        } else {
          this.resolvedView = null
          this.resolvedFields = null
        }
      },
      immediate: true,
    },
  },
  methods: {
    async fetchViewData(viewId) {
      this.loading = true
      this.fetchError = false
      try {
        const [viewResponse, fieldsResponse] = await Promise.all([
          this.$client.database.views.get(viewId),
          this.viewMeta
            ? this.$client.database.fields.fetchAll(this.viewMeta.table_id)
            : Promise.resolve({ data: [] }),
        ])
        this.resolvedView = viewResponse.data
        this.resolvedFields = fieldsResponse.data
      } catch {
        this.fetchError = true
      } finally {
        this.loading = false
      }
    },
  },
}
</script>
