class GeocodingProviderNotConfigured(Exception):
    """Raised when the selected geocoding provider is unknown or missing required config."""


class GeocodingRequestFailed(Exception):
    """Raised when a geocoding provider returns an error or empty response."""
