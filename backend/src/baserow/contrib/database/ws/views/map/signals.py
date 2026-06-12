from django.dispatch import receiver

from baserow.contrib.database.views.map.signals import geocode_pin_updated
from baserow.ws.registries import page_registry


@receiver(geocode_pin_updated)
def broadcast_geocode_pin_updated(sender, row_id, field_id, lat, lng, **kwargs):
    """
    Broadcast geocoded coordinates to all table page subscribers so the Map View
    frontend can add or move the pin without a full page reload.

    No transaction.on_commit — this receiver fires from a Celery worker task
    which has no surrounding DB transaction.
    """
    from baserow.contrib.database.fields.handler import FieldHandler

    try:
        field = FieldHandler().get_field(field_id)
    except Exception:
        return

    table_page_type = page_registry.get("table")
    payload = {
        "type": "geocode_pin_updated",
        "row_id": row_id,
        "lat": float(lat) if lat is not None else None,
        "lng": float(lng) if lng is not None else None,
        "table_id": field.table_id,
    }
    table_page_type.broadcast(payload, None, table_id=field.table_id)
