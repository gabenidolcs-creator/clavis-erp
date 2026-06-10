class TaskDependencyCycle(Exception):
    """
    Raised when creating or importing a dependency edge would introduce a cycle
    in the table's dependency graph.
    """


class TaskDependencyAlreadyExists(Exception):
    """Raised when an identical predecessor -> successor edge already exists."""


class TaskDependencyDoesNotExist(Exception):
    """Raised when a requested dependency edge cannot be found."""


class TaskDependencyRowDoesNotExist(Exception):
    """
    Raised when a predecessor or successor row referenced by an edge does not
    exist in the table.
    """


class InvalidTaskDependencyType(Exception):
    """Raised when a non-FS dependency type is provided (only FS is allowed v1)."""


class GanttViewNotConfiguredForReschedule(Exception):
    """
    Raised when a cascade reschedule is requested on a gantt view that has no
    start and/or end date field configured — there is nothing to shift.
    """
