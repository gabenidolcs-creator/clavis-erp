from baserow.contrib.database.views.gantt.models import TaskDependency


class TaskDependencyFixtures:
    def create_task_dependency(
        self, table, predecessor_row_id, successor_row_id, **kwargs
    ):
        kwargs.setdefault("dependency_type", "FS")
        return TaskDependency.objects.create(
            table=table,
            predecessor_row_id=predecessor_row_id,
            successor_row_id=successor_row_id,
            **kwargs,
        )
