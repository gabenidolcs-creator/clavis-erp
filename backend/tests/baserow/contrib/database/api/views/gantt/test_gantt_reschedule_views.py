from datetime import date

from django.shortcuts import reverse

import pytest
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
)

from baserow.contrib.database.fields.models import FieldPermission
from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.roles import ADMIN, EDITOR


def _setup(data_fixture, user, date_include_time=False):
    """A table with start/end date fields wired to a gantt view."""

    table = data_fixture.create_database_table(user=user)
    start_field = data_fixture.create_date_field(
        table=table, date_include_time=date_include_time, name="Start"
    )
    end_field = data_fixture.create_date_field(
        table=table, date_include_time=date_include_time, name="End"
    )
    gantt = data_fixture.create_gantt_view(
        table=table, start_date_field=start_field, end_date_field=end_field
    )
    return table, start_field, end_field, gantt


def _row(table, start_field, end_field, start, end):
    model = table.get_model()
    return model.objects.create(
        **{f"field_{start_field.id}": start, f"field_{end_field.id}": end}
    ).id


def _dates(table, start_field, end_field, row_id):
    model = table.get_model()
    row = model.objects.get(id=row_id)
    return (
        getattr(row, f"field_{start_field.id}"),
        getattr(row, f"field_{end_field.id}"),
    )


@pytest.mark.django_db
def test_preview_returns_affected_and_count_without_writing(api_client, data_fixture):
    """AC #1 — POST preview reports the cascade but writes nothing to the DB."""

    user, token = data_fixture.create_user_and_token()
    table, start_field, end_field, gantt = _setup(data_fixture, user)
    a = _row(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    b = _row(table, start_field, end_field, date(2026, 1, 6), date(2026, 1, 8))
    c = _row(table, start_field, end_field, date(2026, 1, 9), date(2026, 1, 12))
    for predecessor, successor in [(a, b), (b, c)]:
        data_fixture.create_task_dependency(table, predecessor, successor)

    url = reverse(
        "api:database:views:gantt:reschedule_preview", kwargs={"view_id": gantt.id}
    )
    response = api_client.post(
        url,
        {
            "predecessor_row_id": a,
            "new_start": "2026-01-06",
            "new_end": "2026-01-10",
        },
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    assert response.status_code == HTTP_200_OK
    body = response.json()
    assert body["cascade_count"] == 2
    affected_ids = {item["row_id"] for item in body["affected_successors"]}
    assert affected_ids == {b, c}

    # Preview is read-only: every row keeps its original dates.
    assert _dates(table, start_field, end_field, a) == (
        date(2026, 1, 1),
        date(2026, 1, 5),
    )
    assert _dates(table, start_field, end_field, b) == (
        date(2026, 1, 6),
        date(2026, 1, 8),
    )
    assert _dates(table, start_field, end_field, c) == (
        date(2026, 1, 9),
        date(2026, 1, 12),
    )


@pytest.mark.django_db
def test_apply_shifts_chain_and_survives_reload(api_client, data_fixture):
    """AC #2 — POST apply moves the predecessor + every transitive successor."""

    user, token = data_fixture.create_user_and_token()
    table, start_field, end_field, gantt = _setup(data_fixture, user)
    a = _row(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    b = _row(table, start_field, end_field, date(2026, 1, 6), date(2026, 1, 8))
    c = _row(table, start_field, end_field, date(2026, 1, 9), date(2026, 1, 12))
    for predecessor, successor in [(a, b), (b, c)]:
        data_fixture.create_task_dependency(table, predecessor, successor)

    url = reverse(
        "api:database:views:gantt:reschedule_apply", kwargs={"view_id": gantt.id}
    )
    response = api_client.post(
        url,
        {
            "predecessor_row_id": a,
            "new_start": "2026-01-06",
            "new_end": "2026-01-10",
        },
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    assert response.status_code == HTTP_200_OK
    assert response.json()["cascade_count"] == 2

    # Reload from the DB: predecessor + chain are committed.
    assert _dates(table, start_field, end_field, a) == (
        date(2026, 1, 6),
        date(2026, 1, 10),
    )
    assert _dates(table, start_field, end_field, b) == (
        date(2026, 1, 10),
        date(2026, 1, 12),
    )
    assert _dates(table, start_field, end_field, c)[0] == date(2026, 1, 12)


@pytest.mark.django_db
def test_apply_missing_predecessor_row_errors(api_client, data_fixture):
    """A predecessor_row_id that does not exist is rejected, not silently shifted."""

    user, token = data_fixture.create_user_and_token()
    table, start_field, end_field, gantt = _setup(data_fixture, user)

    url = reverse(
        "api:database:views:gantt:reschedule_apply", kwargs={"view_id": gantt.id}
    )
    response = api_client.post(
        url,
        {
            "predecessor_row_id": 999999,
            "new_start": "2026-01-06",
            "new_end": "2026-01-10",
        },
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    assert response.status_code == HTTP_404_NOT_FOUND
    assert response.json()["error"] == "ERROR_ROW_DOES_NOT_EXIST"


@pytest.mark.django_db
def test_apply_not_configured_for_reschedule_errors(api_client, data_fixture):
    """A gantt view with no date fields cannot compute a cascade."""

    user, token = data_fixture.create_user_and_token()
    table = data_fixture.create_database_table(user=user)
    gantt = data_fixture.create_gantt_view(table=table)
    a = table.get_model().objects.create().id

    url = reverse(
        "api:database:views:gantt:reschedule_apply", kwargs={"view_id": gantt.id}
    )
    response = api_client.post(
        url,
        {"predecessor_row_id": a, "new_start": None, "new_end": None},
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "ERROR_GANTT_NOT_CONFIGURED_FOR_RESCHEDULE"


@pytest.mark.django_db
def test_apply_field_edit_prohibited_returns_403(api_client, data_fixture):
    """A member who may not edit the date field gets 403, not a silent shift."""

    owner = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=owner)
    RbacHandler().assign_role(owner, workspace, ADMIN)
    member = data_fixture.create_user()
    data_fixture.create_user_workspace(
        workspace=workspace, user=member, permissions="MEMBER"
    )
    # The field-permission manager decides by the user's effective RBAC tier, so the
    # member needs a real below-ADMIN role assignment for the threshold to bite.
    RbacHandler().assign_role(member, workspace, EDITOR)
    database = data_fixture.create_database_application(user=owner, workspace=workspace)
    table = data_fixture.create_database_table(user=owner, database=database)
    start_field = data_fixture.create_date_field(table=table, name="Start")
    end_field = data_fixture.create_date_field(table=table, name="End")
    gantt = data_fixture.create_gantt_view(
        table=table, start_date_field=start_field, end_date_field=end_field
    )
    a = _row(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    b = _row(table, start_field, end_field, date(2026, 1, 6), date(2026, 1, 8))
    data_fixture.create_task_dependency(table, a, b)

    # Only an Admin may edit the start date field; the member is below that.
    FieldPermission.objects.create(field=start_field, editable_by_role=ADMIN)

    token = data_fixture.generate_token(member)
    url = reverse(
        "api:database:views:gantt:reschedule_apply", kwargs={"view_id": gantt.id}
    )
    response = api_client.post(
        url,
        {
            "predecessor_row_id": a,
            "new_start": "2026-01-06",
            "new_end": "2026-01-10",
        },
        format="json",
        **{"HTTP_AUTHORIZATION": f"JWT {token}"},
    )
    assert response.status_code == HTTP_403_FORBIDDEN
    assert response.json()["error"] == "ERROR_FIELD_EDIT_PROHIBITED"
    # The cascade did NOT partially apply: rows keep their original dates.
    assert _dates(table, start_field, end_field, b) == (
        date(2026, 1, 6),
        date(2026, 1, 8),
    )
