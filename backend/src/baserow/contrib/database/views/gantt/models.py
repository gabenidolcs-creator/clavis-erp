from django.db import models

from baserow.contrib.database.table.models import Table


class TaskDependency(models.Model):
    """
    A directed finish-to-start scheduling edge between two task rows, rendered as
    a connector line in a Gantt view (Story 3.9 / FR-9).

    Edges are scoped to a ``Table`` rather than a view, because predecessor/
    successor ordering is a property of the data and is shared by every Gantt
    view of that table. Rows live in the dynamic ``GeneratedTableModel``, so
    there is no foreign key to a row; the predecessor and successor are
    referenced by their integer row id, mirroring the
    ``RichTextFieldMention(table_id, row_id)`` precedent in
    ``database/table/models.py``.

    The graph of edges for a table must stay acyclic: cycle detection runs on
    every mutation path (create, restore-from-trash, import) — see
    ``TaskDependencyHandler``.
    """

    table = models.ForeignKey(
        Table,
        on_delete=models.CASCADE,
        related_name="task_dependencies",
        help_text="The table whose rows this dependency edge connects.",
    )
    predecessor_row_id = models.PositiveIntegerField(
        help_text="The id of the row that must come first (the predecessor)."
    )
    successor_row_id = models.PositiveIntegerField(
        help_text="The id of the dependent row that comes after (the successor)."
    )
    dependency_type = models.CharField(
        max_length=2,
        choices=[("FS", "FS")],
        default="FS",
        help_text=(
            "The dependency semantics. v1 ships finish-to-start (FS) only; the "
            "column exists so later stories can add SS/FF/SF without a migration, "
            "but any non-FS value is rejected by the handler for now."
        ),
    )
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)
        # An edge is unique: re-drawing the same predecessor -> successor edge is
        # idempotent (rejected with a 400), never a duplicate row.
        unique_together = ("table", "predecessor_row_id", "successor_row_id")
        indexes = [
            # The cycle walk and the per-row connector lookup both query the edge
            # set by table + one of the endpoints; keep both directions indexed so
            # the bounded-per-table graph stays fast at scale.
            models.Index(fields=["table", "successor_row_id"]),
            models.Index(fields=["table", "predecessor_row_id"]),
        ]
        constraints = [
            # Reject the degenerate 1-cycle (a row depending on itself) at the
            # database level as a backstop to the handler check.
            models.CheckConstraint(
                check=~models.Q(predecessor_row_id=models.F("successor_row_id")),
                name="task_dependency_no_self_loop",
            ),
        ]

    def __str__(self):
        return (
            f"TaskDependency {self.predecessor_row_id} -> {self.successor_row_id} "
            f"(table {self.table_id})"
        )
