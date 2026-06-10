from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

ERROR_GANTT_DOES_NOT_EXIST = (
    "ERROR_GANTT_DOES_NOT_EXIST",
    HTTP_404_NOT_FOUND,
    "The requested gantt view does not exist.",
)

ERROR_TASK_DEPENDENCY_CYCLE = (
    "ERROR_TASK_DEPENDENCY_CYCLE",
    HTTP_400_BAD_REQUEST,
    "The dependency would create a cycle in the schedule and was rejected.",
)

ERROR_TASK_DEPENDENCY_ALREADY_EXISTS = (
    "ERROR_TASK_DEPENDENCY_ALREADY_EXISTS",
    HTTP_400_BAD_REQUEST,
    "An identical dependency edge already exists between these rows.",
)

ERROR_TASK_DEPENDENCY_ROW_DOES_NOT_EXIST = (
    "ERROR_ROW_DOES_NOT_EXIST",
    HTTP_400_BAD_REQUEST,
    "A predecessor or successor row referenced by the dependency does not exist.",
)

ERROR_INVALID_TASK_DEPENDENCY_TYPE = (
    "ERROR_INVALID_TASK_DEPENDENCY_TYPE",
    HTTP_400_BAD_REQUEST,
    "Only the finish-to-start (FS) dependency type is supported.",
)

ERROR_TASK_DEPENDENCY_DOES_NOT_EXIST = (
    "ERROR_TASK_DEPENDENCY_DOES_NOT_EXIST",
    HTTP_404_NOT_FOUND,
    "The requested dependency edge does not exist.",
)

ERROR_GANTT_NOT_CONFIGURED_FOR_RESCHEDULE = (
    "ERROR_GANTT_NOT_CONFIGURED_FOR_RESCHEDULE",
    HTTP_400_BAD_REQUEST,
    "The gantt view has no start and/or end date field configured, so a "
    "cascade reschedule cannot be computed.",
)
