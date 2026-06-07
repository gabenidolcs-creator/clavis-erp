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


# --- Story 1.5: readable_by_role (the read/visibility threshold) -------------


@pytest.mark.django_db
def test_readable_by_role_column_exists():
    """The 1.5 migration adds the ``readable_by_role`` column to the same table."""

    columns = {
        c.name
        for c in connection.introspection.get_table_description(
            connection.cursor(), "database_fieldpermission"
        )
    }
    assert "readable_by_role" in columns


@pytest.mark.django_db
def test_readable_by_role_defaults_to_null_visible_to_all(data_fixture):
    """Absent/null ``readable_by_role`` = visible to all (purely additive default)."""

    field = data_fixture.create_text_field()
    permission = FieldPermission.objects.create(field=field, editable_by_role=ADMIN)

    permission.refresh_from_db()
    assert permission.readable_by_role is None


@pytest.mark.django_db
def test_readable_by_role_round_trips_independently_of_editable(data_fixture):
    """The two thresholds share one row but are independent: setting the read
    threshold does not disturb the 1.4 edit threshold and vice versa."""

    field = data_fixture.create_text_field()

    FieldPermission.objects.create(
        field=field, editable_by_role=EDITOR, readable_by_role=ADMIN
    )

    field.refresh_from_db()
    assert field.permission.editable_by_role == EDITOR
    assert field.permission.readable_by_role == ADMIN


@pytest.mark.django_db
def test_read_threshold_only_leaves_editable_null(data_fixture):
    """A field can be hidden (read threshold) without any edit restriction —
    ``editable_by_role`` stays null, preserving 1.4 semantics (unrestricted edit)."""

    field = data_fixture.create_text_field()

    FieldPermission.objects.create(field=field, readable_by_role=ADMIN)

    field.refresh_from_db()
    assert field.permission.readable_by_role == ADMIN
    assert field.permission.editable_by_role is None
