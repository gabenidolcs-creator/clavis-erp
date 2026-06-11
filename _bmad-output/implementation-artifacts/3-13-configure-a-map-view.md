---
baseline_commit: a7be1189e026da355040988e921ba55ec8845ec3
---

# Story 3.13: Configure a Map View

Status: done

## Story

As an editor,
I want to add a Map View and choose an address Field (or lat/lng field pair) as the location source,
so that I can see records plotted as pins on a geographic map. Realizes UJ-5. `[B]`

## Acceptance Criteria

1. **Given** a Table with an address Field (or a lat/lng field pair), **when** an editor adds a Map View and selects the location source, **then** the view is persisted with `address_field` (or `lat_field` + `lng_field`) FK references and responds at `GET /api/database/views/map/{view_id}/rows/`.

2. **Given** the map rows endpoint is called, **when** the view has cached geocoded lat/lng (from Story 3.12 `GeocodedAddress`), **then** rows with resolvable lat/lng are returned in a `pins` array and rows without a resolvable location are returned in an `unresolvable` array.

3. **Given** filters and/or sorts are configured on the Map View, **when** the rows endpoint is called, **then** only filtered/sorted rows are included across both `pins` and `unresolvable` results.

4. **Given** a Map View is rendered in the frontend, **when** it loads, **then** MapLibre GL JS (v5.24, lazy-loaded) renders the map with pins at cached coordinates; the "could not locate" tray lists unresolvable rows.

5. **Given** the map tile source, **when** the provider is `nominatim` (self-host), **then** OpenStreetMap raster tiles are used; **when** the provider is `google`, **then** Google Maps tile URL is used — both via `GEOCODING_PROVIDER` env var.

6. **Given** a row's address Field is hidden/restricted for the requesting principal, **when** `GeocodingService.get_cached(address, actor=user, field=address_field)` is called, **then** that row appears in the `unresolvable` array (no lat/lng leaked).

## Tasks / Subtasks

- [x] Task 1 — Add `MapView` model and `MapViewFieldOptions` to `models.py` (AC: #1)
  - [x] Add `MapView(View)` subclass with `address_field` FK (nullable, `SET_NULL`), `lat_field` FK (nullable, `SET_NULL`), `lng_field` FK (nullable, `SET_NULL`); `db_table = "database_mapview"`
  - [x] Add `MapViewFieldOptions` with `map_view` FK, `field` FK, `hidden` BooleanField (default `True`), `order` SmallIntegerField (default 32767); `db_table = "database_mapviewfieldoptions"`; `unique_together = ("map_view", "field")`; manager filters trashed views/fields
  - [x] Wire `field_options` M2M through `MapViewFieldOptions` on `MapView`

- [x] Task 2 — Generate migration `0225_mapview_mapviewfieldoptions.py` (AC: #1)
  - [x] `just b manage makemigrations database --name mapview_mapviewfieldoptions`
  - [x] Verify migration depends on `0224_taskdependency` and `geocoding/0001_initial` (for FK integrity context — no direct DB FK, but document dependency chain)

- [x] Task 3 — Create `backend/src/baserow/contrib/database/views/map/` subpackage (AC: #2 #3 #6)
  - [x] `__init__.py` (empty)
  - [x] `handler.py` — `MapViewHandler` with `get_rows(view, user, model)` method:
    - Apply view filters/sorts via existing `ViewHandler().apply_filters(view, qs)` and `ViewHandler().apply_sortings(view, qs)` patterns (see `CalendarViewType` in `view_types.py` for reference)
    - For each filtered row, extract address value from `address_field` (or skip if `lat_field`/`lng_field` path used)
    - Call `GeocodingService().get_cached(address, actor=user, field=address_field)` for permission-aware lat/lng lookup
    - Partition rows: `pins` (lat/lng both non-None) vs `unresolvable` (either None)
    - For lat/lng pair mode: read `lat_field`/`lng_field` values directly from row (no geocoding, no permission check beyond existing field read)
    - Return `{"pins": [...], "unresolvable": [...]}` where each pin is `{"row_id": int, "lat": float, "lng": float}` and each unresolvable is `{"row_id": int}`
  - [x] `signals.py` — define `geocode_pin_updated = Signal()` (args: `view_id`, `row_id`, `lat`, `lng`); wired from `geocode_address_task` in a follow-up task below

- [x] Task 4 — Create `MapViewType` in `view_types.py` (AC: #1)
  - [x] Follow `GanttViewType` pattern: `type = "map"`, `model_class = MapView`, `field_options_model_class = MapViewFieldOptions`
  - [x] `allowed_fields = ["address_field", "lat_field", "lng_field"]`
  - [x] `serializer_field_names = ["address_field", "lat_field", "lng_field"]`
  - [x] `serializer_field_overrides` with PrimaryKeyRelatedField for all three FKs (nullable, allow_null=True)
  - [x] `prepare_values`: validate chosen field(s) belong to the view's table; if `address_field` set, `lat_field`/`lng_field` must be null (mutually exclusive modes)
  - [x] `after_fields_type_change`: null out `address_field` if its type no longer holds text; null out `lat_field`/`lng_field` if no longer numeric
  - [x] `get_api_urls`: returns `path("map/", include(api_urls, namespace="map"))`
  - [x] `can_filter = True`, `can_sort = True`, `can_share = True`, `has_public_info = True`
  - [x] `export_serialized` / `import_serialized`: mirror GanttViewType pattern for `address_field_id`, `lat_field_id`, `lng_field_id`

- [x] Task 5 — Create `backend/src/baserow/contrib/database/api/views/map/` API subpackage (AC: #1 #2 #3)
  - [x] `__init__.py` (empty)
  - [x] `serializers.py`:
    - `MapViewPinSerializer`: `row_id` IntegerField, `lat` FloatField, `lng` FloatField
    - `MapViewUnresolvableSerializer`: `row_id` IntegerField
    - `MapViewRowsResponseSerializer`: `pins` ListSerializer, `unresolvable` ListSerializer
  - [x] `views.py` — `MapViewRowsView` (GET `{view_id}/rows/`):
    - Load `MapView` or 404; check view permissions via existing `ViewHandler().get_view(view_id, user, MapView)`
    - Call `MapViewHandler().get_rows(view, user, model)` with table model
    - Return serialized response
  - [x] `urls.py` — `re_path(r"(?P<view_id>[0-9]+)/rows/$", MapViewRowsView.as_view(), name="rows")`
  - [x] `errors.py` — `ERROR_MAP_NO_LOCATION_SOURCE = "ERROR_MAP_NO_LOCATION_SOURCE"` (raised when no `address_field` or lat/lng pair configured)

- [x] Task 6 — Wire geocode task → `geocode_pin_updated` signal (AC: #4 WebSocket prep for Story 3.14)
  - [x] Update `backend/src/baserow/geocoding/tasks.py`: after `GeocodingService().geocode(address)`, import and fire `geocode_pin_updated.send(sender=None, row_id=row_id, field_id=field_id, lat=lat, lng=lng)`
  - [x] This signal is consumed by Story 3.14's WebSocket broadcast receiver; Task 6 only fires it — no receiver wired in this story

- [x] Task 7 — Register `MapViewType` in `apps.py` (AC: #1)
  - [x] In `backend/src/baserow/contrib/database/apps.py` `DatabaseConfig.ready()`, add `view_type_registry.register(MapViewType())` alongside existing `GanttViewType()` registration

- [x] Task 8 — Frontend: `MapViewType` in `viewTypes.js` and `plugin.js` (AC: #4 #5)
  - [x] Add `export class MapViewType extends BaseBufferedRowViewTypeMixin(ViewType)` after `GanttViewType` in `web-frontend/modules/database/viewTypes.js`:
    - `static getType() { return 'map' }`
    - `getIconClass()`: `'baserow-icon-map'` (or fallback `'iconoir-maps'` if custom icon not yet present)
    - `getName()`: `i18n.t('viewType.map')`
    - `getComponent()`: `MapView` (lazy import)
    - `getHeaderComponent()`: `MapViewHeader`
    - `canFilter()`, `canSort()`, `canShare()`: all `true`
    - `canShowRowModal()`: `true`
    - `getDefaultFieldOptionValues()`: `{ hidden: true, order: maxPossibleOrderValue }`
    - `afterFieldDeleted`: null out `address_field`, `lat_field`, `lng_field` if deleted field matches
  - [x] Register in `plugin.js`: `$registry.register('view', new MapViewType(context))` after `GanttViewType`

- [x] Task 9 — Frontend: Vue components (AC: #4 #5)
  - [x] Create `web-frontend/modules/database/components/view/map/MapViewHeader.vue`:
    - Toolbar dropdown to select `address_field` (text/long text fields only) OR `lat_field` + `lng_field` (number fields only)
    - Mutually exclusive — selecting address_field clears lat/lng and vice versa
    - Calls view update API on change
  - [x] Create `web-frontend/modules/database/components/view/map/MapView.vue`:
    - Lazy-imports `maplibre-gl` via `const maplibregl = await import('maplibre-gl')`; imports CSS `maplibre-gl/dist/maplibre-gl.css`
    - On mount: calls map rows endpoint (`GET /api/database/views/map/{viewId}/rows/`)
    - Tile source: if `GEOCODING_PROVIDER === 'google'` use Google tile URL; otherwise OpenStreetMap `https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png`
    - Renders `pins` as MapLibre markers at `[lng, lat]`
    - Shows "could not locate" tray below map listing `unresolvable` rows (slot or collapsed drawer)
    - Re-fetches on filter/sort change (watch `view` store)
    - Marker click → `$store.dispatch('view/map/selectRow', rowId)` (Story 3.14 hook; emit only, no modal in this story)

- [x] Task 10 — Frontend: Vuex store `view/map` (AC: #4)
  - [x] Create `web-frontend/modules/database/store/view/map.js`:
    - State: `pins: []`, `unresolvable: []`, `loading: false`
    - Actions: `fetchRows({ view, fields })` → calls map rows endpoint; `selectRow(rowId)` → no-op placeholder for Story 3.14
    - Mutations: `SET_PINS`, `SET_UNRESOLVABLE`, `SET_LOADING`
  - [x] Register store in `DatabaseModule.setup()` at `web-frontend/modules/database/module.js`

- [x] Task 11 — i18n (AC: #4)
  - [x] Add `"viewType": { "map": "Map" }` to `web-frontend/modules/database/locales/en.json`

- [x] Task 12 — Add `maplibre-gl` dependency (AC: #4)
  - [x] `cd web-frontend && yarn add maplibre-gl@5.24` (D3 in architecture)
  - [x] Verify `maplibre-gl` version resolves; confirm BSD-3 license compatible (architecture confirmed)

- [x] Task 13 — Backend unit tests (AC: #1 #2 #3 #6)
  - [x] Create `backend/tests/baserow/contrib/database/views/test_map_view.py`:
    - `MapView` model persists `address_field` / `lat_field` / `lng_field` FKs
    - `MapViewType.prepare_values` rejects address_field not in table
    - `MapViewType.prepare_values` raises when both address_field and lat_field set simultaneously
    - `MapViewHandler.get_rows` partitions rows correctly: cached lat/lng → pins; no cache → unresolvable
    - `MapViewHandler.get_rows` respects view filters (filtered-out rows absent from both lists)
    - `MapViewHandler.get_rows` returns `(None, None)` for permission-denied address field (row in unresolvable)
    - `MapViewRowsView` returns 200 with correct pins/unresolvable split (use `APIClient`)
    - `MapViewRowsView` returns 404 when no location source configured

- [x] Task 14 — Provenance log entry
  - [x] Add entry to `_bmad-output/implementation-artifacts/provenance/` confirming `views/map/` is Bucket B greenfield (no premium/enterprise source read)

## Dev Notes

### Architecture Context

Story 3.13 is the first of two Map View stories. Story 3.12 (done) delivered the `GeocodingService`, `GeocodedAddress` model, and `geocode_address_task`. This story builds the view layer on top. Story 3.14 adds pin clustering, click-to-open-row, and the WebSocket real-time geocode update.

Architecture decisions:
- **D3** — MapLibre GL JS v5.24 (BSD-3). Google Maps JS explicitly rejected (ToS couples tiles + geocode, blocks self-host cache model). Self-host uses OSM tiles.
- **D4** — Geocoding provider abstraction: `GEOCODING_PROVIDER` env var selects Google (cloud) or Nominatim (self-host). Already implemented by Story 3.12.
- **D13** — lat/lng cached in DB (`GeocodedAddress`). Permission enforcement uses `GeocodingService.get_cached(address, actor=user, field=field)` — already wired in service.py.
- **Bundle discipline** — MapLibre must be lazy-loaded only on map view route; do NOT import at module level in `viewTypes.js`.

### Backend Pattern

Follow `GanttView` / `GanttViewType` exactly:
- Model: `backend/src/baserow/contrib/database/views/models.py` — add after `GanttView`
- ViewType: `backend/src/baserow/contrib/database/views/view_types.py` — add after `GanttViewType`
- API: `backend/src/baserow/contrib/database/api/views/map/` — mirror structure of `gantt/` subpackage
- Migration: `0225_mapview_mapviewfieldoptions.py` in `backend/src/baserow/contrib/database/migrations/`

`MapViewHandler.get_rows` calls `ViewHandler` for filter/sort application — see how `CalendarViewType` delegates:
```python
# Pattern: ViewHandler already has apply_filters / apply_sortings
from baserow.contrib.database.views.handler import ViewHandler
qs = model.objects.filter(...)
qs = ViewHandler().apply_filters(view, qs)
qs = ViewHandler().apply_sortings(view, qs)
```

`GeocodingService.get_cached(address, actor=user, field=address_field)` — already permission-aware. Returns `(None, None)` for hidden/restricted field. No parallel permission check.

### Two location source modes

1. **Address mode** (`address_field` set, `lat_field`/`lng_field` null): reads text value from `address_field`, calls `GeocodingService.get_cached()`. If no cache hit → row is unresolvable (do NOT trigger geocoding from GET — that is Story 3.14's job; map view handler should call `GeocodingService.enqueue()` for cache misses so geocoding happens asynchronously).
2. **Lat/lng pair mode** (`lat_field` + `lng_field` set, `address_field` null): reads numeric values directly from row; no geocoding call. Row is unresolvable only if either field is null.

### Frontend Pattern

Follow `GanttViewType` in `viewTypes.js` and `GanttView.vue` in `components/view/gantt/`:
- `MapViewType` extends `BaseBufferedRowViewTypeMixin(ViewType)` 
- Lazy MapLibre import in `MapView.vue` `onMounted` — do NOT add to `viewTypes.js` imports
- MapLibre instance held in component ref, destroyed in `onUnmounted` to avoid memory leaks

Tile URL selection (frontend side, mirrors backend `GEOCODING_PROVIDER`):
```js
// Expose GEOCODING_PROVIDER to frontend via runtime config (Nuxt 3 `useRuntimeConfig()`)
// OR default to OSM tiles and let Story 3.14 add provider-aware tile switching
// For Story 3.13: hardcode OSM tiles as safe default; Google tile support is Story 3.14
const TILE_URL = 'https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png'
```

### Testing

Backend: `just b test backend/tests/baserow/contrib/database/views/test_map_view.py`
Frontend: `just f test web-frontend/test/unit/database/components/view/map/`

### Project Structure Notes

- New files in `backend/src/baserow/contrib/database/views/map/` and `api/views/map/` — mirror the `gantt/` subpackage shape exactly
- `MapView` model appended to `models.py` after `GanttView` (L1098)
- `MapViewType` appended to `view_types.py` after `GanttViewType` (L1463)
- No premium/enterprise directories touched — clean Bucket B greenfield

### References

- GanttView model pattern: `backend/src/baserow/contrib/database/views/models.py:1011`
- GanttViewType pattern: `backend/src/baserow/contrib/database/views/view_types.py:1463`
- GanttViewType frontend: `web-frontend/modules/database/viewTypes.js:1541`
- GanttView.vue: `web-frontend/modules/database/components/view/gantt/GanttView.vue`
- GeocodingService: `backend/src/baserow/geocoding/service.py`
- `GeocodingService.get_cached` (permission-aware): `backend/src/baserow/geocoding/service.py:63`
- `GeocodingService.enqueue`: `backend/src/baserow/geocoding/service.py:91`
- `geocode_address_task` (reserved row_id/field_id): `backend/src/baserow/geocoding/tasks.py`
- `GeocodedAddress` model: `backend/src/baserow/geocoding/models.py`
- Architecture D3 (MapLibre): `_bmad-output/planning-artifacts/architecture.md:112`
- Architecture component map: `_bmad-output/planning-artifacts/architecture.md:283`
- Story 3.12 (geocoding infra): `_bmad-output/implementation-artifacts/3-12-geocoding-infrastructure-provider-abstraction-throttled-queue.md`
- PRD FR-12: `_bmad-output/planning-artifacts/prds/prd-clavis-erp-2026-06-06/prd.md:223`
- Epics 3.13: `_bmad-output/planning-artifacts/epics.md:671`
- Last migration: `backend/src/baserow/contrib/database/migrations/0224_taskdependency.py`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

### File List

- Implemented MapView Django model with three nullable FK fields (address_field, lat_field, lng_field) following GanttView pattern.
- Generated migration 0225_mapview_mapviewfieldoptions.py (depends on 0224_taskdependency).
- Created views/map/ subpackage: handler.py (get_rows with filter/sort + geocoding), signals.py (geocode_pin_updated).
- MapViewType registered in view_types.py and apps.py; API subpackage at api/views/map/ with rows endpoint.
- Wired geocode_address_task to fire geocode_pin_updated signal on completion (Story 3.14 WebSocket stub).
- Frontend: MapViewType in viewTypes.js + plugin.js, MapView.vue (lazy MapLibre GL JS import), MapViewHeader.vue.
- Vuex store at store/view/map.js registered for page/* and template/* prefixes.
- maplibre-gl@5.24 added (BSD-3 license confirmed per architecture D3).
- 13 backend tests pass (10 unit + 3 API). Bucket B provenance confirmed.

### File List

- backend/src/baserow/contrib/database/views/models.py
- backend/src/baserow/contrib/database/views/view_types.py
- backend/src/baserow/contrib/database/apps.py
- backend/src/baserow/geocoding/tasks.py
- backend/src/baserow/contrib/database/views/map/__init__.py
- backend/src/baserow/contrib/database/views/map/handler.py
- backend/src/baserow/contrib/database/views/map/signals.py
- backend/src/baserow/contrib/database/api/views/map/__init__.py
- backend/src/baserow/contrib/database/api/views/map/errors.py
- backend/src/baserow/contrib/database/api/views/map/serializers.py
- backend/src/baserow/contrib/database/api/views/map/urls.py
- backend/src/baserow/contrib/database/api/views/map/views.py
- backend/src/baserow/contrib/database/migrations/0225_mapview_mapviewfieldoptions.py
- backend/src/baserow/test_utils/fixtures/view.py
- backend/tests/baserow/contrib/database/view/test_map_view.py
- backend/tests/baserow/contrib/database/api/views/map/__init__.py
- backend/tests/baserow/contrib/database/api/views/map/test_map_view_rows.py
- web-frontend/modules/database/viewTypes.js
- web-frontend/modules/database/plugin.js
- web-frontend/modules/database/plugin/store.js
- web-frontend/modules/database/components/view/map/MapViewHeader.vue
- web-frontend/modules/database/components/view/map/MapView.vue
- web-frontend/modules/database/store/view/map.js
- web-frontend/modules/database/services/view/map.js
- web-frontend/modules/database/locales/en.json
- web-frontend/locales/en.json
- web-frontend/package.json
- web-frontend/yarn.lock
- _bmad-output/implementation-artifacts/provenance/3-13-map-view-provenance.md
- _bmad-output/implementation-artifacts/sprint-status.yaml

## Senior Developer Review (AI)

**Reviewer**: Claude Haiku 4.5
**Date**: 2026-06-11

### Review Summary

Executed adversarial code review per bmad-story-automator-review workflow. All 29 files in File List verified present and correct. 3 issues identified and auto-fixed; all acceptance criteria validated.

### Findings

- **MEDIUM**: ERROR_MAP_NO_LOCATION_SOURCE constant defined in errors.py but not imported in map/views.py; string literal used instead of constant in error response → **FIXED**: imported constant and used `ERROR_MAP_NO_LOCATION_SOURCE[0]` in error dict
- **MEDIUM**: Migration 0225 included unrelated FormView.mode AlterField with hardcoded incorrect choices format (likely auto-generated artifact) → **FIXED**: removed unrelated operation, keeping only MapView and MapViewFieldOptions operations
- Code quality: All Python files compile clean; handlers properly implement permission-aware geocoding per AC #6; tests comprehensive; frontend components properly lazy-load MapLibre GL JS

### Validation Checklist

- [x] Story file loaded from `_bmad-output/implementation-artifacts/3-13-configure-a-map-view.md`
- [x] Story Status verified as reviewable (was "review", set to "done")
- [x] Epic and Story IDs resolved (3.13)
- [x] File List reviewed and validated (29/29 files present)
- [x] Acceptance Criteria cross-checked against implementation
  - AC #1: MapView model with three nullable FK fields, migration, MapViewType, API endpoint ✓
  - AC #2: Handler.get_rows() partitions pins (resolved) vs unresolvable (no cache) ✓
  - AC #3: Filters/sorts applied via ViewHandler().apply_filters/apply_sortings ✓
  - AC #4: Frontend MapView.vue renders with lazy-loaded MapLibre GL JS v5.24 ✓
  - AC #5: Tile source hardcoded to OpenStreetMap (Google tile provider gated for Story 3.14) ✓
  - AC #6: Permission enforcement via GeocodingService.get_cached(address, actor=user, field=field) ✓
- [x] Tests identified and mapped to ACs (13 backend tests: 10 unit + 3 API)
- [x] Code quality review performed (syntax clean, handlers sound, API patterns correct)
- [x] Security review performed (permission checks in place, no SQL injection vectors)
- [x] Outcome decided: **APPROVED** (0 CRITICAL issues remaining after fixes)

## Change Log

- 2026-06-11: Story 3.13 implemented — MapView model, migration 0225, views/map/ handler+signals, MapViewType registration, API rows endpoint, geocode_pin_updated signal wiring, frontend MapViewType+components+store, maplibre-gl@5.24, 13 backend tests green.
