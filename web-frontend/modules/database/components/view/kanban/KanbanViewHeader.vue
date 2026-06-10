<template>
  <ul v-if="!tableLoading" class="header__filter header__filter--full-width">
    <li class="header__filter-item">
      <a
        ref="groupByContextLink"
        class="header__filter-link"
        @click="
          $refs.groupByContext.toggle(
            $refs.groupByContextLink,
            'bottom',
            'left',
            4
          )
        "
      >
        <i class="header__filter-icon iconoir-axes"></i>
        <span class="header__filter-name">{{
          groupingFieldName || $t('kanbanViewHeader.stackBy')
        }}</span>
      </a>
      <Context ref="groupByContext" class="kanban-view-header__group-context">
        <div class="kanban-view-header__group-context-inner">
          <ChooseSingleSelectField
            :database="database"
            :table="table"
            :view="view"
            :fields="fields"
            :read-only="readOnly"
            :loading="updatingGroupingField"
            :value="view.single_select_field"
            @input="updateSingleSelectField($event)"
          ></ChooseSingleSelectField>
        </div>
      </Context>
    </li>
    <li class="header__filter-item">
      <a
        ref="customizeContextLink"
        class="header__filter-link"
        @click="
          $refs.customizeContext.toggle(
            $refs.customizeContextLink,
            'bottom',
            'left',
            4
          )
        "
      >
        <i class="header__filter-icon iconoir-settings"></i>
        <span class="header__filter-name">{{
          $t('kanbanViewHeader.customizeCards')
        }}</span>
      </a>
      <ViewFieldsContext
        ref="customizeContext"
        :database="database"
        :view="view"
        :fields="fields"
        :field-options="fieldOptions"
        :cover-image-field="view.card_cover_image_field"
        :allow-cover-image-field="true"
        @update-all-field-options="updateAllFieldOptions"
        @update-field-options-of-field="updateFieldOptionsOfField"
        @update-order="orderFieldOptions"
        @update-cover-image-field="updateCoverImageField"
      ></ViewFieldsContext>
    </li>
    <li class="header__filter-item header__filter-item--full-width">
      <ViewSearch
        :view="view"
        :fields="fields"
        :store-prefix="storePrefix"
        :always-hide-rows-not-matching-search="true"
        @refresh="$emit('refresh', $event)"
      ></ViewSearch>
    </li>
  </ul>
</template>

<script>
import { mapGetters, mapState } from 'vuex'

import { notifyIf } from '@baserow/modules/core/utils/error'
import ViewFieldsContext from '@baserow/modules/database/components/view/ViewFieldsContext'
import ViewSearch from '@baserow/modules/database/components/view/ViewSearch'
import ChooseSingleSelectField from '@baserow/modules/database/components/field/ChooseSingleSelectField'

export default {
  name: 'KanbanViewHeader',
  components: { ViewFieldsContext, ViewSearch, ChooseSingleSelectField },
  props: {
    database: {
      type: Object,
      required: true,
    },
    table: {
      type: Object,
      required: true,
    },
    view: {
      type: Object,
      required: true,
    },
    fields: {
      type: Array,
      required: true,
    },
    readOnly: {
      type: Boolean,
      required: true,
    },
    storePrefix: {
      type: String,
      required: true,
    },
  },
  emits: ['refresh'],
  data() {
    return {
      updatingGroupingField: false,
    }
  },
  computed: {
    ...mapState({
      tableLoading: (state) => state.table.loading,
    }),
    ...mapGetters({}),
    fieldOptions() {
      return this.$store.getters[
        this.storePrefix + 'view/kanban/getAllFieldOptions'
      ]
    },
    groupingFieldName() {
      const fieldId = this.view.single_select_field
      if (!fieldId) {
        return null
      }
      const field = this.fields.find((f) => f.id === fieldId)
      return field ? field.name : null
    },
  },
  methods: {
    async updateSingleSelectField(fieldId) {
      this.updatingGroupingField = true
      try {
        await this.$store.dispatch('view/update', {
          view: this.view,
          values: { single_select_field: fieldId },
          readOnly: this.readOnly,
        })
        this.$refs.groupByContext.hide()
      } catch (error) {
        notifyIf(error, 'view')
      } finally {
        this.updatingGroupingField = false
      }
    },
    async updateAllFieldOptions({ newFieldOptions, oldFieldOptions }) {
      try {
        await this.$store.dispatch(
          this.storePrefix + 'view/kanban/updateAllFieldOptions',
          {
            newFieldOptions,
            oldFieldOptions,
            readOnly:
              this.readOnly ||
              !this.$hasPermission(
                'database.table.view.update_field_options',
                this.view,
                this.database.workspace.id
              ),
          }
        )
      } catch (error) {
        notifyIf(error, 'view')
      }
    },
    async updateFieldOptionsOfField({ field, values, oldValues }) {
      try {
        await this.$store.dispatch(
          this.storePrefix + 'view/kanban/updateFieldOptionsOfField',
          {
            field,
            values,
            oldValues,
            readOnly:
              this.readOnly ||
              !this.$hasPermission(
                'database.table.view.update_field_options',
                this.view,
                this.database.workspace.id
              ),
          }
        )
      } catch (error) {
        notifyIf(error, 'view')
      }
    },
    async orderFieldOptions({ order }) {
      try {
        await this.$store.dispatch(
          this.storePrefix + 'view/kanban/updateFieldOptionsOrder',
          {
            order,
            readOnly:
              this.readOnly ||
              !this.$hasPermission(
                'database.table.view.update_field_options',
                this.view,
                this.database.workspace.id
              ),
          }
        )
      } catch (error) {
        notifyIf(error, 'view')
      }
    },
    async updateCoverImageField(value) {
      try {
        await this.$store.dispatch('view/update', {
          view: this.view,
          values: { card_cover_image_field: value },
          readOnly: this.readOnly,
        })
      } catch (error) {
        notifyIf(error, 'view')
      }
    },
  },
}
</script>
