from django.urls import re_path

from .views import MapViewRowsView

app_name = "baserow.contrib.database.api.views.map"

urlpatterns = [
    re_path(
        r"(?P<view_id>[0-9]+)/rows/$",
        MapViewRowsView.as_view(),
        name="rows",
    ),
]
