"""Tests for Story 2.3: Barcode Field (BarcodeFieldType)."""
import pytest

from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.fields.models import BarcodeField
from baserow.contrib.database.fields.registries import field_type_registry
from baserow.contrib.database.rows.handler import RowHandler


@pytest.mark.django_db
def test_barcode_field_registered():
    field_type = field_type_registry.get("barcode")
    assert field_type.type == "barcode"
    assert field_type.model_class is BarcodeField


@pytest.mark.django_db
def test_barcode_field_creates_with_default_qr_type(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="barcode",
        name="Code",
    )
    assert field.barcode_type == "qr"
    assert isinstance(field.specific, BarcodeField)


@pytest.mark.django_db
def test_barcode_field_creates_with_code128_type(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="barcode",
        name="Code",
        barcode_type="code128",
    )
    assert field.barcode_type == "code128"
    assert isinstance(field.specific, BarcodeField)


@pytest.mark.django_db
def test_barcode_field_api_round_trip(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)

    # Create via API
    response = api_client.post(
        f"/api/database/fields/table/{table.id}/",
        {"name": "QR", "type": "barcode"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == 200, response.json()
    data = response.json()
    field_id = data["id"]
    assert data["barcode_type"] == "qr"

    # PATCH to code128
    response = api_client.patch(
        f"/api/database/fields/{field_id}/",
        {"barcode_type": "code128"},
        format="json",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == 200
    assert response.json()["barcode_type"] == "code128"

    # GET to confirm persisted
    response = api_client.get(
        f"/api/database/fields/{field_id}/",
        HTTP_AUTHORIZATION=f"JWT {token}",
    )
    assert response.status_code == 200
    assert response.json()["barcode_type"] == "code128"


@pytest.mark.django_db
def test_barcode_field_stores_text_value(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = FieldHandler().create_field(
        user=user,
        table=table,
        type_name="barcode",
        name="Label",
    )
    model = table.get_model()
    row = RowHandler().create_row(
        user=user,
        table=table,
        values={f"field_{field.id}": "ABC-123"},
    )
    stored = model.objects.get(id=row.id)
    assert getattr(stored, f"field_{field.id}") == "ABC-123"


def test_barcode_field_migration_reversible():
    """Migration 0218 must have no irreversible operations."""
    from importlib import import_module

    migration_module = import_module(
        "baserow.contrib.database.migrations"
        ".0218_barcodefield_alter_formview_mode"
    )
    for op in migration_module.Migration.operations:
        if hasattr(op, "reverse_sql"):
            assert op.reverse_sql is not None, f"Operation {op!r} has no reverse_sql"
        if hasattr(op, "reverse"):
            assert op.reverse is not None, f"Operation {op!r} has no reverse function"
