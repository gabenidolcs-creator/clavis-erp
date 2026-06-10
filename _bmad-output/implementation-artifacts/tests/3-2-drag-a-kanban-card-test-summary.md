# Test Automation Summary — Story 3.2: Drag a Kanban card between columns

**Date:** 2026-06-09
**Engineer:** Tinsu (qa-generate-e2e-tests)
**Story:** `_bmad-output/implementation-artifacts/3-2-drag-a-kanban-card-between-columns.md`
**Profile:** OSS-only (free-core Kanban; premium overrides core in full open-core builds)
**Framework:** Vitest (frontend unit) + Playwright (E2E)

## Scope

Story 3.2 is **pure frontend** — drop dispatches the existing `view/kanban/updateRowValue`
optimistic path. Zero backend code, so **no API tests** apply. Coverage is frontend unit +
E2E only. Tests run in the OSS-only context (the free-core `KanbanView`; in a full open-core
build premium's Kanban registers last and overrides core).

## Generated / Extended Tests

### E2E (`e2e-tests/tests/database/kanban_view.spec.ts`) — pre-existing from dev-story
- [x] Drag a "To do" card to "Done" → card re-buckets, "To do" empties, value persists across reload (AC #1; AC #2 via reload).
- Two-context realtime assertion documented as not feasible in this lane (single auth token); covered by single-client reload.
- **Authored only — NOT run locally** (requires Docker stack; targets OSS-only CI lane).

### Frontend unit (`web-frontend/test/unit/database/components/view/kanban/kanbanView.spec.js`)
Method-level units (drive the real `canDrag` computed + drag methods on a minimal instance —
a full mount would pull in the premium store and leave the clean room).

**Pre-existing (dev-story):**
- [x] `canDrag` true only when editable + not read-only + grouping field set (AC #4)
- [x] `onDragStart`/`onDragEnd` toggle dragging flag + track row
- [x] read-only `onDragStart` cancelled (AC #4)
- [x] drop on different column dispatches once with target option (AC #1)
- [x] drop on Uncategorized passes `value: null` (AC #1)
- [x] drop on own column is a no-op (AC #5)
- [x] Uncategorized→Uncategorized no-op (both null equal, AC #5)
- [x] read-only drop dispatches nothing (AC #4)
- [x] non-editable field drop dispatches nothing (AC #4)
- [x] rejected update caught + surfaced via `notifyIf` (AC #3)

**Gaps discovered + filled (this workflow):**
- [x] **`onDragStart` cancelled when grouping field not editable** (AC #4) — previously only read-only was tested.
- [x] **`onDragOver` only `preventDefault`s during a permitted drag** — method was fully untested (gates valid drop-target behaviour on `canDrag` + `draggingRow`).
- [x] **drop with no grouping field configured (`field=null`) dispatches nothing** (AC #4) — drop-level branch was untested.
- [x] **drop with no drag in progress (`draggingRow=null`) is a safe no-op** — defensive guard, untested.
- [x] **after a rejected drop the row grouping value is left unchanged** (AC #3 rollback) — Task 4 explicitly asks; previously only `notifyIf` was asserted. Confirms the component does not splice the value itself (rollback stays the store's job).

## Coverage

| AC | Description | Covered by |
|----|-------------|------------|
| #1 | Drop sets grouping field to target option / null | unit (option + null) + E2E |
| #2 | Realtime broadcast (no refresh) | E2E reload (two-context documented N/A) |
| #3 | Fail → rollback + error | unit (`notifyIf` + value-unchanged) |
| #4 | Drag disabled: read-only / no field / not editable | unit (canDrag + onDragStart + onDrop × all 3 conditions) |
| #5 | Own-column drop no-op (incl. both null) | unit |

- Unit tests: **22 passed** (17 pre-existing + 5 new gap fills).
- AC coverage: **5/5**.

## Validation

```
NODE_OPTIONS="--max-old-space-size=8192" yarn vitest --run \
  test/unit/database/components/view/kanban/kanbanView.spec.js
# → Test Files 1 passed (1) | Tests 22 passed (22)
```

ESLint clean; Prettier formatted. E2E authored, not run locally (Docker/OSS-only CI lane).

## Next Steps

- Run the E2E drag scenario in the OSS-only CI lane (Docker stack).
- If a two-browser-context fixture lands, upgrade AC #2 to a true second-client assertion.
