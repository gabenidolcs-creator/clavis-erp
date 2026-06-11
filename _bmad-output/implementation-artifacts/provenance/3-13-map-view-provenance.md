# Story 3.13 — Map View Provenance Log

**Date:** 2026-06-11
**Bucket:** B (Greenfield — no premium/enterprise source read)
**Developer agent:** claude-sonnet-4-6

## Confirmation

Story 3.13 "Configure a Map View" is a Bucket B greenfield implementation.
No files were read from `premium/` or `enterprise/` directories during this
implementation. All new code was written net-new following existing core
patterns (GanttView structural template).

## New files created

### Backend
- `backend/src/baserow/contrib/database/views/map/__init__.py`
- `backend/src/baserow/contrib/database/views/map/handler.py`
- `backend/src/baserow/contrib/database/views/map/signals.py`
- `backend/src/baserow/contrib/database/api/views/map/__init__.py`
- `backend/src/baserow/contrib/database/api/views/map/errors.py`
- `backend/src/baserow/contrib/database/api/views/map/serializers.py`
- `backend/src/baserow/contrib/database/api/views/map/urls.py`
- `backend/src/baserow/contrib/database/api/views/map/views.py`
- `backend/src/baserow/contrib/database/migrations/0225_mapview_mapviewfieldoptions.py`

### Tests
- `backend/tests/baserow/contrib/database/view/test_map_view.py`
- `backend/tests/baserow/contrib/database/api/views/map/__init__.py`
- `backend/tests/baserow/contrib/database/api/views/map/test_map_view_rows.py`

### Frontend
- `web-frontend/modules/database/components/view/map/MapViewHeader.vue`
- `web-frontend/modules/database/components/view/map/MapView.vue`
- `web-frontend/modules/database/store/view/map.js`
- `web-frontend/modules/database/services/view/map.js`

## Modified files (core only)

- `backend/src/baserow/contrib/database/views/models.py` — added MapView, MapViewFieldOptions
- `backend/src/baserow/contrib/database/views/view_types.py` — added MapViewType
- `backend/src/baserow/contrib/database/apps.py` — registered MapViewType
- `backend/src/baserow/geocoding/tasks.py` — wired geocode_pin_updated signal
- `backend/src/baserow/test_utils/fixtures/view.py` — added create_map_view fixture
- `web-frontend/modules/database/viewTypes.js` — added MapViewType class
- `web-frontend/modules/database/plugin.js` — registered MapViewType
- `web-frontend/modules/database/plugin/store.js` — registered map store modules
- `web-frontend/modules/database/locales/en.json` — added mapViewHeader, mapView keys
- `web-frontend/locales/en.json` — added viewType.map translation
- `web-frontend/package.json` — added maplibre-gl@5.24
