<template>
  <nuxt-link
    class="notification-panel__notification-link"
    :to="route"
    @click="markAsReadAndHandleClick"
  >
    <div class="notification-panel__notification-content-title">
      <i18n-t keypath="rowCommentCreatedNotification.title" tag="span">
        <template #sender>
          <strong v-if="sender">{{ sender }}</strong>
          <strong v-else
            ><s>{{ $t('rowCommentCreatedNotification.unknownUser') }}</s></strong
          >
        </template>
        <template #rowId>
          <strong>{{
            notification.data.row_name || notification.data.row_id
          }}</strong>
        </template>
      </i18n-t>
    </div>
  </nuxt-link>
</template>

<script>
import notificationContent from '@baserow/modules/core/mixins/notificationContent'

export default {
  name: 'RowCommentCreatedNotification',
  mixins: [notificationContent],
  emits: ['close-panel'],
  methods: {
    handleClick() {
      this.$emit('close-panel')
    },
  },
}
</script>
