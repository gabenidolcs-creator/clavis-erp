from django.contrib.contenttypes.models import ContentType
from django.db.models.deletion import ProtectedError

import pytest

from baserow.contrib.dashboard.data_sources.models import DashboardDataSource
from baserow.contrib.dashboard.data_sources.service import DashboardDataSourceService
from baserow.contrib.dashboard.widgets.handler import WidgetHandler
from baserow.contrib.dashboard.widgets.models import Widget
from baserow.contrib.dashboard.widgets.registries import widget_type_registry
from baserow.contrib.dashboard.widgets.widget_types import (
    ChartWidgetType as CoreChartWidgetType,
)
from baserow.contrib.integrations.local_baserow.service_types import (
    LocalBaserowGroupedAggregateRowsServiceType,
)
from baserow.core.services.registries import service_type_registry


@pytest.mark.django_db
def test_create_chart_widget_creates_grouped_aggregate_data_source(data_fixture):
    user = data_fixture.create_user()
    dashboard = data_fixture.create_dashboard_application(user=user)

    # Use handler + core type directly to bypass any premium license check.
    widget = WidgetHandler().create_widget(
        CoreChartWidgetType(), dashboard, title="My chart", chart_type="bar"
    )

    assert widget.data_source is not None
    expected_model = service_type_registry.get(
        LocalBaserowGroupedAggregateRowsServiceType.type
    ).model_class
    assert widget.data_source.service.content_type == ContentType.objects.get_for_model(
        expected_model
    )


@pytest.mark.django_db
def test_create_pie_widget(data_fixture):
    user = data_fixture.create_user()
    dashboard = data_fixture.create_dashboard_application(user=user)

    widget = WidgetHandler().create_widget(
        CoreChartWidgetType(), dashboard, title="My pie", chart_type="pie"
    )

    assert widget.data_source is not None
    assert widget.chart_type == "pie"


@pytest.mark.django_db
def test_create_doughnut_widget(data_fixture):
    user = data_fixture.create_user()
    dashboard = data_fixture.create_dashboard_application(user=user)

    widget = WidgetHandler().create_widget(
        CoreChartWidgetType(), dashboard, title="My doughnut", chart_type="doughnut"
    )

    assert widget.data_source is not None
    assert widget.chart_type == "doughnut"


@pytest.mark.django_db
def test_chart_widget_before_trashed_and_restore(data_fixture):
    dashboard = data_fixture.create_dashboard_application()
    widget = data_fixture.create_chart_widget(dashboard=dashboard)
    data_source_id = widget.data_source.id

    core_type = CoreChartWidgetType()
    core_type.before_trashed(widget)

    ds = DashboardDataSource.objects_and_trash.get(id=data_source_id)
    assert ds.trashed is True

    core_type.before_restore(widget)

    ds = DashboardDataSource.objects_and_trash.get(id=data_source_id)
    assert ds.trashed is False


@pytest.mark.django_db
def test_chart_widget_datasource_cannot_be_deleted(data_fixture):
    user = data_fixture.create_user()
    dashboard = data_fixture.create_dashboard_application(user=user)
    chart_widget = data_fixture.create_chart_widget(dashboard=dashboard)

    with pytest.raises(ProtectedError):
        DashboardDataSourceService().delete_data_source(
            user, chart_widget.data_source.id
        )


@pytest.mark.django_db
def test_chart_widget_and_summary_widget_coexist(data_fixture):
    user = data_fixture.create_user()
    dashboard = data_fixture.create_dashboard_application(user=user)

    # Create summary via service (no license needed).
    from baserow.contrib.dashboard.widgets.service import WidgetService

    summary_widget = WidgetService().create_widget(
        user, "summary", dashboard.id, title="Summary"
    )
    # Create chart via handler + core type directly.
    chart_widget = WidgetHandler().create_widget(
        CoreChartWidgetType(), dashboard, title="Chart", chart_type="bar"
    )

    widgets = Widget.objects.filter(dashboard=dashboard)
    widget_ids = list(widgets.values_list("id", flat=True))
    assert summary_widget.id in widget_ids
    assert chart_widget.id in widget_ids

    assert widget_type_registry.get("summary") is not None
    assert widget_type_registry.get("chart") is not None
