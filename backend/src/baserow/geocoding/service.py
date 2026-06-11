import hashlib

from django.conf import settings
from django.db import IntegrityError

from baserow.core.exceptions import PermissionDenied
from baserow.geocoding.exceptions import GeocodingProviderNotConfigured
from baserow.geocoding.models import GeocodedAddress
from baserow.geocoding.providers import GoogleGeocodingProvider, NominatimProvider


def _hash_address(address: str) -> str:
    return hashlib.sha256(address.strip().lower().encode()).hexdigest()


class GeocodingService:
    _providers = {
        "nominatim": NominatimProvider,
        "google": GoogleGeocodingProvider,
    }

    def _get_provider(self):
        provider_name = settings.GEOCODING_PROVIDER
        cls = self._providers.get(provider_name)
        if cls is None:
            raise GeocodingProviderNotConfigured(
                f"Unknown GEOCODING_PROVIDER: {provider_name!r}. "
                f"Valid values: {list(self._providers)}"
            )
        return cls()

    def geocode(self, address: str) -> tuple[float, float]:
        """Cache-first geocode. Stores result on miss. Returns (lat, lng)."""
        if not address or not address.strip():
            raise ValueError("Address cannot be empty")
        address_hash = _hash_address(address)
        try:
            cached = GeocodedAddress.objects.get(address_hash=address_hash)
            return float(cached.latitude), float(cached.longitude)
        except GeocodedAddress.DoesNotExist:
            pass

        provider = self._get_provider()
        lat, lng = provider.geocode(address)

        try:
            GeocodedAddress.objects.update_or_create(
                address_hash=address_hash,
                defaults={
                    "latitude": lat,
                    "longitude": lng,
                    "provider": settings.GEOCODING_PROVIDER,
                },
            )
        except IntegrityError:
            pass
        return lat, lng

    def get_cached(self, address: str, actor=None, field=None):
        """Return cached (lat, lng) or None. Enforces field read permission when provided."""
        if actor is not None and field is not None:
            from baserow.contrib.database.fields.operations import (
                ReadFieldOperationType,
            )
            from baserow.core.handler import CoreHandler

            workspace = field.table.database.workspace
            try:
                CoreHandler().check_permissions(
                    actor,
                    ReadFieldOperationType.type,
                    workspace=workspace,
                    context=field,
                )
            except PermissionDenied:
                return None, None

        address_hash = _hash_address(address)
        try:
            cached = GeocodedAddress.objects.get(address_hash=address_hash)
            return float(cached.latitude), float(cached.longitude)
        except GeocodedAddress.DoesNotExist:
            return None, None

    def enqueue(self, address: str, row_id: int, field_id: int):
        """Non-blocking entrypoint — fires geocode_address_task and returns immediately."""
        from baserow.geocoding.tasks import geocode_address_task

        geocode_address_task.apply_async(
            kwargs={"address": address, "row_id": row_id, "field_id": field_id}
        )
