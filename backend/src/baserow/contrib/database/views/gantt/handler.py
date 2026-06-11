import dataclasses
from datetime import timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.db import transaction

from baserow.contrib.database.fields.models import Field
from baserow.contrib.database.rows.operations import (
    ReadDatabaseRowOperationType,
    UpdateDatabaseRowOperationType,
)
from baserow.contrib.database.table.models import Table
from baserow.core.handler import CoreHandler

from . import date_utils
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


@dataclasses.dataclass
class CpmResult:
    """
    Result of :meth:`TaskDependencyHandler.compute_cpm` (Story 3.11 / FR-11).
    Pure data — no DB handle.

    ``critical_task_ids``: row ids on the zero-float critical path (FS network
    nodes only; isolated rows never appear here).
    ``conflict_task_ids``: row ids whose stored start date is earlier than the
    dependency-implied earliest start — scheduling conflicts that must be
    resolved before those nodes can join the critical path.
    """

    critical_task_ids: List[int]
    conflict_task_ids: List[int]


@dataclasses.dataclass
class CascadePlan:
    """
    The result of :meth:`TaskDependencyHandler.compute_cascade` (Story 3.10 /
    FR-10). Pure data — no DB handle — so the preview endpoint can return it and
    the apply endpoint can recompute one under a lock.

    ``rows_values`` is the ordered batch handed verbatim to
    ``UpdateRowsActionType.do`` (predecessor first, then each shifted successor);
    each item is ``{"id": row_id, "field_<start_id>": iso, "field_<end_id>":
    iso}``. ``affected`` carries the per-successor before/after dates the prompt
    shows; ``cascade_count`` is its length — the transitive dependent count
    computed BEFORE any write (AC #1).
    """

    rows_values: List[Dict[str, Any]]
    affected: List[Dict[str, Any]]

    @property
    def affected_successor_ids(self) -> List[int]:
        return [a["row_id"] for a in self.affected]

    @property
    def cascade_count(self) -> int:
        return len(self.affected)


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

    def _load_fs_edges(self, table: Table) -> List[Edge]:
        """
        FS-only edge set for the cascade walk. v1 only cascades finish-to-start
        edges (``successor.start >= predecessor.end``); any other type is ignored
        here exactly as it is rejected at create time. [Source: 3.10 Task 1 FS-only]
        """

        return list(
            TaskDependency.objects.filter(
                table=table, dependency_type="FS"
            ).values_list("predecessor_row_id", "successor_row_id")
        )

    # -- cascade reschedule (Story 3.10 / FR-10) --------------------------

    def _load_row_dates(
        self,
        table: Table,
        row_ids: Iterable[int],
        start_date_field: Field,
        end_date_field: Field,
        model=None,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Read the raw start/end cell values for ``row_ids`` keyed by row id. Pure
        read — the values are handed to the DB-free date math in ``date_utils``.
        """

        if model is None:
            model = table.get_model()
        start_attr = f"field_{start_date_field.id}"
        end_attr = f"field_{end_date_field.id}"
        rows = model.objects.filter(id__in=list(row_ids))
        return {
            row.id: {
                "start": getattr(row, start_attr),
                "end": getattr(row, end_attr),
            }
            for row in rows
        }

    # -- CPM (Story 3.11 / FR-11) -----------------------------------------

    def compute_cpm(
        self,
        table: Table,
        start_date_field: Optional[Field],
        end_date_field: Optional[Field],
        model=None,
    ) -> CpmResult:
        """
        Run a forward + backward CPM pass over the FS dependency graph and
        return which rows are on the critical path (zero float) and which are
        in conflict (stored start before dependency-implied earliest start).

        Only nodes that appear in at least one FS edge participate.  Isolated
        rows (no edges at all) are never critical.  Unscheduled nodes (start
        or end is None) are silently skipped.

        Algorithm: Kahn's BFS topological sort for the forward pass (natural
        level-by-level processing), then reverse-topological order for the
        backward pass.
        """

        if start_date_field is None or end_date_field is None:
            return CpmResult(critical_task_ids=[], conflict_task_ids=[])

        edges = self._load_fs_edges(table)
        if not edges:
            return CpmResult(critical_task_ids=[], conflict_task_ids=[])

        # Collect all nodes in the dependency network.
        node_ids = set(p for p, _ in edges) | set(s for _, s in edges)

        # Load dates for network nodes only.
        dates = self._load_row_dates(
            table, node_ids, start_date_field, end_date_field, model=model
        )

        # Drop unscheduled nodes (start or end is None).
        scheduled = {
            nid
            for nid in node_ids
            if dates.get(nid, {}).get("start") is not None
            and dates.get(nid, {}).get("end") is not None
        }

        # Filter edges to scheduled nodes only.
        active_edges = [
            (p, s) for p, s in edges if p in scheduled and s in scheduled
        ]

        if not active_edges:
            return CpmResult(critical_task_ids=[], conflict_task_ids=[])

        # Build adjacency structures for Kahn's BFS.
        successors: Dict[int, List[int]] = {n: [] for n in scheduled}
        predecessors: Dict[int, List[int]] = {n: [] for n in scheduled}
        in_degree: Dict[int, int] = {n: 0 for n in scheduled}

        for p, s in active_edges:
            successors[p].append(s)
            predecessors[s].append(p)
            in_degree[s] += 1

        # Duration helper — always non-negative.
        def duration(node: int) -> timedelta:
            d = dates[node]
            raw = d["end"] - d["start"]
            # date arithmetic can return timedelta — keep it as-is
            return max(timedelta(0), raw) if isinstance(raw, timedelta) else timedelta(0)

        # Forward pass (Kahn's BFS).
        from collections import deque

        queue: deque = deque(n for n in scheduled if in_degree[n] == 0)
        topo_order: List[int] = []
        ES: Dict[int, Any] = {}
        EF: Dict[int, Any] = {}

        for n in scheduled:
            if in_degree[n] == 0:
                # Root node: ES = stored start date.
                ES[n] = dates[n]["start"]
                EF[n] = ES[n] + duration(n)

        while queue:
            node = queue.popleft()
            topo_order.append(node)
            for succ in successors[node]:
                # ES of successor = max(EF of all predecessors).
                pred_ef = EF[node]
                if succ not in ES:
                    ES[succ] = pred_ef
                    EF[succ] = ES[succ] + duration(succ)
                else:
                    if pred_ef > ES[succ]:
                        ES[succ] = pred_ef
                        EF[succ] = ES[succ] + duration(succ)
                in_degree[succ] -= 1
                if in_degree[succ] == 0:
                    queue.append(succ)

        # Conflict detection: stored start < ES (before dependency-implied ES).
        conflict_task_ids = [
            n for n in topo_order if dates[n]["start"] < ES[n]
        ]
        conflict_set = set(conflict_task_ids)

        # Backward pass in reverse topological order.
        project_end = max(EF.values())
        LF: Dict[int, Any] = {}
        LS: Dict[int, Any] = {}

        for node in reversed(topo_order):
            succs = [s for s in successors[node] if s in topo_order]
            if not succs:
                LF[node] = project_end
            else:
                LF[node] = min(LS[s] for s in succs if s in LS)
            LS[node] = LF[node] - duration(node)

        # Critical path: float == 0 and not conflicted.
        critical_task_ids = [
            n
            for n in topo_order
            if n not in conflict_set and (LF[n] - EF[n]) == timedelta(0)
        ]

        return CpmResult(
            critical_task_ids=critical_task_ids,
            conflict_task_ids=conflict_task_ids,
        )

    def compute_cascade(
        self,
        table: Table,
        start_date_field: Field,
        end_date_field: Field,
        predecessor_row_id: int,
        new_start: Any,
        new_end: Any,
        model=None,
    ) -> CascadePlan:
        """
        Compute the forward FS cascade triggered by moving ``predecessor_row_id``
        to ``(new_start, new_end)`` — WITHOUT writing anything (AC #1 preview).

        Walks the ``predecessor -> successors`` adjacency breadth-first. A
        successor ``s`` of a node whose new end is ``E`` is shifted iff
        ``s.start < E`` (FS violated); it then moves forward by ``delta = E -
        s.start`` so ``s.new_start == E`` (its start lands exactly on the
        predecessor's new end), and ``s.new_end = s.end + delta`` (**duration
        preserved**). The shift cascades transitively to ``s``'s own successors.

        A diamond (a node reachable by two paths implying different deltas) is
        shifted **once by the MAX required delta** — never double-counted —
        because each node's delta is relaxed upward to the largest constraint
        any predecessor imposes before its own successors are evaluated. The
        graph is acyclic (enforced on every mutation by 3.9), so the relaxation
        terminates.

        The delta is a whole ``timedelta`` applied through ``date_utils`` so a
        date-only field round-trips as ``YYYY-MM-DD`` and a datetime field keeps
        its time-of-day, matching 3.7's ``shiftDateValue`` at month/DST
        boundaries.
        """

        if model is None:
            model = table.get_model()

        start_attr = f"field_{start_date_field.id}"
        end_attr = f"field_{end_date_field.id}"
        start_has_time = start_date_field.date_include_time
        end_has_time = end_date_field.date_include_time

        edges = self._load_fs_edges(table)
        adjacency = _build_adjacency(edges)

        # Every node that participates in the (sub)graph reachable from the moved
        # predecessor — load their current dates once.
        involved: set = {predecessor_row_id}
        frontier = [predecessor_row_id]
        while frontier:
            node = frontier.pop()
            for successor in adjacency.get(node, ()):
                if successor not in involved:
                    involved.add(successor)
                    frontier.append(successor)
        dates = self._load_row_dates(
            table, involved, start_date_field, end_date_field, model=model
        )

        # `delta[id]` is the forward timedelta a row is shifted by, measured from
        # its ORIGINAL position. The predecessor is the trigger: its new dates are
        # given directly (a resize may change its duration), so it is not part of
        # `delta`.
        new_end_dt = date_utils.to_datetime(new_end, end_has_time)
        delta: Dict[int, timedelta] = {}

        def effective_end_dt(node: int):
            if node == predecessor_row_id:
                return new_end_dt
            row = dates.get(node)
            if row is None:
                return None
            base = date_utils.to_datetime(row["end"], end_has_time)
            if base is None:
                return None
            return base + delta.get(node, timedelta(0))

        # Relax forward from the predecessor breadth-first; re-enqueue any
        # successor whose required delta grows, so the MAX constraint wins
        # (diamond-safe). Bounded by the acyclic graph.
        queue = [predecessor_row_id]
        while queue:
            node = queue.pop(0)
            node_end = effective_end_dt(node)
            if node_end is None:
                continue
            for successor in adjacency.get(node, ()):
                row = dates.get(successor)
                if row is None:
                    continue
                succ_start_dt = date_utils.to_datetime(row["start"], start_has_time)
                if succ_start_dt is None:
                    continue
                # Required forward shift so this successor starts no earlier than
                # the predecessor's (new) end.
                required = node_end - succ_start_dt
                if required <= timedelta(0):
                    continue  # not violated by this predecessor
                if required > delta.get(successor, timedelta(0)):
                    delta[successor] = required
                    queue.append(successor)

        # Build the ordered batch: predecessor first, then each shifted successor.
        rows_values: List[Dict[str, Any]] = [
            {
                "id": predecessor_row_id,
                start_attr: date_utils.format_value(
                    date_utils.to_datetime(new_start, start_has_time), start_has_time
                )
                if new_start not in (None, "")
                else None,
                end_attr: date_utils.format_value(new_end_dt, end_has_time)
                if new_end_dt is not None
                else None,
            }
        ]
        affected: List[Dict[str, Any]] = []
        for successor_id, succ_delta in delta.items():
            row = dates[successor_id]
            new_s = date_utils.shift_value(row["start"], succ_delta, start_has_time)
            new_e = date_utils.shift_value(row["end"], succ_delta, end_has_time)
            rows_values.append(
                {"id": successor_id, start_attr: new_s, end_attr: new_e}
            )
            affected.append(
                {
                    "row_id": successor_id,
                    "current_start": date_utils.format_value(
                        date_utils.to_datetime(row["start"], start_has_time),
                        start_has_time,
                    )
                    if row["start"] not in (None, "")
                    else None,
                    "current_end": date_utils.format_value(
                        date_utils.to_datetime(row["end"], end_has_time), end_has_time
                    )
                    if row["end"] not in (None, "")
                    else None,
                    "new_start": new_s,
                    "new_end": new_e,
                }
            )

        return CascadePlan(rows_values=rows_values, affected=affected)

    def apply_cascade(
        self,
        user,
        table: Table,
        view,
        start_date_field: Field,
        end_date_field: Field,
        predecessor_row_id: int,
        new_start: Any,
        new_end: Any,
    ):
        """
        Commit the cascade as ONE undoable step (AC #2, AC #4).

        Acquires the table-scoped lock FIRST and **recomputes** the cascade from
        fresh row values under that lock — a concurrent edit may have moved a
        successor since the preview, so the stored plan could be stale (AC #4
        no-interleave, same TOCTOU discipline ``create_dependency`` uses). The
        recomputed batch then commits through ``UpdateRowsActionType.do`` — one
        call, one undoable action, atomic, broadcast as one batch (AC #2). Any
        ``RowHandler`` rejection rolls the whole transaction back (AC #5).
        """

        # Imported lazily: ``rows.actions`` pulls in a large dependency graph that
        # would create an import cycle at module load.
        from baserow.contrib.database.rows.actions import UpdateRowsActionType

        with transaction.atomic():
            # Serialize overlapping cascades on the same table so they cannot
            # interleave into an inconsistent schedule (NFR-3 / D8).
            Table.objects.select_for_update().get(id=table.id)
            model = table.get_model()
            plan = self.compute_cascade(
                table,
                start_date_field,
                end_date_field,
                predecessor_row_id,
                new_start,
                new_end,
                model=model,
            )
            UpdateRowsActionType.do(
                user, table, plan.rows_values, model=model, view=view
            )
        return plan

    def find_violations(
        self,
        table: Table,
        start_date_field: Field,
        end_date_field: Field,
        model=None,
    ) -> List[Edge]:
        """
        Return the FS edges that are currently violated — **derived state**, no
        migration, no persisted flag (AC #3). An edge ``predecessor ->
        successor`` is violated iff ``successor.start < predecessor.end`` (the
        successor begins before its predecessor finishes). Dates are normalised
        to aware UTC datetimes so a date-only / datetime field pair compares
        consistently.
        """

        edges = self._load_fs_edges(table)
        if not edges:
            return []
        if model is None:
            model = table.get_model()
        involved = {row_id for edge in edges for row_id in edge}
        dates = self._load_row_dates(
            table, involved, start_date_field, end_date_field, model=model
        )
        start_has_time = start_date_field.date_include_time
        end_has_time = end_date_field.date_include_time

        violated: List[Edge] = []
        for predecessor_row_id, successor_row_id in edges:
            predecessor = dates.get(predecessor_row_id)
            successor = dates.get(successor_row_id)
            if predecessor is None or successor is None:
                continue
            predecessor_end = date_utils.to_datetime(predecessor["end"], end_has_time)
            successor_start = date_utils.to_datetime(
                successor["start"], start_has_time
            )
            if predecessor_end is None or successor_start is None:
                continue
            if successor_start < predecessor_end:
                violated.append((predecessor_row_id, successor_row_id))
        return violated

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
