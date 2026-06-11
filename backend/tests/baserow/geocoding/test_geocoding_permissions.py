from unittest.mock import MagicMock, patch

import pytest

from baserow.geocoding.models import GeocodedAddress
from baserow.geocoding.service import GeocodingService, _hash_address


@pytest.mark.django_db
class TestGeocodingPermissions:
    def _make_field(self, workspace):
        field = MagicMock()
        field.table.database.workspace = workspace
        return field

    def test_get_cached_returns_coords_when_permitted(self):
        address = "1 Permitted Road"
        workspace = MagicMock()
        field = self._make_field(workspace)
        actor = MagicMock()

        GeocodedAddress.objects.update_or_create(
            address_hash=_hash_address(address),
            defaults={
                "latitude": 51.5074,
                "longitude": -0.1278,
                "provider": "nominatim",
            },
        )

        with patch(
            "baserow.core.handler.CoreHandler.check_permissions", return_value=None
        ):
            lat, lng = GeocodingService().get_cached(address, actor=actor, field=field)

        assert lat == pytest.approx(51.5074)
        assert lng == pytest.approx(-0.1278)

    def test_get_cached_returns_null_when_restricted(self):
        address = "2 Restricted Ave"
        workspace = MagicMock()
        field = self._make_field(workspace)
        actor = MagicMock()

        GeocodedAddress.objects.update_or_create(
            address_hash=_hash_address(address),
            defaults={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "provider": "nominatim",
            },
        )

        from baserow.core.exceptions import PermissionDenied

        with patch(
            "baserow.core.handler.CoreHandler.check_permissions",
            side_effect=PermissionDenied("field not readable"),
        ):
            lat, lng = GeocodingService().get_cached(address, actor=actor, field=field)

        assert lat is None
        assert lng is None

    def test_get_cached_without_actor_skips_permission_check(self):
        address = "3 No Actor Lane"
        GeocodedAddress.objects.update_or_create(
            address_hash=_hash_address(address),
            defaults={
                "latitude": 35.6762,
                "longitude": 139.6503,
                "provider": "nominatim",
            },
        )

        lat, lng = GeocodingService().get_cached(address)
        assert lat == pytest.approx(35.6762)
        assert lng == pytest.approx(139.6503)
