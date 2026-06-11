from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

ERROR_MAP_VIEW_DOES_NOT_EXIST = (
    "ERROR_MAP_VIEW_DOES_NOT_EXIST",
    HTTP_404_NOT_FOUND,
    "The requested map view does not exist.",
)

ERROR_MAP_NO_LOCATION_SOURCE = (
    "ERROR_MAP_NO_LOCATION_SOURCE",
    HTTP_400_BAD_REQUEST,
    "The map view has no location source configured. "
    "Set address_field or lat_field+lng_field.",
)
