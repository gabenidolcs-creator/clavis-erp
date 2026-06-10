from django.urls import re_path

from .views import GanttViewView, PublicGanttViewRowsView

app_name = "baserow.contrib.database.api.views.gantt"

urlpatterns = [
    re_path(r"(?P<view_id>[0-9]+)/$", GanttViewView.as_view(), name="list"),
    re_path(
        r"(?P<slug>[-\w]+)/public/rows/$",
        PublicGanttViewRowsView.as_view(),
        name="public_rows",
    ),
]
