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
