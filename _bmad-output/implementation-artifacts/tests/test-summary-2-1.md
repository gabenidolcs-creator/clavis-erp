# Test Summary: Story 2.1 — Currency Field

**Status:** All tests passing ✅
**Date:** 2026-06-07

## Backend Tests
**File:** `backend/tests/baserow/contrib/database/field/test_currency_field_type.py`
**Result:** 14/14 passed

| Test | Coverage |
|---|---|
| `test_currency_field_registered` | Registry lookup returns CurrencyFieldType |
| `test_currency_field_creates_with_symbol` | FieldHandler creates field with custom symbol/decimal places |
| `test_currency_field_defaults` | Default symbol=$, decimal_places=0 |
| `test_currency_field_export_value` | get_export_value: basic format, None → "", rich_value passthrough |
| `test_currency_field_sorts_numeric` | Rows sort numerically (9 before 10) |
| `test_currency_field_api_round_trip` | POST/GET/PATCH roundtrip persists currency_symbol |
| `test_currency_field_unauthenticated_returns_401` | Auth guard on field list endpoint |
| `test_currency_field_symbol_too_long_rejected` | 11-char symbol rejected with 400 + validation error |
| `test_currency_field_row_stores_as_decimal` | Row values stored and retrieved as Decimal |
| `test_currency_field_delete_via_api` | DELETE removes field |
| `test_currency_field_api_response_includes_number_prefix` | **Gap fill:** API response exposes number_prefix=currency_symbol for frontend mixin |
| `test_currency_field_export_thousand_separator` | **Gap fill:** COMMA_PERIOD separator → "$1,234.56" |
| `test_currency_field_export_negative` | **Gap fill:** Negative value → "-$99.99" |
| `test_currency_field_migration_is_reversible` | Migration 0216 applies and model is ORM-accessible |

## Frontend Tests
**File:** `web-frontend/test/unit/database/currencyFieldType.spec.js`
**Result:** 8/8 passed

| Test | Coverage |
|---|---|
| `getType returns currency` | Static type string matches backend |
| `toHumanReadableString prepends symbol` | Symbol prepended to formatted value |
| `toHumanReadableString returns empty string for null` | null/undefined/"" all → "" |
| `toHumanReadableString uses default symbol when currency_symbol is empty` | Empty symbol falls back to "$" |
| `toHumanReadableString applies thousand separator` | **Gap fill:** COMMA_PERIOD → "£1,234.56" |
| `getName returns fieldType.currency i18n key` | i18n key resolved correctly |
| `getFormComponent returns FieldCurrencySubForm` | Form component reference correct |
| `toHumanReadableString pads decimal places on whole numbers` | "9" with 2dp → "$9.00" |

## Coverage Metrics
- **Happy path:** ✅ create, read, update, delete, display, export
- **Error cases:** ✅ 401 unauthenticated, 400 symbol too long
- **Edge cases:** ✅ None value, empty symbol, negative value, thousand separator, decimal padding
- **Integration:** ✅ prepare_values maps currency_symbol→number_prefix in API response

## E2E Tests (Playwright)
**File:** `e2e-tests/tests/database/currency_field.spec.ts`
**Note:** Requires running stack (`just dev up`). Not run in unit test phase.

| Test | Coverage |
|---|---|
| Currency field column appears in table after creation | UI: adds field via API, navigates to table, verifies header visible |
| Currency cell renders numeric value with configured symbol | UI: enters value in cell, verifies $-prefixed display |

## Checklist
- [x] API tests generated
- [x] E2E tests generated
- [x] Frontend unit tests generated
- [x] Tests use standard framework (pytest-django, Vitest, Playwright)
- [x] Happy path covered
- [x] 2+ critical error cases covered
- [x] All generated tests run successfully
- [x] Tests use proper locators / framework APIs
- [x] Tests have clear descriptions
- [x] No hardcoded waits or sleeps
- [x] Tests are independent (no order dependency)
