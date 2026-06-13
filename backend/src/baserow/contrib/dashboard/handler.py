from django.contrib.auth.models import AbstractUser
from django.db.models import QuerySet

from rest_framework.exceptions import AuthenticationFailed

from baserow.contrib.dashboard.models import Dashboard
from baserow.core.handler import CoreHandler
from baserow.core.operations import UpdateApplicationOperationType

from .exceptions import DashboardDoesNotExist


class DashboardHandler:
    def get_dashboard(
        self, dashboard_id: int, base_queryset: QuerySet | None = None
    ) -> Dashboard:
        """
        Get a dashboard by Id.

        :param dashboard_id: The Id of the dashboard to retrieve.
        :param: base_queryset: Optional queryset to be used.
        :raises DashboardDoesNotExist: If the dashboard doesn't exist.
        :return: The model instance of the requested Dashboard.
        """

        if base_queryset is None:
            base_queryset = Dashboard.objects

        try:
            return base_queryset.select_related("workspace").get(id=dashboard_id)
        except Dashboard.DoesNotExist:
            raise DashboardDoesNotExist

    def enable_sharing(self, user: AbstractUser, dashboard: Dashboard) -> Dashboard:
        """
        Enables public sharing for the given dashboard.

        :param user: The user requesting the action.
        :param dashboard: The dashboard to enable sharing for.
        :raises PermissionException: If user lacks application.update permission.
        :return: The updated dashboard.
        """

        CoreHandler().check_permissions(
            user,
            UpdateApplicationOperationType.type,
            workspace=dashboard.workspace,
            context=dashboard,
        )
        dashboard.public = True
        dashboard.save(update_fields=["public"])
        return dashboard

    def disable_sharing(self, user: AbstractUser, dashboard: Dashboard) -> Dashboard:
        """
        Disables public sharing for the given dashboard.

        :param user: The user requesting the action.
        :param dashboard: The dashboard to disable sharing for.
        :raises PermissionException: If user lacks application.update permission.
        :return: The updated dashboard.
        """

        CoreHandler().check_permissions(
            user,
            UpdateApplicationOperationType.type,
            workspace=dashboard.workspace,
            context=dashboard,
        )
        dashboard.public = False
        dashboard.save(update_fields=["public"])
        return dashboard

    def rotate_slug(self, user: AbstractUser, dashboard: Dashboard) -> Dashboard:
        """
        Rotates the share slug of the dashboard, invalidating the old public link.

        :param user: The user requesting the action.
        :param dashboard: The dashboard whose slug to rotate.
        :raises PermissionException: If user lacks application.update permission.
        :return: The updated dashboard.
        """

        CoreHandler().check_permissions(
            user,
            UpdateApplicationOperationType.type,
            workspace=dashboard.workspace,
            context=dashboard,
        )
        dashboard.slug = Dashboard.create_new_slug()
        dashboard.save(update_fields=["slug"])
        return dashboard

    def get_public_dashboard_by_slug(self, slug: str) -> Dashboard:
        """
        Returns the dashboard with the given slug if it is publicly shared.

        Returns 401 (AuthenticationFailed) for both "not found" and "found but
        public=False" to prevent existence oracle attacks.

        :param slug: The share slug of the dashboard.
        :raises AuthenticationFailed: If the dashboard does not exist or is not public.
        :return: The public dashboard.
        """

        try:
            dashboard = Dashboard.objects.select_related("workspace").get(
                slug=slug, public=True
            )
        except Dashboard.DoesNotExist:
            raise AuthenticationFailed(
                "The dashboard does not exist or is not publicly shared."
            )
        return dashboard
