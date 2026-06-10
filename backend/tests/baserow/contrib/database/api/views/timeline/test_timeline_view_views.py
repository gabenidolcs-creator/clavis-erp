from django.shortcuts import reverse

import pytest
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)


@pytest.mark.django_db
def test_list_rows(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token(
        email="test@test.nl", password="password", first_name="Test1"
    )
    table = data_fixture.create_database_table(user=user)
    text_field = data_fixture.create_text_field(
        table=table, order=0, name="Color", text_default="white"
    )
    timeline = data_fixture.create_timeline_view(table=table)
    timeline_2 = data_fixture.create_timeline_view()

    model = timeline.table.get_model()
    row_1 = model.objects.create(**{f"field_{text_field.id}": "Green"})
    row_2 = model.objects.create()
    model.objects.create(**{f"field_{text_field.id}": "Orange"})
    model.objects.create(**{f"field_{text_field.id}": "Purple"})

    url = reverse("api:database:views:timeline:list", kwargs={"view_id": 999})
    response = api_client.get(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})
    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json()["error"] == "ERROR_TIMELINE_DOES_NOT_EXIST"

    url = reverse("api:database:views:timeline:list", kwargs={"view_id": timeline_2.id})
    response = api_client.get(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_USER_NOT_IN_GROUP"

    url = reverse("api:database:views:timeline:list", kwargs={"view_id": timeline.id})
    response = api_client.get(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})
    response_json = response.json()
    assert response.status_code == HTTP_200_OK
    assert response_json["count"] == 4
    assert response_json["results"][0]["id"] == row_1.id
    assert response_json["results"][1]["id"] == row_2.id
    assert "field_options" not in response_json


@pytest.mark.django_db
def test_list_rows_applies_sorts_and_filters(api_client, data_fixture):
    """AC #1 — existing view sorts and filters apply to the rows on the timeline."""

    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    text_field = data_fixture.create_text_field(table=table, order=0, name="Color")
    timeline = data_fixture.create_timeline_view(table=table)

    model = timeline.table.get_model()
    row_1 = model.objects.create(**{f"field_{text_field.id}": "Green"})
    model.objects.create(**{f"field_{text_field.id}": "Orange"})
    row_3 = model.objects.create(**{f"field_{text_field.id}": "Apple"})

    # Sort applies.
    sort = data_fixture.create_view_sort(view=timeline, field=text_field, order="ASC")
    url = reverse("api:database:views:timeline:list", kwargs={"view_id": timeline.id})
    response = api_client.get(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})
    response_json = response.json()
    assert response.status_code == HTTP_200_OK
    assert response_json["results"][0]["id"] == row_3.id  # "Apple" first
    sort.delete()

    # Filter applies.
    view_filter = data_fixture.create_view_filter(
        view=timeline, field=text_field, value="Green"
    )
    response = api_client.get(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})
    response_json = response.json()
    assert response.status_code == HTTP_200_OK
    assert response_json["count"] == 1
    assert response_json["results"][0]["id"] == row_1.id
    view_filter.delete()


@pytest.mark.django_db
def test_list_rows_include_field_options(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    data_fixture.create_text_field(table=table, order=0, name="Color")
    timeline = data_fixture.create_timeline_view(table=table)

    url = reverse("api:database:views:timeline:list", kwargs={"view_id": timeline.id})
    response = api_client.get(
        url, {"include": "field_options"}, **{"HTTP_AUTHORIZATION": f"JWT {token}"}
    )
    response_json = response.json()
    assert response.status_code == HTTP_200_OK
    assert "field_options" in response_json


@pytest.mark.django_db
def test_patch_timeline_view_date_fields(api_client, data_fixture):
    """AC #1 — the start and end date fields are set and returned on the view."""

    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    start_date_field = data_fixture.create_date_field(table=table)
    end_date_field = data_fixture.create_date_field(table=table)
    timeline = data_fixture.create_timeline_view(table=table)

    url = reverse("api:database:views:item", kwargs={"view_id": timeline.id})
    response = api_client.patch(
        url,
        {
            "start_date_field": start_date_field.id,
            "end_date_field": end_date_field.id,
        },
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    response_json = response.json()
    assert response.status_code == HTTP_200_OK
    assert response_json["start_date_field"] == start_date_field.id
    assert response_json["end_date_field"] == end_date_field.id

    # Re-fetch the view to confirm per-view persistence (AC #1).
    response = api_client.get(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})
    assert response.status_code == HTTP_200_OK
    assert response.json()["start_date_field"] == start_date_field.id
    assert response.json()["end_date_field"] == end_date_field.id


@pytest.mark.django_db
def test_patch_timeline_view_timescale_persists(api_client, data_fixture):
    """AC #3 — the zoom level persists through the generic view PATCH."""

    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    timeline = data_fixture.create_timeline_view(table=table)

    url = reverse("api:database:views:item", kwargs={"view_id": timeline.id})
    response = api_client.patch(
        url,
        {"timescale": "week"},
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    response_json = response.json()
    assert response.status_code == HTTP_200_OK
    assert response_json["timescale"] == "week"

    # Re-fetch the view to confirm per-view persistence (AC #3).
    response = api_client.get(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})
    assert response.status_code == HTTP_200_OK
    assert response.json()["timescale"] == "week"


@pytest.mark.django_db
def test_patch_timeline_view_rejects_invalid_timescale(api_client, data_fixture):
    """AC #3 — an invalid zoom level is rejected by the serializer ChoiceField."""

    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    timeline = data_fixture.create_timeline_view(table=table)

    url = reverse("api:database:views:item", kwargs={"view_id": timeline.id})
    response = api_client.patch(
        url,
        {"timescale": "century"},
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    assert response.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_patch_timeline_view_rejects_non_date_field(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    text_field = data_fixture.create_text_field(table=table)
    timeline = data_fixture.create_timeline_view(table=table)

    url = reverse("api:database:views:item", kwargs={"view_id": timeline.id})
    response = api_client.patch(
        url,
        {"start_date_field": text_field.id},
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_INCOMPATIBLE_FIELD"


@pytest.mark.django_db
def test_patch_timeline_view_field_options_hidden_persists(api_client, data_fixture):
    """
    AC #5 — toggling a field's visibility through the shared field_options
    PATCH endpoint persists and is reflected when listing with field_options.
    There is no Timeline-specific field-options endpoint; the generic one is used.
    """

    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    text_field = data_fixture.create_text_field(table=table, order=0, name="Color")
    timeline = data_fixture.create_timeline_view(table=table)

    field_options_url = reverse(
        "api:database:views:field_options", kwargs={"view_id": timeline.id}
    )
    response = api_client.patch(
        field_options_url,
        {"field_options": {text_field.id: {"hidden": True}}},
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    assert response.status_code == HTTP_200_OK
    assert response.json()["field_options"][str(text_field.id)]["hidden"] is True

    # A follow-up list including field_options reflects the persisted toggle.
    list_url = reverse(
        "api:database:views:timeline:list", kwargs={"view_id": timeline.id}
    )
    response = api_client.get(
        list_url,
        {"include": "field_options"},
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    response_json = response.json()
    assert response.status_code == HTTP_200_OK
    assert response_json["field_options"][str(text_field.id)]["hidden"] is True


@pytest.mark.django_db
def test_patch_timeline_view_field_options_order_persists(api_client, data_fixture):
    """
    AC #5 — the per-field card-face `order` persists through the shared
    field_options PATCH endpoint and is reflected when listing with field_options.
    """

    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    first_field = data_fixture.create_text_field(table=table, order=0, name="Color")
    second_field = data_fixture.create_text_field(table=table, order=1, name="Notes")
    timeline = data_fixture.create_timeline_view(table=table)

    field_options_url = reverse(
        "api:database:views:field_options", kwargs={"view_id": timeline.id}
    )
    response = api_client.patch(
        field_options_url,
        {
            "field_options": {
                first_field.id: {"order": 2},
                second_field.id: {"order": 1},
            }
        },
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    assert response.status_code == HTTP_200_OK
    options = response.json()["field_options"]
    assert options[str(first_field.id)]["order"] == 2
    assert options[str(second_field.id)]["order"] == 1

    # A follow-up list including field_options reflects the persisted order.
    list_url = reverse(
        "api:database:views:timeline:list", kwargs={"view_id": timeline.id}
    )
    response = api_client.get(
        list_url,
        {"include": "field_options"},
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    response_json = response.json()
    assert response.status_code == HTTP_200_OK
    assert response_json["field_options"][str(first_field.id)]["order"] == 2
    assert response_json["field_options"][str(second_field.id)]["order"] == 1
