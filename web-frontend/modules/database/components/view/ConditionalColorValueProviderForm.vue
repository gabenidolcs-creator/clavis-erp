<template>
  <div class="conditional-color-form">
    <div
      v-if="rules.length === 0"
      class="conditional-color-form__empty"
    >
      {{ $t('conditionalColorForm.noRules') }}
    </div>

    <div
      v-for="(rule, ruleIndex) in rules"
      :key="rule.id"
      class="conditional-color-form__rule"
    >
      <div class="conditional-color-form__rule-header">
        <div class="conditional-color-form__rule-label">
          {{ $t('conditionalColorForm.ruleLabel', { index: ruleIndex + 1 }) }}
        </div>
        <div class="conditional-color-form__color-picker-wrapper">
          <input
            type="color"
            class="conditional-color-form__color-input"
            :value="rule.color || '#4A90E2'"
            @input="updateRuleColor(ruleIndex, $event.target.value)"
          />
        </div>
        <ButtonIcon
          icon="iconoir-bin"
          class="conditional-color-form__delete-rule"
          @click="deleteRule(ruleIndex)"
        />
      </div>

      <div class="conditional-color-form__filters">
        <div
          v-for="(filter, filterIndex) in rule.filters"
          :key="filter.id || filterIndex"
          class="conditional-color-form__filter-row"
        >
          <ViewFieldConditionItem
            :filter="filter"
            :view="view"
            :is-public-view="false"
            :fields="fields"
            :disable-filter="readOnly"
            :read-only="readOnly"
            @update-filter="updateFilter(ruleIndex, filterIndex, $event)"
            @delete-filter="deleteFilter(ruleIndex, filterIndex)"
          />
        </div>
        <div class="conditional-color-form__filter-actions">
          <ButtonText
            v-if="!readOnly"
            icon="iconoir-plus"
            @click.prevent="addFilter(ruleIndex)"
          >
            {{ $t('conditionalColorForm.addCondition') }}
          </ButtonText>
        </div>
      </div>
    </div>

    <div v-if="!readOnly" class="conditional-color-form__footer">
      <ButtonText icon="iconoir-plus" @click.prevent="addRule">
        {{ $t('conditionalColorForm.addRule') }}
      </ButtonText>
    </div>
  </div>
</template>

<script>
import { ulid } from 'ulid'
import ViewFieldConditionItem from '@baserow/modules/database/components/view/ViewFieldConditionItem'

export default {
  name: 'ConditionalColorValueProviderForm',
  components: { ViewFieldConditionItem },
  props: {
    view: {
      type: Object,
      required: false,
      default: () => ({}),
    },
    table: {
      type: Object,
      required: false,
      default: () => ({}),
    },
    database: {
      type: Object,
      required: false,
      default: () => ({}),
    },
    fields: {
      type: Array,
      required: true,
    },
    readOnly: {
      type: Boolean,
      required: false,
      default: false,
    },
    options: {
      type: Object,
      required: false,
      default: () => ({ rules: [] }),
    },
  },
  emits: ['update'],
  computed: {
    rules() {
      return (this.options && this.options.rules) || []
    },
  },
  methods: {
    emit(rules) {
      this.$emit('update', { ...this.options, rules })
    },
    addRule() {
      const firstField = this.fields[0]
      const newRule = {
        id: ulid(),
        color: '#4A90E2',
        filters: firstField
          ? [
              {
                id: ulid(),
                field: firstField.id,
                type: 'equal',
                value: '',
                group: null,
              },
            ]
          : [],
        filter_groups: [],
        filter_type: 'AND',
      }
      this.emit([...this.rules, newRule])
    },
    deleteRule(index) {
      const rules = this.rules.filter((_, i) => i !== index)
      this.emit(rules)
    },
    updateRuleColor(index, color) {
      const rules = this.rules.map((rule, i) =>
        i === index ? { ...rule, color } : rule
      )
      this.emit(rules)
    },
    addFilter(ruleIndex) {
      const firstField = this.fields[0]
      if (!firstField) return
      const newFilter = {
        id: ulid(),
        field: firstField.id,
        type: 'equal',
        value: '',
        group: null,
      }
      const rules = this.rules.map((rule, i) =>
        i === ruleIndex
          ? { ...rule, filters: [...(rule.filters || []), newFilter] }
          : rule
      )
      this.emit(rules)
    },
    updateFilter(ruleIndex, filterIndex, values) {
      const rules = this.rules.map((rule, i) => {
        if (i !== ruleIndex) return rule
        const filters = (rule.filters || []).map((f, fi) =>
          fi === filterIndex ? { ...f, ...values } : f
        )
        return { ...rule, filters }
      })
      this.emit(rules)
    },
    deleteFilter(ruleIndex, filterIndex) {
      const rules = this.rules.map((rule, i) => {
        if (i !== ruleIndex) return rule
        const filters = (rule.filters || []).filter((_, fi) => fi !== filterIndex)
        return { ...rule, filters }
      })
      this.emit(rules)
    },
  },
}
</script>

<style scoped>
.conditional-color-form {
  padding: 8px 0;
}

.conditional-color-form__empty {
  padding: 12px 16px;
  color: var(--color-neutral-600, #6b7280);
  font-size: 13px;
}

.conditional-color-form__rule {
  border: 1px solid var(--color-neutral-200, #e5e7eb);
  border-radius: 4px;
  margin: 8px 16px;
  padding: 8px;
}

.conditional-color-form__rule-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.conditional-color-form__rule-label {
  flex: 1;
  font-weight: 500;
  font-size: 13px;
}

.conditional-color-form__color-input {
  width: 32px;
  height: 28px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  padding: 0;
}

.conditional-color-form__filter-actions {
  margin-top: 4px;
}

.conditional-color-form__footer {
  padding: 4px 16px;
}
</style>
