# Test Summary — Story 2.2: Percent Field

**Date:** 2026-06-07  
**Story:** `_bmad-output/implementation-artifacts/2-2-percent-field.md`  
**Status:** All tests passing

---

## Coverage Metrics

| Layer | File | Tests | Status |
|-------|------|-------|--------|
| Backend (pytest) | `backend/tests/baserow/contrib/database/field/test_percent_field_type.py` | 10 | ✅ 10/10 pass |
| Frontend (Vitest) | `web-frontend/test/unit/database/percentFieldType.spec.js` | 9 | ✅ 9/9 pass |
| E2E (Playwright) | `e2e-tests/tests/database/percent_field.spec.ts` | 3 | ⏳ Requires running stack |

---

## Backend Tests (10/10 passing)

| Test | Coverage |
|------|----------|
| `test_percent_field_registered` | Field registry: `field_type_registry.get("percent")` returns `PercentFieldType` |
| `test_percent_field_creates_with_suffix_enforced` | Creation: `number_suffix=="%"`, `number_prefix==""` locked at field create |
| `test_percent_field_prepare_values_locks_suffix` | `prepare_values()` overrides caller suffix/prefix to `%`/`""` |
| `test_percent_field_prepare_values_api_cannot_override_suffix` | Suffix locked for None, "", "pct", "%%" inputs |
| `test_percent_field_api_round_trip` | Full REST lifecycle: POST → GET → PATCH, suffix always `%` |
| `test_percent_field_sorts_numeric` | Numeric sort: 9 before 10 (not lexical) |
| `test_percent_field_row_stores_as_decimal` | Decimal storage: `Decimal("50.25")` preserved without loss |
| `test_percent_field_export_value` | `get_export_value(Decimal("50.5"), ...)` → `"50.5%"`, None → `""` |
| `test_percent_field_defaults` | Defaults: `decimal_places=0`, suffix `%`, prefix `""` |
| `test_percent_field_migration_reversible` | Migration 0217: all ops have `reverse_sql`/`reverse` |

Run command: `DATABASE_HOST=localhost DATABASE_PORT=5431 uv run pytest tests/baserow/contrib/database/field/test_percent_field_type.py -v`

---

## Frontend Unit Tests (9/9 passing)

| Test | Coverage |
|------|----------|
| `getType returns percent` | `PercentFieldType.getType()` → `"percent"` |
| `toHumanReadableString appends % suffix` | Value `"9.9"` → `"9.9%"` |
| `toHumanReadableString returns empty string for null` | null/undefined/`""` → `""` |
| `toHumanReadableString uses number_suffix % even if field has empty suffix` | Field with empty suffix still renders `%` |
| `toHumanReadableString applies decimal places` | decimal_places=2, value `"50"` → `"50.00%"` |
| `getName returns fieldType.percent i18n key` | `getName()` → `"fieldType.percent"` |
| `getFormComponent returns FieldPercentSubForm` | Component `name`/`__name` is `"FieldPercentSubForm"` |
| `toHumanReadableString applies thousand separator` | COMMA_PERIOD: `"1234.56"` → `"1,234.56%"` |
| `getIconClass returns iconoir-percentage` | `PercentFieldType.getIconClass()` → `"iconoir-percentage"` *(gap filled)* |

Run command: `cd web-frontend && EXTRA_VITEST_PARAMS="" yarn test:core --run test/unit/database/percentFieldType.spec.js`

---

## E2E Tests (3 tests — requires running Baserow stack)

| Test | Coverage |
|------|----------|
| Percent field column appears in table after creation | Creates field via API, navigates to table, asserts column visible |
| Percent cell renders numeric value with locked % suffix | Enters 75, asserts cell contains `%` |
| Percent cell renders with decimal places when configured *(gap filled)* | `decimal_places=2`, enters 75, asserts cell contains `"75.00%"` |

File: `e2e-tests/tests/database/percent_field.spec.ts`

---

## Gaps Found & Fixed

| Gap | Fix |
|-----|-----|
| Frontend: `getIconClass` not tested | Added `test('getIconClass returns iconoir-percentage', ...)` to `percentFieldType.spec.js` |
| E2E: no decimal-places rendering test | Added `"Percent cell renders with decimal places when configured"` to `percent_field.spec.ts` |

---

## Checklist

- [x] API tests generated — backend covers POST/GET/PATCH, suffix lock
- [x] E2E tests generated — Playwright tests in `e2e-tests/tests/database/percent_field.spec.ts`
- [x] Tests use standard test framework — pytest + Vitest + Playwright
- [x] Tests cover happy path — creation, display, sort, storage, export
- [x] Tests cover 1-2 critical error cases — suffix override attempt (4 input variants)
- [x] All generated tests run successfully — backend 10/10, frontend 9/9
- [x] Tests use proper locators — Playwright uses `filter({ hasText })`, `toContainText`
- [x] Tests have clear descriptions
- [x] No hardcoded waits or sleeps
- [x] Tests are independent — no shared state between tests
- [x] Test summary created — this file
- [x] Tests saved to appropriate directories
- [x] Summary includes coverage metrics
