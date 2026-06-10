# Test Automation Summary — Story 3.8: Render a Gantt View

**Workflow:** bmad-qa-generate-e2e-tests
**Date:** 2026-06-10
**Profile:** default (Gantt has no premium twin — NOT `.env.oss-test`)

## Scope

QA test generation for the implemented Gantt view (Bucket B core view type built on
the core Timeline spine, with the bar/connector layer drawn by the lazy-loaded
third-party Frappe Gantt 1.2.2 (MIT) SVG renderer). Backend type/API tests and
frontend unit tests already shipped with the implementation; this pass validated
that coverage and **closed the E2E gap** (Task 8) — the `gantt_view.spec.ts` E2E
spec and its `createGanttView` fixture did not exist.

## Generated / Applied Tests

### E2E Tests (NEW — gap closed)
- [x] `e2e-tests/tests/database/gantt_view.spec.ts` — 5 Playwright scenarios:
  1. **Bar-vs-tray partition + config persistence (AC #1, #2)** — fully-dated row
     draws one `.bar-wrapper`; rows missing a date go to the tray (count = 2);
     reload re-renders the same partition; clearing `start_date_field` drops the
     view to the empty state (host unmounted).
  2. **Zoom switch + persistence (AC #4)** — default Month is the active zoom;
     switching to Day flips the active RadioGroup button; reload keeps Day active
     (persisted `timescale` → Frappe Gantt `view_mode='Day'`).
  3. **One bar per fully-dated row across multiple tasks (AC #2)** — three dated
     rows → three `.bar-wrapper` groups; no tray.
  4. **View filters honored (AC #1)** — `Name = keep` filter leaves exactly one bar.
  5. **Field-visibility + data-dependency guard (AC #5)** — hiding the primary and
     the start-date card faces still draws the bar (start date keeps driving layout)
     while the tray card omits the hidden faces and keeps the visible "End".
- [x] `e2e-tests/fixtures/database/view.ts` — added `createGanttView(...)` helper
     (mirrors `createTimelineView`; posts `type: "gantt"` with start/end/timescale).

### Frontend Unit Tests (pre-existing — validated)
- [x] `web-frontend/test/unit/database/components/view/gantt/ganttView.spec.js`
  — 30 cases: `getType`/icon/name; `ganttViewMode` day/week/month + fallback;
  field-resolution computeds; scheduled/unscheduled partition (AC #2); `ganttTasks`
  YYYY-MM-DD mapping w/ no day-drift (AC #2); `dependenciesForRow` empty 3.9 seam
  (AC #3); `openTaskRow`; `updateValue` optimistic path; header `view/update`
  dispatches for start/end/timescale + field-option guards (AC #1, #4, #5).

### Backend Tests (pre-existing — validated)
- [x] `backend/tests/baserow/contrib/database/view/test_gantt_view_type.py`
- [x] `backend/tests/baserow/contrib/database/api/views/gantt/test_gantt_view_views.py`
  — date-field validation (`IncompatibleField`/`FieldNotInTable`), `timescale`
  round-trip + invalid-choice rejection, SET_NULL on field delete / type change,
  `get_hidden_fields` keeps start/end visible (AC #5), export/import round-trip,
  row listing honoring filters/sorts/visibility, config + field_options PATCH.

## Verification

| Suite | Command | Result |
|---|---|---|
| Frontend unit | `yarn vitest run test/unit/database/components/view/gantt/` | **30 passed** |
| Backend (default profile) | `uv run pytest .../view/test_gantt_view_type.py .../api/views/gantt/test_gantt_view_views.py` | **22 passed** |
| E2E | authored only — needs Docker e2e stack (Task 8) | not run locally |

E2E `.ts` formatted with `web-frontend/node_modules/.bin/prettier`.

## Coverage vs Acceptance Criteria

| AC | Covered by |
|---|---|
| #1 config persistence + filters/sorts/visibility | E2E #1/#4; backend round-trip + listing; unit header dispatches |
| #2 bar only for both-dated rows, rest to tray | E2E #1/#3/#5; unit partition + `ganttTasks` |
| #3 dependency-layer seam (empty today) | unit `dependenciesForRow` / `ganttTasks.dependencies=''` |
| #4 day/week/month zoom persists, mapped to `view_mode` | E2E #2; unit `ganttViewMode` + `updateTimescale`; backend `timescale` round-trip |
| #5 lazy-load + field permissions / hidden date fields visible | E2E #5; backend `get_hidden_fields`; unit field-option guards |

## Notes

- Frappe Gantt 1.2.2 emits one `.bar-wrapper` group per task → bar assertions count
  `.gantt-view__host .bar-wrapper`. Active zoom asserted via
  `.radio-group__radio-button.button--active`.
- No hardcoded waits — Playwright `expect(...).toHaveCount/toBeVisible` auto-retries
  cover the lazy Frappe Gantt import + render.
- Gantt runs in the **standard** e2e lane (no OSS-only stack) — unlike Timeline it has
  no premium twin to override it.

## Next Steps
- Wire `gantt_view.spec.ts` into the e2e CI lane and run against the Docker stack.
- Story 3.9 will populate the `dependencies` seam — add connector-render assertions then.
