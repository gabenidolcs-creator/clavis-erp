from unittest.mock import patch

from django.shortcuts import reverse

import pytest
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
)


@pytest.mark.django_db
def test_map_rows_view_404_for_unknown_view(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    url = reverse("api:database:views:map:rows", kwargs={"view_id": 999})
    response = api_client.get(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})
    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json()["error"] == "ERROR_MAP_VIEW_DOES_NOT_EXIST"


@pytest.mark.django_db
def test_map_rows_view_400_when_no_location_source(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    view = data_fixture.create_map_view(table=table, user=user)
    # No address_field or lat/lng pair configured

    url = reverse("api:database:views:map:rows", kwargs={"view_id": view.id})
    response = api_client.get(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})
    assert response.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_map_rows_view_returns_pins_and_unresolvable(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    address_field = data_fixture.create_text_field(table=table)

    view = data_fixture.create_map_view(
        table=table, address_field=address_field, user=user
    )
    model = table.get_model()
    row_cached = model.objects.create(**{f"field_{address_field.id}": "123 Main St"})
    row_uncached = model.objects.create(**{f"field_{address_field.id}": "Unknown Rd"})

    url = reverse("api:database:views:map:rows", kwargs={"view_id": view.id})

    with (
        patch(
            "baserow.contrib.database.views.map.handler.GeocodingService.get_cached"
        ) as mock_cached,
        patch("baserow.contrib.database.views.map.handler.GeocodingService.enqueue"),
    ):
        mock_cached.side_effect = lambda addr, actor, field: (
            (51.5, -0.1) if "123 Main" in addr else (None, None)
        )
        response = api_client.get(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})

    assert response.status_code == HTTP_200_OK
    data = response.json()
    assert "pins" in data
    assert "unresolvable" in data
    assert len(data["pins"]) == 1
    assert data["pins"][0]["row_id"] == row_cached.id
    assert data["pins"][0]["lat"] == pytest.approx(51.5)
    assert data["pins"][0]["lng"] == pytest.approx(-0.1)
    assert len(data["unresolvable"]) == 1
    assert data["unresolvable"][0]["row_id"] == row_uncached.id


@pytest.mark.django_db
def test_map_rows_view_unauthenticated_returns_401(api_client, data_fixture):
    url = reverse("api:database:views:map:rows", kwargs={"view_id": 1})
    response = api_client.get(url)
    assert response.status_code == HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_map_rows_view_lat_lng_mode_returns_pins(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    lat_field = data_fixture.create_number_field(table=table)
    lng_field = data_fixture.create_number_field(table=table)

    view = data_fixture.create_map_view(
        table=table, lat_field=lat_field, lng_field=lng_field, user=user
    )
    model = table.get_model()
    row = model.objects.create(
        **{f"field_{lat_field.id}": "48.8566", f"field_{lng_field.id}": "2.3522"}
    )
    model.objects.create(
        **{f"field_{lat_field.id}": None, f"field_{lng_field.id}": None}
    )

    url = reverse("api:database:views:map:rows", kwargs={"view_id": view.id})
    response = api_client.get(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})

    assert response.status_code == HTTP_200_OK
    data = response.json()
    assert len(data["pins"]) == 1
    assert data["pins"][0]["row_id"] == row.id
    assert data["pins"][0]["lat"] == pytest.approx(48.8566, rel=1e-4)
    assert data["pins"][0]["lng"] == pytest.approx(2.3522, rel=1e-4)
    assert len(data["unresolvable"]) == 1
