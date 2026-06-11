from unittest.mock import MagicMock, patch

from django.test import override_settings

import pytest

from baserow.geocoding.exceptions import (
    GeocodingProviderNotConfigured,
    GeocodingRequestFailed,
)
from baserow.geocoding.models import GeocodedAddress
from baserow.geocoding.service import GeocodingService, _hash_address


@pytest.mark.django_db
class TestGeocodingServiceProviderRouting:
    @override_settings(GEOCODING_PROVIDER="nominatim")
    @patch(
        "baserow.geocoding.providers.NominatimProvider.geocode", return_value=(1.0, 2.0)
    )
    def test_nominatim_provider_called_when_configured(self, mock_geocode):
        GeocodedAddress.objects.all().delete()
        lat, lng = GeocodingService().geocode("123 Main St")
        assert lat == 1.0
        assert lng == 2.0
        mock_geocode.assert_called_once_with("123 Main St")

    @override_settings(GEOCODING_PROVIDER="google", GEOCODING_GOOGLE_API_KEY="test-key")
    @patch(
        "baserow.geocoding.providers.GoogleGeocodingProvider.geocode",
        return_value=(3.0, 4.0),
    )
    def test_google_provider_called_when_configured(self, mock_geocode):
        GeocodedAddress.objects.all().delete()
        lat, lng = GeocodingService().geocode("456 Oak Ave")
        assert lat == 3.0
        assert lng == 4.0
        mock_geocode.assert_called_once_with("456 Oak Ave")

    @override_settings(GEOCODING_PROVIDER="unknown_provider")
    def test_unknown_provider_raises_not_configured(self):
        GeocodedAddress.objects.all().delete()
        with pytest.raises(GeocodingProviderNotConfigured):
            GeocodingService().geocode("789 Elm St")


@pytest.mark.django_db
class TestGeocodingServiceCache:
    @override_settings(GEOCODING_PROVIDER="nominatim")
    @patch(
        "baserow.geocoding.providers.NominatimProvider.geocode",
        return_value=(10.0, 20.0),
    )
    def test_cache_miss_stores_result(self, mock_geocode):
        GeocodedAddress.objects.all().delete()
        address = "1 Cache Miss Lane"
        lat, lng = GeocodingService().geocode(address)
        assert lat == 10.0
        assert lng == 20.0
        cached = GeocodedAddress.objects.get(address_hash=_hash_address(address))
        assert float(cached.latitude) == 10.0
        assert float(cached.longitude) == 20.0

    @override_settings(GEOCODING_PROVIDER="nominatim")
    @patch("baserow.geocoding.providers.NominatimProvider.geocode")
    def test_cache_hit_skips_provider_call(self, mock_geocode):
        address = "1 Cache Hit Blvd"
        GeocodedAddress.objects.update_or_create(
            address_hash=_hash_address(address),
            defaults={"latitude": 5.0, "longitude": 6.0, "provider": "nominatim"},
        )
        lat, lng = GeocodingService().geocode(address)
        assert lat == 5.0
        assert lng == 6.0
        mock_geocode.assert_not_called()


@pytest.mark.django_db
class TestGeocodingServiceGetCached:
    def test_returns_cached_coords_without_actor(self):
        address = "42 Cached Ave"
        GeocodedAddress.objects.update_or_create(
            address_hash=_hash_address(address),
            defaults={
                "latitude": 51.5074,
                "longitude": -0.1278,
                "provider": "nominatim",
            },
        )
        lat, lng = GeocodingService().get_cached(address)
        assert lat == pytest.approx(51.5074)
        assert lng == pytest.approx(-0.1278)

    def test_returns_none_on_cache_miss(self):
        lat, lng = GeocodingService().get_cached("Nonexistent Place XYZ123_unique")
        assert lat is None
        assert lng is None


@pytest.mark.django_db
class TestNominatimProvider:
    @override_settings(GEOCODING_NOMINATIM_USER_AGENT="test-agent/1.0")
    @patch("requests.get")
    def test_user_agent_sent(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"lat": "48.8566", "lon": "2.3522"}]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        from baserow.geocoding.providers import NominatimProvider

        lat, lng = NominatimProvider().geocode("Paris, France")

        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["headers"]["User-Agent"] == "test-agent/1.0"
        assert lat == pytest.approx(48.8566)
        assert lng == pytest.approx(2.3522)

    @patch("requests.get")
    def test_empty_response_raises_failed(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        from baserow.geocoding.providers import NominatimProvider

        with pytest.raises(GeocodingRequestFailed):
            NominatimProvider().geocode("Nowhere, Zzz")

    @patch("requests.get")
    def test_http_error_raises_failed(self, mock_get):
        import requests as req

        mock_get.side_effect = req.RequestException("connection refused")

        from baserow.geocoding.providers import NominatimProvider

        with pytest.raises(GeocodingRequestFailed):
            NominatimProvider().geocode("Bad Place")


@pytest.mark.django_db
class TestGoogleGeocodingProvider:
    @override_settings(GEOCODING_GOOGLE_API_KEY="")
    def test_raises_when_api_key_empty(self):
        from baserow.geocoding.providers import GoogleGeocodingProvider

        with pytest.raises(GeocodingProviderNotConfigured):
            GoogleGeocodingProvider().geocode("Some Address")

    @override_settings(GEOCODING_GOOGLE_API_KEY="fake-key")
    @patch("requests.get")
    def test_parses_result(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": [{"geometry": {"location": {"lat": 37.4221, "lng": -122.0841}}}]
        }
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        from baserow.geocoding.providers import GoogleGeocodingProvider

        lat, lng = GoogleGeocodingProvider().geocode("1600 Amphitheatre Pkwy")
        assert lat == pytest.approx(37.4221)
        assert lng == pytest.approx(-122.0841)

    @override_settings(GEOCODING_GOOGLE_API_KEY="fake-key")
    @patch("requests.get")
    def test_empty_results_raises_failed(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        from baserow.geocoding.providers import GoogleGeocodingProvider

        with pytest.raises(GeocodingRequestFailed):
            GoogleGeocodingProvider().geocode("Nowhere Known")

    @override_settings(GEOCODING_GOOGLE_API_KEY="fake-key")
    @patch("requests.get")
    def test_http_error_raises_failed(self, mock_get):
        import requests as req

        mock_get.side_effect = req.RequestException("connection refused")

        from baserow.geocoding.providers import GoogleGeocodingProvider

        with pytest.raises(GeocodingRequestFailed):
            GoogleGeocodingProvider().geocode("Bad Place")
