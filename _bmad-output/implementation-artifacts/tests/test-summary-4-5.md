# Test Summary — Story 4.5: Metric Widget Non-Regression

## Overview

Story 4.5 is a pure non-regression story. No new backend implementation was added; all
deliverables are test coverage confirmations and a new frontend component spec.

---

## Generated Test Files

### New: E2E Spec (Playwright API-level)

**File:** `e2e-tests/tests/dashboard/summary_widget.spec.ts`
**Tests:** 4

| # | Test name | AC | Result |
|---|-----------|-----|--------|
| 1 | Summary widget creation auto-provisions a `local_baserow_aggregate_rows` data source | AC #1 | ✅ authored |
| 2 | Summary widget and chart widget have independent data sources with different service types | AC #3 | ✅ authored |
| 3 | Configured summary data source dispatch returns scalar result | AC #4 | ✅ authored |
| 4 | Unconfigured summary data source dispatch returns error response | AC #4 error path | ✅ authored |

> E2E tests require the Docker e2e stack. Run with `e2e-tests/run-e2e-tests-locally.sh` or
> `cd e2e-tests && yarn playwright test tests/dashboard/summary_widget.spec.ts`.

---

### New: Frontend Unit Spec (Vitest)

**File:** `web-frontend/test/unit/dashboard/components/SummaryWidget.spec.js`
**Tests:** 4 — **All pass locally** ✅

| # | Test name | AC | Result |
|---|-----------|-----|--------|
| 1 | renders result from data source | AC #3 | ✅ pass |
| 2 | renders 0 when data source has no data | AC #3 | ✅ pass |
| 3 | shows misconfigured badge when data has `_error` | AC #3 | ✅ pass |
| 4 | coexistence: SummaryWidget reads only its own data source from shared store | AC #4 store isolation | ✅ pass |

Run: `cd web-frontend && npx vitest run test/unit/dashboard/components/SummaryWidget.spec.js`

---

### Existing: Backend Unit Tests (pytest)

**File:** `backend/tests/baserow/contrib/dashboard/widgets/test_chart_widget_type.py`
**Test:** `test_chart_widget_and_summary_widget_coexist`
**Tests confirmed passing (Story 4.4 session):** 49/49 dashboard widget tests ✅

**File:** `backend/tests/baserow/contrib/dashboard/widgets/test_summary_widget_type.py`
**Tests:** 3 (create, trash/restore, delete protection)

Run: `cd backend && .venv/bin/pytest tests/baserow/contrib/dashboard/ -q`
(Requires running test DB container — use `just b test` from repo root.)

---

## Coverage Map

| Acceptance Criteria | Backend | Frontend | E2E |
|---------------------|---------|----------|-----|
| AC #1: Non-regression rendering (widget creation + data source auto-provision) | `test_create_summary_widget_creates_data_source` | `SummaryWidget.spec.js` test 1 | `summary_widget.spec.ts` test 1 |
| AC #2: Backend coexistence test exists and passes | `test_chart_widget_and_summary_widget_coexist` | — | — |
| AC #3: Frontend SummaryWidget renders from store | — | `SummaryWidget.spec.js` tests 1–3 | `summary_widget.spec.ts` test 2 |
| AC #4: Store isolation from ChartWidget data | — | `SummaryWidget.spec.js` test 4 | `summary_widget.spec.ts` tests 2, 3, 4 |

---

## Key Technical Finding

Vue Test Utils v2 requires `global.mocks` for `$store`/`$registry` injection (not `provide`).
Vuex getter factories are `(id) => value` (single curry), not `() => (id) => value`.
This pattern is documented in `SummaryWidget.spec.js` and serves as the reference for
future dashboard widget frontend tests.

---

## Notes

- No production code was modified. SummaryWidget, ChartWidget, and widgetTypes.js are untouched.
- The `_error` badge test confirms the misconfigured-service rendering path without requiring a live backend.
- E2E tests follow the same API-level Playwright pattern established in `chart_widget.spec.ts` (Story 4.3).
