from unittest.mock import patch

from django.conf import settings
from django.test import override_settings

import pytest

from baserow.geocoding.service import GeocodingService


@pytest.mark.django_db
class TestGeocodingTask:
    @override_settings(GEOCODING_PROVIDER="nominatim")
    @patch(
        "baserow.geocoding.providers.NominatimProvider.geocode", return_value=(1.0, 2.0)
    )
    def test_task_stores_geocoded_address(self, mock_geocode):
        from baserow.geocoding.models import GeocodedAddress
        from baserow.geocoding.service import _hash_address
        from baserow.geocoding.tasks import geocode_address_task

        GeocodedAddress.objects.all().delete()
        address = "100 Task Street"
        geocode_address_task.apply(
            kwargs={"address": address, "row_id": 1, "field_id": 2}
        )
        assert GeocodedAddress.objects.filter(
            address_hash=_hash_address(address)
        ).exists()

    def test_task_has_rate_limit_annotation(self):
        from baserow.geocoding.tasks import geocode_address_task

        rate_limit = geocode_address_task.rate_limit
        assert rate_limit == settings.GEOCODING_RATE_LIMIT

    def test_task_routes_to_geocoding_queue(self):
        routes = settings.CELERY_TASK_ROUTES
        assert "baserow.geocoding.tasks.geocode_address_task" in routes
        assert (
            routes["baserow.geocoding.tasks.geocode_address_task"]["queue"]
            == "geocoding"
        )

    @patch("baserow.geocoding.tasks.geocode_address_task.apply_async")
    def test_enqueue_fires_task_with_correct_kwargs(self, mock_apply):
        GeocodingService().enqueue("100 Enqueue St", row_id=5, field_id=7)
        mock_apply.assert_called_once_with(
            kwargs={"address": "100 Enqueue St", "row_id": 5, "field_id": 7}
        )
