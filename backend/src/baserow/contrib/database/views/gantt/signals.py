from django.dispatch import Signal

# Sent after a TaskDependency edge is created. Mirrors the existing view signals
# so the WebSocket broadcast layer can push edge changes to live Gantt sessions.
task_dependency_created = Signal()

# Sent after a TaskDependency edge is deleted.
task_dependency_deleted = Signal()
