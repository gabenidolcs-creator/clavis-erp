from django.conf import settings

from baserow.config.celery import app


@app.task(
    bind=True,
    rate_limit=settings.GEOCODING_RATE_LIMIT,
)
def geocode_address_task(self, address: str, row_id: int, field_id: int):
    from baserow.contrib.database.views.map.signals import geocode_pin_updated
    from baserow.geocoding.service import GeocodingService

    lat, lng = GeocodingService().geocode(address)
    geocode_pin_updated.send(
        sender=None, row_id=row_id, field_id=field_id, lat=lat, lng=lng
    )
