"""Tests for Story 2.1: Currency Field (CurrencyFieldType)."""
from decimal import Decimal

import pytest

from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.fields.models import CurrencyField
from baserow.contrib.database.fields.registries import field_type_registry
from baserow.contrib.database.rows.handler import RowHandler


@pytest.mark.django_db
def test_currency_field_registered():
    field_type = field_type_registry.get("currency")
    assert field_type.type == "currency"
    assert field_type.model_class is CurrencyField


@pytest.mark.django_db
def test_currency_field_creates_with_symbol(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="currency",
        name="Budget",
        currency_symbol="€",
        number_decimal_places=2,
    )
    assert field.currency_symbol == "€"
    assert field.number_decimal_places == 2
    assert isinstance(field.specific, CurrencyField)


@pytest.mark.django_db
def test_currency_field_defaults(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="currency",
        name="Price",
    )
    assert field.currency_symbol == "$"
    assert field.number_decimal_places == 0


@pytest.mark.django_db
def test_currency_field_export_value(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="currency",
        name="Price",
        currency_symbol="$",
        number_decimal_places=2,
    )
    specific = field.specific
    field_type = field_type_registry.get("currency")
    field_object = {"field": specific}

    result = field_type.get_export_value(Decimal("12.50"), field_object)
    assert result == "$12.50"

    result_none = field_type.get_export_value(None, field_object)
    assert result_none == ""

    result_rich = field_type.get_export_value(Decimal("9.99"), field_object, rich_value=True)
    # rich value returns raw formatted decimal (no symbol)
    assert "9.99" in str(result_rich)


@pytest.mark.django_db
def test_currency_field_sorts_numeric(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="currency",
        name="Amount",
        currency_symbol="$",
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
    # Sort ascending — 9 must come before 10 (numeric, not lexical)
    rows = list(model.objects.order_by(f"field_{field.id}"))
    assert rows[0].id == row9.id
    assert rows[1].id == row10.id


@pytest.mark.django_db
def test_currency_field_api_round_trip(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)

    # Create via API
    response = api_client.post(
        f"/api/database/fields/table/{table.id}/",
        {
            "name": "Revenue",
            "type": "currency",
            "currency_symbol": "£",
            "number_decimal_places": 2,
        },
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == 200, response.json()
    data = response.json()
    field_id = data["id"]
    assert data["currency_symbol"] == "£"
    assert data["number_decimal_places"] == 2

    # GET to confirm persisted
    response = api_client.get(
        f"/api/database/fields/{field_id}/",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == 200
    assert response.json()["currency_symbol"] == "£"

    # PATCH to update symbol
    response = api_client.patch(
        f"/api/database/fields/{field_id}/",
        {"currency_symbol": "¥"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == 200
    assert response.json()["currency_symbol"] == "¥"
