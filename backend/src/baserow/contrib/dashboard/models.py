import secrets

from django.db import models

from baserow.contrib.dashboard.data_sources.models import DashboardDataSource
from baserow.contrib.dashboard.widgets.models import SummaryWidget, Widget
from baserow.core.models import Application

__all__ = ["Dashboard", "DashboardDataSource", "SummaryWidget", "Widget"]


class Dashboard(Application):
    description = models.TextField(blank=True, db_default="")
    slug = models.SlugField(
        default=secrets.token_urlsafe, unique=True, db_index=True, max_length=64
    )
    public = models.BooleanField(default=False, db_index=True)

    @classmethod
    def create_new_slug(cls) -> str:
        return secrets.token_urlsafe()

    def get_parent(self):
        # Parent is the Application here even if it's at the "same" level
        # but it's a more generic type
        return self.application_ptr
