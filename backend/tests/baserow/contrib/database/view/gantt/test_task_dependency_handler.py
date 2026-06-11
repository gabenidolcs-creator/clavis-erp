import pytest

from baserow.contrib.database.views.gantt.exceptions import (
    InvalidTaskDependencyType,
    TaskDependencyAlreadyExists,
    TaskDependencyCycle,
    TaskDependencyRowDoesNotExist,
)
from baserow.contrib.database.views.gantt.handler import TaskDependencyHandler
from baserow.contrib.database.views.gantt.models import TaskDependency


def _make_rows(data_fixture, table, count):
    """Create ``count`` empty rows and return their ids in order."""

    model = table.get_model()
    return [model.objects.create().id for _ in range(count)]


@pytest.mark.django_db
def test_create_dependency_persists_and_is_unique(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    a, b = _make_rows(data_fixture, table, 2)

    handler = TaskDependencyHandler()
    dependency = handler.create_dependency(user, table, a, b)

    assert dependency.pk is not None
    assert dependency.predecessor_row_id == a
    assert dependency.successor_row_id == b
    assert dependency.dependency_type == "FS"
    assert TaskDependency.objects.filter(table=table).count() == 1

    # Re-drawing the same edge is idempotent at the API level: a 400, not a dup.
    with pytest.raises(TaskDependencyAlreadyExists):
        handler.create_dependency(user, table, a, b)
    assert TaskDependency.objects.filter(table=table).count() == 1


@pytest.mark.django_db
def test_create_dependency_rejects_self_loop(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    (a,) = _make_rows(data_fixture, table, 1)

    handler = TaskDependencyHandler()
    with pytest.raises(TaskDependencyCycle):
        handler.create_dependency(user, table, a, a)
    assert TaskDependency.objects.filter(table=table).count() == 0


@pytest.mark.django_db
def test_create_dependency_rejects_direct_cycle(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    a, b, c = _make_rows(data_fixture, table, 3)

    handler = TaskDependencyHandler()
    handler.create_dependency(user, table, a, b)
    handler.create_dependency(user, table, b, c)

    # c -> a would close the cycle a -> b -> c -> a.
    with pytest.raises(TaskDependencyCycle):
        handler.create_dependency(user, table, c, a)
    assert TaskDependency.objects.filter(table=table).count() == 2


@pytest.mark.django_db
def test_create_dependency_rejects_long_chain_cycle(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    a, b, c, d = _make_rows(data_fixture, table, 4)

    handler = TaskDependencyHandler()
    handler.create_dependency(user, table, a, b)
    handler.create_dependency(user, table, b, c)
    handler.create_dependency(user, table, c, d)

    with pytest.raises(TaskDependencyCycle):
        handler.create_dependency(user, table, d, a)


@pytest.mark.django_db
def test_create_dependency_missing_row_rejected(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    (a,) = _make_rows(data_fixture, table, 1)

    handler = TaskDependencyHandler()
    with pytest.raises(TaskDependencyRowDoesNotExist):
        handler.create_dependency(user, table, a, 999999)
    with pytest.raises(TaskDependencyRowDoesNotExist):
        handler.create_dependency(user, table, 888888, a)


@pytest.mark.django_db
def test_create_dependency_rejects_non_fs_type(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    a, b = _make_rows(data_fixture, table, 2)

    handler = TaskDependencyHandler()
    with pytest.raises(InvalidTaskDependencyType):
        handler.create_dependency(user, table, a, b, dependency_type="SS")
    assert TaskDependency.objects.filter(table=table).count() == 0


@pytest.mark.django_db
def test_delete_dependency(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    a, b = _make_rows(data_fixture, table, 2)

    handler = TaskDependencyHandler()
    dependency = handler.create_dependency(user, table, a, b)
    handler.delete_dependency(user, dependency)

    assert TaskDependency.objects.filter(table=table).count() == 0


@pytest.mark.django_db
def test_list_dependencies(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    a, b, c = _make_rows(data_fixture, table, 3)

    handler = TaskDependencyHandler()
    handler.create_dependency(user, table, a, b)
    handler.create_dependency(user, table, b, c)

    edges = handler.list_dependencies(user, table)
    assert len(edges) == 2


@pytest.mark.django_db
def test_permanent_row_delete_removes_edges_both_sides(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    a, b, c = _make_rows(data_fixture, table, 3)

    handler = TaskDependencyHandler()
    handler.create_dependency(user, table, a, b)  # b as successor
    handler.create_dependency(user, table, b, c)  # b as predecessor

    handler.delete_dependencies_for_row(table.id, b)

    # Both edges touching b are gone; no edge references b any more.
    assert (
        TaskDependency.objects.filter(table=table).filter(predecessor_row_id=b).count()
        == 0
    )
    assert (
        TaskDependency.objects.filter(table=table).filter(successor_row_id=b).count()
        == 0
    )
    assert TaskDependency.objects.filter(table=table).count() == 0


@pytest.mark.django_db
def test_revalidate_on_restore_drops_cyclic_edge(data_fixture):
    """
    AR-8 teeth: if the graph became cyclic while a row was trashed, restoring it
    must not silently materialize the cycle. The revalidate hook drops the
    offending edge touching the restored row.
    """

    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    a, b, c = _make_rows(data_fixture, table, 3)

    # Inject a cyclic graph directly (as a corrupt/import path could), with the
    # cycle running through row b: a -> b -> c -> a.
    data_fixture.create_task_dependency(table, a, b)
    data_fixture.create_task_dependency(table, b, c)
    data_fixture.create_task_dependency(table, c, a)

    handler = TaskDependencyHandler()
    dropped = handler.revalidate_on_rows_restored(table, [b])

    assert len(dropped) >= 1
    # After dropping, the remaining graph is acyclic.
    remaining = list(
        TaskDependency.objects.filter(table=table).values_list(
            "predecessor_row_id", "successor_row_id"
        )
    )
    from baserow.contrib.database.views.gantt.handler import _graph_has_cycle

    assert _graph_has_cycle(remaining) is False
    # The edge that was dropped touches the restored row b.
    for edge in dropped:
        assert b in (edge.predecessor_row_id, edge.successor_row_id)


@pytest.mark.django_db
def test_revalidate_on_restore_noop_when_acyclic(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    a, b, c = _make_rows(data_fixture, table, 3)

    handler = TaskDependencyHandler()
    handler.create_dependency(user, table, a, b)
    handler.create_dependency(user, table, b, c)

    dropped = handler.revalidate_on_rows_restored(table, [b])
    assert dropped == []
    assert TaskDependency.objects.filter(table=table).count() == 2


@pytest.mark.django_db
def test_import_serialized_rejects_cycle(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    a, b, c = _make_rows(data_fixture, table, 3)

    handler = TaskDependencyHandler()
    cyclic = [
        {"predecessor_row_id": a, "successor_row_id": b, "dependency_type": "FS"},
        {"predecessor_row_id": b, "successor_row_id": c, "dependency_type": "FS"},
        {"predecessor_row_id": c, "successor_row_id": a, "dependency_type": "FS"},
    ]
    with pytest.raises(TaskDependencyCycle):
        handler.import_serialized(table, cyclic)
    assert TaskDependency.objects.filter(table=table).count() == 0


@pytest.mark.django_db
def test_export_import_round_trip_acyclic(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    a, b, c = _make_rows(data_fixture, table, 3)

    handler = TaskDependencyHandler()
    handler.create_dependency(user, table, a, b)
    handler.create_dependency(user, table, b, c)

    serialized = handler.export_serialized(table)
    assert len(serialized) == 2

    # Import the same edge set into a fresh table; ids are preserved on import,
    # so an identity remap round-trips. import_serialized validates acyclicity of
    # the batch (row existence is the caller/import-flow's concern).
    target = data_fixture.create_database_table(user=user)
    imported = handler.import_serialized(target, serialized)
    assert len(imported) == 2
    assert TaskDependency.objects.filter(table=target).count() == 2


# ---------------------------------------------------------------------------
# CPM tests (Story 3.11 / FR-11)
# ---------------------------------------------------------------------------

from datetime import date


def _setup_cpm(data_fixture):
    """Table + start/end date fields + gantt view wired to both."""
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    start_field = data_fixture.create_date_field(table=table, name="Start")
    end_field = data_fixture.create_date_field(table=table, name="End")
    data_fixture.create_gantt_view(
        table=table, start_date_field=start_field, end_date_field=end_field
    )
    return table, start_field, end_field


def _row_with_dates(table, start_field, end_field, start, end):
    model = table.get_model()
    return model.objects.create(
        **{f"field_{start_field.id}": start, f"field_{end_field.id}": end}
    ).id


@pytest.mark.django_db
def test_cpm_no_edges_returns_empty_result(data_fixture):
    table, start_field, end_field = _setup_cpm(data_fixture)
    _row_with_dates(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    _row_with_dates(table, start_field, end_field, date(2026, 1, 6), date(2026, 1, 10))

    result = TaskDependencyHandler().compute_cpm(table, start_field, end_field)

    assert result.critical_task_ids == []
    assert result.conflict_task_ids == []


@pytest.mark.django_db
def test_cpm_linear_chain_critical_path(data_fixture):
    table, start_field, end_field = _setup_cpm(data_fixture)
    # A=5d, B=5d, C=5d — perfectly aligned, zero slack.
    a = _row_with_dates(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    b = _row_with_dates(table, start_field, end_field, date(2026, 1, 5), date(2026, 1, 10))
    c = _row_with_dates(table, start_field, end_field, date(2026, 1, 10), date(2026, 1, 15))
    data_fixture.create_task_dependency(table, a, b)
    data_fixture.create_task_dependency(table, b, c)

    result = TaskDependencyHandler().compute_cpm(table, start_field, end_field)

    assert set(result.critical_task_ids) == {a, b, c}
    assert result.conflict_task_ids == []


@pytest.mark.django_db
def test_cpm_parallel_paths_only_longest_is_critical(data_fixture):
    table, start_field, end_field = _setup_cpm(data_fixture)
    # A(1d) -> C(1d) and A(1d) -> B(3d) -> C(1d)
    # Longest path: A->B->C (1+3+1=5d). A->C path (1+1=2d) has slack.
    a = _row_with_dates(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 2))
    b = _row_with_dates(table, start_field, end_field, date(2026, 1, 2), date(2026, 1, 5))
    c = _row_with_dates(table, start_field, end_field, date(2026, 1, 5), date(2026, 1, 6))
    data_fixture.create_task_dependency(table, a, b)
    data_fixture.create_task_dependency(table, b, c)
    data_fixture.create_task_dependency(table, a, c)

    result = TaskDependencyHandler().compute_cpm(table, start_field, end_field)

    # A, B, C are all on the critical path (longest chain A->B->C has zero float).
    assert set(result.critical_task_ids) == {a, b, c}
    assert result.conflict_task_ids == []


@pytest.mark.django_db
def test_cpm_conflict_detection(data_fixture):
    table, start_field, end_field = _setup_cpm(data_fixture)
    # A ends day 5, B starts day 3 — B starts before A finishes → conflict.
    a = _row_with_dates(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    b = _row_with_dates(table, start_field, end_field, date(2026, 1, 3), date(2026, 1, 8))
    data_fixture.create_task_dependency(table, a, b)

    result = TaskDependencyHandler().compute_cpm(table, start_field, end_field)

    assert b in result.conflict_task_ids
    assert b not in result.critical_task_ids


@pytest.mark.django_db
def test_cpm_isolated_nodes_not_critical(data_fixture):
    table, start_field, end_field = _setup_cpm(data_fixture)
    # Rows a & b are connected (chain), row c has no edges.
    a = _row_with_dates(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    b = _row_with_dates(table, start_field, end_field, date(2026, 1, 5), date(2026, 1, 10))
    c = _row_with_dates(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 3))
    data_fixture.create_task_dependency(table, a, b)

    result = TaskDependencyHandler().compute_cpm(table, start_field, end_field)

    assert c not in result.critical_task_ids
    assert c not in result.conflict_task_ids


@pytest.mark.django_db
def test_cpm_unscheduled_nodes_skipped(data_fixture):
    table, start_field, end_field = _setup_cpm(data_fixture)
    # a is scheduled, b has no dates.
    a = _row_with_dates(table, start_field, end_field, date(2026, 1, 1), date(2026, 1, 5))
    model = table.get_model()
    b = model.objects.create(
        **{f"field_{start_field.id}": None, f"field_{end_field.id}": None}
    ).id
    data_fixture.create_task_dependency(table, a, b)

    result = TaskDependencyHandler().compute_cpm(table, start_field, end_field)

    assert b not in result.critical_task_ids
    assert b not in result.conflict_task_ids
