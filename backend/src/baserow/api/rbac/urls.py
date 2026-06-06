from django.urls import re_path

from .views import WorkspaceRoleAssignmentsView

app_name = "baserow.api.rbac"

urlpatterns = [
    re_path(
        r"workspaces/(?P<workspace_id>[0-9]+)/role-assignments/$",
        WorkspaceRoleAssignmentsView.as_view(),
        name="workspace_role_assignments",
    ),
]
