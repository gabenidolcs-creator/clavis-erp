"""Tests for LocalBaserowGroupedAggregateRowsServiceType (Story 4.2)."""

import pytest
from rest_framework.exceptions import ValidationError as DRFValidationError

from baserow.contrib.database.fields.models import FieldPermission
from baserow.contrib.database.rows.handler import RowHandler
from baserow.contrib.integrations.local_baserow.service_types import (
    LocalBaserowGroupedAggregateRowsServiceType,
)
from baserow.core.rbac.handler import RbacHandler
from baserow.core.services.exceptions import (
    ServiceImproperlyConfiguredDispatchException,
)
from baserow.test_utils.pytest_conftest import FakeDispatchContext


def _make_service(data_fixture, table, user, **kwargs):
    """Helper: create a grouped aggregate service with integration."""
    workspace = table.database.workspace
    dashboard = data_fixture.create_dashboard_application(workspace=workspace)
    integration = data_fixture.create_local_baserow_integration(
        authorized_user=user, application=dashboard
    )
    service = data_fixture.create_local_baserow_grouped_aggregate_rows_service(
        integration=integration, table=table, **kwargs
    )
    return service


@pytest.mark.django_db
def test_dispatch_count_aggregation(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    text_field = data_fixture.create_text_field(table=table)
    RowHandler().create_rows(
        user,
        table,
        [
            {f"field_{text_field.id}": "A"},
            {f"field_{text_field.id}": "A"},
            {f"field_{text_field.id}": "B"},
        ],
    )
    service = _make_service(
        data_fixture, table, user,
        group_by_field=text_field,
        aggregation_type="count",
    )

    dispatch_context = FakeDispatchContext()
    service_type = LocalBaserowGroupedAggregateRowsServiceType()
    result = service_type.dispatch_data(service, {}, dispatch_context)

    assert "results" in result
    results_map = {r["category"]: r["value"] for r in result["results"]}
    assert results_map["A"] == 2
    assert results_map["B"] == 1
    # No "series" key when series_field is None
    assert all("series" not in r for r in result["results"])


@pytest.mark.django_db
def test_dispatch_sum_aggregation(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    text_field = data_fixture.create_text_field(table=table)
    number_field = data_fixture.create_number_field(table=table)
    RowHandler().create_rows(
        user,
        table,
        [
            {f"field_{text_field.id}": "A", f"field_{number_field.id}": 10},
            {f"field_{text_field.id}": "A", f"field_{number_field.id}": 20},
            {f"field_{text_field.id}": "B", f"field_{number_field.id}": 5},
        ],
    )
    service = _make_service(
        data_fixture, table, user,
        group_by_field=text_field,
        value_field=number_field,
        aggregation_type="sum",
    )

    dispatch_context = FakeDispatchContext()
    service_type = LocalBaserowGroupedAggregateRowsServiceType()
    result = service_type.dispatch_data(service, {}, dispatch_context)

    results_map = {r["category"]: r["value"] for r in result["results"]}
    assert results_map["A"] == 30
    assert results_map["B"] == 5


@pytest.mark.django_db
def test_dispatch_avg_min_max(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    text_field = data_fixture.create_text_field(table=table)
    number_field = data_fixture.create_number_field(table=table)
    RowHandler().create_rows(
        user,
        table,
        [
            {f"field_{text_field.id}": "X", f"field_{number_field.id}": 10},
            {f"field_{text_field.id}": "X", f"field_{number_field.id}": 20},
        ],
    )
    dispatch_context = FakeDispatchContext()
    service_type = LocalBaserowGroupedAggregateRowsServiceType()

    for agg_type in ("avg", "min", "max"):
        service = _make_service(
            data_fixture, table, user,
            group_by_field=text_field,
            value_field=number_field,
            aggregation_type=agg_type,
        )
        result = service_type.dispatch_data(service, {}, dispatch_context)
        assert result["results"][0]["category"] == "X"
        assert "value" in result["results"][0]


@pytest.mark.django_db
def test_dispatch_with_series_field(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    cat_field = data_fixture.create_text_field(table=table)
    series_field = data_fixture.create_text_field(table=table)
    RowHandler().create_rows(
        user,
        table,
        [
            {f"field_{cat_field.id}": "A", f"field_{series_field.id}": "S1"},
            {f"field_{cat_field.id}": "A", f"field_{series_field.id}": "S2"},
            {f"field_{cat_field.id}": "B", f"field_{series_field.id}": "S1"},
        ],
    )
    service = _make_service(
        data_fixture, table, user,
        group_by_field=cat_field,
        series_field=series_field,
        aggregation_type="count",
    )

    dispatch_context = FakeDispatchContext()
    service_type = LocalBaserowGroupedAggregateRowsServiceType()
    result = service_type.dispatch_data(service, {}, dispatch_context)

    assert all("series" in r for r in result["results"])
    assert all("category" in r for r in result["results"])
    assert all("value" in r for r in result["results"])
    assert len(result["results"]) == 3


@pytest.mark.django_db
def test_dispatch_honors_field_hide_on_group_by_field(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    text_field = data_fixture.create_text_field(table=table)
    # Assign user EDITOR role (below ADMIN threshold) so the field is hidden
    RbacHandler().assign_role(user, workspace, "EDITOR")
    FieldPermission.objects.create(field=text_field, readable_by_role="ADMIN")

    service = _make_service(
        data_fixture, table, user,
        group_by_field=text_field,
        aggregation_type="count",
    )

    # authorized_user is a workspace MEMBER (default role)
    dispatch_context = FakeDispatchContext()
    service_type = LocalBaserowGroupedAggregateRowsServiceType()

    with pytest.raises(ServiceImproperlyConfiguredDispatchException) as exc_info:
        service_type.resolve_service_formulas(service, dispatch_context)
    assert "group_by_field" in exc_info.value.args[0]


@pytest.mark.django_db
def test_dispatch_honors_field_hide_on_value_field(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    cat_field = data_fixture.create_text_field(table=table)
    value_field = data_fixture.create_number_field(table=table)
    # Assign user EDITOR role (below ADMIN threshold) so the field is hidden
    RbacHandler().assign_role(user, workspace, "EDITOR")
    FieldPermission.objects.create(field=value_field, readable_by_role="ADMIN")

    service = _make_service(
        data_fixture, table, user,
        group_by_field=cat_field,
        value_field=value_field,
        aggregation_type="sum",
    )

    dispatch_context = FakeDispatchContext()
    service_type = LocalBaserowGroupedAggregateRowsServiceType()

    with pytest.raises(ServiceImproperlyConfiguredDispatchException) as exc_info:
        service_type.resolve_service_formulas(service, dispatch_context)
    assert "value_field" in exc_info.value.args[0]


@pytest.mark.django_db
def test_dispatch_count_does_not_require_value_field(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    text_field = data_fixture.create_text_field(table=table)
    RowHandler().create_rows(
        user,
        table,
        [{f"field_{text_field.id}": "A"}],
    )
    service = _make_service(
        data_fixture, table, user,
        group_by_field=text_field,
        aggregation_type="count",
        value_field=None,
    )

    dispatch_context = FakeDispatchContext()
    service_type = LocalBaserowGroupedAggregateRowsServiceType()
    # Should not raise
    resolved = service_type.resolve_service_formulas(service, dispatch_context)
    assert resolved is not None


@pytest.mark.django_db
def test_resolve_formulas_raises_when_group_by_missing(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    service = _make_service(
        data_fixture, table, user,
        group_by_field=None,
        aggregation_type="count",
    )

    dispatch_context = FakeDispatchContext()
    service_type = LocalBaserowGroupedAggregateRowsServiceType()

    with pytest.raises(ServiceImproperlyConfiguredDispatchException) as exc_info:
        service_type.resolve_service_formulas(service, dispatch_context)
    assert "group_by_field" in exc_info.value.args[0]


@pytest.mark.django_db
def test_resolve_formulas_raises_when_value_field_missing_for_sum(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    text_field = data_fixture.create_text_field(table=table)
    service = _make_service(
        data_fixture, table, user,
        group_by_field=text_field,
        value_field=None,
        aggregation_type="sum",
    )

    dispatch_context = FakeDispatchContext()
    service_type = LocalBaserowGroupedAggregateRowsServiceType()

    with pytest.raises(ServiceImproperlyConfiguredDispatchException) as exc_info:
        service_type.resolve_service_formulas(service, dispatch_context)
    assert "value_field" in exc_info.value.args[0]


@pytest.mark.django_db
def test_generate_schema_without_series(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    text_field = data_fixture.create_text_field(table=table)
    service = _make_service(
        data_fixture, table, user,
        group_by_field=text_field,
        aggregation_type="count",
    )

    service_type = LocalBaserowGroupedAggregateRowsServiceType()
    schema = service_type.generate_schema(service)

    assert schema is not None
    assert schema["type"] == "array"
    props = schema["items"]["properties"]
    assert "category" in props
    assert "value" in props
    assert "series" not in props


@pytest.mark.django_db
def test_dispatch_honors_field_hide_on_series_field(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    cat_field = data_fixture.create_text_field(table=table)
    series_field = data_fixture.create_text_field(table=table)
    RbacHandler().assign_role(user, workspace, "EDITOR")
    FieldPermission.objects.create(field=series_field, readable_by_role="ADMIN")

    service = _make_service(
        data_fixture, table, user,
        group_by_field=cat_field,
        series_field=series_field,
        aggregation_type="count",
    )

    dispatch_context = FakeDispatchContext()
    service_type = LocalBaserowGroupedAggregateRowsServiceType()

    with pytest.raises(ServiceImproperlyConfiguredDispatchException) as exc_info:
        service_type.resolve_service_formulas(service, dispatch_context)
    assert "series_field" in exc_info.value.args[0]


@pytest.mark.django_db
def test_dispatch_null_category_becomes_empty_string(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    text_field = data_fixture.create_text_field(table=table)
    RowHandler().create_rows(
        user,
        table,
        [
            {f"field_{text_field.id}": None},
            {f"field_{text_field.id}": "A"},
        ],
    )
    service = _make_service(
        data_fixture, table, user,
        group_by_field=text_field,
        aggregation_type="count",
    )

    dispatch_context = FakeDispatchContext()
    service_type = LocalBaserowGroupedAggregateRowsServiceType()
    result = service_type.dispatch_data(service, {}, dispatch_context)

    categories = {r["category"] for r in result["results"]}
    assert "" in categories, "NULL category must become empty string"
    assert "A" in categories
    assert all(isinstance(r["category"], str) for r in result["results"])


@pytest.mark.django_db
def test_prepare_values_raises_when_non_count_has_no_value_field(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    text_field = data_fixture.create_text_field(table=table)

    service_type = LocalBaserowGroupedAggregateRowsServiceType()
    with pytest.raises(DRFValidationError) as exc_info:
        service_type.prepare_values(
            {
                "table": table,
                "group_by_field_id": text_field.id,
                "aggregation_type": "sum",
                "value_field_id": None,
            },
            user,
        )
    assert "value_field" in str(exc_info.value.detail)


@pytest.mark.django_db
def test_generate_schema_with_series(data_fixture):
    user = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=user)
    database = data_fixture.create_database_application(workspace=workspace)
    table = data_fixture.create_database_table(database=database)
    text_field = data_fixture.create_text_field(table=table)
    series_field = data_fixture.create_text_field(table=table)
    service = _make_service(
        data_fixture, table, user,
        group_by_field=text_field,
        series_field=series_field,
        aggregation_type="count",
    )

    service_type = LocalBaserowGroupedAggregateRowsServiceType()
    schema = service_type.generate_schema(service)

    assert schema is not None
    props = schema["items"]["properties"]
    assert "category" in props
    assert "value" in props
    assert "series" in props
