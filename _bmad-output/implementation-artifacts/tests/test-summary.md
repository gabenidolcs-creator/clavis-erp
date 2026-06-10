# Test Automation Summary — Story 2.5: Running Count Field

**Date:** 2026-06-09
**QA workflow:** bmad-qa-generate-e2e-tests
**Story:** `_bmad-output/implementation-artifacts/2-5-running-count-field.md` (Status: review)

## Scope

Story 2.5 was already fully implemented (dev-story complete) with backend (6), frontend
unit (6), and E2E (3) tests. This QA pass performed gap analysis of the E2E suite against
the four acceptance criteria and auto-applied the discovered gaps.

## Gap Analysis

| AC | Behavior | Pre-existing E2E coverage | Gap found |
|----|----------|---------------------------|-----------|
| #1 | Whole-table count displayed, read-only | 3 tests (column visible, cell read-only, value=2) | none |
| #2 | Count updates on row **create** | none | **GAP — added** |
| #3 | Count updates on row **delete** | none | **GAP — added** |
| #4 | Relational `count` type unaffected | n/a — backend registry concern | covered by `test_running_count_field_registered` (backend) |

AC #2 and AC #3 are user-facing behaviors (counts recompute across all rows on mutation)
that had backend unit coverage but **no E2E coverage**. These are exactly the
end-to-end workflows the QA E2E workflow targets.

## Generated Tests

### E2E Tests — `e2e-tests/tests/database/running_count_field.spec.ts`

Pre-existing (kept):
- [x] Running Count field column appears in table after creation (AC #1)
- [x] Running Count cell is read-only — no input appears on click (AC #1)
- [x] Running Count cell displays the whole-table row count (AC #1)

Added this pass:
- [x] **Running Count increments for all rows when a row is created** (AC #2) — seeds
  2 rows (count=2), creates a 3rd row via API (`after_rows_created` hook recomputes),
  reloads the grid, asserts the cell reads `3` and 3 rows are present.
- [x] **Running Count decrements for all rows when a row is deleted** (AC #3) — seeds
  2 rows (count=2), deletes one via API (`rows_deleted` signal recomputes), reloads
  the grid, asserts the cell reads `1` and 1 row remains.

### Fixture additions — `e2e-tests/fixtures/database/rows.ts`

`createRows` did not exist (story Task 9 confirmed). Added three minimal API helpers,
mirroring the existing `updateRows`:
- `createRow(user, table, rowValues = {})` — POST a row, returns the created row.
- `listRows(user, table)` — GET rows, returns the `results` array (used to resolve a
  seeded row id for deletion).
- `deleteRow(user, table, rowId)` — DELETE a row.

## Coverage

- Acceptance criteria with E2E coverage: **3/4** (AC #1, #2, #3). AC #4 is a backend
  registry invariant, not an E2E-suitable flow — covered by backend unit test.
- E2E tests: 3 -> **5**.

## Validation

- E2E tests **not run locally**: `e2e-tests/` has no installed `node_modules`
  (`Cannot find module '@playwright/test'`) and the suite requires the full Docker stack,
  per the story's explicit instruction ("Do NOT run E2E tests locally"). Same documented
  constraint as `autonumber_field.spec.ts` / `currency_field.spec.ts`.
- New tests are structural mirrors of the existing passing AC #1 specs; added fixture
  helpers mirror the existing `updateRows` pattern and use Baserow's standard row REST
  endpoints (`database/rows/table/{id}/`).
- Locators are the established semantic/class locators already used by the autonumber
  suite (`.grid-field-number`, `firstNonPrimaryCellWrappingColumnDiv`, `rows()`).
- No hardcoded sleeps; assertions use Playwright auto-waiting `expect`.
- Tests are independent — each provisions its own database/table.

## Next Steps

- Run the full E2E suite in CI / Docker stack to confirm green.
- Story remains in `review`; advance via `bmad-code-review` (adversarial review),
  consistent with stories 2.1-2.4.
