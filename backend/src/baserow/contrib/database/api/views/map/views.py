from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from baserow.api.decorators import map_exceptions
from baserow.api.errors import ERROR_USER_NOT_IN_GROUP
from baserow.contrib.database.table.operations import ListRowsDatabaseTableOperationType
from baserow.contrib.database.views.exceptions import ViewDoesNotExist
from baserow.contrib.database.views.handler import ViewHandler
from baserow.contrib.database.views.map.handler import MapViewHandler
from baserow.contrib.database.views.models import MapView
from baserow.contrib.database.views.operations import ListViewRowsOperationType
from baserow.contrib.database.views.utils import check_permissions_with_view_fallback
from baserow.core.exceptions import UserNotInWorkspace

from .errors import ERROR_MAP_NO_LOCATION_SOURCE, ERROR_MAP_VIEW_DOES_NOT_EXIST
from .serializers import MapViewRowsResponseSerializer


class MapViewRowsView(APIView):
    @extend_schema(
        tags=["Database table map view"],
        operation_id="list_database_table_map_view_rows",
        description=(
            "Returns the rows for a map view partitioned into `pins` "
            "(rows with resolved lat/lng) and `unresolvable` (rows without a "
            "cached location). Filters and sorts configured on the view are applied. "
            "Does NOT trigger geocoding; cache misses are queued asynchronously."
        ),
        responses={200: MapViewRowsResponseSerializer},
    )
    @map_exceptions(
        {
            ViewDoesNotExist: ERROR_MAP_VIEW_DOES_NOT_EXIST,
            UserNotInWorkspace: ERROR_USER_NOT_IN_GROUP,
        }
    )
    def get(self, request: Request, view_id: int) -> Response:
        view = ViewHandler().get_view_as_user(request.user, view_id, MapView)

        check_permissions_with_view_fallback(
            ListRowsDatabaseTableOperationType.type,
            ListViewRowsOperationType.type,
            request.user,
            view.table,
            view,
        )

        if view.address_field_id is None and (
            view.lat_field_id is None or view.lng_field_id is None
        ):
            from baserow.api.exceptions import RequestBodyValidationException

            raise RequestBodyValidationException(
                {
                    "non_field_errors": [
                        {
                            "error": ERROR_MAP_NO_LOCATION_SOURCE[0],
                            "code": "error",
                        }
                    ]
                }
            )

        model = view.table.get_model()
        result = MapViewHandler().get_rows(view, request.user, model)
        serializer = MapViewRowsResponseSerializer(result)
        return Response(serializer.data)
