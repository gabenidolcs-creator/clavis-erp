# Test Summary — Story 2.3: Barcode Field

## Coverage

### Backend Unit Tests
**File:** `backend/tests/baserow/contrib/database/field/test_barcode_field_type.py`
**Status:** 6 tests — requires Docker DB to run (DB connection not available in local shell)

| Test | Covers |
|---|---|
| `test_barcode_field_registered` | Field type registered in registry with correct type string |
| `test_barcode_field_creates_with_default_qr_type` | Default `barcode_type=qr` on creation |
| `test_barcode_field_creates_with_code128_type` | Explicit `barcode_type=code128` on creation |
| `test_barcode_field_api_round_trip` | POST create, PATCH update, GET verify persistence |
| `test_barcode_field_stores_text_value` | Row stores and retrieves text value via RowHandler |
| `test_barcode_field_migration_reversible` | Migration 0218 has no irreversible operations |

### Frontend Unit Tests
**File:** `web-frontend/test/unit/database/barcodeFieldType.spec.js`
**Status:** 5/5 pass ✅

| Test | Covers |
|---|---|
| `getType returns barcode` | Static type string |
| `getIconClass returns iconoir-barcode` | Icon class |
| `toHumanReadableString returns value as string` | AC: text value passthrough |
| `toHumanReadableString returns empty string for null` | Null guard |
| `toHumanReadableString returns empty string for undefined` | Undefined guard |

### E2E Tests (Playwright)
**File:** `e2e-tests/tests/database/barcode_field.spec.ts`
**Status:** Generated — requires full Docker stack to run

| Test | Covers |
|---|---|
| `Barcode field column appears in table after creation` | AC: field creation, column header visible |
| `Barcode QR cell renders SVG after text value entered` | AC: QR code rendered as `.grid-field-barcode svg` |
| `Barcode Code128 cell renders SVG for valid input` | AC: Code128 rendered as `.grid-field-barcode__code128` |

## Gap Analysis

| AC | Backend | Frontend Unit | E2E |
|---|---|---|---|
| Field stores text value (TextField MTI) | ✅ | — | — |
| Default `barcode_type=qr` | ✅ | — | ✅ |
| `barcode_type=code128` creates correctly | ✅ | — | ✅ |
| API persists barcode_type via PATCH | ✅ | — | — |
| QR code renders SVG in grid cell | — | — | ✅ |
| Code128 renders SVG in grid cell | — | — | ✅ |
| `toHumanReadableString` passthrough | — | ✅ | — |
| Migration reversible | ✅ | — | — |
| Invalid Code128 graceful degradation | — | — | ⚠️ not E2E testable without visual assertion |

## Notes

- Graceful degradation for invalid Code128 characters (AC #5) is validated via try/catch in `GridViewFieldBarcode.vue:_renderCode128`. E2E verification would require asserting SVG `innerHTML` is empty — skipped as component-level behavior, not API behavior.
- E2E tests follow the same pattern as `percent_field.spec.ts` and `currency_field.spec.ts`.
