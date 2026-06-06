from django.contrib.auth import get_user_model
from django.db import transaction

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
    ReadRoleAssignmentsWorkspaceOperationType,
)

from .serializers import AssignRoleSerializer, RoleAssignmentSerializer

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
