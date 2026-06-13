<template>
  <div class="row-comment-item">
    <div class="row-comment-item__header">
      <div class="row-comment-item__avatar">
        {{ initials }}
      </div>
      <div class="row-comment-item__meta">
        <span class="row-comment-item__author">{{ comment.author.name || 'Unknown' }}</span>
        <span class="row-comment-item__time">{{ formattedTime }}</span>
      </div>
      <div v-if="canModify && !readOnly" class="row-comment-item__actions">
        <a
          v-if="isOwn"
          class="row-comment-item__action"
          @click="startEdit"
        >
          <i class="iconoir-edit-pencil"></i>
        </a>
        <a
          class="row-comment-item__action row-comment-item__action--danger"
          @click="confirmDelete"
        >
          <i class="iconoir-trash"></i>
        </a>
      </div>
    </div>

    <div v-if="!editing" class="row-comment-item__body">
      <RichTextEditor
        :model-value="comment.message"
        :editable="false"
        :mentionable-users="[]"
      />
    </div>

    <div v-else class="row-comment-item__edit">
      <RichTextEditor
        v-model="editMessage"
        :editable="true"
        :mentionable-users="mentionableUsers"
        @shift-enter="submitEdit"
      />
      <div class="row-comment-item__edit-actions">
        <button class="button button--tiny button--ghost" @click="cancelEdit">
          {{ $t('action.cancel') }}
        </button>
        <button
          class="button button--tiny button--primary"
          :disabled="saving"
          @click="submitEdit"
        >
          {{ $t('action.save') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import RichTextEditor from '@baserow/modules/core/components/editor/RichTextEditor'

export default {
  name: 'RowCommentItem',
  components: { RichTextEditor },
  props: {
    comment: {
      type: Object,
      required: true,
    },
    currentUserId: {
      type: Number,
      default: null,
    },
    isAdmin: {
      type: Boolean,
      default: false,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
    mentionableUsers: {
      type: Array,
      default: () => [],
    },
  },
  emits: ['update', 'delete'],
  data() {
    return {
      editing: false,
      editMessage: null,
      saving: false,
    }
  },
  computed: {
    initials() {
      const name = this.comment.author.name || '?'
      return name
        .split(' ')
        .slice(0, 2)
        .map((w) => w[0])
        .join('')
        .toUpperCase()
    },
    formattedTime() {
      return new Date(this.comment.created_on).toLocaleString()
    },
    isOwn() {
      return this.comment.author.id === this.currentUserId
    },
    canModify() {
      return this.isOwn || this.isAdmin
    },
  },
  methods: {
    startEdit() {
      this.editMessage = JSON.parse(JSON.stringify(this.comment.message))
      this.editing = true
    },
    cancelEdit() {
      this.editing = false
      this.editMessage = null
    },
    async submitEdit() {
      if (this.saving) return
      this.saving = true
      try {
        this.$emit('update', { commentId: this.comment.id, message: this.editMessage })
        this.editing = false
      } finally {
        this.saving = false
      }
    },
    confirmDelete() {
      if (window.confirm(this.$t('rowComments.deleteConfirm'))) {
        this.$emit('delete', { commentId: this.comment.id })
      }
    },
  },
}
</script>
