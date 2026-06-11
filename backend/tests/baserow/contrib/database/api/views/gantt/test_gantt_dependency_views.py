from django.shortcuts import reverse

import pytest
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)

from baserow.contrib.database.views.gantt.models import TaskDependency


def _make_rows(table, count):
    model = table.get_model()
    return [model.objects.create().id for _ in range(count)]


@pytest.mark.django_db
def test_create_and_list_dependency_survives_reload(api_client, data_fixture):
    """AC #1 — a created edge persists and is returned by a fresh GET (reload)."""

    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    gantt = data_fixture.create_gantt_view(table=table)
    a, b = _make_rows(table, 2)

    create_url = reverse(
        "api:database:views:gantt:dependencies", kwargs={"view_id": gantt.id}
    )
    response = api_client.post(
        create_url,
        {"predecessor_row_id": a, "successor_row_id": b},
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    assert response.status_code == HTTP_200_OK
    created = response.json()
    assert created["predecessor_row_id"] == a
    assert created["successor_row_id"] == b
    assert created["dependency_type"] == "FS"

    # A fresh GET (reload proof) returns the persisted edge.
    response = api_client.get(create_url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})
    assert response.status_code == HTTP_200_OK
    body = response.json()
    listed = body["dependencies"]
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]


@pytest.mark.django_db
def test_create_dependency_cycle_rejected(api_client, data_fixture):
    """AC #2 — an edge that would close a cycle is rejected with a clear error."""

    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    gantt = data_fixture.create_gantt_view(table=table)
    a, b, c = _make_rows(table, 3)

    url = reverse("api:database:views:gantt:dependencies", kwargs={"view_id": gantt.id})
    for predecessor, successor in [(a, b), (b, c)]:
        response = api_client.post(
            url,
            {"predecessor_row_id": predecessor, "successor_row_id": successor},
            format="json",
            **{"HTTP_AUTHORIZATION": f"JWT {token}"},
        )
        assert response.status_code == HTTP_200_OK

    # c -> a closes the cycle a -> b -> c -> a.
    response = api_client.post(
        url,
        {"predecessor_row_id": c, "successor_row_id": a},
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_TASK_DEPENDENCY_CYCLE"
    assert TaskDependency.objects.filter(table=table).count() == 2


@pytest.mark.django_db
def test_create_duplicate_dependency_rejected(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    gantt = data_fixture.create_gantt_view(table=table)
    a, b = _make_rows(table, 2)

    url = reverse("api:database:views:gantt:dependencies", kwargs={"view_id": gantt.id})
    payload = {"predecessor_row_id": a, "successor_row_id": b}
    assert (
        api_client.post(
            url, payload, format="json", **{"HTTP_AUTHORIZATION": f"JWT {token}"}
        ).status_code
        == HTTP_200_OK
    )
    response = api_client.post(
        url, payload, format="json", **{"HTTP_AUTHORIZATION": f"JWT {token}"}
    )
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_TASK_DEPENDENCY_ALREADY_EXISTS"


@pytest.mark.django_db
def test_delete_dependency(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    gantt = data_fixture.create_gantt_view(table=table)
    a, b = _make_rows(table, 2)
    dependency = data_fixture.create_task_dependency(table, a, b)

    url = reverse(
        "api:database:views:gantt:dependency",
        kwargs={"view_id": gantt.id, "dependency_id": dependency.id},
    )
    response = api_client.delete(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})
    assert response.status_code == HTTP_204_NO_CONTENT
    assert TaskDependency.objects.filter(table=table).count() == 0


@pytest.mark.django_db
def test_delete_missing_dependency_404(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    gantt = data_fixture.create_gantt_view(table=table)

    url = reverse(
        "api:database:views:gantt:dependency",
        kwargs={"view_id": gantt.id, "dependency_id": 999999},
    )
    response = api_client.delete(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})
    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json()["error"] == "ERROR_TASK_DEPENDENCY_DOES_NOT_EXIST"


@pytest.mark.django_db
def test_dependencies_permission_denied_for_non_member(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    other_user = data_fixture.create_user()
    other_table = data_fixture.create_database_table(user=other_user)
    gantt = data_fixture.create_gantt_view(table=other_table)

    url = reverse("api:database:views:gantt:dependencies", kwargs={"view_id": gantt.id})
    response = api_client.get(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_USER_NOT_IN_GROUP"


# ---------------------------------------------------------------------------
# CPM response shape tests (Story 3.11 / FR-11)
# ---------------------------------------------------------------------------

from datetime import date


def _row_with_dates(table, start_field, end_field, start, end):
    model = table.get_model()
    return model.objects.create(
        **{f"field_{start_field.id}": start, f"field_{end_field.id}": end}
    ).id


@pytest.mark.django_db
def test_list_dependencies_includes_cpm_keys(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    gantt = data_fixture.create_gantt_view(table=table)
    url = reverse("api:database:views:gantt:dependencies", kwargs={"view_id": gantt.id})

    response = api_client.get(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})

    assert response.status_code == HTTP_200_OK
    body = response.json()
    assert "cpm" in body
    assert "critical_task_ids" in body["cpm"]
    assert "conflict_task_ids" in body["cpm"]


@pytest.mark.django_db
def test_list_dependencies_cpm_correct_values(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    start_field = data_fixture.create_date_field(table=table, name="Start")
    end_field = data_fixture.create_date_field(table=table, name="End")
    gantt = data_fixture.create_gantt_view(
        table=table, start_date_field=start_field, end_date_field=end_field
    )
    a = _row_with_dates(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    b = _row_with_dates(table, start_field, end_field, date(2026, 1, 5), date(2026, 1, 10))
    data_fixture.create_task_dependency(table, a, b)
    url = reverse("api:database:views:gantt:dependencies", kwargs={"view_id": gantt.id})

    response = api_client.get(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})

    assert response.status_code == HTTP_200_OK
    cpm = response.json()["cpm"]
    assert set(cpm["critical_task_ids"]) == {a, b}
    assert cpm["conflict_task_ids"] == []


@pytest.mark.django_db
def test_list_dependencies_cpm_empty_when_no_date_fields(api_client, data_fixture):
    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    # Gantt view without start/end date fields configured.
    gantt = data_fixture.create_gantt_view(table=table)
    url = reverse("api:database:views:gantt:dependencies", kwargs={"view_id": gantt.id})

    response = api_client.get(url, **{"HTTP_AUTHORIZATION": f"JWT {token}"})

    assert response.status_code == HTTP_200_OK
    cpm = response.json()["cpm"]
    assert cpm["critical_task_ids"] == []
    assert cpm["conflict_task_ids"] == []
