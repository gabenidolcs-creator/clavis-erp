from abc import ABC, abstractmethod

from django.conf import settings

import requests

from baserow.geocoding.exceptions import (
    GeocodingProviderNotConfigured,
    GeocodingRequestFailed,
)


class GeocodingProvider(ABC):
    @abstractmethod
    def geocode(self, address: str) -> tuple[float, float]:
        """Return (latitude, longitude) for the given address string."""


class NominatimProvider(GeocodingProvider):
    def geocode(self, address: str) -> tuple[float, float]:
        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": settings.GEOCODING_NOMINATIM_USER_AGENT}
        params = {"q": address, "format": "json", "limit": 1}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise GeocodingRequestFailed(str(exc)) from exc

        data = resp.json()
        if not data:
            raise GeocodingRequestFailed(
                f"Nominatim returned no results for: {address}"
            )

        return float(data[0]["lat"]), float(data[0]["lon"])


class GoogleGeocodingProvider(GeocodingProvider):
    def geocode(self, address: str) -> tuple[float, float]:
        api_key = settings.GEOCODING_GOOGLE_API_KEY
        if not api_key:
            raise GeocodingProviderNotConfigured(
                "GEOCODING_GOOGLE_API_KEY is required when using the google provider."
            )

        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": address, "key": api_key}
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise GeocodingRequestFailed(str(exc)) from exc

        data = resp.json()
        results = data.get("results", [])
        if not results:
            raise GeocodingRequestFailed(
                f"Google Geocoding returned no results for: {address}"
            )

        location = results[0]["geometry"]["location"]
        return float(location["lat"]), float(location["lng"])
