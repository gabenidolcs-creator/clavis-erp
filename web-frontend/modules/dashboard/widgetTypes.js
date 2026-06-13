import { Registerable } from '@baserow/modules/core/registry'
import SummaryWidgetSvg from '@baserow/modules/dashboard/assets/images/widgets/summary_widget.svg?url'
import SummaryWidget from '@baserow/modules/dashboard/components/widget/SummaryWidget'
import SummaryWidgetSettings from '@baserow/modules/dashboard/components/widget/SummaryWidgetSettings'
import BarChartWidgetSvg from '@baserow/modules/dashboard/assets/images/widgets/bar_chart_widget.svg?url'
import PieChartWidgetSvg from '@baserow/modules/dashboard/assets/images/widgets/pie_chart_widget.svg?url'
import LineChartWidgetSvg from '@baserow/modules/dashboard/assets/images/widgets/line_chart_widget.svg?url'
import ScatterChartWidgetSvg from '@baserow/modules/dashboard/assets/images/widgets/scatter_chart_widget.svg?url'
import ChartWidget from '@baserow/modules/dashboard/components/widget/ChartWidget'
import ChartWidgetSettings from '@baserow/modules/dashboard/components/widget/ChartWidgetSettings'

export class WidgetType extends Registerable {
  constructor(...args) {
    super(...args)
    this.type = this.getType()

    if (this.type === null) {
      throw new Error('The type name of a widget type must be set.')
    }

    if (this.name === null) {
      throw new Error('The name of a widget type must be set.')
    }
  }

  get name() {
    return null
  }

  get createWidgetImage() {
    return null
  }

  get component() {
    return null
  }

  get settingsComponent() {
    return null
  }

  /**
   * When the same widget can be created with different
   * options resulting in different name, image, and
   * settings.
   */
  get variations() {
    return [
      {
        name: this.name,
        createWidgetImage: this.createWidgetImage,
        type: this,
        params: {},
        dropdownIcon: '',
      },
    ]
  }

  getOrder() {
    return 0
  }

  isLoading(widget, data) {
    return false
  }

  isAvailable() {
    return true
  }

  getDeactivatedModal() {
    return null
  }
}

export class SummaryWidgetType extends WidgetType {
  static getType() {
    return 'summary'
  }

  get name() {
    const { $i18n: i18n } = this.app
    return i18n.t('summaryWidget.name')
  }

  get createWidgetImage() {
    return SummaryWidgetSvg
  }

  get component() {
    return SummaryWidget
  }

  get settingsComponent() {
    return SummaryWidgetSettings
  }

  isLoading(widget, data) {
    const dataSourceId = widget.data_source_id
    if (data[dataSourceId] && Object.keys(data[dataSourceId]).length !== 0) {
      return false
    }
    return true
  }
}

export class ChartWidgetType extends WidgetType {
  static getType() {
    return 'chart'
  }

  get name() {
    return this.app.$i18n.t('chartWidget.name')
  }

  get component() {
    return ChartWidget
  }

  get settingsComponent() {
    return ChartWidgetSettings
  }

  get variations() {
    const { $i18n: i18n } = this.app
    return [
      {
        name: i18n.t('barChartWidget.name'),
        createWidgetImage: BarChartWidgetSvg,
        type: this,
        params: { chart_type: 'bar' },
        dropdownIcon: '',
      },
      {
        name: i18n.t('pieChartWidget.name'),
        createWidgetImage: PieChartWidgetSvg,
        type: this,
        params: { chart_type: 'pie' },
        dropdownIcon: '',
      },
      {
        name: i18n.t('doughnutChartWidget.name'),
        createWidgetImage: PieChartWidgetSvg,
        type: this,
        params: { chart_type: 'doughnut' },
        dropdownIcon: '',
      },
      {
        name: i18n.t('lineChartWidget.name'),
        createWidgetImage: LineChartWidgetSvg,
        type: this,
        params: { chart_type: 'line' },
        dropdownIcon: '',
      },
      {
        name: i18n.t('scatterChartWidget.name'),
        createWidgetImage: ScatterChartWidgetSvg,
        type: this,
        params: { chart_type: 'scatter' },
        dropdownIcon: '',
      },
    ]
  }

  isLoading(widget, data) {
    const dataSourceId = widget.data_source_id
    if (data[dataSourceId] && Object.keys(data[dataSourceId]).length !== 0) {
      return false
    }
    return true
  }
}
