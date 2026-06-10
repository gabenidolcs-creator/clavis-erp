# Test Automation Summary — Story 3.7 (Reschedule and resize Timeline bars)

**Feature:** Pointer-drag move + edge-resize of Timeline bars (core, Bucket A clean-room).
**Workflow:** bmad-qa-generate-e2e-tests — generate/verify tests, auto-apply discovered gaps.
**Engineer role:** QA automation (test generation only — no code review / story validation).
**Date:** 2026-06-10

## Test Framework

- **Frontend unit:** Vitest (`web-frontend/test/...`) — method/computed-level + pure-fn pattern (NO `testApp.mount(TimelineView)`; premium store last-wins → OOM).
- **E2E:** Playwright (`e2e-tests/tests/...`) — continuous pointer-drag via `mouse.move`/`down`/`up`. OSS-only CI lane; authored, not run locally (needs Docker stack).
- **API:** none added — ZERO backend story. Move/resize reuses the existing `updateRowValues`/`updateValue` → `batchUpdate` → `RowHandler` path, already covered by backend row-update suites. No new endpoint to test.

## Generated / Verified Tests

### Unit (`web-frontend/test/unit/database/components/view/timeline/timelineView.spec.js`)
- [x] 70/70 passing (41 pre-existing 3.6 + 29 Story 3.7). Verified green this run.
- Covers: `pixelsToUnits`, `shiftDateValue` (local-frame, month/boundary, datetime time-of-day), `clampResizeUnits` (both directions, past-edge, 1-unit floor, empty), `canDragBars` (readOnly / null field / non-writable), `onCommitMove` (atomic plural `updateRowValues`), `onCommitResize` (single-field, resize-start vs resize-end), rollback `notifyIf`, `onMouseUp` no-op + permission-loss abort.

### E2E (`e2e-tests/tests/database/timeline_view.spec.ts`) — 10 scenarios
Pre-existing (3.6 + 3.7 happy):
- [x] render bars/tray + config persist (AC #1, #2)
- [x] zoom switch persist (AC #3)
- [x] longer span = wider bar (AC #2)
- [x] view filters honored (AC #1)
- [x] card-face visibility vs date-driving field (AC #5)
- [x] **move** shifts BOTH cells, span preserved (AC #1, #3, #4)
- [x] **resize right edge** → only end date (AC #2, #4)

Added this run (gap-fill, auto-applied):
- [x] **resize LEFT edge → only start date**, bar widens (AC #2) — symmetric half was untested.
- [x] **resize past opposite edge clamps to 1-unit bar** (no inversion) (AC #2) — clamp keystone at E2E level.
- [x] **zero-unit release = no-op** — dates unchanged, no request (AC #1).

## Coverage vs Acceptance Criteria

| AC | Unit | E2E |
|---|---|---|
| #1 Move preserves duration + zero no-op | ✅ | ✅ (move + no-op added) |
| #2 Resize only dragged endpoint + clamp | ✅ | ✅ (resize-end + **resize-start added** + **clamp added**) |
| #3 Real-time broadcast | ✅ (one `updateRowValues`) | ✅ (DB read after move) |
| #4 Optimistic + rollback | ✅ (`notifyIf`) | ⚠️ indirect (no E2E permission-denial harness) |
| #5 Permission / read-only gate | ✅ (`canDragBars` all branches) | ⚠️ unit-only (see gaps) |

## Gaps Not Auto-Applied (rationale)

- **AC #4 rollback at E2E level** — requires injecting a backend field-permission denial mid-drag; no existing E2E fixture sets a per-field write-deny. Fully covered at unit level (`a failed move is caught and surfaced via notifyIf`). Backend rollback path covered by `bufferedRows` suites.
- **AC #5 read-only / non-writable → no handles at E2E level** — making a view `readOnly` (viewer role / shared link) is not reachable through current e2e fixtures without new auth scaffolding. Exhaustively covered at unit level (`canDragBars` readOnly / null / non-writable branches). Deferred to avoid over-engineering per skill "Keep It Simple".

## Coverage Metrics

- Unit pure-fn + handler: 7/7 net-new units (`pixelsToUnits`, `shiftDateValue`, `clampResizeUnits`, `canDragBars`, `onCommitMove`, `onCommitResize`, `onMouseUp`).
- E2E scenarios: 10 total (3 added this run).
- ACs with executable E2E happy-path: 1, 2, 3 fully; 4, 5 unit-only (documented).

## Validation

- Unit: `web-frontend/node_modules/.bin/vitest run test/unit/database/components/view/timeline/timelineView.spec.js` → **70 passed**.
- E2E: Prettier `--check` clean (formatted via web-frontend prettier — `e2e-tests/` has no local prettier). Runs in OSS-only CI lane (not local — Docker stack).

## Next Steps

- Run the new E2E scenarios in the OSS-only CI lane.
- If an E2E permission-deny fixture is added later, lift AC #4/#5 from unit-only to E2E.
