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
    TimelineView,
    TimelineViewFieldOptions,
)
from baserow.contrib.database.views.registries import (
    view_type_registry,
)
from baserow.core.registries import ImportExportConfig


def test_timeline_view_type_registered():
    view_type = view_type_registry.get("timeline")
    assert view_type.type == "timeline"
    assert view_type.model_class == TimelineView


@pytest.mark.django_db
def test_create_timeline_view(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="timeline", name="Timeline")

    assert isinstance(view, TimelineView)
    assert view.start_date_field_id is None
    assert view.end_date_field_id is None
    # The persisted zoom level defaults to "month" (AC #3).
    assert view.timescale == "month"


@pytest.mark.django_db
def test_timeline_set_start_and_end_date_fields(data_fixture):
    """AC #1 — both the start and end date fields persist and reopen."""

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    start_date_field = data_fixture.create_date_field(table=table)
    end_date_field = data_fixture.create_date_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="timeline", name="Timeline")
    handler.update_view(
        user,
        view,
        start_date_field=start_date_field.id,
        end_date_field=end_date_field.id,
    )

    view.refresh_from_db()
    assert view.start_date_field_id == start_date_field.id
    assert view.end_date_field_id == end_date_field.id

    # Reload from the database to confirm the configuration persists (AC #1).
    reloaded = TimelineView.objects.get(pk=view.id)
    assert reloaded.start_date_field_id == start_date_field.id
    assert reloaded.end_date_field_id == end_date_field.id


@pytest.mark.django_db
def test_timeline_timescale_persists_and_round_trips(data_fixture):
    """AC #3 — the selected zoom level is a persisted backend column."""

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="timeline", name="Timeline")

    for timescale in ("day", "week", "month"):
        handler.update_view(user, view, timescale=timescale)
        view.refresh_from_db()
        assert view.timescale == timescale
        reloaded = TimelineView.objects.get(pk=view.id)
        assert reloaded.timescale == timescale


@pytest.mark.django_db
def test_timeline_rejects_non_date_start_field(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    text_field = data_fixture.create_text_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="timeline", name="Timeline")

    with pytest.raises(IncompatibleField):
        handler.update_view(user, view, start_date_field=text_field.id)


@pytest.mark.django_db
def test_timeline_rejects_non_date_end_field(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    text_field = data_fixture.create_text_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="timeline", name="Timeline")

    with pytest.raises(IncompatibleField):
        handler.update_view(user, view, end_date_field=text_field.id)


@pytest.mark.django_db
def test_timeline_rejects_field_from_other_table(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    other_table = data_fixture.create_database_table(user=user)
    other_date_field = data_fixture.create_date_field(table=other_table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="timeline", name="Timeline")

    with pytest.raises(FieldNotInTable):
        handler.update_view(user, view, start_date_field=other_date_field.id)


@pytest.mark.django_db
def test_timeline_start_date_field_nulled_on_delete(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    start_date_field = data_fixture.create_date_field(table=table)
    end_date_field = data_fixture.create_date_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="timeline", name="Timeline")
    handler.update_view(
        user,
        view,
        start_date_field=start_date_field.id,
        end_date_field=end_date_field.id,
    )

    FieldHandler().delete_field(user, start_date_field)

    view.refresh_from_db()
    assert view.start_date_field_id is None
    # The end date field is untouched.
    assert view.end_date_field_id == end_date_field.id


@pytest.mark.django_db
def test_timeline_end_date_field_nulled_on_delete(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    start_date_field = data_fixture.create_date_field(table=table)
    end_date_field = data_fixture.create_date_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="timeline", name="Timeline")
    handler.update_view(
        user,
        view,
        start_date_field=start_date_field.id,
        end_date_field=end_date_field.id,
    )

    FieldHandler().delete_field(user, end_date_field)

    view.refresh_from_db()
    assert view.end_date_field_id is None
    assert view.start_date_field_id == start_date_field.id


@pytest.mark.django_db
def test_timeline_date_field_changed_to_incompatible_type_nulls_reference(
    data_fixture,
):
    """
    The date field references are nulled when a field is changed to a type that
    can no longer represent a date (soft-delete safe handler).
    """

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    start_date_field = data_fixture.create_date_field(table=table)
    end_date_field = data_fixture.create_date_field(table=table)
    timeline_view = data_fixture.create_timeline_view(
        table=table,
        start_date_field=start_date_field,
        end_date_field=end_date_field,
    )

    FieldHandler().update_field(user, start_date_field, new_type_name="text")

    timeline_view.refresh_from_db()
    assert timeline_view.start_date_field_id is None
    assert timeline_view.end_date_field_id == end_date_field.id


@pytest.mark.django_db
def test_timeline_get_hidden_fields_keeps_date_fields_visible(data_fixture):
    """
    AC #5 — the start and end date fields are always treated as visible by
    get_hidden_fields, even when their field option is explicitly hidden. This
    protects the timeline's data dependencies (the date values must remain
    fetchable to position the bars).
    """

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    start_date_field = data_fixture.create_date_field(table=table)
    end_date_field = data_fixture.create_date_field(table=table)
    text_field = data_fixture.create_text_field(table=table)

    timeline_view = data_fixture.create_timeline_view(
        table=table,
        start_date_field=start_date_field,
        end_date_field=end_date_field,
        create_options=False,
    )

    # Mark every field option as hidden — including the positioning date fields.
    data_fixture.create_timeline_view_field_option(
        timeline_view, start_date_field, hidden=True, order=0
    )
    data_fixture.create_timeline_view_field_option(
        timeline_view, end_date_field, hidden=True, order=1
    )
    data_fixture.create_timeline_view_field_option(
        timeline_view, text_field, hidden=True, order=2
    )

    timeline_view_type = view_type_registry.get("timeline")
    hidden_field_ids = timeline_view_type.get_hidden_fields(timeline_view)

    # The start and end date fields are excluded from hidden despite hidden=True.
    assert start_date_field.id not in hidden_field_ids
    assert end_date_field.id not in hidden_field_ids
    # A regular hidden field stays hidden.
    assert text_field.id in hidden_field_ids


@pytest.mark.django_db
def test_timeline_export_import_round_trip(data_fixture, tmpdir):
    """AC #1, #3 — start/end date fields, timescale, and field options round-trip."""

    user = data_fixture.create_user()
    storage = FileSystemStorage(location=str(tmpdir), base_url="http://localhost")
    table = data_fixture.create_database_table(user=user)
    start_date_field = data_fixture.create_date_field(table=table)
    end_date_field = data_fixture.create_date_field(table=table)
    timeline_view = data_fixture.create_timeline_view(
        table=table,
        start_date_field=start_date_field,
        end_date_field=end_date_field,
        timescale="week",
    )
    text_field = data_fixture.create_text_field(table=table)
    data_fixture.create_timeline_view_field_option(timeline_view, text_field, order=1)

    files_buffer = BytesIO()
    timeline_view_type = view_type_registry.get("timeline")

    with ZipFile(files_buffer, "a", ZIP_DEFLATED, False) as files_zip:
        serialized = timeline_view_type.export_serialized(
            timeline_view,
            ImportExportConfig(include_permission_data=False),
            None,
            files_zip=files_zip,
            storage=storage,
        )

    assert serialized["id"] == timeline_view.id
    assert serialized["type"] == "timeline"
    assert serialized["start_date_field_id"] == start_date_field.id
    assert serialized["end_date_field_id"] == end_date_field.id
    assert serialized["timescale"] == "week"
    assert len(serialized["field_options"]) == 3

    imported_start_date_field = data_fixture.create_date_field(table=table)
    imported_end_date_field = data_fixture.create_date_field(table=table)
    imported_text_field = data_fixture.create_text_field(table=table)
    id_mapping = {
        "database_fields": {
            start_date_field.id: imported_start_date_field.id,
            end_date_field.id: imported_end_date_field.id,
            text_field.id: imported_text_field.id,
        }
    }

    with ZipFile(files_buffer, "a", ZIP_DEFLATED, False) as files_zip:
        imported_timeline_view = timeline_view_type.import_serialized(
            timeline_view.table,
            serialized,
            ImportExportConfig(include_permission_data=False),
            id_mapping,
            {},
            files_zip,
            storage,
        )

    assert timeline_view.id != imported_timeline_view.id
    assert imported_timeline_view.start_date_field_id == imported_start_date_field.id
    assert imported_timeline_view.end_date_field_id == imported_end_date_field.id
    assert imported_timeline_view.timescale == "week"
    imported_field_options = imported_timeline_view.get_field_options()
    assert len(imported_field_options) == 3


@pytest.mark.django_db
def test_newly_created_timeline_view_shows_first_three_fields(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    data_fixture.create_text_field(table=table, primary=True)
    data_fixture.create_text_field(table=table)
    data_fixture.create_text_field(table=table)
    data_fixture.create_text_field(table=table)

    handler = ViewHandler()
    handler.create_view(user, table=table, type_name="timeline")

    hidden_values = list(
        TimelineViewFieldOptions.objects.all()
        .order_by("field_id")
        .values_list("hidden", flat=True)
    )
    assert hidden_values.count(False) == 3
