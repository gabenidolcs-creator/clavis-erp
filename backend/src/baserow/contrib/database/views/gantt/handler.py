from typing import Dict, Iterable, List, Optional, Tuple

from django.db import transaction

from baserow.contrib.database.rows.operations import (
    ReadDatabaseRowOperationType,
    UpdateDatabaseRowOperationType,
)
from baserow.contrib.database.table.models import Table
from baserow.core.handler import CoreHandler

from .exceptions import (
    InvalidTaskDependencyType,
    TaskDependencyAlreadyExists,
    TaskDependencyCycle,
    TaskDependencyDoesNotExist,
    TaskDependencyRowDoesNotExist,
)
from .models import TaskDependency
from .signals import task_dependency_created, task_dependency_deleted

# v1 ships finish-to-start only (see model + prd.md:184). Any other value is
# rejected at the handler so the cycle/cascade semantics stay well-defined.
ALLOWED_DEPENDENCY_TYPES = {"FS"}

# A directed edge as a plain ``(predecessor_row_id, successor_row_id)`` tuple. The
# whole cycle layer works on these tuples so the create path and the batch
# (restore / import) paths share ONE verified graph implementation.
Edge = Tuple[int, int]


def _build_adjacency(edges: Iterable[Edge]) -> Dict[int, List[int]]:
    """
    Build a ``predecessor -> [successors]`` adjacency map. Walking this map
    forward from a node follows ``predecessor -> successor`` edges (i.e. moves
    downstream along the schedule).
    """

    adjacency: Dict[int, List[int]] = {}
    for predecessor_row_id, successor_row_id in edges:
        adjacency.setdefault(predecessor_row_id, []).append(successor_row_id)
    return adjacency


def _path_exists(adjacency: Dict[int, List[int]], start: int, target: int) -> bool:
    """
    Bounded in-memory BFS: is ``target`` reachable from ``start`` by following
    ``predecessor -> successor`` edges? The graph is loaded once and walked in
    memory (no query per node) because it is bounded per table.
    """

    if start == target:
        return True
    seen = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for successor in adjacency.get(node, ()):
            if successor == target:
                return True
            if successor not in seen:
                seen.add(successor)
                stack.append(successor)
    return False


def _graph_has_cycle(edges: Iterable[Edge]) -> bool:
    """
    Full-graph cycle scan via Kahn's algorithm (iterative topological sort). If
    fewer nodes than present can be ordered, the leftover nodes sit on a cycle.
    Used by the batch (restore / import) paths; the create path uses the cheaper
    single-edge ``_path_exists`` reachability check. Both are the same graph
    semantics — there is no second copy of the cycle rule.
    """

    edges = list(edges)
    in_degree: Dict[int, int] = {}
    adjacency: Dict[int, List[int]] = {}
    for predecessor_row_id, successor_row_id in edges:
        # A self-loop is a 1-cycle by definition.
        if predecessor_row_id == successor_row_id:
            return True
        adjacency.setdefault(predecessor_row_id, []).append(successor_row_id)
        in_degree.setdefault(predecessor_row_id, 0)
        in_degree[successor_row_id] = in_degree.get(successor_row_id, 0) + 1

    queue = [node for node, degree in in_degree.items() if degree == 0]
    ordered = 0
    while queue:
        node = queue.pop()
        ordered += 1
        for successor in adjacency.get(node, ()):
            in_degree[successor] -= 1
            if in_degree[successor] == 0:
                queue.append(successor)
    return ordered != len(in_degree)


class TaskDependencyHandler:
    """
    All mutation + cycle logic for Gantt ``TaskDependency`` edges (Story 3.9 /
    FR-9). REST views are thin wrappers over this handler (handler-first
    pattern). Cycle prevention runs on EVERY mutation path — create, restore,
    import — through the shared graph routines above (AR-8).
    """

    # -- cycle detection ---------------------------------------------------

    def would_create_cycle(
        self,
        table: Table,
        predecessor_row_id: int,
        successor_row_id: int,
        edges: Optional[List[Edge]] = None,
    ) -> bool:
        """
        Would adding the edge ``predecessor -> successor`` close a cycle?

        A new edge ``p -> s`` closes a cycle iff ``p`` is already reachable from
        ``s`` in the existing graph (a path ``s -> ... -> p`` exists), or ``p ==
        s`` (self-loop). ``edges`` may be supplied by a caller that has already
        loaded (and locked) the table's edge set, to avoid a second query.
        """

        if predecessor_row_id == successor_row_id:
            return True
        if edges is None:
            edges = self._load_edges(table)
        adjacency = _build_adjacency(edges)
        # Reachable from the successor back to the predecessor => cycle.
        return _path_exists(adjacency, successor_row_id, predecessor_row_id)

    def validate_acyclic(self, table: Table, candidate_edges: List[Edge]) -> None:
        """
        Batch guard for the restore / import paths: raise ``TaskDependencyCycle``
        if the supplied complete edge set contains any cycle. One routine backs
        every non-interactive path.
        """

        if _graph_has_cycle(candidate_edges):
            raise TaskDependencyCycle(
                "The dependency edge set contains a cycle and cannot be applied."
            )

    def _load_edges(self, table: Table) -> List[Edge]:
        return list(
            TaskDependency.objects.filter(table=table).values_list(
                "predecessor_row_id", "successor_row_id"
            )
        )

    # -- create / delete / list -------------------------------------------

    def create_dependency(
        self,
        user,
        table: Table,
        predecessor_row_id: int,
        successor_row_id: int,
        dependency_type: str = "FS",
    ) -> TaskDependency:
        """
        Create a single ``predecessor -> successor`` edge after enforcing: FS-only
        type, both rows exist, uniqueness, and acyclicity. The graph read +
        insert run under a table-scoped lock so two concurrent creates cannot
        each pass the cycle check and then jointly close a cycle (TOCTOU).
        """

        workspace = table.database.workspace
        CoreHandler().check_permissions(
            user,
            UpdateDatabaseRowOperationType.type,
            workspace=workspace,
            context=table,
        )

        if dependency_type not in ALLOWED_DEPENDENCY_TYPES:
            raise InvalidTaskDependencyType(
                f"Dependency type '{dependency_type}' is not supported; only FS "
                f"(finish-to-start) is allowed."
            )

        model = table.get_model()
        existing_row_ids = set(
            model.objects.filter(
                id__in=[predecessor_row_id, successor_row_id]
            ).values_list("id", flat=True)
        )
        for row_id in (predecessor_row_id, successor_row_id):
            if row_id not in existing_row_ids:
                raise TaskDependencyRowDoesNotExist(
                    f"Row {row_id} does not exist in table {table.id}."
                )

        with transaction.atomic():
            # Serialize per-table edge mutations: lock the table row so two
            # concurrent edge creates cannot interleave their check-then-insert.
            Table.objects.select_for_update().get(id=table.id)

            edges = self._load_edges(table)

            if (predecessor_row_id, successor_row_id) in edges:
                raise TaskDependencyAlreadyExists(
                    f"A dependency {predecessor_row_id} -> {successor_row_id} "
                    f"already exists."
                )

            if self.would_create_cycle(
                table, predecessor_row_id, successor_row_id, edges=edges
            ):
                raise TaskDependencyCycle(
                    f"Adding the dependency {predecessor_row_id} -> "
                    f"{successor_row_id} would create a cycle in the schedule and "
                    f"was rejected."
                )

            dependency = TaskDependency.objects.create(
                table=table,
                predecessor_row_id=predecessor_row_id,
                successor_row_id=successor_row_id,
                dependency_type=dependency_type,
            )

        task_dependency_created.send(
            self, dependency=dependency, table=table, user=user
        )
        return dependency

    def get_dependency(self, table: Table, dependency_id: int) -> TaskDependency:
        try:
            return TaskDependency.objects.get(id=dependency_id, table=table)
        except TaskDependency.DoesNotExist:
            raise TaskDependencyDoesNotExist(
                f"Dependency {dependency_id} does not exist in table {table.id}."
            )

    def delete_dependency(self, user, dependency: TaskDependency) -> None:
        """Remove an edge (idempotent from the caller's perspective)."""

        table = dependency.table
        workspace = table.database.workspace
        CoreHandler().check_permissions(
            user,
            UpdateDatabaseRowOperationType.type,
            workspace=workspace,
            context=table,
        )

        dependency_id = dependency.id
        predecessor_row_id = dependency.predecessor_row_id
        successor_row_id = dependency.successor_row_id
        dependency.delete()

        task_dependency_deleted.send(
            self,
            dependency_id=dependency_id,
            table=table,
            predecessor_row_id=predecessor_row_id,
            successor_row_id=successor_row_id,
            user=user,
        )

    def list_dependencies(self, user, table: Table) -> List[TaskDependency]:
        """Return all edges for a table (the frontend connector source)."""

        workspace = table.database.workspace
        CoreHandler().check_permissions(
            user,
            ReadDatabaseRowOperationType.type,
            workspace=workspace,
            context=table,
        )
        return list(TaskDependency.objects.filter(table=table))

    # -- non-interactive paths (restore / permanent delete / import) ------

    def delete_dependencies_for_row(self, table_id: int, row_id: int) -> None:
        """
        Remove every edge touching ``row_id`` (as predecessor OR successor) when
        that row is permanently deleted. Mirrors the ``RichTextFieldMention``
        cleanup in ``RowTrashableItemType.permanently_delete_item``.
        """

        from django.db.models import Q

        TaskDependency.objects.filter(table_id=table_id).filter(
            Q(predecessor_row_id=row_id) | Q(successor_row_id=row_id)
        ).delete()

    def delete_dependencies_for_rows(
        self, table_id: int, row_ids: Iterable[int]
    ) -> None:
        """Bulk variant of :meth:`delete_dependencies_for_row`."""

        from django.db.models import Q

        row_ids = list(row_ids)
        if not row_ids:
            return
        TaskDependency.objects.filter(table_id=table_id).filter(
            Q(predecessor_row_id__in=row_ids) | Q(successor_row_id__in=row_ids)
        ).delete()

    def revalidate_on_rows_restored(
        self, table: Table, restored_row_ids: Iterable[int]
    ) -> List[TaskDependency]:
        """
        After rows are restored from trash, re-check the dependency graph. While a
        row was trashed the graph may have mutated so that restoring its edges now
        closes a cycle. Drop the offending edges that touch a restored row until
        the graph is acyclic again (and broadcast each removal) rather than
        silently materializing a cycle (AR-8).

        Returns the list of edges that were dropped (empty when the graph was
        already acyclic).
        """

        restored_row_ids = set(restored_row_ids)
        if not restored_row_ids:
            return []

        edges = list(TaskDependency.objects.filter(table=table))
        edge_tuples = [(e.predecessor_row_id, e.successor_row_id) for e in edges]
        if not _graph_has_cycle(edge_tuples):
            return []

        dropped: List[TaskDependency] = []
        # Prefer dropping edges that touch the just-restored rows, since those are
        # the edges the restore reintroduced.
        candidates = [
            e
            for e in edges
            if e.predecessor_row_id in restored_row_ids
            or e.successor_row_id in restored_row_ids
        ]
        remaining = list(edges)
        for edge in candidates:
            current = [(e.predecessor_row_id, e.successor_row_id) for e in remaining]
            if not _graph_has_cycle(current):
                break
            remaining = [e for e in remaining if e.id != edge.id]
            edge.delete()
            dropped.append(edge)
            task_dependency_deleted.send(
                self,
                dependency_id=edge.id,
                table=table,
                predecessor_row_id=edge.predecessor_row_id,
                successor_row_id=edge.successor_row_id,
                user=None,
            )

        return dropped

    # -- export / import (table + view duplication) -----------------------

    def export_serialized(self, table: Table) -> List[dict]:
        """Serialize a table's edges for export/duplication round-trips."""

        return [
            {
                "predecessor_row_id": e.predecessor_row_id,
                "successor_row_id": e.successor_row_id,
                "dependency_type": e.dependency_type,
            }
            for e in TaskDependency.objects.filter(table=table)
        ]

    def import_serialized(
        self,
        table: Table,
        serialized_dependencies: List[dict],
        row_id_mapping: Optional[Dict[int, int]] = None,
    ) -> List[TaskDependency]:
        """
        Import a serialized edge set into ``table``, remapping row ids through
        ``row_id_mapping`` (old -> new; identity when omitted, since the row
        import preserves ids). The remapped batch must pass a full-graph cycle
        check before commit; a cyclic batch raises ``TaskDependencyCycle`` and
        nothing is written.
        """

        if not serialized_dependencies:
            return []

        def remap(row_id: int) -> int:
            if row_id_mapping is None:
                return row_id
            return row_id_mapping.get(row_id, row_id)

        candidate_edges: List[Edge] = []
        instances: List[TaskDependency] = []
        for serialized in serialized_dependencies:
            predecessor_row_id = remap(serialized["predecessor_row_id"])
            successor_row_id = remap(serialized["successor_row_id"])
            candidate_edges.append((predecessor_row_id, successor_row_id))
            instances.append(
                TaskDependency(
                    table=table,
                    predecessor_row_id=predecessor_row_id,
                    successor_row_id=successor_row_id,
                    dependency_type=serialized.get("dependency_type", "FS"),
                )
            )

        self.validate_acyclic(table, candidate_edges)

        return TaskDependency.objects.bulk_create(instances)
