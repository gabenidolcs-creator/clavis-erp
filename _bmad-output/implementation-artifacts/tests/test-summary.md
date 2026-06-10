# Test Automation Summary — Story 3.5: Reschedule a Calendar Entry by Drag

**Workflow:** `bmad-qa-generate-e2e-tests`
**Date:** 2026-06-10
**Engineer role:** QA automation (test generation only — no code review / story validation)
**Story status at run:** `review` (implementation pre-applied; this run audits coverage and auto-applies gaps)
**Profile:** OSS-only (clean-room Bucket A — core `.calendar-view__*` DOM; never `premium/`/`enterprise/`)

## Gap Analysis

Coverage audited against the 5 acceptance criteria and the implemented handlers in
`CalendarView.vue` (`onDragStart`/`onDragEnd`/`onDragOver`/`onDropDay`/`onDropUnscheduled`,
`dateValueForDay`, `canDragDate`).

| Surface | Already covered (pre-run) | Gap found | Action |
|---|---|---|---|
| Unit — `dateValueForDay`, `onDropDay`, `onDropUnscheduled`, `canDragDate`, `updateValue`, computeds | ✅ | — | kept |
| Unit — `onDragStart` | ❌ | drag lifecycle / AC #4 cancel-when-not-permitted / payload | **added** |
| Unit — `onDragEnd` | ❌ | flag teardown + null-row safety | **added** |
| Unit — `onDragOver` | ❌ | AC #4 drop-target gate (`canDragDate && draggingRow`) | **added** |
| E2E — day→day reschedule, scheduled→tray clear | ✅ | — | kept |
| E2E — unscheduled-tray→day (AC #5 *schedule* direction) | ❌ | only the clear direction was tested | **added** |
| E2E — no-op self-day drop (AC #1) | ❌ | guard untested end-to-end | **added** |

## Generated / Extended Tests

### Unit — `web-frontend/test/unit/database/components/view/calendar/calendarView.spec.js`
- [x] `CalendarView.onDragStart` — tracks `draggingRow`, flips `row._.dragging`, sets `effectAllowed`/payload; **cancels + tracks nothing when `canDragDate` false (AC #4)**; survives a row with no `_` bag.
- [x] `CalendarView.onDragEnd` — clears the dragging flag + tracked row; null-row safe.
- [x] `CalendarView.onDragOver` — `preventDefault` only during a permitted drag; **does not claim the drop target when `canDragDate` false or no drag in progress (AC #4)**.

### E2E — `e2e-tests/tests/database/calendar_view.spec.ts`
- [x] Drag an **unscheduled** tray card onto a day cell → date field set, card leaves tray, lands under target day, DB read confirms value (AC #5 schedule direction).
- [x] Drop a card on its **own current day** → no request, value unchanged, card stays put (AC #1 no-op guard).

## Coverage vs Acceptance Criteria

| AC | Description | Unit | E2E |
|---|---|---|---|
| #1 | Drag→reschedule + reactive re-bucket + no-op self-drop | ✅ | ✅ |
| #2 | Real-time broadcast via reused row-update path (persisted on reload) | ✅ (`updateValue` dispatch) | ✅ (reload assert) |
| #3 | Optimistic + rollback via `notifyIf` | ✅ (`updateValue` reject) | n/a (server fault injection out of e2e scope) |
| #4 | Permission / read-only drag gate | ✅ (`canDragDate`, `onDragStart`, `onDragOver`) | n/a (UI gate; server is backstop) |
| #5 | Unscheduled tray, both directions | ✅ | ✅ (both directions) |

## Verification

- **Unit:** `yarn vitest run web-frontend/test/unit/database/components/view/calendar/calendarView.spec.js`
  → **60 passed** (52 pre-run + 8 new). No mount (premium store override → OOM); method/computed-level only.
- **ESLint** (repo root, `web-frontend/node_modules/.bin/eslint`): clean on the unit spec.
- **Prettier** `--check`: clean on `calendar_view.spec.ts`.
- **E2E:** authored only — NOT run locally (requires the OSS-only Docker stack); wired to the dedicated OSS-only CI lane (same lane as the Kanban spec). [Source: story Task 6 / 3-2 test-run note]

## Coverage Metrics
- Drag-lifecycle handlers: 5/5 covered at the unit level (was 2/5).
- AC coverage: 5/5 with at least one automated assertion.
- E2E reschedule scenarios: 4 (day→day, scheduled→tray, tray→day, self-day no-op).

## Next Steps
- Run the E2E suite in the OSS-only CI lane (Docker required).
- AC #3 server-side rollback remains a unit-level assertion; a fault-injection e2e (e.g. revoke field write mid-session) is a possible future enhancement.
