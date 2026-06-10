"""Tests for Story 2.5: Running Count Field (RunningCountFieldType)."""

import pytest

from baserow.contrib.database.fields.field_types import (
    CountFieldType,
    RunningCountFieldType,
)
from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.fields.models import RunningCountField
from baserow.contrib.database.fields.registries import field_type_registry
from baserow.contrib.database.rows.handler import RowHandler


@pytest.mark.django_db
def test_running_count_field_registered():
    """AC #1, #4: running_count resolves to RunningCountFieldType and the relational
    count type is unaffected."""

    field_type = field_type_registry.get("running_count")
    assert field_type.type == "running_count"
    assert field_type.model_class is RunningCountField
    assert isinstance(field_type, RunningCountFieldType)

    # AC #4: existing relational "count" type must still resolve to CountFieldType.
    assert isinstance(field_type_registry.get("count"), CountFieldType)


@pytest.mark.django_db
def test_running_count_field_creates(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)

    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="running_count",
        name="Total",
    )
    assert isinstance(field.specific, RunningCountField)
    # V1: whole-table scope, no filter persisted.
    assert field.specific.filter_conditions is None


@pytest.mark.django_db
def test_running_count_shows_total_row_count(data_fixture):
    """AC #1: every row shows the total non-trashed row count."""

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    data_fixture.create_text_field(table=table, primary=True, name="Name")

    # Seed 3 rows before the field exists.
    model = table.get_model()
    model.objects.create()
    model.objects.create()
    model.objects.create()

    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="running_count",
        name="Total",
    )

    model = table.get_model()
    values = list(
        model.objects.filter(trashed=False).values_list(f"field_{field.id}", flat=True)
    )
    assert values == [3, 3, 3]


@pytest.mark.django_db
def test_running_count_updates_on_row_create(data_fixture):
    """AC #2: creating a row updates the count on all rows."""

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    data_fixture.create_text_field(table=table, primary=True, name="Name")

    model = table.get_model()
    model.objects.create()
    model.objects.create()

    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="running_count",
        name="Total",
    )

    model = table.get_model()
    assert list(
        model.objects.filter(trashed=False).values_list(f"field_{field.id}", flat=True)
    ) == [2, 2]

    # Create a new row through the batch handler (fires the rows_created signal).
    RowHandler().create_rows(user=user, table=table, rows_values=[{}])

    model = table.get_model()
    values = list(
        model.objects.filter(trashed=False).values_list(f"field_{field.id}", flat=True)
    )
    assert values == [3, 3, 3]


@pytest.mark.django_db
def test_running_count_updates_on_single_row_create(data_fixture):
    """AC #2: the single-row create path (RowHandler.create_row, used by the
    create_row API and the grid 'add row' button) must also recompute the count.

    Regression guard: the FieldType.after_rows_created hook only fires on the batch
    create_rows path, so single-row creates relied on the rows_created signal."""

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    data_fixture.create_text_field(table=table, primary=True, name="Name")

    model = table.get_model()
    model.objects.create()
    model.objects.create()

    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="running_count",
        name="Total",
    )

    model = table.get_model()
    assert list(
        model.objects.filter(trashed=False).values_list(f"field_{field.id}", flat=True)
    ) == [2, 2]

    # Single-row create path — NOT create_rows.
    RowHandler().create_row(user=user, table=table, values={})

    model = table.get_model()
    values = list(
        model.objects.filter(trashed=False).values_list(f"field_{field.id}", flat=True)
    )
    assert values == [3, 3, 3]


@pytest.mark.django_db
def test_running_count_updates_on_row_delete(data_fixture):
    """AC #3: deleting a row decrements the count on all remaining rows."""

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    data_fixture.create_text_field(table=table, primary=True, name="Name")

    model = table.get_model()
    row_1 = model.objects.create()
    model.objects.create()
    model.objects.create()

    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="running_count",
        name="Total",
    )

    model = table.get_model()
    assert list(
        model.objects.filter(trashed=False).values_list(f"field_{field.id}", flat=True)
    ) == [3, 3, 3]

    # Delete one row through the handler so the rows_deleted signal fires.
    RowHandler().delete_row(user=user, table=table, row=row_1)

    model = table.get_model()
    values = list(
        model.objects.filter(trashed=False).values_list(f"field_{field.id}", flat=True)
    )
    assert values == [2, 2]


@pytest.mark.django_db
def test_running_count_api_round_trip(api_client, data_fixture):
    """AC #1: create via API, confirm type and value appear in row data."""

    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    data_fixture.create_text_field(table=table, primary=True, name="Name")

    # Seed a couple of rows so the count is non-zero.
    model = table.get_model()
    model.objects.create()
    model.objects.create()

    # Create the running_count field via the REST API.
    response = api_client.post(
        f"/api/database/fields/table/{table.id}/",
        {"name": "Total", "type": "running_count"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == 200, response.json()
    data = response.json()
    field_id = data["id"]
    assert data["type"] == "running_count"

    # GET the field to confirm the type persisted.
    response = api_client.get(
        f"/api/database/fields/{field_id}/",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == 200
    assert response.json()["type"] == "running_count"

    # The stored count value must appear in the row list response.
    response = api_client.get(
        f"/api/database/rows/table/{table.id}/",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == 200
    rows = response.json()["results"]
    assert all(row[f"field_{field_id}"] == 2 for row in rows)
