# Test Automation Summary — Story 3.9: Define Task Dependencies with Cycle Prevention

**Workflow:** bmad-qa-generate-e2e-tests
**Role:** QA automation engineer (test generation only — no code review / story validation)
**Date:** 2026-06-10
**Baseline commit:** 787cbd22c (Story 3.8 Gantt spine)
**Framework:** pytest/pytest-django (backend), Vitest (frontend), Playwright (e2e)

## Acceptance Criteria under test

- **AC #1** — Persisted directed edge (`predecessor → successor`) survives reload and renders as a connector line.
- **AC #2** — Cycle prevention across **all** mutation paths: interactive create, restore-from-trash, import.

## Gap analysis

The implementing dev work already shipped thorough backend + frontend tests. The single
discovered coverage gap was the **E2E spec**: `e2e-tests/tests/database/gantt_view.spec.ts`
held only Story 3.8 render scenarios and **zero Story 3.9 dependency/connector coverage**.
Two E2E scenarios were authored to close it (AC #1 draw+reload, AC #2 cycle reject).

## Generated / verified tests

### E2E Tests (NEW — authored this workflow, author-only per Task 10)

- [x] `e2e-tests/tests/database/gantt_view.spec.ts`
  - **AC #1** — "draws a dependency connector between two task bars via the predecessor
    picker and persists it on reload": opens task B's bar → predecessor picker
    (`.gantt-view__dependencies-add` Dropdown) → selects A → asserts the Frappe Gantt
    connector `path[data-from][data-to]` in the `.arrow` layer → reloads → connector still
    rendered (re-fetched server edge).
  - **AC #2** — "rejects a dependency that would close a cycle with a clear error and adds
    no connector": precondition A→B drawn; opens A; attempts to add B as predecessor (B→A
    closes the cycle) → asserts the `ganttView.cycleRejectedTitle` toast
    ("Dependency would create a cycle") and that **no** reverse connector was added (only
    the original A→B arrow remains).
  - Selectors derived from the live implementation: bar `.bar-wrapper[data-id]`, picker
    `.gantt-view__dependencies` / `.gantt-view__dependencies-add .dropdown__selected`,
    candidate `.select__item-name-text[title=...]`, connector
    `.gantt-view__host .arrow path[data-from][data-to]`, toast `.toast__title`.
  - **Not run locally** (needs the Docker e2e stack; `e2e-tests/` has no local
    tsconfig/node_modules). Formatted with `web-frontend/node_modules/.bin/prettier`
    (clean).

### Backend API Tests (pre-existing — verified GREEN)

- [x] `backend/tests/baserow/contrib/database/api/views/gantt/test_gantt_dependency_views.py`
  - POST create + fresh GET reload proof (AC #1), POST cycle → 400 `ERROR_TASK_DEPENDENCY_CYCLE`
    (AC #2), duplicate → 400 `ERROR_TASK_DEPENDENCY_ALREADY_EXISTS`, DELETE → 204,
    delete-missing → 404 `ERROR_TASK_DEPENDENCY_DOES_NOT_EXIST`, non-member → 400
    `ERROR_USER_NOT_IN_GROUP`.

### Backend Handler / cycle-engine Tests (pre-existing — verified GREEN)

- [x] `backend/tests/baserow/contrib/database/view/gantt/test_task_dependency_handler.py`
  - create persists + unique idempotency, self-loop rejected, direct cycle, long-chain
    cycle, missing-row, non-FS type rejected, delete, list, permanent-row-delete cleanup
    (both sides), **restore-from-trash revalidation** (drops cyclic edge + acyclic no-op),
    **import_serialized cycle rejection** + acyclic export/import round-trip. All three
    AR-8 non-interactive paths covered (AC #2 teeth).

### Frontend Unit Tests (pre-existing — verified GREEN)

- [x] `web-frontend/test/unit/database/components/view/gantt/ganttView.spec.js`
  - live `dependenciesForRow` seam (predecessor-id string / empty), picker `addPredecessor`
    dispatch with correct ids, cycle rejection → clear toast (no rethrow), `removeDependency`
    dispatch, **readOnly/permission guard** (add + remove are no-ops when `canEditDependencies`
    is false), store `createDependency`/`deleteDependency` optimistic add/remove with rollback
    on the cycle 400.

## Run results

| Suite | Command | Result |
|---|---|---|
| Backend handler + API | `uv run pytest tests/.../view/gantt/ tests/.../api/views/gantt/test_gantt_dependency_views.py` (default profile, test DB :5431) | **19 passed** |
| Frontend gantt unit | `yarn vitest run test/unit/database/components/view/gantt/` | **39 passed** |
| E2E | author-only — not run (Docker stack required) | authored, prettier-clean |

## Coverage

- AC #1 (persist + reload + connector render): backend API ✅, frontend seam ✅, E2E ✅
- AC #2 interactive cycle: handler ✅, API ✅, frontend toast/rollback ✅, E2E ✅
- AC #2 restore-from-trash cycle: handler ✅ (E2E impractical — backend-only path)
- AC #2 import cycle: handler ✅ (E2E impractical — backend-only path)
- Permanent-delete edge cleanup: handler ✅

## Next steps

- Run the E2E scenario in CI (Docker e2e lane) — the only suite not exercised locally.
- Optional future coverage: an API test asserting the **public** Gantt payload surfaces
  dependency edges read-only (`has_public_info=True` parity, story Task 4) — not an AC gate.
