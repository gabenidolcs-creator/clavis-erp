<template>
  <div class="header__filter">
    <li class="header__filter-item">
      <a v-if="canEdit" class="header__filter-link" @click="toggleEditMode">
        <i class="header__filter-icon iconoir-edit"></i>
        <span class="header__filter-name">{{
          $t('dashboardHeaderMenuItems.editMode')
        }}</span>
      </a>
    </li>
    <li class="header__filter-item">
      <a
        v-if="canEdit"
        class="header__filter-link"
        @click="showShareModal = true"
      >
        <i class="header__filter-icon iconoir-share-android"></i>
        <span class="header__filter-name">{{
          $t('dashboardHeaderMenuItems.share')
        }}</span>
      </a>
    </li>
    <Modal
      v-if="canEdit"
      :open="showShareModal"
      @close="showShareModal = false"
    >
      <template #content>
        <ShareDashboardLink
          :dashboard="localDashboard"
          :workspace-id="dashboard.workspace.id"
          @sharing-changed="onSharingChanged"
        />
      </template>
    </Modal>
  </div>
</template>

<script>
import ShareDashboardLink from '@baserow/modules/dashboard/components/ShareDashboardLink'

export default {
  name: 'DashboardHeaderMenuItems',
  components: {
    ShareDashboardLink,
  },
  props: {
    dashboard: {
      type: Object,
      required: true,
    },
    storePrefix: {
      type: String,
      required: false,
      default: '',
    },
  },
  data() {
    return {
      showShareModal: false,
      localDashboard: { ...this.dashboard },
    }
  },
  computed: {
    canEdit() {
      return this.$hasPermission(
        'application.update',
        this.dashboard,
        this.dashboard.workspace.id
      )
    },
  },
  watch: {
    dashboard: {
      deep: true,
      handler(val) {
        this.localDashboard = { ...val }
      },
    },
  },
  methods: {
    toggleEditMode() {
      this.$store.dispatch(
        this.storePrefix + `dashboardApplication/toggleEditMode`
      )
    },
    onSharingChanged(data) {
      this.localDashboard = { ...this.localDashboard, ...data }
      this.$store.dispatch('dashboardApplication/setSharingState', {
        dashboardId: this.dashboard.id,
        public: data.public,
        slug: data.slug,
      })
    },
  },
}
</script>
