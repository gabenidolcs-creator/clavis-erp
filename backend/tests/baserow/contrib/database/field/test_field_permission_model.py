from django.db import connection
from django.db.utils import IntegrityError

import pytest

from baserow.contrib.database.fields.models import Field, FieldPermission
from baserow.core.rbac.roles import ADMIN, EDITOR


@pytest.mark.django_db
def test_field_permission_table_exists():
    """The migration creates the database_fieldpermission table + columns."""

    table_names = connection.introspection.table_names()
    assert "database_fieldpermission" in table_names

    columns = {
        c.name
        for c in connection.introspection.get_table_description(
            connection.cursor(), "database_fieldpermission"
        )
    }
    assert {"id", "field_id", "editable_by_role"} <= columns


@pytest.mark.django_db
def test_field_default_has_no_permission_row(data_fixture):
    """Absence of a row is the default: a freshly created field is unrestricted."""

    field = data_fixture.create_text_field()

    assert FieldPermission.objects.filter(field=field).count() == 0
    assert not hasattr(field, "permission") or field.permission is None


@pytest.mark.django_db
def test_field_permission_round_trip(data_fixture):
    field = data_fixture.create_text_field()

    FieldPermission.objects.create(field=field, editable_by_role=EDITOR)

    field.refresh_from_db()
    assert field.permission.editable_by_role == EDITOR
    assert field.permission.field_id == field.id


@pytest.mark.django_db
def test_field_permission_is_one_to_one(data_fixture):
    field = data_fixture.create_text_field()
    FieldPermission.objects.create(field=field, editable_by_role=ADMIN)

    with pytest.raises(IntegrityError):
        FieldPermission.objects.create(field=field, editable_by_role=EDITOR)


@pytest.mark.django_db
def test_field_permission_cascades_on_field_delete(data_fixture):
    field = data_fixture.create_text_field()
    FieldPermission.objects.create(field=field, editable_by_role=ADMIN)
    field_id = field.id

    Field.objects.filter(id=field_id).delete()

    assert FieldPermission.objects.filter(field_id=field_id).count() == 0
