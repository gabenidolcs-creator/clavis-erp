from django.urls import include, path, re_path

from .data_sync import urls as data_sync_urls
from .export import urls as export_urls
from .field_rules import urls as field_rules_urls
from .fields import urls as field_urls
from .formula import urls as formula_urls
from .rows import urls as row_urls
from .tables import urls as table_urls
from .tokens import urls as token_urls
from .views import urls as view_urls
from .webhooks import urls as webhook_urls
from baserow.contrib.database.row_comments.api import urls as row_comment_urls

app_name = "baserow.contrib.database.api"

urlpatterns = [
    path("tables/", include(table_urls, namespace="tables")),
    path("views/", include(view_urls, namespace="views")),
    path("fields/", include(field_urls, namespace="fields")),
    path("webhooks/", include(webhook_urls, namespace="webhooks")),
    path("rows/", include(row_urls, namespace="rows")),
    path("tokens/", include(token_urls, namespace="tokens")),
    path("export/", include(export_urls, namespace="export")),
    path("formula/", include(formula_urls, namespace="formula")),
    path("data-sync/", include(data_sync_urls, namespace="data_sync")),
    path("field-rules/", include(field_rules_urls, namespace="field_rules")),
    re_path(
        r"rows/table/(?P<table_id>[0-9]+)/(?P<row_id>[0-9]+)/comments/",
        include(row_comment_urls, namespace="row_comments"),
    ),
]
