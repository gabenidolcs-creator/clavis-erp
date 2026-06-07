"""Tests for Story 2.2: Percent Field (PercentFieldType)."""
from decimal import Decimal

import pytest

from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.fields.models import PercentField
from baserow.contrib.database.fields.registries import field_type_registry
from baserow.contrib.database.rows.handler import RowHandler


@pytest.mark.django_db
def test_percent_field_registered():
    field_type = field_type_registry.get("percent")
    assert field_type.type == "percent"
    assert field_type.model_class is PercentField


@pytest.mark.django_db
def test_percent_field_creates_with_suffix_enforced(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="percent",
        name="Rate",
        number_decimal_places=1,
    )
    assert field.number_suffix == "%"
    assert field.number_prefix == ""
    assert field.number_decimal_places == 1
    assert isinstance(field.specific, PercentField)


@pytest.mark.django_db
def test_percent_field_prepare_values_locks_suffix(data_fixture):
    user = data_fixture.create_user()
    field_type = field_type_registry.get("percent")
    result = field_type.prepare_values(
        {"number_suffix": "x", "number_prefix": "y", "number_decimal_places": 0},
        user,
    )
    assert result["number_suffix"] == "%"
    assert result["number_prefix"] == ""


@pytest.mark.django_db
def test_percent_field_prepare_values_api_cannot_override_suffix(data_fixture):
    """Ensure prepare_values enforces % regardless of caller input."""
    user = data_fixture.create_user()
    field_type = field_type_registry.get("percent")
    for suffix_attempt in [None, "", "pct", "%%"]:
        result = field_type.prepare_values(
            {"number_suffix": suffix_attempt, "number_decimal_places": 2},
            user,
        )
        assert result["number_suffix"] == "%"
        assert result["number_prefix"] == ""


@pytest.mark.django_db
def test_percent_field_api_round_trip(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)

    # Create via API
    response = api_client.post(
        f"/api/database/fields/table/{table.id}/",
        {"name": "Completion", "type": "percent", "number_decimal_places": 1},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == 200, response.json()
    data = response.json()
    field_id = data["id"]
    assert data["number_decimal_places"] == 1
    assert data["number_suffix"] == "%"
    assert data["number_prefix"] == ""

    # GET to confirm persisted
    response = api_client.get(
        f"/api/database/fields/{field_id}/",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == 200
    resp_data = response.json()
    assert resp_data["number_decimal_places"] == 1
    assert resp_data["number_suffix"] == "%"

    # PATCH to change precision
    response = api_client.patch(
        f"/api/database/fields/{field_id}/",
        {"number_decimal_places": 2},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == 200
    assert response.json()["number_decimal_places"] == 2
    # suffix must still be locked
    assert response.json()["number_suffix"] == "%"


@pytest.mark.django_db
def test_percent_field_sorts_numeric(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="percent",
        name="Progress",
        number_decimal_places=0,
    )
    model = table.get_model()
    row_handler = RowHandler()
    row9 = row_handler.create_row(
        user=user, table=table, values={f"field_{field.id}": 9}
    )
    row10 = row_handler.create_row(
        user=user, table=table, values={f"field_{field.id}": 10}
    )
    # Numeric sort: 9 before 10 (not lexical "10" before "9")
    rows = list(model.objects.order_by(f"field_{field.id}"))
    assert rows[0].id == row9.id
    assert rows[1].id == row10.id


@pytest.mark.django_db
def test_percent_field_row_stores_as_decimal(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="percent",
        name="Rate",
        number_decimal_places=2,
    )
    model = table.get_model()
    row = RowHandler().create_row(
        user=user,
        table=table,
        values={f"field_{field.id}": Decimal("50.25")},
    )
    stored = model.objects.get(id=row.id)
    assert getattr(stored, f"field_{field.id}") == Decimal("50.25")


@pytest.mark.django_db
def test_percent_field_export_value(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="percent",
        name="Progress",
        number_decimal_places=1,
    )
    specific = field.specific
    field_type = field_type_registry.get("percent")
    field_object = {"field": specific}

    result = field_type.get_export_value(Decimal("50.5"), field_object)
    assert result == "50.5%"

    result_none = field_type.get_export_value(None, field_object)
    assert result_none == ""


@pytest.mark.django_db
def test_percent_field_defaults(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="percent",
        name="Rate",
    )
    assert field.number_suffix == "%"
    assert field.number_prefix == ""
    assert field.number_decimal_places == 0


def test_percent_field_migration_reversible():
    """Migration 0217 must have no irreversible RunSQL/RunPython operations."""
    from importlib import import_module

    migration_module = import_module(
        "baserow.contrib.database.migrations"
        ".0217_percentfield_alter_formview_mode"
    )
    for op in migration_module.Migration.operations:
        if hasattr(op, "reverse_sql"):
            assert op.reverse_sql is not None, f"Operation {op!r} has no reverse_sql"
        if hasattr(op, "reverse"):
            assert op.reverse is not None, f"Operation {op!r} has no reverse function"
