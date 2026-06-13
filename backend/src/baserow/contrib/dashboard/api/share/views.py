from django.contrib.auth.models import AnonymousUser

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from baserow.api.decorators import map_exceptions
from baserow.api.schemas import get_error_schema
from baserow.contrib.dashboard.api.data_sources.errors import (
    ERROR_DASHBOARD_DATA_DOES_NOT_EXIST,
    ERROR_DASHBOARD_DATA_SOURCE_DOES_NOT_EXIST,
    ERROR_DASHBOARD_DATA_SOURCE_IMPROPERLY_CONFIGURED,
)
from baserow.contrib.dashboard.api.errors import ERROR_DASHBOARD_DOES_NOT_EXIST
from baserow.contrib.dashboard.api.widgets.serializers import WidgetSerializer
from baserow.contrib.dashboard.data_sources.dispatch_context import (
    DashboardDispatchContext,
)
from baserow.contrib.dashboard.data_sources.exceptions import (
    DashboardDataSourceDoesNotExist,
    DashboardDataSourceImproperlyConfigured,
)
from baserow.contrib.dashboard.data_sources.handler import DashboardDataSourceHandler
from baserow.contrib.dashboard.exceptions import DashboardDoesNotExist
from baserow.contrib.dashboard.handler import DashboardHandler
from baserow.contrib.dashboard.widgets.handler import WidgetHandler
from baserow.core.services.exceptions import (
    DoesNotExist,
    ServiceImproperlyConfiguredDispatchException,
)

from .serializers import DashboardPublicSerializer, DashboardShareSerializer


class EnableDashboardSharingView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="dashboard_id",
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
                description="The dashboard to enable sharing for.",
            )
        ],
        tags=["Dashboard sharing"],
        operation_id="enable_dashboard_sharing",
        description="Enables public sharing for the dashboard.",
        responses={
            200: DashboardShareSerializer,
            401: get_error_schema(["ERROR_PERMISSION_DENIED"]),
            404: get_error_schema(["ERROR_DASHBOARD_DOES_NOT_EXIST"]),
        },
    )
    @map_exceptions({DashboardDoesNotExist: ERROR_DASHBOARD_DOES_NOT_EXIST})
    def post(self, request, dashboard_id: int):
        dashboard = DashboardHandler().get_dashboard(dashboard_id)
        dashboard = DashboardHandler().enable_sharing(request.user, dashboard)
        return Response(DashboardShareSerializer(dashboard).data)


class DisableDashboardSharingView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="dashboard_id",
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
                description="The dashboard to disable sharing for.",
            )
        ],
        tags=["Dashboard sharing"],
        operation_id="disable_dashboard_sharing",
        description="Disables public sharing for the dashboard.",
        responses={
            200: DashboardShareSerializer,
            401: get_error_schema(["ERROR_PERMISSION_DENIED"]),
            404: get_error_schema(["ERROR_DASHBOARD_DOES_NOT_EXIST"]),
        },
    )
    @map_exceptions({DashboardDoesNotExist: ERROR_DASHBOARD_DOES_NOT_EXIST})
    def post(self, request, dashboard_id: int):
        dashboard = DashboardHandler().get_dashboard(dashboard_id)
        dashboard = DashboardHandler().disable_sharing(request.user, dashboard)
        return Response(DashboardShareSerializer(dashboard).data)


class RotateDashboardSlugView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="dashboard_id",
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
                description="The dashboard whose share slug to rotate.",
            )
        ],
        tags=["Dashboard sharing"],
        operation_id="rotate_dashboard_share_slug",
        description="Rotates the share slug, invalidating the old public link.",
        responses={
            200: DashboardShareSerializer,
            401: get_error_schema(["ERROR_PERMISSION_DENIED"]),
            404: get_error_schema(["ERROR_DASHBOARD_DOES_NOT_EXIST"]),
        },
    )
    @map_exceptions({DashboardDoesNotExist: ERROR_DASHBOARD_DOES_NOT_EXIST})
    def post(self, request, dashboard_id: int):
        dashboard = DashboardHandler().get_dashboard(dashboard_id)
        dashboard = DashboardHandler().rotate_slug(request.user, dashboard)
        return Response(DashboardShareSerializer(dashboard).data)


class PublicDashboardView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="slug",
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.STR,
                description="The public share slug of the dashboard.",
            )
        ],
        tags=["Dashboard sharing"],
        operation_id="get_public_dashboard",
        description=(
            "Returns the public dashboard by slug. Returns 401 if the dashboard "
            "does not exist or is not publicly shared."
        ),
        responses={
            200: DashboardPublicSerializer,
            401: get_error_schema(["ERROR_PERMISSION_DENIED"]),
        },
    )
    def get(self, request, slug: str):
        dashboard = DashboardHandler().get_public_dashboard_by_slug(slug)
        widgets = WidgetHandler().get_widgets(dashboard)
        data_sources = DashboardDataSourceHandler().get_data_sources(dashboard)

        dashboard_data = DashboardPublicSerializer(dashboard).data
        dashboard_data["widgets"] = WidgetSerializer(widgets, many=True).data
        dashboard_data["data_sources"] = [
            {"id": ds.id, "name": ds.name} for ds in data_sources
        ]
        return Response(dashboard_data)


class PublicDashboardDataSourceDispatchView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="slug",
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.STR,
                description="The public share slug of the dashboard.",
            ),
            OpenApiParameter(
                name="data_source_id",
                location=OpenApiParameter.PATH,
                type=OpenApiTypes.INT,
                description="The data source to dispatch.",
            ),
        ],
        tags=["Dashboard sharing"],
        operation_id="dispatch_public_dashboard_data_source",
        description=(
            "Dispatches the data source under AnonymousUser so that "
            "field-permission deny-by-default applies (Story 1.8). "
            "Returns 401 if the dashboard slug is invalid or not public."
        ),
        responses={
            200: None,
            400: get_error_schema(
                ["ERROR_DASHBOARD_DATA_SOURCE_IMPROPERLY_CONFIGURED"]
            ),
            401: get_error_schema(["ERROR_PERMISSION_DENIED"]),
            404: get_error_schema(
                [
                    "ERROR_DASHBOARD_DATA_SOURCE_DOES_NOT_EXIST",
                    "ERROR_DASHBOARD_DATA_DOES_NOT_EXIST",
                ]
            ),
        },
    )
    @map_exceptions(
        {
            DashboardDataSourceDoesNotExist: ERROR_DASHBOARD_DATA_SOURCE_DOES_NOT_EXIST,
            DashboardDataSourceImproperlyConfigured: ERROR_DASHBOARD_DATA_SOURCE_IMPROPERLY_CONFIGURED,
            ServiceImproperlyConfiguredDispatchException: ERROR_DASHBOARD_DATA_SOURCE_IMPROPERLY_CONFIGURED,
            DoesNotExist: ERROR_DASHBOARD_DATA_DOES_NOT_EXIST,
        }
    )
    def get(self, request, slug: str, data_source_id: int):
        # 401 if dashboard not found or not public — no existence oracle
        dashboard = DashboardHandler().get_public_dashboard_by_slug(slug)

        # Verify data source belongs to this dashboard
        try:
            data_source = DashboardDataSourceHandler().get_data_source(data_source_id)
        except Exception:
            raise DashboardDataSourceDoesNotExist()

        if data_source.dashboard_id != dashboard.id:
            raise DashboardDataSourceDoesNotExist()

        # Dispatch under AnonymousUser so FieldPermissionManagerType deny-by-default fires
        request.user = AnonymousUser()
        dispatch_context = DashboardDispatchContext(request)
        result = DashboardDataSourceHandler().dispatch_data_source(
            data_source, dispatch_context
        )
        return Response(result)
