from django.urls import re_path

from .views import RowCommentsView, RowCommentView

app_name = "baserow.contrib.database.row_comments.api"

urlpatterns = [
    re_path(
        r"^$",
        RowCommentsView.as_view(),
        name="list",
    ),
    re_path(
        r"^(?P<comment_id>[0-9]+)/$",
        RowCommentView.as_view(),
        name="item",
    ),
]
