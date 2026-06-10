# Test Summary: Story 2.4 — Autonumber Field

## Coverage Metrics

| Layer | Tests | Status |
|---|---|---|
| Frontend unit (Vitest) | 6 | ✅ All pass |
| E2E Playwright | 3 | Syntactically valid; require Docker stack |
| Backend unit | 17 (pre-existing) | ✅ All pass (upstream) |

## Frontend Unit Tests

**File:** `web-frontend/test/unit/database/autonumberFieldType.spec.js`

| Test | Assertion | Result |
|---|---|---|
| `getType` returns 'autonumber' | `toBe('autonumber')` | ✅ |
| `getIconClass` returns icon | `toBe('iconoir-numbered-list-left')` | ✅ |
| `isReadOnlyField` returns true | `toBe(true)` | ✅ |
| `shouldFetchDataWhenAdded` returns true | `toBe(true)` | ✅ |
| `toHumanReadableString` returns number | `toBe(42)` (not `'42'` — base impl returns raw value) | ✅ |
| `toHumanReadableString` null → empty string | `toBe('')` | ✅ |

Run: `EXTRA_VITEST_PARAMS="" yarn test:core test/unit/database/autonumberFieldType.spec.js`

## E2E Tests

**File:** `e2e-tests/tests/database/autonumber_field.spec.ts`

| Test | AC Covered | Pattern |
|---|---|---|
| Column appears in table after creation | AC1 (integration) | `tablePage.fields().filter({hasText})` |
| Cell is read-only — no input on click | AC1 (read-only) | `firstNonPrimaryCellWrappingColumnDiv.click()` + `toHaveCount(0)` |
| Cell displays numeric value for backfilled rows | AC1 (value render) | `firstNonPrimaryCellWrappingColumnDiv.locator(".grid-field-number").toHaveText("1")` |

E2E tests require Docker stack: `yarn playwright test e2e-tests/tests/database/autonumber_field.spec.ts`

## Gap Analysis (QA Workflow)

**Gap found and filled:** Tests 1–2 from dev session verified column creation and read-only behavior but did NOT verify the actual numeric value rendered in the cell. Test 3 added to assert `.grid-field-number` contains `"1"` (first row of backfilled table).

**Gaps not pursued (out of scope for E2E):**
- AC2 (sequence doesn't reset on deletion) — covered by 17 backend unit tests
- AC3 (collision-free import/duplicate) — covered by `test_import_rows_assign_new_values` and `test_duplicate_autonumber_field`

## Notes

- `createTable` fixture calls `POST /api/database/tables/database/{id}/` without `data`, triggering `fill_example=True` → 2 rows seeded automatically. Autonumber backfills these as 1 and 2.
- `createRows` fixture does not exist in `e2e-tests/fixtures/database/rows.ts` (only `updateRows` for PATCH batch). API row creation can be done inline via `getClient` if needed in future tests.
- TypeScript compiler not available in `e2e-tests/` locally — syntax-check only; full run requires Docker stack.
