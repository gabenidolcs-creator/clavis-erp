<template>
  <div class="share-dashboard-link">
    <div class="share-dashboard-link__toggle">
      <label class="share-dashboard-link__label">
        {{ $t('shareDashboardLink.enablePublicShare') }}
      </label>
      <SwitchInput
        v-if="canEdit"
        :value="dashboard.public"
        @input="toggleSharing"
      />
      <span v-else>
        {{
          dashboard.public
            ? $t('shareDashboardLink.enabled')
            : $t('shareDashboardLink.disabled')
        }}
      </span>
    </div>

    <template v-if="dashboard.public">
      <div class="share-dashboard-link__url">
        <input
          ref="urlInput"
          class="share-dashboard-link__url-input"
          type="text"
          readonly
          :value="shareUrl"
          @click="$refs.urlInput.select()"
        />
        <Button type="secondary" @click="copyToClipboard">
          {{ $t('shareDashboardLink.copyLink') }}
        </Button>
      </div>

      <div v-if="canEdit" class="share-dashboard-link__rotate">
        <a @click="rotateLink">{{ $t('shareDashboardLink.rotateLink') }}</a>
      </div>
    </template>
  </div>
</template>

<script>
import ShareService from '@baserow/modules/dashboard/services/share'
import { notifyIf } from '@baserow/modules/core/utils/error'

export default {
  name: 'ShareDashboardLink',
  props: {
    dashboard: {
      type: Object,
      required: true,
    },
    workspaceId: {
      type: Number,
      required: true,
    },
  },
  emits: ['sharing-changed'],
  computed: {
    canEdit() {
      return this.$hasPermission(
        'application.update',
        this.dashboard,
        this.workspaceId
      )
    },
    shareUrl() {
      return (
        this.$config.PUBLIC_WEB_FRONTEND_URL +
        '/public/dashboard/' +
        this.dashboard.slug
      )
    },
  },
  methods: {
    async toggleSharing() {
      const { $client } = this
      try {
        const action = this.dashboard.public
          ? 'disableSharing'
          : 'enableSharing'
        const { data } = await ShareService($client)[action](this.dashboard.id)
        this.$emit('sharing-changed', data)
      } catch (error) {
        notifyIf(error, 'application')
      }
    },
    async rotateLink() {
      const { $client } = this
      try {
        const { data } = await ShareService($client).rotateSlug(
          this.dashboard.id
        )
        this.$emit('sharing-changed', data)
      } catch (error) {
        notifyIf(error, 'application')
      }
    },
    async copyToClipboard() {
      try {
        await navigator.clipboard.writeText(this.shareUrl)
      } catch {
        this.$refs.urlInput.select()
        document.execCommand('copy')
      }
    },
  },
}
</script>
