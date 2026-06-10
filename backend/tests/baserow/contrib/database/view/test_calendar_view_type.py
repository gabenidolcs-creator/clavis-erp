from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.core.files.storage import FileSystemStorage

import pytest

from baserow.contrib.database.fields.exceptions import (
    FieldNotInTable,
    IncompatibleField,
)
from baserow.contrib.database.fields.handler import FieldHandler
from baserow.contrib.database.views.handler import ViewHandler
from baserow.contrib.database.views.models import (
    CalendarView,
    CalendarViewFieldOptions,
)
from baserow.contrib.database.views.registries import (
    view_type_registry,
)
from baserow.core.registries import ImportExportConfig


def test_calendar_view_type_registered():
    view_type = view_type_registry.get("calendar")
    assert view_type.type == "calendar"
    assert view_type.model_class == CalendarView


@pytest.mark.django_db
def test_create_calendar_view(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="calendar", name="Calendar")

    assert isinstance(view, CalendarView)
    assert view.date_field_id is None
    assert view.end_date_field_id is None


@pytest.mark.django_db
def test_calendar_set_date_field(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    date_field = data_fixture.create_date_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="calendar", name="Calendar")
    handler.update_view(user, view, date_field=date_field.id)

    view.refresh_from_db()
    assert view.date_field_id == date_field.id

    # Reload from the database to confirm the configuration persists (AC #3).
    reloaded = CalendarView.objects.get(pk=view.id)
    assert reloaded.date_field_id == date_field.id


@pytest.mark.django_db
def test_calendar_set_end_date_field(data_fixture):
    """AC #1 — an optional end date field can be set for multi-day events."""

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    date_field = data_fixture.create_date_field(table=table)
    end_date_field = data_fixture.create_date_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="calendar", name="Calendar")
    handler.update_view(
        user, view, date_field=date_field.id, end_date_field=end_date_field.id
    )

    view.refresh_from_db()
    assert view.date_field_id == date_field.id
    assert view.end_date_field_id == end_date_field.id

    reloaded = CalendarView.objects.get(pk=view.id)
    assert reloaded.end_date_field_id == end_date_field.id


@pytest.mark.django_db
def test_calendar_rejects_non_date_field(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    text_field = data_fixture.create_text_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="calendar", name="Calendar")

    with pytest.raises(IncompatibleField):
        handler.update_view(user, view, date_field=text_field.id)


@pytest.mark.django_db
def test_calendar_rejects_non_date_end_date_field(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    text_field = data_fixture.create_text_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="calendar", name="Calendar")

    with pytest.raises(IncompatibleField):
        handler.update_view(user, view, end_date_field=text_field.id)


@pytest.mark.django_db
def test_calendar_rejects_field_from_other_table(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    other_table = data_fixture.create_database_table(user=user)
    other_date_field = data_fixture.create_date_field(table=other_table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="calendar", name="Calendar")

    with pytest.raises(FieldNotInTable):
        handler.update_view(user, view, date_field=other_date_field.id)


@pytest.mark.django_db
def test_calendar_date_field_nulled_on_delete(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    date_field = data_fixture.create_date_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="calendar", name="Calendar")
    handler.update_view(user, view, date_field=date_field.id)

    FieldHandler().delete_field(user, date_field)

    view.refresh_from_db()
    assert view.date_field_id is None


@pytest.mark.django_db
def test_calendar_end_date_field_nulled_on_delete(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    date_field = data_fixture.create_date_field(table=table)
    end_date_field = data_fixture.create_date_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="calendar", name="Calendar")
    handler.update_view(
        user, view, date_field=date_field.id, end_date_field=end_date_field.id
    )

    FieldHandler().delete_field(user, end_date_field)

    view.refresh_from_db()
    assert view.end_date_field_id is None
    # The primary date field is untouched.
    assert view.date_field_id == date_field.id


@pytest.mark.django_db
def test_calendar_export_import_round_trip(data_fixture, tmpdir):
    user = data_fixture.create_user()
    storage = FileSystemStorage(location=str(tmpdir), base_url="http://localhost")
    table = data_fixture.create_database_table(user=user)
    date_field = data_fixture.create_date_field(table=table)
    end_date_field = data_fixture.create_date_field(table=table)
    calendar_view = data_fixture.create_calendar_view(
        table=table, date_field=date_field, end_date_field=end_date_field
    )
    text_field = data_fixture.create_text_field(table=table)
    data_fixture.create_calendar_view_field_option(calendar_view, text_field, order=1)

    files_buffer = BytesIO()
    calendar_view_type = view_type_registry.get("calendar")

    with ZipFile(files_buffer, "a", ZIP_DEFLATED, False) as files_zip:
        serialized = calendar_view_type.export_serialized(
            calendar_view,
            ImportExportConfig(include_permission_data=False),
            None,
            files_zip=files_zip,
            storage=storage,
        )

    assert serialized["id"] == calendar_view.id
    assert serialized["type"] == "calendar"
    assert serialized["date_field_id"] == date_field.id
    assert serialized["end_date_field_id"] == end_date_field.id
    assert len(serialized["field_options"]) == 3

    imported_date_field = data_fixture.create_date_field(table=table)
    imported_end_date_field = data_fixture.create_date_field(table=table)
    imported_text_field = data_fixture.create_text_field(table=table)
    id_mapping = {
        "database_fields": {
            date_field.id: imported_date_field.id,
            end_date_field.id: imported_end_date_field.id,
            text_field.id: imported_text_field.id,
        }
    }

    with ZipFile(files_buffer, "a", ZIP_DEFLATED, False) as files_zip:
        imported_calendar_view = calendar_view_type.import_serialized(
            calendar_view.table,
            serialized,
            ImportExportConfig(include_permission_data=False),
            id_mapping,
            {},
            files_zip,
            storage,
        )

    assert calendar_view.id != imported_calendar_view.id
    assert imported_calendar_view.date_field_id == imported_date_field.id
    assert imported_calendar_view.end_date_field_id == imported_end_date_field.id
    imported_field_options = imported_calendar_view.get_field_options()
    assert len(imported_field_options) == 3


@pytest.mark.django_db
def test_calendar_get_hidden_fields_keeps_date_fields_visible(data_fixture):
    """
    AC #5 — the positioning date field and the optional end date field are always
    treated as visible by get_hidden_fields, even when their field option is
    explicitly hidden. This protects the calendar's data dependencies (the date
    values must remain fetchable to position the rows).
    """

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    date_field = data_fixture.create_date_field(table=table)
    end_date_field = data_fixture.create_date_field(table=table)
    text_field = data_fixture.create_text_field(table=table)

    calendar_view = data_fixture.create_calendar_view(
        table=table,
        date_field=date_field,
        end_date_field=end_date_field,
        create_options=False,
    )

    # Mark every field option as hidden — including the positioning date fields.
    data_fixture.create_calendar_view_field_option(
        calendar_view, date_field, hidden=True, order=0
    )
    data_fixture.create_calendar_view_field_option(
        calendar_view, end_date_field, hidden=True, order=1
    )
    data_fixture.create_calendar_view_field_option(
        calendar_view, text_field, hidden=True, order=2
    )

    calendar_view_type = view_type_registry.get("calendar")
    hidden_field_ids = calendar_view_type.get_hidden_fields(calendar_view)

    # The date and end date fields are excluded from hidden despite hidden=True.
    assert date_field.id not in hidden_field_ids
    assert end_date_field.id not in hidden_field_ids
    # A regular hidden field stays hidden.
    assert text_field.id in hidden_field_ids


@pytest.mark.django_db
def test_calendar_date_field_changed_to_incompatible_type_nulls_reference(
    data_fixture,
):
    """
    The date field reference is nulled when the field is changed to a type that
    can no longer represent a date.
    """

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    date_field = data_fixture.create_date_field(table=table)
    calendar_view = data_fixture.create_calendar_view(
        table=table, date_field=date_field
    )

    FieldHandler().update_field(user, date_field, new_type_name="text")

    calendar_view.refresh_from_db()
    assert calendar_view.date_field_id is None


@pytest.mark.django_db
def test_newly_created_calendar_view_shows_first_three_fields(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    data_fixture.create_text_field(table=table, primary=True)
    data_fixture.create_text_field(table=table)
    data_fixture.create_text_field(table=table)
    data_fixture.create_text_field(table=table)

    handler = ViewHandler()
    handler.create_view(user, table=table, type_name="calendar")

    hidden_values = list(
        CalendarViewFieldOptions.objects.all()
        .order_by("field_id")
        .values_list("hidden", flat=True)
    )
    assert hidden_values.count(False) == 3
