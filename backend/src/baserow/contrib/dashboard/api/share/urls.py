from django.urls import re_path

from .views import (
    DisableDashboardSharingView,
    EnableDashboardSharingView,
    PublicDashboardDataSourceDispatchView,
    PublicDashboardView,
    RotateDashboardSlugView,
)

app_name = "baserow.contrib.dashboard.api.share"

urlpatterns = [
    re_path(
        r"(?P<dashboard_id>[0-9]+)/share/enable/$",
        EnableDashboardSharingView.as_view(),
        name="enable",
    ),
    re_path(
        r"(?P<dashboard_id>[0-9]+)/share/disable/$",
        DisableDashboardSharingView.as_view(),
        name="disable",
    ),
    re_path(
        r"(?P<dashboard_id>[0-9]+)/share/rotate-slug/$",
        RotateDashboardSlugView.as_view(),
        name="rotate_slug",
    ),
    re_path(
        r"public/(?P<slug>[A-Za-z0-9_-]+)/$",
        PublicDashboardView.as_view(),
        name="public_dashboard",
    ),
    re_path(
        r"public/(?P<slug>[A-Za-z0-9_-]+)/dispatch/(?P<data_source_id>[0-9]+)/$",
        PublicDashboardDataSourceDispatchView.as_view(),
        name="public_dispatch",
    ),
]
