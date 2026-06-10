from django.urls import re_path

from .views import (
    GanttViewDependenciesView,
    GanttViewDependencyView,
    GanttViewView,
    PublicGanttViewDependenciesView,
    PublicGanttViewRowsView,
)

app_name = "baserow.contrib.database.api.views.gantt"

urlpatterns = [
    re_path(
        r"(?P<view_id>[0-9]+)/dependencies/$",
        GanttViewDependenciesView.as_view(),
        name="dependencies",
    ),
    re_path(
        r"(?P<view_id>[0-9]+)/dependencies/(?P<dependency_id>[0-9]+)/$",
        GanttViewDependencyView.as_view(),
        name="dependency",
    ),
    re_path(r"(?P<view_id>[0-9]+)/$", GanttViewView.as_view(), name="list"),
    re_path(
        r"(?P<slug>[-\w]+)/public/rows/$",
        PublicGanttViewRowsView.as_view(),
        name="public_rows",
    ),
    re_path(
        r"(?P<slug>[-\w]+)/public/dependencies/$",
        PublicGanttViewDependenciesView.as_view(),
        name="public_dependencies",
    ),
]
