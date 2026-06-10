from django.urls import re_path

from .views import CalendarViewView, PublicCalendarViewRowsView

app_name = "baserow.contrib.database.api.views.calendar"

urlpatterns = [
    re_path(r"(?P<view_id>[0-9]+)/$", CalendarViewView.as_view(), name="list"),
    re_path(
        r"(?P<slug>[-\w]+)/public/rows/$",
        PublicCalendarViewRowsView.as_view(),
        name="public_rows",
    ),
]
