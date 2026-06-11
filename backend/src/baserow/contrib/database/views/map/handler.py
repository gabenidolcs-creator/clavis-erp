from typing import Any

from baserow.contrib.database.views.handler import ViewHandler
from baserow.geocoding.service import GeocodingService


class MapViewHandler:
    def get_rows(self, view, user, model) -> dict[str, list[dict[str, Any]]]:
        """
        Returns rows partitioned into ``pins`` (resolved lat/lng) and
        ``unresolvable`` (no cached coordinate) after applying view filters
        and sorts.

        Two location-source modes:
        - Address mode: ``view.address_field`` set → geocoding service lookup.
        - Lat/lng pair mode: ``view.lat_field`` + ``view.lng_field`` set → direct
          field value read, no geocoding.

        GET calls must NOT block on network geocoding; cache misses are queued
        via ``GeocodingService.enqueue()`` and the row lands in ``unresolvable``
        for this request.
        """
        qs = model.objects.all().enhance_by_fields()
        qs = ViewHandler().apply_filters(view, qs)
        qs = ViewHandler().apply_sorting(view, qs)

        pins = []
        unresolvable = []

        address_field = view.address_field
        lat_field = view.lat_field
        lng_field = view.lng_field

        for row in qs:
            if address_field is not None:
                # Address mode: geocode via cache only
                address_attr = f"field_{address_field.id}"
                address_value = getattr(row, address_attr, None) or ""
                address_value = str(address_value).strip()

                if not address_value:
                    unresolvable.append({"row_id": row.id})
                    continue

                lat, lng = GeocodingService().get_cached(
                    address_value, actor=user, field=address_field
                )
                if lat is not None and lng is not None:
                    pins.append({"row_id": row.id, "lat": lat, "lng": lng})
                else:
                    # Enqueue async geocoding for the next request to resolve
                    GeocodingService().enqueue(address_value, row.id, address_field.id)
                    unresolvable.append({"row_id": row.id})

            elif lat_field is not None and lng_field is not None:
                # Lat/lng pair mode: read numeric values directly
                lat_attr = f"field_{lat_field.id}"
                lng_attr = f"field_{lng_field.id}"
                lat_val = getattr(row, lat_attr, None)
                lng_val = getattr(row, lng_attr, None)

                if lat_val is not None and lng_val is not None:
                    try:
                        pins.append(
                            {
                                "row_id": row.id,
                                "lat": float(lat_val),
                                "lng": float(lng_val),
                            }
                        )
                    except (TypeError, ValueError):
                        unresolvable.append({"row_id": row.id})
                else:
                    unresolvable.append({"row_id": row.id})

            else:
                # No location source configured → unresolvable
                unresolvable.append({"row_id": row.id})

        return {"pins": pins, "unresolvable": unresolvable}
