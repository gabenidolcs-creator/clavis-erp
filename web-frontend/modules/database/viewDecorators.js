import { Registerable } from '@baserow/modules/core/registry'
import LeftBorderColorViewDecorator from '@baserow/modules/database/components/view/LeftBorderColorViewDecorator'
import BackgroundColorViewDecorator from '@baserow/modules/database/components/view/BackgroundColorViewDecorator'

export class ViewDecoratorType extends Registerable {
  /**
   * A human readable name of the decorator type.
   */
  getName() {
    return null
  }

  /**
   * A description of the decorator type.
   */
  getDescription() {
    return null
  }

  /**
   * @returns the image URL to illustrate this decorator.
   */
  getImage() {
    return null
  }

  /**
   * If the decorator type is disabled, this text will be visible explaining why.
   */
  getDeactivatedText({ view }) {}

  /**
   * When the deactivated view decorator is clicked, this modal will be shown.
   */
  getDeactivatedClickModal() {
    return null
  }

  /**
   * Indicates if the decorator type is disabled.
   */
  isDeactivated(workspaceId) {
    return false
  }

  /**
   * Returns whether or not the user can add a new instance of this decorator.
   * A decorator might be disabled if, for example, there is already one occurrence
   * of the same type for the view.
   * The result must be an array. The first item is a boolean value, `true` if
   * the decorator is enabled. If not, it should be `false` and the second item
   * must be a user string describing the reason why it's not available.
   */
  canAdd({ view }) {
    return [false, '']
  }

  /**
   * Returns whether or not a given viewType is compatible with this view decorator.
   */
  isCompatible(view) {
    return false
  }

  /**
   * Should return the component that will actually decorate the record.
   */
  getComponent() {
    throw new Error(
      'Not implemented error. This view decorator should return a component.'
    )
  }

  /**
   * Returns the place where the decorator should appears. Allowed values are:
   * - `wrapper` if the decorator is a wrapper of the record.
   * - `first_cell` to decorate the first cell.
   */
  getPlace() {
    return null
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

const ALL_FIVE_VIEW_TYPES = ['grid', 'gallery', 'kanban', 'calendar', 'timeline']

export class LeftBorderColorViewDecoratorType extends ViewDecoratorType {
  static getType() {
    return 'left_border_color'
  }

  getName() {
    return this.app.$i18n.t('leftBorderColorDecorator.name')
  }

  getDescription() {
    return this.app.$i18n.t('leftBorderColorDecorator.description')
  }

  getIconClass() {
    return 'iconoir-eject'
  }

  isCompatible(view) {
    return ALL_FIVE_VIEW_TYPES.includes(view.type)
  }

  canAdd({ view }) {
    const existing = view.decorations.filter((d) => d.type === this.getType())
    if (existing.length > 0) {
      return [false, 'Only one left border color decorator per view is allowed.']
    }
    return [true, '']
  }

  getComponent() {
    return LeftBorderColorViewDecorator
  }

  getPlace() {
    return 'first_cell'
  }

  getOrder() {
    return 10
  }
}

export class BackgroundColorViewDecoratorType extends ViewDecoratorType {
  static getType() {
    return 'background_color'
  }

  getName() {
    return this.app.$i18n.t('backgroundColorDecorator.name')
  }

  getDescription() {
    return this.app.$i18n.t('backgroundColorDecorator.description')
  }

  getIconClass() {
    return 'iconoir-fill-color'
  }

  isCompatible(view) {
    return ALL_FIVE_VIEW_TYPES.includes(view.type)
  }

  canAdd({ view }) {
    const existing = view.decorations.filter((d) => d.type === this.getType())
    if (existing.length > 0) {
      return [false, 'Only one background color decorator per view is allowed.']
    }
    return [true, '']
  }

  getComponent() {
    return BackgroundColorViewDecorator
  }

  getPlace() {
    return 'wrapper'
  }

  getOrder() {
    return 20
  }
}
