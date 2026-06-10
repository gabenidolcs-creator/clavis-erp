# Test Automation Summary — Story 2.2: Percent Field

## Generated Tests

### Backend Unit/API Tests (10)
- [x] `backend/tests/baserow/contrib/database/field/test_percent_field_type.py`
  - `test_percent_field_registered` — PercentField type in registry with correct model_class
  - `test_percent_field_creates_with_suffix_enforced` — number_suffix=% and number_prefix="" on creation
  - `test_percent_field_prepare_values_locks_suffix` — prepare_values() always overrides suffix to %
  - `test_percent_field_prepare_values_api_cannot_override_suffix` — None/""/pct/%% inputs all locked to %
  - `test_percent_field_api_round_trip` — full REST lifecycle POST/GET/PATCH, suffix always %
  - `test_percent_field_sorts_numeric` — 9 sorts before 10 (numeric, not lexicographic)
  - `test_percent_field_row_stores_as_decimal` — row value stored as Decimal without precision loss
  - `test_percent_field_export_value` — get_export_value returns "50.5%"; None returns ""
  - `test_percent_field_defaults` — default decimal_places=0, suffix=%, prefix=""
  - `test_percent_field_migration_reversible` — migration 0217 all ops have reverse_sql/reverse

### Frontend Unit Tests (8)
- [x] `web-frontend/test/unit/database/percentFieldType.spec.js`
  - `getType returns percent`
  - `toHumanReadableString appends % suffix`
  - `toHumanReadableString returns empty string for null/undefined/empty`
  - `toHumanReadableString uses % even if field has empty suffix`
  - `toHumanReadableString applies decimal places`
  - `getName returns fieldType.percent i18n key`
  - `getFormComponent returns FieldPercentSubForm`
  - `toHumanReadableString applies thousand separator`

### E2E Tests (3) — NEW
- [x] `e2e-tests/tests/database/percent_field.spec.ts`
  - `Percent field column appears in table after creation` — API creates field, UI asserts column header visible
  - `Percent cell renders numeric value with locked % suffix` — inputs 75, asserts % renders in cell
  - `Percent cell renders with decimal places when configured` — decimal_places=2, inputs 75, asserts "75.00%"

## Coverage

| Layer | Tests | Key Invariants Covered |
|---|---|---|
| Backend unit | 10 | Registry, suffix lock, API round-trip, sort, Decimal storage, export, migration |
| Frontend unit | 8 | Type identity, human-readable string, null/empty, decimal places, separator, i18n, component |
| E2E Playwright | 3 | Column visibility, % suffix in grid cell, decimal precision in grid |

## Gap Analysis

**Before this workflow:** 18 tests (10 backend + 8 frontend), 0 E2E
**After this workflow:** 21 tests (10 backend + 8 frontend + 3 E2E)

**Remaining gap (acceptable):**
- Invalid decimal_places value (e.g. -1) — covered at the serializer level, not needed in E2E
- Unauthenticated access — covered by shared auth infrastructure, not field-specific

## Test Commands

```bash
# Backend (requires Docker with DB)
just b test backend/tests/baserow/contrib/database/field/test_percent_field_type.py

# Frontend unit
EXTRA_VITEST_PARAMS="" yarn test:core -- test/unit/database/percentFieldType.spec.js

# E2E (requires running stack)
cd e2e-tests && yarn playwright test tests/database/percent_field.spec.ts
```
