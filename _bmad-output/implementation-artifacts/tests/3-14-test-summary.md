# Test Automation Summary — Story 3.14: Geocode and Interact with Map Pins

**Workflow:** bmad-qa-generate-e2e-tests
**Date:** 2026-06-12

## Generated Tests

### Backend Tests
- [x] `backend/tests/baserow/contrib/database/ws/views/map/test_map_ws_signals.py` — WS broadcast receiver
  - `test_broadcast_geocode_pin_updated` — valid coordinates broadcast to correct channel group
  - `test_broadcast_geocode_pin_updated_none_coordinates` — None lat/lng forwarded as None
  - `test_broadcast_geocode_pin_updated_invalid_field` — unknown field_id suppressed (no broadcast)

### Frontend Unit Tests
- [x] `web-frontend/test/unit/database/store/view/map.spec.js` — Vuex store behaviors
  - `pinUpdated` → adds new pin when row_id not in pins
  - `pinUpdated` → replaces existing pin by row_id
  - `pinUpdated` → removes row from `unresolvable` when resolved
  - `pinUpdated` → leaves `unresolvable` unchanged when row was not there
  - `selectRow` → sets `selectedRowId` in state
  - `selectRow` → can clear `selectedRowId` to null
  - `fetchRows` → loads pins and unresolvable from API response *(gap filled)*
  - `fetchRows` → resets loading to false after success *(gap filled)*
  - `fetchRows` → resets loading to false on API error *(gap filled)*
  - `fetchRows` → handles empty/missing fields in response *(gap filled)*

## Coverage

| Layer | AC | Tests |
|---|---|---|
| Backend WS broadcast (AC#1) | ✅ | 3 backend tests |
| Store pinUpdated / UPDATE_PIN (AC#1) | ✅ | 4 frontend tests |
| Store selectRow (AC#2) | ✅ | 2 frontend tests |
| Store fetchRows (primary data load) | ✅ | 4 frontend tests (gap filled) |
| MapView.vue GeoJSON clustering (AC#3) | — | MapLibre not runnable in JSDOM |
| realtime.js handler guard | — | No unit-test pattern in codebase |

## Test Results

- Backend: **3/3 passed** (local venv + PostgreSQL at 172.22.0.5)
- Frontend: **10/10 passed** (yarn vitest run)

## Gap Applied

Added `fetchRows` describe block (4 tests) to `web-frontend/test/unit/database/store/view/map.spec.js` covering:
- Happy path loads pins + unresolvable from API
- Loading flag cleared on success (finally block)
- Loading flag cleared on error (finally block)
- Empty/missing response fields default to `[]`
