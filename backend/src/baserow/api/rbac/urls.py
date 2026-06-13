from django.urls import re_path

from .views import InterfaceCollaboratorPageGrantsView, WorkspaceRoleAssignmentsView

app_name = "baserow.api.rbac"

urlpatterns = [
    re_path(
        r"workspaces/(?P<workspace_id>[0-9]+)/role-assignments/$",
        WorkspaceRoleAssignmentsView.as_view(),
        name="workspace_role_assignments",
    ),
    re_path(
        r"workspaces/(?P<workspace_id>[0-9]+)/interface-collaborators/(?P<target_user_id>[0-9]+)/page-grants/$",
        InterfaceCollaboratorPageGrantsView.as_view(),
        name="interface_page_grants",
    ),
]
