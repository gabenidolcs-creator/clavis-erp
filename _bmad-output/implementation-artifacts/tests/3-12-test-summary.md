# Story 3.12 — Test Summary: Geocoding Infrastructure

**Generated:** 2026-06-11  
**Result:** 21 passed, 0 failed

---

## Coverage

| File | Tests | Notes |
|---|---|---|
| `test_geocoding_service.py` | 12 | Provider routing, cache hit/miss, `get_cached()`, HTTP errors |
| `test_geocoding_tasks.py` | 4 | Task execution, rate-limit annotation, queue route, `enqueue()` |
| `test_geocoding_permissions.py` | 3 | Field permission enforcement via `get_cached()` |
| **Total** | **21** | |

---

## Test Classes

### test_geocoding_service.py

**TestGeocodingServiceProviderRouting** (3 tests)
- `test_nominatim_provider_called_when_configured` — Nominatim dispatched when `GEOCODING_PROVIDER=nominatim`
- `test_google_provider_called_when_configured` — Google dispatched when `GEOCODING_PROVIDER=google`
- `test_unknown_provider_raises_not_configured` — `GeocodingProviderNotConfigured` on unknown provider

**TestGeocodingServiceCache** (2 tests)
- `test_cache_miss_stores_result` — On miss: calls provider, stores `GeocodedAddress` row, returns lat/lng
- `test_cache_hit_skips_provider_call` — On hit: returns cached coords, provider not called

**TestGeocodingServiceGetCached** (2 tests)
- `test_returns_cached_coords_without_actor` — `get_cached()` returns DB-cached lat/lng when no actor
- `test_returns_none_on_cache_miss` — `get_cached()` returns `(None, None)` when no DB entry

**TestNominatimProvider** (3 tests)
- `test_user_agent_sent` — OSM ToS User-Agent header set from `GEOCODING_NOMINATIM_USER_AGENT`
- `test_empty_response_raises_failed` — `GeocodingRequestFailed` on empty JSON array
- `test_http_error_raises_failed` — `GeocodingRequestFailed` on `requests.RequestException`

**TestGoogleGeocodingProvider** (4 tests)
- `test_raises_when_api_key_empty` — `GeocodingProviderNotConfigured` when `GEOCODING_GOOGLE_API_KEY=""`
- `test_parses_result` — Correct lat/lng extracted from Google API response structure
- `test_empty_results_raises_failed` — `GeocodingRequestFailed` on empty `results` array
- `test_http_error_raises_failed` — `GeocodingRequestFailed` on `requests.RequestException`

### test_geocoding_tasks.py

**TestGeocodingTask** (4 tests)
- `test_task_stores_geocoded_address` — Task execution persists `GeocodedAddress` row
- `test_task_has_rate_limit_annotation` — Task `rate_limit` matches `settings.GEOCODING_RATE_LIMIT`
- `test_task_routes_to_geocoding_queue` — `CELERY_TASK_ROUTES` maps task to `"geocoding"` queue
- `test_enqueue_fires_task_with_correct_kwargs` — `GeocodingService.enqueue()` calls `apply_async` with address/row_id/field_id

### test_geocoding_permissions.py

**TestGeocodingPermissions** (3 tests)
- `test_get_cached_returns_coords_when_permitted` — Returns lat/lng when `check_permissions` passes
- `test_get_cached_returns_null_when_restricted` — Returns `(None, None)` when `check_permissions` raises
- `test_get_cached_without_actor_skips_permission_check` — No permission check when `actor=None`

---

## AC Coverage

| AC | Tests |
|---|---|
| AC#1 — Provider abstraction, cache-first, throttled queue | 11 tests (routing, cache, task, enqueue) |
| AC#2 — Env vars follow pattern | Verified by `@override_settings` in all tests |
| AC#3 — Field permission enforcement | 3 tests in `test_geocoding_permissions.py` |

---

## No E2E Browser Tests

Story 3.12 is pure backend infrastructure with no API endpoint and no frontend. No browser E2E tests apply. Integration with the Map View UI is deferred to Stories 3.13 and 3.14.
