# Test Summary — Story 5.1: Chart Element (FR-22)

## Coverage

### E2E Tests (new)

**File:** `e2e-tests/tests/builder/elements/chartElement.spec.ts`

| # | Test | Type | Coverage |
|---|------|------|----------|
| 1 | Creates chart element with default bar chart_type | API | Happy path — default chart_type=bar, data_source_id=null |
| 2 | Creates chart element with chart_type=line | API | chart_type persistence |
| 3 | Creates chart element with chart_type=pie | API | chart_type persistence |
| 4 | Creates chart element with chart_type=doughnut | API | chart_type persistence |
| 5 | Creates chart element with chart_type=scatter | API | chart_type persistence |
| 6 | Updates chart_type via PATCH | API | Mutation — bar → pie |
| 7 | Returns 400 for invalid chart_type | API | Error path — invalid "radar" rejected |
| 8 | Can add chart element from modal | UI | Modal → `.chart-element` rendered |
| 9 | Shows empty-data placeholder when no data source configured | UI | `.chart-element__empty` visible when no data source |

**Total new E2E tests: 9**

### Pre-existing Unit Tests

| File | Count | Status |
|------|-------|--------|
| `backend/tests/baserow/contrib/builder/elements/test_element_types.py` — `TestChartElementType` | 3 | ✅ pass |
| `web-frontend/test/unit/builder/components/elements/components/ChartElement.spec.js` | 5 | ✅ pass |

### Full Frontend Suite

16/16 files, 162 tests — all pass.

## Checklist

- [x] API tests generated
- [x] E2E tests generated (UI exists)
- [x] Tests use standard test framework APIs (Playwright / `@nuxt/test-utils/playwright`)
- [x] Tests cover happy path
- [x] Tests cover critical error cases (invalid chart_type → 400)
- [x] Tests use proper locators (semantic CSS classes from component)
- [x] Tests have clear descriptions
- [x] No hardcoded waits or sleeps
- [x] Tests are independent (no order dependency)
- [x] Test summary created
- [x] Tests saved to `e2e-tests/tests/builder/elements/chartElement.spec.ts`

## Notes

- E2E tests require Docker stack (`just dc-dev up -d`) — no local Nuxt server needed for API-level tests.
- UI tests (`test.describe("UI")`) depend on `builderPagePage` fixture and require full browser context.
- Backend PATCH endpoint: `builder/elements/{id}/` — confirmed from existing codebase patterns.
