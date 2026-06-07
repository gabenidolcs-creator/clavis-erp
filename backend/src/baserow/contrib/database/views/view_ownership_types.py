from typing import List, Optional, Set

from django.contrib.auth.models import AbstractUser

from baserow.contrib.database.views.models import View
from baserow.contrib.database.views.operations import (
    ReadViewDefaultValuesOperationType,
    UpdateViewOperationType,
)
from baserow.contrib.database.views.registries import ViewOwnershipType
from baserow.core.exceptions import PermissionDenied
from baserow.core.handler import CoreHandler


class CollaborativeViewOwnershipType(ViewOwnershipType):
    """
    Represents views that are shared between all users that can access
    a specific table.
    """

    type = "collaborative"

    def change_ownership_type(self, user: AbstractUser, view: View) -> View:
        view.ownership_type = self.type
        # The previous permission check (when updating the view) was done using
        # the old ownership_type. Verify that the user has permission to update
        # the view with the new one as well:
        CoreHandler().check_permissions(
            user,
            UpdateViewOperationType.type,
            workspace=view.table.database.workspace,
            context=view,
        )
        view.owned_by = user
        return view

    def prepare_views_for_user(
        self,
        user: Optional[AbstractUser],
        views: List[View],
        includes: Optional[Set[str]] = None,
    ) -> List[View]:
        if not views or user is None:
            return views

        # Skip work entirely when default_row_values is not requested.
        if includes is not None and "default_row_values" not in includes:
            return views

        # All collaborative views in the same table share the same permissions,
        # so a single check using the first view is sufficient.
        can_read_default_values = CoreHandler().check_permissions(
            user,
            ReadViewDefaultValuesOperationType.type,
            workspace=views[0].table.database.workspace,
            context=views[0],
            raise_permission_exceptions=False,
        )
        for view in views:
            if not hasattr(view, "_prefetched_objects_cache"):
                view._prefetched_objects_cache = {}
            if not can_read_default_values:
                view._prefetched_objects_cache["view_default_values"] = []
            elif "view_default_values" not in view._prefetched_objects_cache:
                view._prefetched_objects_cache["view_default_values"] = list(
                    view.view_default_values.all()
                )

        return views


class PersonalViewOwnershipType(ViewOwnershipType):
    """
    Represents views that are personal to their creator — visible only to the
    owner; other workspace members cannot list or fetch them.
    """

    type = "personal"

    def get_trashed_item_owner(self, view):
        return view.owned_by

    def should_broadcast_signal_to(self, view):
        if view.owned_by_id is None:
            return "", None
        return "users", [view.owned_by_id]

    def get_operation_to_check_to_create_view(self):
        from .operations import CreateAndUsePersonalViewOperationType

        return CreateAndUsePersonalViewOperationType

    def change_ownership_type(self, user: AbstractUser, view: View) -> View:
        from .operations import CreateAndUsePersonalViewOperationType

        CoreHandler().check_permissions(
            user,
            CreateAndUsePersonalViewOperationType.type,
            workspace=view.table.database.workspace,
            context=view.table,
        )
        view.ownership_type = self.type
        view.owned_by = user
        return view

    def view_created(self, user: AbstractUser, view: View, workspace) -> None:
        pass

    def before_form_view_submitted(self, form, request):
        from baserow.contrib.database.table.operations import (
            CreateRowDatabaseTableOperationType,
        )

        if not CoreHandler().check_permissions(
            form.owned_by,
            CreateRowDatabaseTableOperationType.type,
            workspace=form.table.database.workspace,
            context=form.table,
            raise_permission_exceptions=False,
        ):
            raise PermissionDenied(
                "The form owner no longer has permission to submit rows."
            )

    def before_public_view_accessed(self, view):
        from .exceptions import ViewDoesNotExist
        from .operations import CreatePublicViewOperationType

        if not CoreHandler().check_permissions(
            view.owned_by,
            CreatePublicViewOperationType.type,
            workspace=view.table.database.workspace,
            context=view.table,
            raise_permission_exceptions=False,
        ):
            raise ViewDoesNotExist("The view does not exist.")
