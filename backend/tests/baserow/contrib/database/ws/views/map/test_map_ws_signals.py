from unittest.mock import patch

import pytest

# Import the receiver to ensure it is registered before the test sends the signal.
import baserow.contrib.database.ws.views.map.signals  # noqa: F401
from baserow.contrib.database.views.map.signals import geocode_pin_updated


@pytest.mark.django_db
@patch("baserow.ws.registries.broadcast_to_channel_group")
def test_broadcast_geocode_pin_updated(mock_broadcast, data_fixture):
    """
    Sending geocode_pin_updated fires a WS broadcast to the table page group
    with the correct payload type, coordinates, and table_id.
    """
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = data_fixture.create_text_field(user=user, table=table)

    geocode_pin_updated.send(
        sender=None,
        row_id=42,
        field_id=field.id,
        lat=1.23,
        lng=4.56,
    )

    mock_broadcast.delay.assert_called_once()
    group_name, payload, *_ = mock_broadcast.delay.call_args[0]
    assert group_name == f"table-{table.id}"
    assert payload["type"] == "geocode_pin_updated"
    assert payload["row_id"] == 42
    assert payload["lat"] == 1.23
    assert payload["lng"] == 4.56
    assert payload["table_id"] == table.id


@pytest.mark.django_db
@patch("baserow.ws.registries.broadcast_to_channel_group")
def test_broadcast_geocode_pin_updated_none_coordinates(mock_broadcast, data_fixture):
    """None lat/lng (un-geocodable) should be forwarded as None in payload."""
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    field = data_fixture.create_text_field(user=user, table=table)

    geocode_pin_updated.send(
        sender=None,
        row_id=7,
        field_id=field.id,
        lat=None,
        lng=None,
    )

    mock_broadcast.delay.assert_called_once()
    _, payload, *_ = mock_broadcast.delay.call_args[0]
    assert payload["lat"] is None
    assert payload["lng"] is None


@pytest.mark.django_db
@patch("baserow.ws.registries.broadcast_to_channel_group")
def test_broadcast_geocode_pin_updated_invalid_field(mock_broadcast, data_fixture):
    """Unknown field_id must not raise and must not call broadcast."""
    geocode_pin_updated.send(
        sender=None,
        row_id=1,
        field_id=99999999,
        lat=0.0,
        lng=0.0,
    )

    mock_broadcast.delay.assert_not_called()
