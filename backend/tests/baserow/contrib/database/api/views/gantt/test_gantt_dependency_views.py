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
    listed = response.json()
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
