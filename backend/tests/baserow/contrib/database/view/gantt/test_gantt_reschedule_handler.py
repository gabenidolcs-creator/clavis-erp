from datetime import date

import pytest

from baserow.contrib.database.action.scopes import TableActionScopeType
from baserow.contrib.database.rows.actions import UpdateRowsActionType
from baserow.contrib.database.views.gantt.handler import TaskDependencyHandler
from baserow.contrib.database.views.gantt.models import TaskDependency
from baserow.core.action.handler import ActionHandler


def _setup(data_fixture, date_include_time=False, session_id="session-id"):
    """A table + a start/end date field + a gantt view wired to both."""

    user = data_fixture.create_user(session_id=session_id)
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
    return user, table, start_field, end_field, gantt


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


def _by_id(plan):
    return {item["id"]: item for item in plan.rows_values}


@pytest.mark.django_db
def test_compute_cascade_single_edge_shifts_successor_preserving_duration(
    data_fixture,
):
    """AC #1/#2 — a→b: moving a past b.start shifts b so b.start == a.new_end."""

    user, table, start_field, end_field, gantt = _setup(data_fixture)
    a = _row(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    b = _row(table, start_field, end_field, date(2026, 1, 6), date(2026, 1, 10))
    data_fixture.create_task_dependency(table, a, b)

    handler = TaskDependencyHandler()
    plan = handler.compute_cascade(
        table, start_field, end_field, a, date(2026, 1, 6), date(2026, 1, 10)
    )

    assert plan.cascade_count == 1
    assert plan.affected_successor_ids == [b]
    rows = _by_id(plan)
    # b's start lands exactly on a's new end; its 4-day duration is preserved.
    assert rows[b][f"field_{start_field.id}"] == "2026-01-10"
    assert rows[b][f"field_{end_field.id}"] == "2026-01-14"
    # compute_cascade is read-only: the DB is untouched.
    assert _dates(table, start_field, end_field, b) == (
        date(2026, 1, 6),
        date(2026, 1, 10),
    )


@pytest.mark.django_db
def test_compute_cascade_no_violation_does_not_shift(data_fixture):
    """AC #1 — a move that keeps successor.start >= new end yields no shift."""

    user, table, start_field, end_field, gantt = _setup(data_fixture)
    a = _row(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    b = _row(table, start_field, end_field, date(2026, 1, 6), date(2026, 1, 10))
    data_fixture.create_task_dependency(table, a, b)

    plan = TaskDependencyHandler().compute_cascade(
        table, start_field, end_field, a, date(2026, 1, 1), date(2026, 1, 5)
    )

    assert plan.cascade_count == 0
    assert plan.affected == []


@pytest.mark.django_db
def test_compute_cascade_transitive_chain(data_fixture):
    """AC #1/#2 — a→b→c→d cascades to all three; count == 3 before any write."""

    user, table, start_field, end_field, gantt = _setup(data_fixture)
    a = _row(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    b = _row(table, start_field, end_field, date(2026, 1, 6), date(2026, 1, 8))
    c = _row(table, start_field, end_field, date(2026, 1, 9), date(2026, 1, 12))
    d = _row(table, start_field, end_field, date(2026, 1, 13), date(2026, 1, 14))
    for predecessor, successor in [(a, b), (b, c), (c, d)]:
        data_fixture.create_task_dependency(table, predecessor, successor)

    plan = TaskDependencyHandler().compute_cascade(
        table, start_field, end_field, a, date(2026, 1, 6), date(2026, 1, 10)
    )

    assert plan.cascade_count == 3
    assert set(plan.affected_successor_ids) == {b, c, d}
    rows = _by_id(plan)
    # b: start Jan6 < Jan10 -> delta 4 -> Jan10..Jan12 (dur 2 preserved).
    assert rows[b][f"field_{start_field.id}"] == "2026-01-10"
    assert rows[b][f"field_{end_field.id}"] == "2026-01-12"
    # c: start Jan9 < b.new_end Jan12 -> delta 3 -> Jan12..Jan15 (dur 3).
    assert rows[c][f"field_{start_field.id}"] == "2026-01-12"
    assert rows[c][f"field_{end_field.id}"] == "2026-01-15"
    # d: start Jan13 < c.new_end Jan15 -> delta 2 -> Jan15..Jan16 (dur 1).
    assert rows[d][f"field_{start_field.id}"] == "2026-01-15"
    assert rows[d][f"field_{end_field.id}"] == "2026-01-16"


@pytest.mark.django_db
def test_compute_cascade_diamond_shifted_once_by_max_delta(data_fixture):
    """AC #1 — diamond a→b,a→c,b→d,c→d: d shifts ONCE by the MAX delta."""

    user, table, start_field, end_field, gantt = _setup(data_fixture)
    a = _row(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    b = _row(table, start_field, end_field, date(2026, 1, 6), date(2026, 1, 8))
    c = _row(table, start_field, end_field, date(2026, 1, 6), date(2026, 1, 20))
    d = _row(table, start_field, end_field, date(2026, 1, 9), date(2026, 1, 10))
    for predecessor, successor in [(a, b), (a, c), (b, d), (c, d)]:
        data_fixture.create_task_dependency(table, predecessor, successor)

    plan = TaskDependencyHandler().compute_cascade(
        table, start_field, end_field, a, date(2026, 1, 6), date(2026, 1, 10)
    )

    rows = plan.rows_values
    # d appears exactly once (no double-count).
    d_entries = [r for r in rows if r["id"] == d]
    assert len(d_entries) == 1
    # The c→d path needs delta 15 (c.new_end Jan24); the b→d path only 3. d
    # must move by the MAX: start Jan9 + 15 = Jan24 == c.new_end, dur 1 kept.
    by_id = _by_id(plan)
    assert by_id[c][f"field_{end_field.id}"] == "2026-01-24"
    assert by_id[d][f"field_{start_field.id}"] == "2026-01-24"
    assert by_id[d][f"field_{end_field.id}"] == "2026-01-25"
    assert plan.cascade_count == 3


@pytest.mark.django_db
def test_compute_cascade_preserves_time_of_day_for_datetime_fields(data_fixture):
    """AC #2 — a datetime field keeps HH:mm when shifted by whole days."""

    from datetime import datetime, timezone

    user, table, start_field, end_field, gantt = _setup(
        data_fixture, date_include_time=True
    )
    a = _row(
        table,
        start_field,
        end_field,
        datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 5, 17, 0, tzinfo=timezone.utc),
    )
    b = _row(
        table,
        start_field,
        end_field,
        datetime(2026, 1, 6, 8, 30, tzinfo=timezone.utc),
        datetime(2026, 1, 8, 12, 0, tzinfo=timezone.utc),
    )
    data_fixture.create_task_dependency(table, a, b)

    plan = TaskDependencyHandler().compute_cascade(
        table,
        start_field,
        end_field,
        a,
        datetime(2026, 1, 6, 9, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 10, 17, 0, tzinfo=timezone.utc),
    )

    rows = _by_id(plan)
    # FS with datetime fields: b must START exactly when a now ends (Jan10
    # 17:00) — minute-precise, not a whole-day rounding — and its 2d3h30m
    # duration is preserved, so b ends Jan12 20:30.
    assert rows[b][f"field_{start_field.id}"] == "2026-01-10T17:00:00+00:00"
    assert rows[b][f"field_{end_field.id}"] == "2026-01-12T20:30:00+00:00"


@pytest.mark.django_db
@pytest.mark.undo_redo
def test_apply_cascade_is_single_undoable_step(data_fixture):
    """AC #2 — apply commits one undoable action; undo reverts all rows together."""

    session_id = "session-id"
    user, table, start_field, end_field, gantt = _setup(
        data_fixture, session_id=session_id
    )
    a = _row(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    b = _row(table, start_field, end_field, date(2026, 1, 6), date(2026, 1, 8))
    c = _row(table, start_field, end_field, date(2026, 1, 9), date(2026, 1, 12))
    for predecessor, successor in [(a, b), (b, c)]:
        data_fixture.create_task_dependency(table, predecessor, successor)

    handler = TaskDependencyHandler()
    handler.apply_cascade(
        user, table, gantt, start_field, end_field, a, date(2026, 1, 6),
        date(2026, 1, 10),
    )

    # Predecessor + both successors are shifted.
    assert _dates(table, start_field, end_field, a) == (
        date(2026, 1, 6),
        date(2026, 1, 10),
    )
    assert _dates(table, start_field, end_field, b) == (
        date(2026, 1, 10),
        date(2026, 1, 12),
    )
    assert _dates(table, start_field, end_field, c)[0] == date(2026, 1, 12)

    # A SINGLE undo reverts the predecessor AND every successor together.
    ActionHandler.undo(
        user, [TableActionScopeType.value(table_id=table.id)], session_id
    )
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
def test_apply_cascade_recomputes_under_lock_not_stale_plan(data_fixture):
    """AC #4 — apply recomputes from FRESH row values, not a stale preview."""

    user, table, start_field, end_field, gantt = _setup(data_fixture)
    a = _row(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    b = _row(table, start_field, end_field, date(2026, 1, 6), date(2026, 1, 8))
    data_fixture.create_task_dependency(table, a, b)

    handler = TaskDependencyHandler()
    # A preview computed when b started Jan6 WOULD shift b (b.start < Jan10).
    preview = handler.compute_cascade(
        table, start_field, end_field, a, date(2026, 1, 6), date(2026, 1, 10)
    )
    assert preview.cascade_count == 1

    # A concurrent edit moves b far into the future before apply runs.
    model = table.get_model()
    moved = model.objects.get(id=b)
    setattr(moved, f"field_{start_field.id}", date(2026, 2, 1))
    setattr(moved, f"field_{end_field.id}", date(2026, 2, 3))
    moved.save()

    # apply recomputes under the lock: b is no longer violated, so it is NOT
    # shifted (the stale plan is discarded).
    handler.apply_cascade(
        user, table, gantt, start_field, end_field, a, date(2026, 1, 6),
        date(2026, 1, 10),
    )
    assert _dates(table, start_field, end_field, b) == (
        date(2026, 2, 1),
        date(2026, 2, 3),
    )


@pytest.mark.django_db
def test_find_violations_derived(data_fixture):
    """AC #3 — violated iff successor.start < predecessor.end; FS-only."""

    user, table, start_field, end_field, gantt = _setup(data_fixture)
    # Violated FS edge: b starts before a ends.
    a = _row(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 10))
    b = _row(table, start_field, end_field, date(2026, 1, 5), date(2026, 1, 8))
    # Healthy FS edge: d starts after c ends.
    c = _row(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 3))
    d = _row(table, start_field, end_field, date(2026, 1, 5), date(2026, 1, 6))
    # Violated, but NON-FS edge -> must be ignored by the cascade view.
    e = _row(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 10))
    f = _row(table, start_field, end_field, date(2026, 1, 5), date(2026, 1, 6))
    data_fixture.create_task_dependency(table, a, b)
    data_fixture.create_task_dependency(table, c, d)
    data_fixture.create_task_dependency(table, e, f, dependency_type="SS")

    violations = TaskDependencyHandler().find_violations(
        table, start_field, end_field
    )

    assert (a, b) in violations
    assert (c, d) not in violations
    assert (e, f) not in violations


@pytest.mark.django_db
def test_decline_path_keeps_edge_and_reads_violated(data_fixture):
    """AC #3 — declining keeps the predecessor move; the edge is not deleted and
    reads as violated (derived), never silently broken."""

    user, table, start_field, end_field, gantt = _setup(data_fixture)
    a = _row(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    b = _row(table, start_field, end_field, date(2026, 1, 6), date(2026, 1, 10))
    dependency = data_fixture.create_task_dependency(table, a, b)

    handler = TaskDependencyHandler()
    assert handler.find_violations(table, start_field, end_field) == []

    # Decline = predecessor-only move past the successor's start (no cascade).
    UpdateRowsActionType.do(
        user,
        table,
        [
            {
                "id": a,
                f"field_{start_field.id}": "2026-01-06",
                f"field_{end_field.id}": "2026-01-12",
            }
        ],
    )

    # The edge still exists and now reads as violated — not deleted.
    assert TaskDependency.objects.filter(id=dependency.id).exists()
    assert (a, b) in handler.find_violations(table, start_field, end_field)
