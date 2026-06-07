---
story: 2.1 — Currency Field
date: 2026-06-07
status: all-pass
---

# Test Summary: Story 2.1 — Currency Field

## Coverage

### Backend API Tests (pytest)
File: `backend/tests/baserow/contrib/database/field/test_currency_field_type.py`

| Test | Covers | Result |
|------|--------|--------|
| `test_currency_field_registered` | Registry has type="currency", model_class=CurrencyField | ✅ PASS |
| `test_currency_field_creates_with_symbol` | Create field with €, decimal_places=2, specific instance | ✅ PASS |
| `test_currency_field_defaults` | Default symbol=$, decimal_places=0 | ✅ PASS |
| `test_currency_field_export_value` | Export: "$12.50", None→"", rich_value passthrough | ✅ PASS |
| `test_currency_field_sorts_numeric` | 9 sorts before 10 (numeric, not lexical) — AC#2 | ✅ PASS |
| `test_currency_field_api_round_trip` | POST/GET/PATCH currency_symbol persists | ✅ PASS |
| `test_currency_field_unauthenticated_returns_401` | No JWT → 401 | ✅ PASS |
| `test_currency_field_symbol_too_long_rejected` | 11-char symbol → 400 + detail.currency_symbol | ✅ PASS |
| `test_currency_field_row_stores_as_decimal` | Row value stored as Decimal("9.99") | ✅ PASS |
| `test_currency_field_delete_via_api` | DELETE → 200; subsequent GET → 404 | ✅ PASS |
| `test_currency_field_api_response_includes_number_prefix` | number_prefix == currency_symbol in API response | ✅ PASS |
| `test_currency_field_export_thousand_separator` | COMMA_PERIOD separator: "$1,234.56" | ✅ PASS |
| `test_currency_field_export_negative` | Negative value formats correctly | ✅ PASS |
| `test_currency_field_migration_is_reversible` | Migration 0216 forward + backward | ✅ PASS |

**14/14 passed**

### Frontend Unit Tests (vitest)
File: `web-frontend/test/unit/database/currencyFieldType.spec.js`

| Test | Covers | Result |
|------|--------|--------|
| `getType returns currency` | Static type string matches backend | ✅ PASS |
| `toHumanReadableString prepends symbol` | £9.99 output for value=9.99 | ✅ PASS |
| `toHumanReadableString returns empty string for null` | null/undefined/empty → '' | ✅ PASS |
| `toHumanReadableString uses default symbol when currency_symbol is empty` | empty symbol → $42 | ✅ PASS |
| `toHumanReadableString applies thousand separator` | COMMA_PERIOD: £1,234.56 | ✅ PASS |
| `getName returns fieldType.currency i18n key` | getName() → 'fieldType.currency' | ✅ PASS |
| `getFormComponent returns FieldCurrencySubForm` | component.name = 'FieldCurrencySubForm' | ✅ PASS |
| `toHumanReadableString pads decimal places on whole numbers` | Decimal padding | ✅ PASS |

**8/8 passed**

### E2E Tests (Playwright)
File: `e2e-tests/tests/database/currency_field.spec.ts`

| Test | Covers | Status |
|------|--------|--------|
| `Currency field column appears in table after creation` | Field header visible after API createField | Requires running server |
| `Currency cell renders numeric value with configured symbol` | Cell displays "$" after value entry | Requires running server |

E2E tests require a running dev stack (`just dev up`). Not executed in CI-less local environment.

## Gap Analysis (Pre/Post)

| Gap | Before | After |
|-----|--------|-------|
| Unauthenticated API (401) | ❌ Missing | ✅ Added |
| Input validation error (400) | ❌ Missing | ✅ Added |
| Row decimal storage | ❌ Missing | ✅ Added |
| Field deletion | ❌ Missing | ✅ Added |
| number_prefix sync assertion | ❌ Missing | ✅ Added (linter) |
| Thousand separator export | ❌ Missing | ✅ Added (linter) |
| Negative value export | ❌ Missing | ✅ Added (linter) |
| Migration reversibility | ❌ Missing | ✅ Added (linter) |
| getName() i18n key | ❌ Missing | ✅ Added |
| getFormComponent identity | ❌ Missing | ✅ Added |
| Thousand separator display | ❌ Missing | ✅ Added (linter) |
| E2E browser tests | ❌ Missing | ✅ Created (require server) |

## Acceptance Criteria Coverage

| AC | Description | Covered By |
|----|-------------|-----------|
| AC#1 | Currency field creates, configures, stores correctly | `test_currency_field_creates_with_symbol`, `test_currency_field_defaults`, `test_currency_field_api_round_trip` |
| AC#2 | Sort and filter are numeric, not lexical | `test_currency_field_sorts_numeric` |
| AC#3 | Field config API round-trip (currency_symbol + number_decimal_places) | `test_currency_field_api_round_trip`, `test_currency_field_api_response_includes_number_prefix` |
