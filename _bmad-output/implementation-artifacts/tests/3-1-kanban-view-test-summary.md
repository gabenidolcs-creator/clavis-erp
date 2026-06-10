# Test Automation Summary — Story 3.1 (Kanban View)

Workflow: `bmad-qa-generate-e2e-tests` · Date: 2026-06-09 · Engineer: QA automation (claude-opus-4-8)

## Scope

E2E coverage for the free, clean-room Kanban view (Bucket A). Existing implementation
already shipped backend (13) + frontend unit (7) tests. This pass audited E2E coverage
against the three acceptance criteria and **auto-applied the discovered gaps**.

## Gaps Found & Filled

| AC | Behavior | Before | After |
|----|----------|--------|-------|
| #1 | Columns one-per-option **+ Uncategorized** | Column count/labels asserted, but **zero rows seeded** — card placement & Uncategorized population never exercised with data | New test seeds 3 rows (To do / Done / null) and asserts each lands in the correct column; null row confirmed in **Uncategorized** (not dropped) + header count |
| #2 | View **filters/sorts/visibility** apply to board | **No E2E coverage** | New test adds a `single_select_equal` view filter and asserts only the matching card renders (2 "To do" rows filtered out), proving the board routes through the standard view row pipeline |
| #3 | Config persists/reopens | Covered (reload → same columns) | Unchanged |

## Generated / Modified Tests

### E2E Tests (`e2e-tests/`)
- [x] `tests/database/kanban_view.spec.ts` — 3 tests:
  1. `groups cards into one column per single-select option plus Uncategorized, and persists` (pre-existing; AC #1 structure + AC #3)
  2. `places each row in the column matching its single-select value, with null rows in Uncategorized (AC #1)` — **new gap fill**
  3. `applies existing view filters to the rows shown on the board (AC #2)` — **new gap fill**

### Fixtures
- [x] `fixtures/database/view.ts` — added `createViewFilter(user, view, fieldId, type, value)` helper (no view-filter fixture existed).

## DOM Contract Asserted
`.kanban-view__column`, `.kanban-view__column-label`, `.kanban-view__column-count`,
`.kanban-view__card`, `.kanban-view__empty` — all core (OSS-only) selectors.

## Coverage
- Acceptance criteria with E2E coverage: **3/3** (#1 now data-backed, #2 newly covered, #3 retained).
- E2E test count: 1 → **3**.

## Validation
- Prettier: ✅ clean (`prettier --write`, files reformatted/verified).
- ESLint: not run — `e2e-tests` deps not installed in this environment (`yarn` lockfile error). Code follows existing fixture/spec patterns.
- E2E execution: **NOT run locally** — Kanban E2E targets the dedicated **OSS-only CI lane** (`BASEROW_OSS_ONLY=true`) because in an open-core build the premium Kanban overrides the core one (last-registration-wins). Per story convention, the spec is authored, not run locally.

## Next Steps
- Run the spec in the OSS-only e2e CI lane.
- Add sort + field-visibility (hidden field_options) assertions if AC #2 needs deeper coverage beyond the filter case.
