---
baseline_commit: 8e78336eb7325af928e477b240d8e9aa301d8b47
---

# Story 3.7: Reschedule and resize Timeline bars

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to drag a Timeline bar to move it or drag its edge to resize it,
so that I can adjust schedule and duration. `[A]`

## Context & Scope

### 🚨 THIS IS A BUCKET A CLEAN-ROOM STORY — READ FIRST, NON-NEGOTIABLE

Timeline is a **Bucket A** feature: every line lands in **core** without ever reading, copying, or being "influenced by" any `premium/` or `enterprise/` source. The PE/EE license forbids copying; a provenance record is a **hard CI merge gate**.

- **Do NOT open, read, `grep`, or adapt** anything under `premium/` or `enterprise/`. A full premium Timeline (with its own drag/resize) exists — `premium/web-frontend/modules/baserow_premium/components/views/timeline/*` (`TimelineView.vue`, `TimelineGrid.vue`, `TimelineContainer.vue`, …), `premium/.../store/view/timeline.js`, `premium/.../utils/timeline.js`, `premium/.../mixins/timelineViewHelpers.js`. **Opening any of it = contamination = the PR cannot merge.** These paths are listed here ONLY so you know what NOT to open. [Source: 3-6 Context & Scope; memory clean-room-isolation-porous]
- All code lands in **core** (`web-frontend/modules/{database,core}/...`, `web-frontend/test/...`, `e2e-tests/...`). No `backend/` changes (see "ZERO backend code"). [Source: architecture.md line 279; 3-5 ZERO-backend precedent]
- A provenance record under `docs/clean-room/provenance/3-7-reschedule-and-resize-timeline-bars.md` is **mandatory** (Task 7). [Source: 1-1-establish-the-clean-room-process-gate.md]
- Your **only** references for "what drag/resize looks like" are the **core Kanban** drag (3.2, MIT-derived), the **core Calendar** drag-to-reschedule (3.5), and the **core Timeline** render (3.6). The premium timeline directories exist **only so you know what NOT to open**. [Source: memory clean-room-isolation-porous]

### 🧭 THE BUILD STRATEGY: extend the 3.6 Timeline, mirror the 3.5 Calendar drag — but TWO fields and a continuous pointer-drag

Story 3.6 shipped `TimelineView.vue` already wired for this — the bar DOM, the pure geometry helpers (`barGeometry`, `rowDateRange`, `parseTimelineValue`, `timelineUnit`, `axisUnitCount`), the `updateValue` optimistic-update method, and the pre-seeded `row._.dragging` flag — explicitly so 3.7 can add drag/resize **without a rewrite**. This story **extends** that component; it does not invent a new architecture. [Source: 3-6 Completion Notes "Store pre-seeds dragging:false for the future Story 3.7"; TimelineView.vue]

Story 3.5 (Calendar drag-to-reschedule) is the closest behavioural precedent — pure-frontend, reuse the existing optimistic row-update path, let the store re-bucket reactively, no new endpoint. **Clone its discipline.** But 3.7 differs from 3.5 in two structural ways:

1. **Two date fields, not one.** A **move** shifts BOTH `start_date_field` and `end_date_field` by the same delta (preserving duration); a **resize** shifts only the dragged endpoint. A move must update both cells **atomically in one request** via the existing `updateRowValues` (plural) action — `bufferedRows.js:917`, already spread into the timeline store — so the change is a single `batchUpdate` → single WebSocket broadcast → single rollback unit. **Do NOT** fire two separate `updateRowValue` calls for a move (two requests, two rollback units, a window of half-moved state). [Source: bufferedRows.js:917 updateRowValues / :778 prepareMultipleRowValues; store/view/timeline.js spreads ...timelineBufferedRows.actions]
2. **Continuous pointer-drag, NOT HTML5 drag-and-drop.** Kanban (3.2) and Calendar (3.5) used native `draggable` + `dragstart`/`drop` between discrete drop targets (columns / day cells). A timeline bar moves a **continuous** number of pixels along an axis and is released anywhere — there are no discrete drop cells. So 3.7 uses **pointer events** (`mousedown` on the bar → `mousemove` on `document` → `mouseup`), converts the accumulated pixel delta to a whole number of timescale units, and commits on release. This is the one genuinely net-new mechanic; everything downstream (value building, optimistic update, rollback, broadcast) reuses 3.5/3.6 plumbing. [Source: epics.md#Story 3.7 "drag a bar to move it or drag its edge to resize it"]

> ⚠️ **Anti-pattern (forbidden):** adding a Gantt/timeline/drag library (interact.js, Frappe Gantt, vis-timeline, vuedraggable), a bespoke "move bar" / "resize bar" backend endpoint or store action, two separate requests for one move, or building the new date value with `moment.utc` for the date arithmetic so it disagrees with `parseTimelineValue`'s local-frame parse (bar lands a unit off near a boundary). If you reach for any of these, **stop — re-derive from the 3.6 helpers + the 3.5 drag pattern + bundled `moment`.**

### What this story is NOT

- ❌ **Gantt / task dependencies / CPM / milestones / Frappe Gantt** — Stories 3.8–3.11 (Bucket B). Moving a bar here updates **only** its own two date cells; it does not cascade to dependent rows (that is Story 3.10's prompt-first reschedule). Do not add a dependency model, CPM engine, or `frappe-gantt`. [Source: epics.md#Story 3.8–3.11]
- ❌ **A new view, new field-options shape, new persisted column, or new zoom level** — the view config (`start_date_field`/`end_date_field`/`timescale`) is unchanged from 3.6. This story adds **interaction**, not configuration.
- ❌ **Intra-day (sub-unit) precision drag.** A drag snaps to whole `timescale` units (day/week/month). Dragging within a single day to set an exact hour is out of scope; the value keeps its existing time-of-day on datetime fields (a move shifts the date part by N units, preserving `HH:mm:ss`).
- ❌ **Any backend change** — no endpoint, handler, serializer, signal, or migration. Rescheduling/resizing is changing one or two Date cells through the existing optimistic path (see ZERO backend code). [Source: 3-5 Dev Notes]
- ❌ **Dragging tray (unscheduled) cards onto the axis.** A tray row is missing a start or end value, so it has no bar to grab. Scheduling-from-tray (filling the missing date) is not in this story's ACs — bars are moved/resized; tray rows stay in the tray. (Note it in the Change Log if you add it, but the default scope is move/resize of already-scheduled bars only.)

## Acceptance Criteria

1. **Move preserves duration (both fields).** Dragging a bar's body horizontally by N whole `timescale` units and releasing sets BOTH the Row's `start_date_field` and `end_date_field` forward/back by N units, **preserving the span** between them; the bar re-positions reactively to the new dates. Releasing with a net zero-unit delta (dropped where it started) is a **no-op** — no request, no flicker. [Source: epics.md#Story 3.7 "When it is moved, Then both Date Fields update preserving duration"]
2. **Resize updates only the dragged endpoint.** Dragging the bar's **left edge** changes only `start_date_field` (the right/end stays put); dragging the **right edge** changes only `end_date_field` (the left/start stays put). The opposite endpoint's cell is not written. A resize that would invert the bar (drag start past end, or end before start) is **clamped to a minimum 1-unit bar** rather than producing a reversed/zero-width bar or throwing. A net zero-unit resize is a no-op. [Source: epics.md#Story 3.7 "when an edge is dragged the dragged endpoint updates"; 3-6 barGeometry reversed-range clamp]
3. **Real-time broadcast (NFR-1).** The move/resize reuses the existing row-update path (`updateRowValues`/`updateRowValue` → `updatePreparedRowValues` → `RowService.batchUpdate` → backend `RowHandler`), so the change broadcasts over WebSocket to other clients and invalidates the model cache automatically — **no new endpoint, handler, signal, or migration**. Inbound `rows_updated` on other clients re-positions the bar with no new code (the bar style is a computed over the store value). [Source: epics.md#Story 3.7 "changes broadcast in real time"; architecture.md:223–226,342; 3-5 AC #2]
4. **Optimistic + rollback (NFR-3).** The move/resize applies optimistically; a failed backend update (e.g. field-permission denied on either date field) rolls **all** changed cells back to their previous values and surfaces an error via `notifyIf`. The bar returns to its original position/size. For a move this is automatic because `updateRowValues` sends both cells in **one** `batchUpdate` whose rollback reverts both together. [Source: epics.md#Story 3.7 "failures roll back (NFR-3)"; bufferedRows.js updatePreparedRowValues rollback; 3-5 AC #3]
5. **Permission / read-only gate.** A bar is only draggable/resizable when the view is not `readOnly` **and** BOTH date fields are writable for the user (`fieldRegistry.get('field', field.type).canWriteFieldValues(field)` for both `start_date_field` and `end_date_field`). A read-only view, or either date field being non-writable, offers no move/resize affordance and ignores pointer-drags; the server-side field-permission layer (Epic 1) remains the authoritative backstop (denied → rollback per AC #4). [Source: epics.md#Story 3.7 NFR refs; KanbanView.vue `canDrag`:230; architecture.md:316; Epic 1 field-permission layer]

## Tasks / Subtasks

### Task 1 — Permission gate + drag state on `TimelineView.vue` (AC: #1, #2, #5) — frontend only

- [x] Add a `canDragBars` computed: `false` when `readOnly`, or `startDateField`/`endDateField` is null; else `true` only when BOTH fields are writable — `[this.startDateField, this.endDateField].every((f) => this.$registry.get('field', f.type).canWriteFieldValues(f))`. Mirror `KanbanView.canDrag:230` / Calendar `canDragDate` (3.5) but require **both** fields. [Source: KanbanView.vue:230; 3-5 Task 1 canDragDate]
- [x] Add drag state to `data()`: `dragState: null`. While a drag is active it holds `{ row, mode, startX, deltaUnits }` where `mode ∈ { 'move', 'resize-start', 'resize-end' }`. `null` when idle. (Reuse the pre-seeded `row._.dragging` flag from `store/view/timeline.js populateRow` for the per-row visual class — do NOT re-add it.) [Source: store/view/timeline.js populateRow `dragging:false`]
- [x] Add a `axisWidthPx()` method (or cache on `mousedown`) that reads the pixel width of the bar track — add a `ref` (e.g. `ref="rowsTrack"`) to `.timeline-view__rows` (or `.timeline-view__main`) and return `this.$refs.rowsTrack?.clientWidth || 0`. This is the px→unit denominator. (The axis and the rows share the same horizontal extent, so either element's `clientWidth` works; pick the one whose padding is zero.)

### Task 2 — Bar DOM: move handle (bar body) + two resize handles (edges) (AC: #1, #2, #5)

- [x] In `.timeline-view__bar`, when `canDragBars`, render two edge handles inside the bar: `<div class="timeline-view__resize-handle timeline-view__resize-handle--start" @mousedown.stop.prevent="onBarMouseDown(row, 'resize-start', $event)">` and `--end` with `'resize-end'`. The bar body itself gets `@mousedown.prevent="onBarMouseDown(row, 'move', $event)"`. Use `.stop` on the handles so an edge `mousedown` does not also start a move. Bind `:class="{ 'timeline-view__bar--draggable': canDragBars, 'timeline-view__bar--dragging': row._.dragging }"`. When `!canDragBars`, render no handles and no `mousedown` binding (bar stays click-to-open only).
- [x] **Preserve the existing click-to-open.** The bar currently has `@click="rowClick(row)"`. A pointer-drag must NOT also open the row modal. Track a `moved` flag in the drag lifecycle (set true once `deltaUnits !== 0` or pointer travel exceeds a few px) and in `rowClick` early-return if a drag just moved. Simplest: in `onMouseUp`, if `moved`, `event.stopPropagation()` / set a transient `suppressClick` that `rowClick` checks and clears. Verify a plain click (no drag) still opens the modal. [Source: TimelineView.vue rowClick]

### Task 3 — Pointer-drag lifecycle handlers (AC: #1, #2, #5)

- [x] `onBarMouseDown(row, mode, event)`: bail if `!this.canDragBars`. Set `this.dragState = { row, mode, startX: event.clientX, deltaUnits: 0 }`, `row._.dragging = true`, cache `axisWidthPx`. Attach `mousemove`/`mouseup` listeners on `document` (so the drag tracks even when the cursor leaves the bar) — add them in `mounted`/here and **remove them in `beforeUnmount`/on `mouseup`** to avoid leaks. (Use `window.addEventListener('mousemove', this.onMouseMove)` pattern.)
- [x] `onMouseMove(event)`: if `!this.dragState` return. Compute `deltaPx = event.clientX - this.dragState.startX`, `deltaUnits = pixelsToUnits(deltaPx, axisWidthPx, this.totalUnits)` (Task 4 pure fn). Store on `dragState.deltaUnits`. Optionally apply a **transient visual offset** to the dragged bar (translate by `deltaPx` or snap-preview by `deltaUnits`) for feedback — keep it a local style, do NOT mutate the store mid-drag. No request fires during move.
- [x] `onMouseUp(event)`: detach the `document` listeners; pull `{ row, mode, deltaUnits }`; clear `this.dragState` and `row._.dragging`. Guard: `if (!row || deltaUnits === 0) return` (no-op — AC #1/#2). Else dispatch the commit (Task 5) for the mode. Re-guard `canDragBars` before dispatching (permission could have changed). Set the `suppressClick` flag if `deltaUnits !== 0` (Task 2).

### Task 4 — Net-new pure logic: px→units + value building + resize clamp (AC: #1, #2)

Keep these **pure, exported** module-scope functions (like 3.6's `barGeometry`) so Task 6 unit-tests them directly and no DOM is needed.

- [x] `pixelsToUnits(deltaPx, axisWidthPx, totalUnits)`: `unitPx = axisWidthPx / totalUnits`; return `0` when `axisWidthPx <= 0` or `totalUnits <= 0` (guard divide-by-zero); else `Math.round(deltaPx / unitPx)`. This snaps a continuous drag to whole timescale units. [Source: 3-6 barGeometry units/axis maths]
- [x] `shiftDateValue(field, oldValue, deltaUnits, unit)`: the date-value builder (the analogue of 3.5's `dateValueForDay`). Parse `oldValue` in the **local user frame** with `parseTimelineValue` (never `moment.utc` — same lesson as 3.5/3.6); `add(deltaUnits, unit)`; then serialise in the canonical cell shape: date-only field (`!field.date_include_time`) → `m.format('YYYY-MM-DD')`; datetime field (`field.date_include_time`) → `m.utc().format()` **preserving the original time-of-day** (only the date part shifts by whole units, so `HH:mm:ss` is carried). Returns `null` if `oldValue` is empty (should not happen for a scheduled bar, but guard). [Source: 3-5 Task 3 dateValueForDay; fieldTypes.js BaseDateFieldType.formatValue ~2588; TimelineView.parseTimelineValue]
- [x] `clampResizeUnits(mode, oldStart, oldEnd, deltaUnits, unit)`: for `resize-start`, the new start must stay `<= oldEnd` → clamp `deltaUnits` so `start + deltaUnits` is at most `endSnap - 1 unit` (min 1-unit bar); for `resize-end`, the new end must stay `>= oldStart` → clamp so `end + deltaUnits` is at least `startSnap + 1 unit`. Returns the clamped integer `deltaUnits` (may be 0 → caller treats as no-op). Compute the boundary using whole-unit `diff` on `startOf(unit)`-snapped moments, consistent with `barGeometry`'s span maths (a 1-unit bar = start and end in the same unit). This clamp is the **resize correctness keystone** — unit-test it both directions including the "drag past the opposite edge" case. [Source: 3-6 barGeometry reversed-range → 1-unit clamp]

### Task 5 — Commit handlers reusing the existing optimistic path (AC: #1, #2, #3, #4)

- [x] **Move** → `onCommitMove(row, deltaUnits)`: `unit = timelineUnit(this.timescale)`. Read `oldStart = row['field_'+startDateField.id]`, `oldEnd = row['field_'+endDateField.id]`. Build `newStart = shiftDateValue(startDateField, oldStart, deltaUnits, unit)`, `newEnd = shiftDateValue(endDateField, oldEnd, deltaUnits, unit)`. Dispatch the **plural** action ONCE so both cells go in one `batchUpdate`:

  ```js
  await this.$store.dispatch(this.storePrefix + 'view/timeline/updateRowValues', {
    table: this.table,
    view: this.view,
    fields: this.fields,
    row,
    values: { [startDateField.id]: newStart, [endDateField.id]: newEnd },
    oldValues: { [startDateField.id]: oldStart, [endDateField.id]: oldEnd },
  })
  ```
  Wrap in `try/catch` → `notifyIf(error, 'field')` (mirror the existing `updateValue`). Atomic two-field update ⇒ AC #1 (duration preserved), AC #3 (one broadcast), AC #4 (both roll back together). **Do NOT** call `updateRowValue` (singular) twice. [Source: bufferedRows.js:917 updateRowValues; TimelineView.updateValue error pattern]
- [x] **Resize** → `onCommitResize(row, mode, deltaUnits)`: `clamped = clampResizeUnits(mode, oldStart, oldEnd, deltaUnits, unit)`; if `clamped === 0` return (no-op). For `resize-start`: `field = startDateField`, `value = shiftDateValue(startDateField, oldStart, clamped, unit)`, `oldValue = oldStart`. For `resize-end`: `field = endDateField`, `value = shiftDateValue(endDateField, oldEnd, clamped, unit)`, `oldValue = oldEnd`. Dispatch the existing **single-field** `this.updateValue({ field, row, value, oldValue })` (already in the component) — only the dragged endpoint is written (AC #2). [Source: TimelineView.updateValue]
- [x] **Reactive re-position (no manual DOM):** because `barStyle`/`scheduledRows` are computeds over the store row values, the optimistic write re-positions the bar instantly and a rollback reverts it — exactly as Calendar's `rowsByDay` re-buckets in 3.5. **Never** manually translate/splice the bar to its final spot from JS; clear the transient drag offset and let the computed re-render. [Source: 3-5 Dev Notes "let the computed re-bucket"]

### Task 6 — Frontend unit tests (AC: #1, #2, #5) — method/computed-level only

- [x] **Do NOT `testApp.mount(TimelineView)`** — the premium Timeline store registers last (override) → mock-miss + JS-heap OOM (the same failure 3.2/3.3/3.4/3.6 hit). Extend `web-frontend/test/unit/database/components/view/timeline/timelineView.spec.js` with the **method/computed-level** pattern: export the new pure fns and bind the handler methods to a minimal fake `vm`. [Source: 3-6 Task 7; timelineView.spec.js existing pattern]
  - [x] `pixelsToUnits`: a px delta of one unit-width → `1`; half a unit → rounds to `0`/`1` correctly; negative delta → negative units; `axisWidthPx=0` or `totalUnits=0` → `0` (no divide-by-zero).
  - [x] `shiftDateValue`: date-only field shifts the `YYYY-MM-DD` by N units (day/week/month); datetime field preserves `HH:mm:ss` and only moves the date; round-trips through `parseTimelineValue` in the local frame (assert `parseTimelineValue(shiftDateValue(...)).isSame(expected)`), including a month-boundary / DST-adjacent case (the correctness keystone).
  - [x] `clampResizeUnits`: `resize-start` dragged right past end → clamps to leave a 1-unit bar; `resize-end` dragged left past start → clamps to a 1-unit bar; an in-bounds resize passes through unchanged; both directions return `0` when the clamp collapses the move.
  - [x] `onCommitMove`: dispatches `view/timeline/updateRowValues` **once** with both `startDateField`/`endDateField` ids in `values` and `oldValues`, deltas applied, duration preserved. (AC #1/#3)
  - [x] `onCommitResize`: `resize-start` dispatches `updateValue` with only `startDateField`; `resize-end` with only `endDateField`; the opposite field is untouched. (AC #2)
  - [x] `onMouseUp`/lifecycle: `deltaUnits === 0` → no dispatch (no-op move and no-op resize); `canDragBars` false → no dispatch.
  - [x] `canDragBars`: false when `readOnly`, false when either date field null, false when EITHER field's `canWriteFieldValues` is false, true only when both writable (stub the registry). (AC #5)
- [x] Run: `yarn vitest run web-frontend/test/unit/database/components/view/timeline/timelineView.spec.js`. Expect green (existing 41 + new). [Source: 3-6 Debug Log run command]

### Task 7 — Clean-room provenance (gate, MANDATORY) (AC: all)

- [x] Add `docs/clean-room/provenance/3-7-reschedule-and-resize-timeline-bars.md` declaring **Bucket A**: no `premium/`/`enterprise/` sources read; built by extending the core Timeline (3.6) with the core Kanban drag (3.2) + core Calendar drag-to-reschedule (3.5) pattern and bundled `moment`; pointer-drag derived from primitives, no drag library. Mirror the 3-5/3-6 provenance file structure (allowed-source list + implementer-eligibility + reviewer-confirmation checkboxes — check them). Validate with the gate (`docs/clean-room/scripts/check_provenance.py` / `validate_provenance()` → expect **PASS** as Bucket A; `PR_LABELS=bucket-a`). PR must carry the `bucket-a` label/checkbox. [Source: 1-1-establish-the-clean-room-process-gate.md; 3-5 Task 7; 3-6 Task 9]

### Task 8 — SCSS drag/resize visual states (AC: #1, #2, #5)

- [x] In `web-frontend/modules/core/assets/scss/components/views/timeline.scss` add: `.timeline-view__bar--draggable` (`cursor: grab`), `.timeline-view__bar--dragging` (`cursor: grabbing`, e.g. raised `z-index`/shadow/opacity), and `.timeline-view__resize-handle` (absolutely positioned, ~6px wide, `cursor: ew-resize`, `--start { left: 0 }` / `--end { right: 0 }`, visible on bar hover). Keep `pointer-events` so handles capture their own `mousedown` but the bar body still gets clicks elsewhere. Mirror `kanban.scss` `--draggable`/`--dragging` precedent; no new dependency. The bar already has `cursor: pointer` — make `--draggable` override to `grab`. [Source: timeline.scss `.timeline-view__bar`; kanban.scss:58–62 drag states; 3-5 Task 4]

### Task 9 — E2E scenario (AC: #1, #2, #3, #4) — author only

- [x] Extend `e2e-tests/tests/database/timeline_view.spec.ts` (the 3.6 spec; `createTimelineView` fixture already exists) with move + resize scenarios. Use Playwright `mouse.move`/`mouse.down`/`mouse.up` (continuous pointer-drag — there is no native `dragTo` drop cell). Scenarios: (a) **move** a bar right by a known pixel distance ≈ N units → reopen the row / DB read asserts BOTH date cells advanced by N units preserving the span, and the bar re-renders at the new offset; (b) **resize** the right edge → only `end_date_field` changed, `start_date_field` unchanged, bar is wider; (c) reload → the new dates persist. [Source: 3-6 Task 8 timeline_view.spec.ts; e2e-tests/fixtures/database/view.ts createTimelineView]
- [x] **Do NOT run E2E locally** — requires the Docker stack; targets the OSS-only CI lane (`e2e-tests/` has no local tsconfig/node_modules). Author the spec only. Format `.ts` with `web-frontend/node_modules/.bin/prettier`. [Source: 3-6 Task 8; 3-5 Debug Log prettier-for-ts note]

### Task 10 — Lint + verify (AC: all)

- [x] ESLint + Prettier on `TimelineView.vue` + spec; Stylelint on `timeline.scss`; Prettier on the e2e `.ts`. ESLint 9 must be invoked from **repo root** with `web-frontend/node_modules/.bin/eslint` (fails with "No files matching" from inside `web-frontend/`). [Source: 3-5/3-6 Debug Log ESLint-from-root note]
- [x] `just b run pre-commit run --files $(git diff --name-only origin/develop...HEAD)` (or run the individual linters directly if `just`/`pre-commit` not on PATH, as in 3-5/3-6). No backend lint expected (frontend-only). [Source: AGENTS.md code-quality]

## Dev Notes

### 🧭 Single most important constraint: ZERO backend code

Like Story 3.5 (Calendar drag), this is a **pure-frontend** story. Move/resize = changing one or two Date cell values. The full backend path already exists and is load-bearing:

- `updateValue`/`updateRowValues` → `view/timeline/updateRowValue(s)` → `bufferedRows.updatePreparedRowValues` → `RowService.batchUpdate` → backend `RowHandler` → Postgres + **permission check** → **WebSocket `rows_updated` broadcast** → **Redis model-cache invalidation**. All of this is free **only because** the existing handler path is reused. A new/direct path would bypass the permission boundary and the broadcast. [Source: architecture.md:223–226,342; 3-5 Dev Notes]
- **If you find yourself editing `backend/`, stop — you've left the story.** No new endpoint, "move/resize bar" view, signal, or migration. [Source: 3-5 Dev Notes]

### Everything you need is already in `TimelineView.vue` (3.6) — extend, don't rebuild

- **`updateValue({ field, row, value, oldValue })`** already dispatches `view/timeline/updateRowValue` with `notifyIf` on failure — reuse verbatim for **resize** (single field). [Source: TimelineView.vue updateValue]
- **`updateRowValues` (plural)** is spread into the timeline store via `...timelineBufferedRows.actions` (it lives in `bufferedRows.js:917`, calling `prepareMultipleRowValues` → one `batchUpdate`). Use it for **move** so both cells go in one atomic request. There is no timeline-specific multi-field action to write. [Source: store/view/timeline.js; bufferedRows.js:778,917]
- **Pure geometry helpers** (`timelineUnit`, `parseTimelineValue`, `rowDateRange`, `barGeometry`, `axisUnitCount`) are already exported and unit-tested. `totalUnits`/`axisRange`/`timescale`/`scheduledRows` computeds exist. Reuse them: `timelineUnit(this.timescale)` is the move/resize unit; `this.totalUnits` is the px→unit denominator. [Source: TimelineView.vue exports]
- **`row._.dragging`** is pre-seeded `false` by `store/view/timeline.js populateRow` (3.6 anticipated this story) — reuse it for the `--dragging` class; don't re-add it. [Source: store/view/timeline.js populateRow]
- **Reactive re-position:** `barStyle(row)` is a method over `barGeometry` reading live store values; the optimistic write re-renders the bar, the rollback reverts it. **Never** splice/translate the bar to its final position manually. [Source: 3-5 "let the computed re-bucket"]

### The net-new logic (three pure functions — the keystones)

Everything else reuses 3.5/3.6. The genuinely new pieces:

1. **`pixelsToUnits(deltaPx, axisWidthPx, totalUnits)`** — snaps a continuous pixel drag to whole `timescale` units. `unitPx = axisWidthPx / totalUnits`; `Math.round(deltaPx / unitPx)`; guard `axisWidthPx<=0 || totalUnits<=0 → 0`.
2. **`shiftDateValue(field, oldValue, deltaUnits, unit)`** — the date-value builder. Parse in the **local user frame** (`parseTimelineValue`, never `moment.utc`), `add(deltaUnits, unit)`, serialise as `YYYY-MM-DD` (date-only) or `m.utc().format()` preserving time-of-day (datetime). Round-trip invariant: `parseTimelineValue(shiftDateValue(field, v, n, unit))` is `parseTimelineValue(v).add(n, unit)`. The local-frame parse matters at month/DST boundaries — 3.5's `dateValueForDay` learned this; do not regress to `moment.utc` for the arithmetic. [Source: 3-5 Task 3; 3-6 parseTimelineValue rationale]
3. **`clampResizeUnits(mode, oldStart, oldEnd, deltaUnits, unit)`** — keeps a resize from inverting the bar: `resize-start` clamps so the new start stays ≤ end−1unit; `resize-end` clamps so the new end stays ≥ start+1unit. Minimum bar = 1 unit (consistent with `barGeometry`'s reversed-range → 1-unit clamp). Returns clamped int (0 ⇒ no-op).

### Move vs resize — which store action

| Interaction | Fields written | Store action | Why |
|---|---|---|---|
| **Move** (drag body) | start **and** end | `view/timeline/updateRowValues` (plural, once) | Atomic two-field `batchUpdate` ⇒ duration preserved, single broadcast (AC #3), single rollback (AC #4). |
| **Resize** (drag edge) | only the dragged endpoint | `this.updateValue` (single) | Only one cell changes (AC #2). |

**Do NOT** issue two `updateRowValue` calls for a move — that is two requests, two rollback units, and a visible half-moved state if the second fails.

### Pointer-drag, not HTML5 DnD (the mechanic delta from 3.2/3.5)

Kanban/Calendar used native `draggable`+`drop` between discrete targets. A timeline bar slides a continuous distance with no drop cells, so use `mousedown` (on bar body for move, on edge handle for resize) → `document`-level `mousemove` (track `clientX` delta) → `mouseup` (commit). Attach the `mousemove`/`mouseup` listeners to `document`/`window` on `mousedown` and **remove them on `mouseup` and in `beforeUnmount`** (leak guard). Use `@mousedown.stop` on the resize handles so an edge press doesn't also trigger a move. Suppress the bar's `@click` row-open when a drag actually moved (track a `moved`/`suppressClick` flag), but keep a no-drag click opening the modal. [Source: epics.md#Story 3.7; TimelineView.vue rowClick]

### Permission / read-only (AC #5)

`canDragBars` mirrors `KanbanView.canDrag:230` / Calendar `canDragDate` (3.5) but requires **both** date fields writable: `!readOnly && startDateField && endDateField && [start,end].every(f => fieldRegistry.get('field', f.type).canWriteFieldValues(f))`. **Reuse this existing predicate — do not invent a new permission check.** Epic 1's central field-permission layer enforces server-side regardless; a forbidden update returns an error → `updateRowValues`/`updateRowValue` rolls back and re-throws → `notifyIf` surfaces it. UI gating is UX; the server is the backstop. [Source: KanbanView.vue:230; 3-5 Task 1; architecture.md:316]

### Date value shape (reused from 3.5)

`BaseDateFieldType.formatValue(field, value)` returns `field.date_include_time ? moment.utc(value).format() : moment.utc(value).format('YYYY-MM-DD')` (fieldTypes.js ~2588) — the canonical store shape. `shiftDateValue` must emit that shape: `YYYY-MM-DD` for date-only; `m.utc().format()` for datetime (preserving `HH:mm:ss`). `DateFieldType.prepareValueForUpdate` is the identity default — send the formatted string as-is; don't over-convert. [Source: fieldTypes.js BaseDateFieldType.formatValue; 3-5 Dev Notes "Date value shape"]

### Clean-room reminder (the porous boundary)

Bucket A `[A]` story. The clean-room boundary **leaks under debugging** — prior agents drifted into `premium/`/`enterprise/` while "just checking how the premium timeline drags". Hold the line: every file you read is under `web-frontend/modules/{database,core}/...`, `web-frontend/test/...`, or `e2e-tests/...`. Your **only** references for "what drag/resize looks like" are the **core Kanban** drag (3.2), the **core Calendar** drag (3.5), and the **core Timeline** render (3.6). The premium timeline directories exist **only so you know what NOT to open**. A contaminated Bucket A PR cannot merge. [Source: memory clean-room-isolation-porous; baserow-open-core-license-constraint; 1-1 provenance gate]

### Anti-patterns (forbidden)

- ❌ Any backend file change (endpoint/handler/serializer/signal/migration) — the row-update + broadcast path already exists. [Source: 3-5 Dev Notes]
- ❌ Opening/reading/adapting anything under `premium/` or `enterprise/` (clean-room contamination → PR cannot merge).
- ❌ A drag/resize/Gantt library (interact.js, Frappe Gantt, vis-timeline, vuedraggable) — bundled `moment` + pointer events suffice. (Frappe Gantt is Story 3.8 Bucket B, render-only.) [Source: architecture.md:111,168]
- ❌ Two separate `updateRowValue` calls for a move instead of one atomic `updateRowValues` (breaks AC #3/#4 atomicity).
- ❌ A bespoke "move bar"/"resize bar" store action or service — reuse `updateRowValues`/`updateValue`.
- ❌ Manually translating/splicing the bar to its final position instead of letting `barStyle`/`scheduledRows` re-render from the store (breaks rollback + realtime). [Source: 3-5]
- ❌ Building the new datetime value with `moment.utc(...)` for the date arithmetic so it disagrees with `parseTimelineValue`'s local parse (bar lands a unit off near a boundary). [Source: 3-5/3-6 local-frame parse]
- ❌ Producing a reversed/zero-width bar on resize instead of clamping to a 1-unit minimum.
- ❌ Leaking `document`/`window` `mousemove`/`mouseup` listeners (remove on `mouseup` + `beforeUnmount`).
- ❌ Letting a drag also fire the bar's `@click` row-open (suppress click after a real drag).
- ❌ `testApp.mount(TimelineView)` in unit tests (premium store override → mock-miss + OOM) — method/computed-level only.
- ❌ Marking a task `[x]` without the cited verification / passing test ("lying about completion").
- ❌ Merging a Bucket A PR without a passing provenance record (CI gate blocks it).

### Project Structure Notes

**New files (core):**
- `docs/clean-room/provenance/3-7-reschedule-and-resize-timeline-bars.md`

**Modified files (core):**
- `web-frontend/modules/database/components/view/timeline/TimelineView.vue` (resize-handle DOM + `canDragBars` + `dragState` + `onBarMouseDown`/`onMouseMove`/`onMouseUp` + `onCommitMove`/`onCommitResize` + exported pure fns `pixelsToUnits`/`shiftDateValue`/`clampResizeUnits`)
- `web-frontend/modules/core/assets/scss/components/views/timeline.scss` (`--draggable`/`--dragging` + `.timeline-view__resize-handle*`)
- `web-frontend/test/unit/database/components/view/timeline/timelineView.spec.js` (drag/resize/value/permission tests + new exports)
- `e2e-tests/tests/database/timeline_view.spec.ts` (move + resize scenarios)

No backend files. No new migration. No new locale keys expected (drag/resize is gesture-only; add an i18n key only if you surface visible text). Naming follows existing conventions: `.vue` PascalCase, methods camelCase, BEM SCSS. [Source: architecture.md:279; AGENTS.md Coding Style]

### References

- [Source: epics.md#Epic 3 → Story 3.7, lines 562–574] — user story + AC (move → both fields update preserving duration; edge drag → dragged endpoint updates; realtime broadcast NFR-1; failures roll back NFR-3).
- [Source: epics.md NFR-1 (realtime broadcast), NFR-3 (optimistic + rollback, LWW per field)].
- [Source: web-frontend/modules/database/components/view/timeline/TimelineView.vue] — the component to extend: `updateValue`, `barStyle`/`barGeometry`, `rowDateRange`/`parseTimelineValue`/`timelineUnit`/`axisUnitCount`, `startDateField`/`endDateField`/`timescale`/`totalUnits`/`axisRange`/`scheduledRows`, `rowClick`, bar DOM `.timeline-view__bar`. (Story 3.6)
- [Source: web-frontend/modules/database/store/view/bufferedRows.js:858 (`updateRowValue`), :917 (`updateRowValues`), :778 (`prepareMultipleRowValues`), :775 (`updatePreparedRowValues`)] — single- and multi-field optimistic commit + `batchUpdate` + rollback/re-throw path.
- [Source: web-frontend/modules/database/store/view/timeline.js] — timeline bufferedRows store (spreads `updateRowValue`/`updateRowValues`); `populateRow` pre-seeds `row._.dragging`.
- [Source: web-frontend/modules/database/components/view/kanban/KanbanView.vue:230 (`canDrag`), :310/:330/:344/:368 (drag handlers)] — permission gate (`canWriteFieldValues`) + drag mechanics precedent (Story 3.2).
- [Source: web-frontend/modules/database/fieldTypes.js — `BaseDateFieldType.formatValue` (~2588), `DateFieldType`] — canonical Date cell value shape (date-only vs datetime); identity `prepareValueForUpdate`.
- [Source: web-frontend/modules/database/realtime.js (`rows_updated`)] + [viewTypes.js (`rowUpdated` mixin)] — inbound realtime re-position path (verify-only, no new code).
- [Source: web-frontend/modules/core/assets/scss/components/views/{timeline,kanban}.scss] — `.timeline-view__bar`; `--draggable`/`--dragging` SCSS precedent.
- [Source: 3-5-reschedule-a-calendar-entry-by-drag.md] — the immediate drag-story precedent: ZERO backend, reuse `updateValue`, let the computed re-bucket, local-frame date value (`dateValueForDay`), `canDrag*` permission gate, method/computed-level unit tests (no mount/OOM), provenance hard gate, prettier-for-ts, ESLint-from-repo-root. Clone this discipline.
- [Source: 3-6-create-and-configure-a-timeline-view.md] — the Timeline render this extends: pure geometry helpers, `updateValue`, `row._.dragging` pre-seed, OSS-only test note, premium last-wins registration, provenance gate.
- [Source: 3-2-drag-a-kanban-card-between-columns.md] — original core drag precedent (ZERO backend, reuse update path, computed re-bucket).
- [Source: 1-1-establish-the-clean-room-process-gate.md] — provenance = hard merge gate; "influenced by" = contamination.
- [Source: memory clean-room-isolation-porous] — clean-room drift during verify/debug; hold the line.
- [Source: memory baserow-open-core-license-constraint] — paid features need clean-room reimplement; PE/EE forbids copying.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (BMAD dev-story workflow)

### Debug Log References

- **`clampResizeUnits` `-0` regression.** A `resize-end` clamp on a 1-unit bar returned `-0` (`Math.max(deltaUnits, -span)` with `span=0`), failing `expected -0 to be +0`. Fixed by appending `+ 0` to both return branches to normalise `-0`→`0`, keeping the no-op case a true no-op so the commit short-circuits.
- **Unit tests run method/computed-level — NO `testApp.mount(TimelineView)`.** Mounting registers the premium Timeline store last (override) → mock-miss + JS-heap OOM (same failure 3.2/3.3/3.4/3.6 hit). The new suites bind handler methods / computeds to a minimal fake `vm` and call the exported pure fns directly.
- **Run:** `web-frontend/node_modules/.bin/vitest run test/unit/database/components/view/timeline/timelineView.spec.js` → **70 passed** (41 pre-existing 3.6 + 29 new 3.7).
- **Lint:** ESLint (from repo root via `web-frontend/node_modules/.bin/eslint`) clean; Prettier reformatted the spec + the e2e `.ts` (web-frontend prettier — `e2e-tests/` has no local prettier); Stylelint on `timeline.scss` clean.
- **Provenance gate:** `PR_LABELS=bucket-a CHANGED_FILES=docs/clean-room/provenance/3-7-…md python3 docs/clean-room/scripts/check_provenance.py` → **PASS** (valid Bucket A record).

### Completion Notes List

- **ZERO backend code.** Move/resize is one (resize) or two (move) Date-cell writes through the existing optimistic path. No endpoint, handler, serializer, signal, or migration touched.
- **Move = atomic two-field write.** `onCommitMove` dispatches the plural `view/timeline/updateRowValues` ONCE — both date fields in a single `batchUpdate` → one broadcast, one rollback, duration preserved (AC #1/#3/#4). **Resize = single-field write** via `updateValue` on only the dragged endpoint (AC #2).
- **Pointer-drag, not HTML5 DnD.** `mousedown` on bar/edge → `document`-level `mousemove` (track `clientX` delta) → `mouseup` commit. Three net-new pure exported fns: `pixelsToUnits` (px→whole units, divide-by-zero guarded), `shiftDateValue` (local-frame `parseTimelineValue` + `add`, canonical `YYYY-MM-DD`/UTC-ISO shape preserving time-of-day), `clampResizeUnits` (min 1-unit bar, `-0` normalised). Window listeners torn down in `beforeUnmount` (leak guard); drag suppresses the bar's `@click` row-open.
- **`canDragBars`** requires `!readOnly` AND both date fields set AND both writable via `canWriteFieldValues` (Epic 1 field-permission layer); affordances only render when true, commit re-checks before writing.
- **Clean-room held.** No `premium/`/`enterprise/` source opened. Sources: core 3.2 Kanban drag, core 3.5 Calendar drag, core 3.6 Timeline render, `canWriteFieldValues`, `BaseDateFieldType.formatValue`, bufferedRows update path, bundled `moment`, `RowCard`, Playwright. Provenance gate PASS.
- **E2E authored only** (`e2e-tests/` needs the Docker stack; OSS-only CI lane): five scenarios — move → both date cells +N units span preserved; resize right edge → only end date changes; resize left edge → only start date changes; resize past the opposite edge → clamps to a 1-unit bar; zero-unit release → no-op (dates unchanged).

### File List

**New:**
- `docs/clean-room/provenance/3-7-reschedule-and-resize-timeline-bars.md`

**Modified:**
- `web-frontend/modules/database/components/view/timeline/TimelineView.vue`
- `web-frontend/modules/core/assets/scss/components/views/timeline.scss`
- `web-frontend/test/unit/database/components/view/timeline/timelineView.spec.js`
- `e2e-tests/tests/database/timeline_view.spec.ts`

## Change Log

| Date | Version | Description | Author |
|---|---|---|---|
| 2026-06-10 | 0.1 | Story 3.7 implemented: pointer-drag move (atomic two-field) + edge resize (single-field) on Timeline bars; net-new pure fns `pixelsToUnits`/`shiftDateValue`/`clampResizeUnits`; `canDragBars` permission gate; SCSS drag/resize states; 70/70 unit tests; E2E authored; clean-room provenance PASS. Status → review. | claude-opus-4-8 (dev-story) |
| 2026-06-10 | 0.2 | Senior Developer Review (AI): adversarial review — 0 CRITICAL / 0 HIGH, 1 MEDIUM + 2 LOW auto-fixed (gate bar-body `mousedown` on `canDragBars` + primary-button guard; E2E-scenario-count doc drift). 70/70 unit tests, ESLint/Stylelint/Prettier clean, provenance gate PASS (Bucket A). Status → done. | claude-opus-4-8 (review) |

## Senior Developer Review (AI)

**Reviewer:** Pham (claude-opus-4-8) · **Date:** 2026-06-10 · **Outcome:** Approve (status → done)

### Scope

Adversarial review of the Story 3.7 implementation against the 5 ACs, the 10 tasks, and the git-discovered File List. Source files reviewed: `TimelineView.vue`, `timeline.scss`, `timelineView.spec.js`, `timeline_view.spec.ts`, provenance record. (`_bmad-output/`, `_bmad/` excluded per review policy.)

### Verification

- **AC #1 (move preserves duration, zero = no-op):** `onCommitMove` dispatches the plural `view/timeline/updateRowValues` ONCE with both field deltas; `onMouseUp` guards `deltaUnits === 0`. ✅ (unit + E2E)
- **AC #2 (resize one endpoint, 1-unit clamp):** `onCommitResize` writes only the dragged field via `updateValue`; `clampResizeUnits` floors at a 1-unit bar (`barGeometry` renders same-unit start/end as width 1). ✅ (unit + E2E)
- **AC #3 (realtime broadcast):** reuses `bufferedRows` → `batchUpdate`, no new endpoint/handler/signal/migration. ✅
- **AC #4 (optimistic + rollback):** move = atomic two-field `batchUpdate` (one rollback unit); resize `updateValue` try/catch → `notifyIf('field')`. ✅
- **AC #5 (permission gate):** `canDragBars` requires `!readOnly` AND both date fields set AND both `canWriteFieldValues`; `onMouseUp` re-checks before commit. ✅
- **Clean-room:** no `premium/`/`enterprise/` source read; provenance gate `PASS` (`PR_LABELS=bucket-a`). ✅
- **Tests:** 70/70 unit pass (verified live). ESLint / Stylelint / Prettier clean.

### Findings (all auto-fixed)

| Sev | Finding | Resolution |
|---|---|---|
| MEDIUM | Bar-body `@mousedown.prevent` was bound unconditionally — Task 2 requires no mousedown binding when `!canDragBars`; `.prevent` fired on read-only bars, blocking native focus/text-selection. | Removed `.prevent`; `onBarMouseDown` now `event.preventDefault()`s only after the `canDragBars` guard. `TimelineView.vue:29,652` |
| LOW | No mouse-button guard — a right/middle-click started a phantom drag and attached global `window` listeners. | Added `if (event.button !== 0) return` at the top of `onBarMouseDown`. |
| LOW | Doc drift — Completion Notes + provenance said "two new E2E scenarios"; the spec carries five (3 added by the QA gap-fill pass). | Updated both to enumerate all five scenarios. |

No CRITICAL or HIGH findings: every `[x]` task has matching implementation evidence and every AC is implemented and tested.
