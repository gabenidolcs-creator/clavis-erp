from django.dispatch import Signal

# Sent after geocode_address_task completes a geocode for a map-view pin.
# Story 3.14 wires a WebSocket broadcast receiver to this signal.
geocode_pin_updated = Signal()
