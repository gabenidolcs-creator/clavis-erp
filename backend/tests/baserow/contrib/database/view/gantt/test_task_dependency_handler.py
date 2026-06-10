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
