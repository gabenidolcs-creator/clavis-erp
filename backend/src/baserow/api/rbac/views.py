from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import Http404

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from baserow.api.applications.errors import ERROR_APPLICATION_DOES_NOT_EXIST
from baserow.api.decorators import map_exceptions, validate_body
from baserow.api.errors import (
    ERROR_GROUP_DOES_NOT_EXIST,
    ERROR_USER_INVALID_GROUP_PERMISSIONS,
    ERROR_USER_NOT_IN_GROUP,
)
from baserow.api.schemas import get_error_schema
from baserow.core.exceptions import (
    ApplicationDoesNotExist,
    ApplicationNotInWorkspace,
    UserInvalidWorkspacePermissionsError,
    UserNotInWorkspace,
    WorkspaceDoesNotExist,
)
from baserow.core.handler import CoreHandler
from baserow.core.rbac.handler import RbacHandler
from baserow.core.rbac.operations import (
    AssignRoleWorkspaceOperationType,
    GrantPageAccessOperationType,
    ListPageGrantsOperationType,
    ReadRoleAssignmentsWorkspaceOperationType,
    RevokePageAccessOperationType,
)

from .serializers import (
    AssignRoleSerializer,
    GrantPageAccessSerializer,
    InterfaceCollaboratorPageGrantSerializer,
    RoleAssignmentSerializer,
)

User = get_user_model()


class WorkspaceRoleAssignmentsView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="workspace_id",
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
                description="The workspace whose role assignments are listed.",
            ),
        ],
        tags=["Rbac"],
        operation_id="list_workspace_role_assignments",
        description=(
            "Lists the RBAC role assignments in the given workspace. Only workspace "
            "admins are allowed to read role assignments."
        ),
        responses={
            200: RoleAssignmentSerializer(many=True),
            400: get_error_schema(
                ["ERROR_USER_NOT_IN_GROUP", "ERROR_USER_INVALID_GROUP_PERMISSIONS"]
            ),
            404: get_error_schema(["ERROR_GROUP_DOES_NOT_EXIST"]),
        },
    )
    @map_exceptions(
        {
            WorkspaceDoesNotExist: ERROR_GROUP_DOES_NOT_EXIST,
            UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
            UserInvalidWorkspacePermissionsError: ERROR_USER_INVALID_GROUP_PERMISSIONS,
        }
    )
    def get(self, request, workspace_id):
        workspace = CoreHandler().get_workspace(workspace_id)
        CoreHandler().check_permissions(
            request.user,
            ReadRoleAssignmentsWorkspaceOperationType.type,
            workspace=workspace,
            context=workspace,
        )
        assignments = RbacHandler().list_role_assignments(workspace)
        return Response(RoleAssignmentSerializer(assignments, many=True).data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="workspace_id",
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
                description="The workspace the role is assigned in.",
            ),
        ],
        tags=["Rbac"],
        operation_id="assign_workspace_role",
        description=(
            "Assigns a fixed-tier RBAC role to a workspace member at workspace or "
            "database scope. Only workspace admins are allowed to assign roles."
        ),
        request=AssignRoleSerializer,
        responses={
            200: RoleAssignmentSerializer,
            400: get_error_schema(
                [
                    "ERROR_USER_NOT_IN_GROUP",
                    "ERROR_USER_INVALID_GROUP_PERMISSIONS",
                    "ERROR_REQUEST_BODY_VALIDATION",
                ]
            ),
            404: get_error_schema(
                ["ERROR_GROUP_DOES_NOT_EXIST", "ERROR_APPLICATION_DOES_NOT_EXIST"]
            ),
        },
    )
    @map_exceptions(
        {
            WorkspaceDoesNotExist: ERROR_GROUP_DOES_NOT_EXIST,
            ApplicationDoesNotExist: ERROR_APPLICATION_DOES_NOT_EXIST,
            ApplicationNotInWorkspace: ERROR_APPLICATION_DOES_NOT_EXIST,
            UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
            UserInvalidWorkspacePermissionsError: ERROR_USER_INVALID_GROUP_PERMISSIONS,
        }
    )
    @validate_body(AssignRoleSerializer)
    @transaction.atomic
    def post(self, request, data, workspace_id):
        workspace = CoreHandler().get_workspace(workspace_id)
        CoreHandler().check_permissions(
            request.user,
            AssignRoleWorkspaceOperationType.type,
            workspace=workspace,
            context=workspace,
        )

        # Resolve and validate the target member.
        try:
            target_user = User.objects.get(id=data["user_id"])
        except User.DoesNotExist:
            raise UserNotInWorkspace()
        if not workspace.users.filter(id=target_user.id).exists():
            raise UserNotInWorkspace(target_user, workspace)

        # Resolve optional database/application scope (must belong to the workspace).
        application = None
        application_id = data.get("application_id")
        if application_id is not None:
            application = CoreHandler().get_application(application_id)
            if application.workspace_id != workspace.id:
                raise ApplicationNotInWorkspace(application_id)

        assignment = RbacHandler().assign_role(
            target_user, workspace, data["role"], application=application
        )
        return Response(RoleAssignmentSerializer(assignment).data)


class InterfaceCollaboratorPageGrantsView(APIView):
    """CRUD for page grants given to interface-only collaborators (Story 6.3).

    GET  — list all granted pages for the target user in this workspace.
    POST — grant access to a page (idempotent).
    DELETE — revoke access to a page.
    """

    permission_classes = (IsAuthenticated,)

    def _resolve_workspace_and_user(self, request, workspace_id, target_user_id):
        workspace = CoreHandler().get_workspace(workspace_id)
        try:
            target_user = User.objects.get(id=target_user_id)
        except User.DoesNotExist:
            raise UserNotInWorkspace()
        if not workspace.users.filter(id=target_user.id).exists():
            raise UserNotInWorkspace(target_user, workspace)
        return workspace, target_user

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="workspace_id",
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="target_user_id",
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
            ),
        ],
        tags=["Rbac"],
        operation_id="list_interface_collaborator_page_grants",
        description="List all App Builder page grants for an interface-only collaborator.",
        responses={
            200: InterfaceCollaboratorPageGrantSerializer(many=True),
            400: get_error_schema(
                ["ERROR_USER_NOT_IN_GROUP", "ERROR_USER_INVALID_GROUP_PERMISSIONS"]
            ),
            404: get_error_schema(["ERROR_GROUP_DOES_NOT_EXIST"]),
        },
    )
    @map_exceptions(
        {
            WorkspaceDoesNotExist: ERROR_GROUP_DOES_NOT_EXIST,
            UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
            UserInvalidWorkspacePermissionsError: ERROR_USER_INVALID_GROUP_PERMISSIONS,
        }
    )
    def get(self, request, workspace_id, target_user_id):
        workspace, target_user = self._resolve_workspace_and_user(
            request, workspace_id, target_user_id
        )
        CoreHandler().check_permissions(
            request.user,
            ListPageGrantsOperationType.type,
            workspace=workspace,
            context=workspace,
        )
        grants = RbacHandler().list_granted_pages(target_user, workspace)
        return Response(
            InterfaceCollaboratorPageGrantSerializer(grants, many=True).data
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="workspace_id",
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="target_user_id",
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
            ),
        ],
        tags=["Rbac"],
        operation_id="grant_interface_collaborator_page_access",
        description="Grant an interface-only collaborator access to an App Builder page.",
        request=GrantPageAccessSerializer,
        responses={
            200: InterfaceCollaboratorPageGrantSerializer,
            400: get_error_schema(
                [
                    "ERROR_USER_NOT_IN_GROUP",
                    "ERROR_USER_INVALID_GROUP_PERMISSIONS",
                    "ERROR_REQUEST_BODY_VALIDATION",
                ]
            ),
            404: get_error_schema(
                ["ERROR_GROUP_DOES_NOT_EXIST"]
            ),
        },
    )
    @map_exceptions(
        {
            WorkspaceDoesNotExist: ERROR_GROUP_DOES_NOT_EXIST,
            UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
            UserInvalidWorkspacePermissionsError: ERROR_USER_INVALID_GROUP_PERMISSIONS,
        }
    )
    @validate_body(GrantPageAccessSerializer)
    @transaction.atomic
    def post(self, request, data, workspace_id, target_user_id):
        from baserow.contrib.builder.pages.exceptions import PageDoesNotExist
        from baserow.contrib.builder.pages.handler import PageHandler

        workspace, target_user = self._resolve_workspace_and_user(
            request, workspace_id, target_user_id
        )
        CoreHandler().check_permissions(
            request.user,
            GrantPageAccessOperationType.type,
            workspace=workspace,
            context=workspace,
        )
        try:
            page = PageHandler().get_page(data["page_id"])
        except PageDoesNotExist:
            raise Http404
        if page.builder.workspace_id != workspace.id:
            raise Http404
        grant = RbacHandler().grant_page_access(target_user, workspace, page)
        return Response(InterfaceCollaboratorPageGrantSerializer(grant).data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="workspace_id",
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
            ),
            OpenApiParameter(
                name="target_user_id",
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
            ),
        ],
        tags=["Rbac"],
        operation_id="revoke_interface_collaborator_page_access",
        description="Revoke an interface-only collaborator's access to an App Builder page.",
        request=GrantPageAccessSerializer,
        responses={
            204: None,
            400: get_error_schema(
                [
                    "ERROR_USER_NOT_IN_GROUP",
                    "ERROR_USER_INVALID_GROUP_PERMISSIONS",
                    "ERROR_REQUEST_BODY_VALIDATION",
                ]
            ),
            404: get_error_schema(["ERROR_GROUP_DOES_NOT_EXIST"]),
        },
    )
    @map_exceptions(
        {
            WorkspaceDoesNotExist: ERROR_GROUP_DOES_NOT_EXIST,
            UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
            UserInvalidWorkspacePermissionsError: ERROR_USER_INVALID_GROUP_PERMISSIONS,
        }
    )
    @validate_body(GrantPageAccessSerializer)
    @transaction.atomic
    def delete(self, request, data, workspace_id, target_user_id):
        from baserow.contrib.builder.pages.exceptions import PageDoesNotExist
        from baserow.contrib.builder.pages.handler import PageHandler

        workspace, target_user = self._resolve_workspace_and_user(
            request, workspace_id, target_user_id
        )
        CoreHandler().check_permissions(
            request.user,
            RevokePageAccessOperationType.type,
            workspace=workspace,
            context=workspace,
        )
        try:
            page = PageHandler().get_page(data["page_id"])
        except PageDoesNotExist:
            raise Http404
        RbacHandler().revoke_page_access(target_user, page)
        return Response(status=204)
