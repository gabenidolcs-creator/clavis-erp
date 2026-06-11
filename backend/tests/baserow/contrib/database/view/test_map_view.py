from unittest.mock import patch

import pytest

from baserow.contrib.database.fields.exceptions import (
    FieldNotInTable,
    IncompatibleField,
)
from baserow.contrib.database.views.handler import ViewHandler
from baserow.contrib.database.views.map.handler import MapViewHandler
from baserow.contrib.database.views.map.signals import geocode_pin_updated
from baserow.contrib.database.views.models import MapView
from baserow.contrib.database.views.registries import view_type_registry
from baserow.contrib.database.views.view_types import MapViewType


def test_map_view_type_registered():
    view_type = view_type_registry.get("map")
    assert view_type.type == "map"
    assert view_type.model_class == MapView


@pytest.mark.django_db
def test_create_map_view(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="map", name="Map")

    assert isinstance(view, MapView)
    assert view.address_field_id is None
    assert view.lat_field_id is None
    assert view.lng_field_id is None


@pytest.mark.django_db
def test_map_view_persists_address_field(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    address_field = data_fixture.create_text_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="map", name="Map")
    handler.update_view(user, view, address_field=address_field.id)

    view.refresh_from_db()
    assert view.address_field_id == address_field.id
    reloaded = MapView.objects.get(pk=view.id)
    assert reloaded.address_field_id == address_field.id


@pytest.mark.django_db
def test_map_view_persists_lat_lng_fields(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    lat_field = data_fixture.create_number_field(table=table)
    lng_field = data_fixture.create_number_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="map", name="Map")
    handler.update_view(user, view, lat_field=lat_field.id, lng_field=lng_field.id)

    view.refresh_from_db()
    assert view.lat_field_id == lat_field.id
    assert view.lng_field_id == lng_field.id


@pytest.mark.django_db
def test_map_prepare_values_rejects_field_not_in_table(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    other_table = data_fixture.create_database_table(user=user)
    foreign_field = data_fixture.create_text_field(table=other_table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="map", name="Map")

    with pytest.raises(FieldNotInTable):
        handler.update_view(user, view, address_field=foreign_field.id)


@pytest.mark.django_db
def test_map_prepare_values_rejects_address_and_lat_lng_simultaneous(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    address_field = data_fixture.create_text_field(table=table)
    lat_field = data_fixture.create_number_field(table=table)

    handler = ViewHandler()
    view = handler.create_view(user, table=table, type_name="map", name="Map")

    with pytest.raises(IncompatibleField):
        handler.update_view(
            user, view, address_field=address_field.id, lat_field=lat_field.id
        )


@pytest.mark.django_db
def test_map_handler_get_rows_partitions_pins_and_unresolvable(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    address_field = data_fixture.create_text_field(table=table)

    view = data_fixture.create_map_view(
        table=table, address_field=address_field, user=user
    )
    model = table.get_model()
    row_cached = model.objects.create(**{f"field_{address_field.id}": "123 Main St"})
    row_uncached = model.objects.create(**{f"field_{address_field.id}": "456 Oak Ave"})

    with (
        patch(
            "baserow.contrib.database.views.map.handler.GeocodingService.get_cached"
        ) as mock_cached,
        patch(
            "baserow.contrib.database.views.map.handler.GeocodingService.enqueue"
        ) as mock_enqueue,
    ):
        mock_cached.side_effect = lambda addr, actor, field: (
            (51.5, -0.1) if "123 Main" in addr else (None, None)
        )

        result = MapViewHandler().get_rows(view, user, model)

    pins = result["pins"]
    unresolvable = result["unresolvable"]

    assert len(pins) == 1
    assert pins[0]["row_id"] == row_cached.id
    assert pins[0]["lat"] == pytest.approx(51.5)
    assert pins[0]["lng"] == pytest.approx(-0.1)

    assert len(unresolvable) == 1
    assert unresolvable[0]["row_id"] == row_uncached.id
    mock_enqueue.assert_called_once()


@pytest.mark.django_db
def test_map_handler_get_rows_respects_view_filter(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    address_field = data_fixture.create_text_field(table=table)

    view = data_fixture.create_map_view(
        table=table, address_field=address_field, user=user
    )
    data_fixture.create_view_filter(
        view=view,
        field=address_field,
        type="contains",
        value="Main",
    )

    model = table.get_model()
    model.objects.create(**{f"field_{address_field.id}": "123 Main St"})
    model.objects.create(**{f"field_{address_field.id}": "456 Oak Ave"})  # filtered out

    with (
        patch(
            "baserow.contrib.database.views.map.handler.GeocodingService.get_cached"
        ) as mock_cached,
        patch("baserow.contrib.database.views.map.handler.GeocodingService.enqueue"),
    ):
        mock_cached.return_value = (51.5, -0.1)
        result = MapViewHandler().get_rows(view, user, model)

    # Only the "Main St" row passes the filter
    total = len(result["pins"]) + len(result["unresolvable"])
    assert total == 1


@pytest.mark.django_db
def test_map_handler_get_rows_permission_denied_returns_unresolvable(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    address_field = data_fixture.create_text_field(table=table)

    view = data_fixture.create_map_view(
        table=table, address_field=address_field, user=user
    )
    model = table.get_model()
    model.objects.create(**{f"field_{address_field.id}": "123 Main St"})

    with (
        patch(
            "baserow.contrib.database.views.map.handler.GeocodingService.get_cached"
        ) as mock_cached,
        patch(
            "baserow.contrib.database.views.map.handler.GeocodingService.enqueue"
        ) as mock_enqueue,
    ):
        # Permission denied path: returns (None, None) silently
        mock_cached.return_value = (None, None)
        result = MapViewHandler().get_rows(view, user, model)

    assert len(result["pins"]) == 0
    assert len(result["unresolvable"]) == 1
    mock_enqueue.assert_called_once()


@pytest.mark.django_db
def test_map_handler_lat_lng_mode(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    lat_field = data_fixture.create_number_field(table=table)
    lng_field = data_fixture.create_number_field(table=table)

    view = data_fixture.create_map_view(
        table=table, lat_field=lat_field, lng_field=lng_field, user=user
    )
    model = table.get_model()
    row1 = model.objects.create(
        **{f"field_{lat_field.id}": 51.5, f"field_{lng_field.id}": -0.1}
    )
    row2 = model.objects.create(
        **{f"field_{lat_field.id}": None, f"field_{lng_field.id}": -0.1}
    )

    result = MapViewHandler().get_rows(view, user, model)

    assert len(result["pins"]) == 1
    assert result["pins"][0]["row_id"] == row1.id
    assert len(result["unresolvable"]) == 1
    assert result["unresolvable"][0]["row_id"] == row2.id


def test_geocode_pin_updated_signal_defined():
    assert geocode_pin_updated is not None


@pytest.mark.django_db
def test_map_view_after_field_delete_nullifies_address_field(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    address_field = data_fixture.create_text_field(table=table)

    view = data_fixture.create_map_view(
        table=table, address_field=address_field, user=user
    )
    assert view.address_field_id == address_field.id

    MapViewType().after_field_delete(address_field)

    view.refresh_from_db()
    assert view.address_field_id is None


@pytest.mark.django_db
def test_map_view_after_field_delete_nullifies_lat_lng_fields(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    lat_field = data_fixture.create_number_field(table=table)
    lng_field = data_fixture.create_number_field(table=table)

    view = data_fixture.create_map_view(
        table=table, lat_field=lat_field, lng_field=lng_field, user=user
    )
    assert view.lat_field_id == lat_field.id
    assert view.lng_field_id == lng_field.id

    MapViewType().after_field_delete(lat_field)
    MapViewType().after_field_delete(lng_field)

    view.refresh_from_db()
    assert view.lat_field_id is None
    assert view.lng_field_id is None


@pytest.mark.django_db
def test_map_handler_empty_address_is_unresolvable_no_enqueue(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    address_field = data_fixture.create_text_field(table=table)

    view = data_fixture.create_map_view(
        table=table, address_field=address_field, user=user
    )
    model = table.get_model()
    row = model.objects.create(**{f"field_{address_field.id}": ""})

    with (
        patch(
            "baserow.contrib.database.views.map.handler.GeocodingService.get_cached"
        ) as mock_cached,
        patch(
            "baserow.contrib.database.views.map.handler.GeocodingService.enqueue"
        ) as mock_enqueue,
    ):
        result = MapViewHandler().get_rows(view, user, model)

    assert len(result["pins"]) == 0
    assert len(result["unresolvable"]) == 1
    assert result["unresolvable"][0]["row_id"] == row.id
    # Empty address must not call geocoding service at all
    mock_cached.assert_not_called()
    mock_enqueue.assert_not_called()
