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
    KanbanView,
    KanbanViewFieldOptions,
)
from baserow.contrib.database.views.registries import (
    view_type_registry,
)
from baserow.core.registries import ImportExportConfig


def test_kanban_view_type_registered():
    view_type = view_type_registry.get("kanban")
    assert view_type.type == "kanban"
    assert view_type.model_class == KanbanView


@pytest.mark.django_db
def test_create_kanban_view(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="kanban", name="Board")

    assert isinstance(view, KanbanView)
    assert view.single_select_field_id is None


@pytest.mark.django_db
def test_kanban_set_single_select_field(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    single_select_field = data_fixture.create_single_select_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="kanban", name="Board")
    handler.update_view(user, view, single_select_field=single_select_field.id)

    view.refresh_from_db()
    assert view.single_select_field_id == single_select_field.id

    # Reload from the database to confirm the configuration persists (AC #3).
    reloaded = KanbanView.objects.get(pk=view.id)
    assert reloaded.single_select_field_id == single_select_field.id


@pytest.mark.django_db
def test_kanban_rejects_non_single_select_field(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    text_field = data_fixture.create_text_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="kanban", name="Board")

    with pytest.raises(IncompatibleField):
        handler.update_view(user, view, single_select_field=text_field.id)


@pytest.mark.django_db
def test_kanban_rejects_field_from_other_table(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    other_table = data_fixture.create_database_table(user=user)
    other_single_select = data_fixture.create_single_select_field(table=other_table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="kanban", name="Board")

    with pytest.raises(FieldNotInTable):
        handler.update_view(user, view, single_select_field=other_single_select.id)


@pytest.mark.django_db
def test_kanban_single_select_field_nulled_on_delete(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    single_select_field = data_fixture.create_single_select_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="kanban", name="Board")
    handler.update_view(user, view, single_select_field=single_select_field.id)

    FieldHandler().delete_field(user, single_select_field)

    view.refresh_from_db()
    assert view.single_select_field_id is None


@pytest.mark.django_db
def test_kanban_export_import_round_trip(data_fixture, tmpdir):
    user = data_fixture.create_user()
    storage = FileSystemStorage(location=str(tmpdir), base_url="http://localhost")
    table = data_fixture.create_database_table(user=user)
    single_select_field = data_fixture.create_single_select_field(table=table)
    kanban_view = data_fixture.create_kanban_view(
        table=table, single_select_field=single_select_field
    )
    text_field = data_fixture.create_text_field(table=table)
    field_option = data_fixture.create_kanban_view_field_option(
        kanban_view, text_field, order=1
    )

    files_buffer = BytesIO()
    kanban_view_type = view_type_registry.get("kanban")

    with ZipFile(files_buffer, "a", ZIP_DEFLATED, False) as files_zip:
        serialized = kanban_view_type.export_serialized(
            kanban_view,
            ImportExportConfig(include_permission_data=False),
            None,
            files_zip=files_zip,
            storage=storage,
        )

    assert serialized["id"] == kanban_view.id
    assert serialized["type"] == "kanban"
    assert serialized["single_select_field_id"] == single_select_field.id
    assert len(serialized["field_options"]) == 2

    imported_single_select_field = data_fixture.create_single_select_field(table=table)
    imported_text_field = data_fixture.create_text_field(table=table)
    id_mapping = {
        "database_fields": {
            single_select_field.id: imported_single_select_field.id,
            text_field.id: imported_text_field.id,
        }
    }

    with ZipFile(files_buffer, "a", ZIP_DEFLATED, False) as files_zip:
        imported_kanban_view = kanban_view_type.import_serialized(
            kanban_view.table,
            serialized,
            ImportExportConfig(include_permission_data=False),
            id_mapping,
            {},
            files_zip,
            storage,
        )

    assert kanban_view.id != imported_kanban_view.id
    assert (
        imported_kanban_view.single_select_field_id == imported_single_select_field.id
    )
    imported_field_options = imported_kanban_view.get_field_options()
    assert len(imported_field_options) == 2


@pytest.mark.django_db
def test_kanban_set_card_cover_image_field(data_fixture):
    """AC #1/#2 — a file field can be set as the card cover image and persists."""

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    file_field = data_fixture.create_file_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="kanban", name="Board")
    handler.update_view(user, view, card_cover_image_field=file_field.id)

    view.refresh_from_db()
    assert view.card_cover_image_field_id == file_field.id

    # Reload from the database to confirm the configuration persists (AC #2).
    reloaded = KanbanView.objects.get(pk=view.id)
    assert reloaded.card_cover_image_field_id == file_field.id


@pytest.mark.django_db
def test_kanban_rejects_non_file_card_cover_image_field(data_fixture):
    """AC #1 — a field that cannot represent files is rejected as the cover."""

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    text_field = data_fixture.create_text_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="kanban", name="Board")

    with pytest.raises(IncompatibleField):
        handler.update_view(user, view, card_cover_image_field=text_field.id)


@pytest.mark.django_db
def test_kanban_rejects_card_cover_image_field_from_other_table(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    other_table = data_fixture.create_database_table(user=user)
    other_file_field = data_fixture.create_file_field(table=other_table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="kanban", name="Board")

    with pytest.raises(FieldNotInTable):
        handler.update_view(user, view, card_cover_image_field=other_file_field.id)


@pytest.mark.django_db
def test_kanban_card_cover_image_field_nulled_on_delete(data_fixture):
    """AC #2 — deleting the referenced file field nulls the cover reference."""

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    file_field = data_fixture.create_file_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="kanban", name="Board")
    handler.update_view(user, view, card_cover_image_field=file_field.id)

    FieldHandler().delete_field(user, file_field)

    view.refresh_from_db()
    assert view.card_cover_image_field_id is None


@pytest.mark.django_db
def test_kanban_get_hidden_fields_keeps_single_select_and_cover_visible(data_fixture):
    """
    AC #4 — the grouping single-select field and the card cover image field are
    always treated as visible by get_hidden_fields, even when their field option
    is explicitly hidden. This protects the board's data dependencies (the
    grouping value and the cover thumbnail must remain fetchable).
    """

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    single_select_field = data_fixture.create_single_select_field(table=table)
    file_field = data_fixture.create_file_field(table=table)
    text_field = data_fixture.create_text_field(table=table)

    kanban_view = data_fixture.create_kanban_view(
        table=table,
        single_select_field=single_select_field,
        card_cover_image_field=file_field,
        create_options=False,
    )

    # Mark every field option as hidden — including the grouping and cover fields.
    data_fixture.create_kanban_view_field_option(
        kanban_view, single_select_field, hidden=True, order=0
    )
    data_fixture.create_kanban_view_field_option(
        kanban_view, file_field, hidden=True, order=1
    )
    data_fixture.create_kanban_view_field_option(
        kanban_view, text_field, hidden=True, order=2
    )

    kanban_view_type = view_type_registry.get("kanban")
    hidden_field_ids = kanban_view_type.get_hidden_fields(kanban_view)

    # The grouping and cover fields are excluded from hidden despite hidden=True.
    assert single_select_field.id not in hidden_field_ids
    assert file_field.id not in hidden_field_ids
    # A regular hidden field stays hidden.
    assert text_field.id in hidden_field_ids


@pytest.mark.django_db
def test_kanban_card_cover_image_field_export_import_round_trip(data_fixture, tmpdir):
    """AC #2 — the cover image field reference round-trips through export/import."""

    user = data_fixture.create_user()
    storage = FileSystemStorage(location=str(tmpdir), base_url="http://localhost")
    table = data_fixture.create_database_table(user=user)
    file_field = data_fixture.create_file_field(table=table)
    kanban_view = data_fixture.create_kanban_view(
        table=table, card_cover_image_field=file_field
    )

    files_buffer = BytesIO()
    kanban_view_type = view_type_registry.get("kanban")

    with ZipFile(files_buffer, "a", ZIP_DEFLATED, False) as files_zip:
        serialized = kanban_view_type.export_serialized(
            kanban_view,
            ImportExportConfig(include_permission_data=False),
            None,
            files_zip=files_zip,
            storage=storage,
        )

    assert serialized["card_cover_image_field_id"] == file_field.id

    imported_file_field = data_fixture.create_file_field(table=table)
    id_mapping = {"database_fields": {file_field.id: imported_file_field.id}}

    with ZipFile(files_buffer, "a", ZIP_DEFLATED, False) as files_zip:
        imported_kanban_view = kanban_view_type.import_serialized(
            kanban_view.table,
            serialized,
            ImportExportConfig(include_permission_data=False),
            id_mapping,
            {},
            files_zip,
            storage,
        )

    assert imported_kanban_view.card_cover_image_field_id == imported_file_field.id


@pytest.mark.django_db
def test_newly_created_kanban_view_shows_first_three_fields(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    data_fixture.create_text_field(table=table, primary=True)
    data_fixture.create_text_field(table=table)
    data_fixture.create_text_field(table=table)
    data_fixture.create_text_field(table=table)

    handler = ViewHandler()
    handler.create_view(user, table=table, type_name="kanban")

    hidden_values = list(
        KanbanViewFieldOptions.objects.all()
        .order_by("field_id")
        .values_list("hidden", flat=True)
    )
    assert hidden_values.count(False) == 3
