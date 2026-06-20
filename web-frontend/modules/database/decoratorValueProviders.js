import { Registerable } from '@baserow/modules/core/registry'
import {
  createFiltersTree,
} from '@baserow/modules/database/utils/view'
import ConditionalColorValueProviderForm from '@baserow/modules/database/components/view/ConditionalColorValueProviderForm'
import {
  LeftBorderColorViewDecoratorType,
  BackgroundColorViewDecoratorType,
} from '@baserow/modules/database/viewDecorators'

export class DecoratorValueProviderType extends Registerable {
  /**
   * A human readable name of the decorator provider type.
   */
  getName() {
    return null
  }

  /**
   * Returns a user description for this value provider.
   */
  getDescription() {}

  /**
   * The icon class name that is used as convenience for the user to
   * recognize certain valueProvider types. If you for example want the filter
   * icon, you must return 'filter' here. This will result in the classname
   * 'iconoir-filter'.
   */
  getIconClass() {
    return null
  }

  /**
   * Should return the view decorator type that the value provider is compatible with or
   * functions which take a view decoratorType and return a boolean indicating if the
   * value provider is compatible or not.
   *
   * You can also use a function like in this example:
   * [(decoratorType) => decoratorType.some_prop === 10, LeftBorderColorViewDecoratorType]
   * and then decoratorType which pass the test defined by the function will be
   * deemed as compatible.
   */
  getCompatibleDecoratorTypes() {
    return []
  }

  /**
   * Returns if a given view decoratorType is compatible with this value provider or
   * not.
   * Uses the list provided by `.getCompatibleDecoratorTypes()` to calculate this.
   */
  isCompatible(decorationType) {
    for (const typeOrFunc of this.getCompatibleDecoratorTypes()) {
      if (Object.prototype.hasOwnProperty.call(typeOrFunc, 'getType')) {
        if (decorationType.getType() === typeOrFunc.getType()) {
          return true
        }
      } else if (typeOrFunc instanceof Function) {
        if (typeOrFunc(decorationType)) {
          return true
        }
      }
    }
    return false
  }

  /**
   * Returns the component that allows the user to configure the value provider.
   * This component is responsible for creating the `value_provider_conf` object.
   *
   * If you want to reference fields in this object, you must use the key name
   * `field_id` to allow import/export to replace automatically any field id by the new
   * field id. `field_id`s can be anywhere in this object and this object can be as
   * deep as you need.
   */
  getFormComponent() {
    throw new Error(
      'Not implemented error. This value provider should return a component.'
    )
  }

  /**
   * Returns the default configuration when selecting this value provider from fields
   * and view
   * @returns the configuration object
   */
  getDefaultConfiguration({ fields, view }) {
    return {}
  }

  /**
   * Returns the value of this provider for the given row considering the configuration.
   *
   * @param {array} row the row
   * @param {object} options the configuration of the value provider
   * @param {array} fields the array of the fields of the current view
   *
   */
  getValue({ options, fields, row }) {
    throw new Error(
      'Not implemented error. This value provider should return a value.'
    )
  }

  getOrder() {
    return 50
  }

  /**
   * @return object
   */
  serialize() {
    return {
      type: this.type,
      name: this.getName(),
    }
  }
}

export class ConditionalColorValueProviderType extends DecoratorValueProviderType {
  static getType() {
    return 'conditional_color'
  }

  getName() {
    return this.app.$i18n.t('conditionalColorProvider.name')
  }

  getDescription() {
    return this.app.$i18n.t('conditionalColorProvider.description')
  }

  getIconClass() {
    return 'iconoir-filter'
  }

  getCompatibleDecoratorTypes() {
    return [LeftBorderColorViewDecoratorType, BackgroundColorViewDecoratorType]
  }

  getFormComponent() {
    return ConditionalColorValueProviderForm
  }

  getDefaultConfiguration({ fields }) {
    return { rules: [] }
  }

  /**
   * Evaluates the ordered list of color rules against a row and returns the
   * color of the first matching rule, or null if no rule matches.
   *
   * @param {object} row - The row data object.
   * @param {object} options - The value_provider_conf: { rules: [...] }.
   * @param {Array} fields - The list of field definitions for the view.
   * @returns {string|null} CSS color string, or null.
   */
  getValue({ row, options, fields }) {
    const rules = (options && options.rules) || []
    if (!rules.length) return null

    for (const rule of rules) {
      const filters = rule.filters || []
      const filterGroups = rule.filter_groups || []
      const filterType = rule.filter_type || 'AND'

      if (!filters.length) {
        // Rule with no conditions matches all rows.
        return rule.color || null
      }

      try {
        const tree = createFiltersTree(filterType, filters, filterGroups)
        const matches = tree.matches(this.app.$registry, fields, row)
        if (matches) {
          return rule.color || null
        }
      } catch {
        // Skip malformed rules rather than crashing the view.
      }
    }
    return null
  }
}
