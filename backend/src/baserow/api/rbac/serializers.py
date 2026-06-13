from rest_framework import serializers

from baserow.core.rbac.models import RoleAssignment
from baserow.core.rbac.roles import ALL_ROLES


class RoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleAssignment
        fields = (
            "id",
            "user_id",
            "workspace_id",
            "application_id",
            "role",
            "created_on",
            "updated_on",
        )


class AssignRoleSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(
        help_text="The id of the workspace member receiving the role."
    )
    role = serializers.ChoiceField(
        choices=ALL_ROLES,
        help_text="The fixed role tier (VIEWER / COMMENTER / EDITOR / ADMIN / INTERFACE_ONLY).",
    )
    application_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text=(
            "Optional database/application id for a database-scoped assignment. When "
            "omitted the assignment is workspace-scoped."
        ),
    )


class InterfaceCollaboratorPageGrantSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(read_only=True)
    page_id = serializers.IntegerField(read_only=True)
    workspace_id = serializers.IntegerField(read_only=True)


class GrantPageAccessSerializer(serializers.Serializer):
    page_id = serializers.IntegerField(
        help_text="The id of the App Builder page to grant access to."
    )
