<template>
  <div class="row-comments-panel">
    <div v-if="loading" class="row-comments-panel__loading">
      <div class="loading"></div>
    </div>

    <div v-else-if="comments.length === 0" class="row-comments-panel__empty">
      {{ $t('rowComments.noComments') }}
    </div>

    <div v-else ref="commentList" class="row-comments-panel__list">
      <RowCommentItem
        v-for="comment in comments"
        :key="comment.id"
        :comment="comment"
        :current-user-id="currentUserId"
        :is-admin="isAdmin"
        :read-only="readOnly"
        :mentionable-users="mentionableUsers"
        @update="onUpdateComment"
        @delete="onDeleteComment"
      />
    </div>

    <div v-if="!readOnly" class="row-comments-panel__compose">
      <RichTextEditor
        v-model="newMessage"
        :placeholder="$t('rowComments.placeholder')"
        :editable="true"
        :mentionable-users="mentionableUsers"
        :shift-enter-stop-edit="true"
        @shift-enter="submitComment"
      />
      <div class="row-comments-panel__compose-footer">
        <button
          class="button button--tiny button--primary"
          :disabled="submitting || !hasContent"
          @click="submitComment"
        >
          {{ $t('rowComments.post') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { mapGetters } from 'vuex'
import RichTextEditor from '@baserow/modules/core/components/editor/RichTextEditor'
import RowCommentItem from './RowCommentItem'

const EMPTY_DOC = { type: 'doc', content: [{ type: 'paragraph' }] }

export default {
  name: 'RowCommentsPanel',
  components: { RichTextEditor, RowCommentItem },
  props: {
    table: {
      type: Object,
      required: true,
    },
    row: {
      type: Object,
      required: true,
    },
    readOnly: {
      type: Boolean,
      default: false,
    },
    mentionableUsers: {
      type: Array,
      default: () => [],
    },
    isAdmin: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      newMessage: { ...EMPTY_DOC },
      submitting: false,
    }
  },
  computed: {
    ...mapGetters({
      getComments: 'rowComments/getComments',
      isLoading: 'rowComments/isLoading',
    }),
    comments() {
      return this.getComments(this.table.id, this.row.id)
    },
    loading() {
      return this.isLoading(this.table.id, this.row.id)
    },
    currentUserId() {
      return this.$store.getters['auth/getUserId']
    },
    hasContent() {
      const content = this.newMessage?.content || []
      return content.some(
        (node) =>
          node.content?.length > 0 || node.type === 'mention'
      )
    },
  },
  mounted() {
    this.loadComments()
  },
  methods: {
    async loadComments() {
      await this.$store.dispatch('rowComments/fetchComments', {
        tableId: this.table.id,
        rowId: this.row.id,
      })
      this.$nextTick(() => this.scrollToBottom())
    },
    scrollToBottom() {
      const list = this.$refs.commentList
      if (list) list.scrollTop = list.scrollHeight
    },
    async submitComment() {
      if (this.submitting || !this.hasContent) return
      this.submitting = true
      try {
        await this.$store.dispatch('rowComments/createComment', {
          tableId: this.table.id,
          rowId: this.row.id,
          message: this.newMessage,
        })
        this.newMessage = { ...EMPTY_DOC }
        this.$nextTick(() => this.scrollToBottom())
      } catch (e) {
        this.$store.dispatch('toast/error', {
          title: this.$t('rowComments.errorTitle'),
          message: e.message,
        })
      } finally {
        this.submitting = false
      }
    },
    async onUpdateComment({ commentId, message }) {
      await this.$store.dispatch('rowComments/updateComment', {
        tableId: this.table.id,
        rowId: this.row.id,
        commentId,
        message,
      })
    },
    async onDeleteComment({ commentId }) {
      await this.$store.dispatch('rowComments/deleteComment', {
        tableId: this.table.id,
        rowId: this.row.id,
        commentId,
      })
    },
  },
}
</script>
