from django.db import transaction
from django.dispatch import receiver

from baserow.contrib.database.api.views.gantt.serializers import (
    TaskDependencySerializer,
)
from baserow.contrib.database.views.gantt import signals as task_dependency_signals
from baserow.ws.registries import page_registry


@receiver(task_dependency_signals.task_dependency_created)
def task_dependency_created(sender, dependency, table, user, **kwargs):
    """
    Broadcast a created Gantt ``TaskDependency`` edge to every subscriber of the
    table page so live Gantt sessions repaint the new connector. Mirrors the
    row broadcast pattern (``ws/rows/signals.py``): serialize once, broadcast on
    commit to the table page group, excluding the originating socket.
    """

    table_page_type = page_registry.get("table")
    payload = {
        "type": "task_dependency_created",
        "table_id": table.id,
        "dependency": TaskDependencySerializer(dependency).data,
    }
    transaction.on_commit(
        lambda: table_page_type.broadcast(
            payload,
            getattr(user, "web_socket_id", None),
            table_id=table.id,
        )
    )


@receiver(task_dependency_signals.task_dependency_deleted)
def task_dependency_deleted(
    sender,
    dependency_id,
    table,
    predecessor_row_id,
    successor_row_id,
    user,
    **kwargs,
):
    """
    Broadcast a deleted edge to the table page group. ``user`` may be ``None``
    (e.g. an edge dropped by the restore-from-trash re-validation), in which
    case there is no originating socket to exclude.
    """

    table_page_type = page_registry.get("table")
    payload = {
        "type": "task_dependency_deleted",
        "table_id": table.id,
        "dependency_id": dependency_id,
    }
    transaction.on_commit(
        lambda: table_page_type.broadcast(
            payload,
            getattr(user, "web_socket_id", None),
            table_id=table.id,
        )
    )
