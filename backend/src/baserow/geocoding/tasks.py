from django.conf import settings

from baserow.config.celery import app


@app.task(
    bind=True,
    rate_limit=settings.GEOCODING_RATE_LIMIT,
)
def geocode_address_task(self, address: str, row_id: int, field_id: int):
    # row_id and field_id are reserved for Story 3.13 (WebSocket signal on geocode completion)
    from baserow.geocoding.service import GeocodingService

    GeocodingService().geocode(address)
