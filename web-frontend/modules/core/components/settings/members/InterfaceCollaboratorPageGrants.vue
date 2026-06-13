<template>
  <div class="interface-page-grants">
    <div class="interface-page-grants__header">
      <h3 class="interface-page-grants__title">
        {{ $t('interfaceCollaboratorPageGrants.title') }}
      </h3>
      <p class="interface-page-grants__description">
        {{ $t('interfaceCollaboratorPageGrants.description') }}
      </p>
    </div>
    <div v-if="loading" class="loading"></div>
    <p v-else-if="builderApps.length === 0" class="interface-page-grants__empty">
      {{ $t('interfaceCollaboratorPageGrants.noApps') }}
    </p>
    <div v-else class="interface-page-grants__apps">
      <div
        v-for="app in builderApps"
        :key="app.id"
        class="interface-page-grants__app"
      >
        <div class="interface-page-grants__app-name">
          <i class="iconoir-app-window"></i>
          {{ app.name }}
        </div>
        <div
          v-for="page in visiblePages(app)"
          :key="page.id"
          class="interface-page-grants__page"
        >
          <Checkbox
            :checked="isGranted(page.id)"
            :disabled="toggling[page.id]"
            @input="toggleGrant(page)"
          >
            {{ page.name || page.path }}
          </Checkbox>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'
import { notifyIf } from '@baserow/modules/core/utils/error'

export default {
  name: 'InterfaceCollaboratorPageGrants',
  props: {
    workspace: {
      type: Object,
      required: true,
    },
    member: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      loading: true,
      grantedPageIds: new Set(),
      toggling: {},
    }
  },
  computed: {
    ...mapGetters({
      getAllOfWorkspace: 'application/getAllOfWorkspace',
    }),
    builderApps() {
      return this.getAllOfWorkspace(this.workspace).filter(
        (app) => app.type === 'builder'
      )
    },
  },
  watch: {
    member: {
      immediate: true,
      async handler() {
        await this.loadGrants()
      },
    },
  },
  methods: {
    visiblePages(app) {
      return (app.pages || []).filter((p) => !p.shared)
    },
    isGranted(pageId) {
      return this.grantedPageIds.has(pageId)
    },
    async loadGrants() {
      this.loading = true
      try {
        const { data } = await this.$client.get(
          `/rbac/workspaces/${this.workspace.id}/interface-collaborators/${this.member.id}/page-grants/`
        )
        this.grantedPageIds = new Set(data.map((g) => g.page_id))
      } catch (error) {
        notifyIf(error, 'workspace')
      } finally {
        this.loading = false
      }
    },
    async toggleGrant(page) {
      if (this.toggling[page.id]) return
      this.toggling = { ...this.toggling, [page.id]: true }
      const granted = this.isGranted(page.id)
      try {
        const url = `/rbac/workspaces/${this.workspace.id}/interface-collaborators/${this.member.id}/page-grants/`
        if (granted) {
          await this.$client.delete(url, { data: { page_id: page.id } })
          this.grantedPageIds.delete(page.id)
          this.grantedPageIds = new Set(this.grantedPageIds)
        } else {
          await this.$client.post(url, { page_id: page.id })
          this.grantedPageIds.add(page.id)
          this.grantedPageIds = new Set(this.grantedPageIds)
        }
      } catch (error) {
        notifyIf(error, 'workspace')
      } finally {
        this.toggling = { ...this.toggling, [page.id]: false }
      }
    },
  },
}
</script>
