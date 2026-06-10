---
baseline_commit: 4a33c01fde9fa8a2439d54a5fb46c5d248eef769
---

# Story 3.5: Reschedule a Calendar Entry by Drag

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to drag a calendar entry to another date,
so that the Row's Date Field updates without opening the row.

## Acceptance Criteria

1. **Drag → reschedule.** Dragging a calendar card from one day cell and dropping it on another day cell sets the Row's configured Date Field (`view.date_field`) to the target day, and the card re-buckets onto the target cell reactively. Dropping a card on its own current day is a no-op (no request, no flicker). [Source: epics.md#Story 3.5; CalendarView.vue `groupRowsByDate`/`rowsByDay`]
2. **Real-time broadcast (NFR-1).** The reschedule reuses the existing row-update handler path, so the change broadcasts over WebSocket to other clients and invalidates the model cache automatically — **no new endpoint, handler, signal, or migration**. Inbound `rows_updated` on other clients re-buckets the card with no new code. [Source: architecture.md:223–226,342; 3-2 Dev Notes "ZERO backend code"]
3. **Optimistic + rollback (NFR-3).** The move applies optimistically; a failed backend update (e.g. field permission denied) rolls the cell back to its previous value and surfaces an error via `notifyIf`. The card returns to its origin day. [Source: bufferedRows.js `updateRowValue`/`updatePreparedRowValues`:858–916; 3-2 AC #3]
4. **Permission / read-only gate (AC ties to NFR-3 + Epic 1 field perms).** Cards are only draggable when the view is not `readOnly` **and** the Date Field is writable for the user (`canWriteFieldValues(dateField)`). A read-only view or a non-writable Date Field offers no drag and ignores drops; the server-side field-permission layer remains the authoritative backstop (denied → rollback per AC #3). [Source: KanbanView.vue `canDrag`:230; architecture.md:316]
5. **Unscheduled tray, both directions.** Dragging an **unscheduled** card (empty Date Field) onto a day cell sets the Date Field (schedules it); dragging a scheduled card onto the unscheduled tray clears the Date Field to `null` (unschedules it). Both ride the same single `updateValue` call. Value-cleared rows move to the tray reactively. [Source: CalendarView.vue `unscheduledRows`/`rowDateKey`]

## Tasks / Subtasks

- [x] Task 1: Add drag source + drop targets to `CalendarView.vue` (AC: #1, #4) — frontend only
  - [x] Add `draggingRow: null` to `data()`; add a `canDragDate` computed: `false` when `readOnly` or no `dateField`, else `this.$registry.get('field', dateField.type).canWriteFieldValues(dateField)` (mirror `KanbanView.canDrag:230`).
  - [x] On each `RowCard` (both grid cells and the unscheduled tray) bind `:draggable="canDragDate"`, `:class="{ 'calendar-view__card--draggable': canDragDate, 'calendar-view__card--dragging': row._.dragging }"`, `@dragstart="onDragStart(row, $event)"`, `@dragend="onDragEnd(row)"`. (`row._.dragging` is already pre-seeded `false` by `store/view/calendar.js populateRow` — do NOT add it.)
  - [x] Add `@dragover="onDragOver($event)"` + `@drop="onDropDay(day, $event)"` to `.calendar-view__day`; add `@dragover="onDragOver($event)"` + `@drop="onDropUnscheduled($event)"` to `.calendar-view__unscheduled`. Bind `@dragover` WITHOUT the `.prevent` modifier (guard prevents non-drag dragover from claiming the target — see kanban note at KanbanView.vue:336).
- [x] Task 2: Implement drag handlers (AC: #1, #3, #4, #5)
  - [x] `onDragStart(row, event)`: if `!canDragDate` → `event.preventDefault()` + return; else set `draggingRow`, `row._.dragging = true`, `event.dataTransfer.effectAllowed = 'move'`, and `setData('text/plain', String(row.id))` in a try/catch (some browsers require a payload). Mirror `KanbanView.onDragStart:310`.
  - [x] `onDragEnd(row)` + `onDragOver(event)`: copy from `KanbanView` verbatim (clear `dragging`/`draggingRow`; `onDragOver` calls `preventDefault` only while `canDragDate && draggingRow !== null`).
  - [x] `onDropDay(day, event)`: `preventDefault`; pull `row = draggingRow`, clear drag state; bail if `!canDragDate || !row`. Compute `oldValue = row['field_'+dateField.id] ?? null`. **No-op guard:** if `rowDateKey(oldValue) === day.key` → return. Else build `value` (Task 3) and `return this.updateValue({ field: this.dateField, row, value, oldValue })`.
  - [x] `onDropUnscheduled(event)`: `preventDefault`; same drag-state teardown + `canDragDate`/row guard. If `oldValue` is already empty (`rowDateKey(oldValue) === null`) → no-op return. Else `return this.updateValue({ field: this.dateField, row, value: null, oldValue })`.
- [x] Task 3: Build the target Date Field value so the card lands exactly on the dropped day (AC: #1)
  - [x] Add a helper (component method or module-scope pure fn alongside `rowDateKey`) `dateValueForDay(dateField, oldValue, dayKey)`:
    - Date-only field (`!dateField.date_include_time`): return `dayKey` (`'YYYY-MM-DD'`) — matches `BaseDateFieldType.formatValue` output (fieldTypes.js ~2588).
    - Datetime field (`date_include_time`): preserve time-of-day, swap the date in the **same frame `rowDateKey` reads** (local `moment`, not `moment.utc`) so the result satisfies `rowDateKey(value) === dayKey` and the card lands where dropped. E.g. `const m = oldValue ? moment(oldValue) : moment(dayKey + ' 00:00'); const [y, mo, d] = dayKey.split('-'); m.year(+y).month(+mo - 1).date(+d); return m.utc().format()`.
  - [x] The value is passed through `updateValue` → `updateRowValue` → `prepareNewOldAndUpdateRequestValues` → `DateFieldType.prepareValueForUpdate` (inherited default = identity); do NOT pre-convert beyond the formatted string/`null`.
- [x] Task 4: SCSS drag/drop visual states (AC: #1, #4)
  - [x] In `web-frontend/modules/core/assets/scss/components/views/calendar.scss` add `.calendar-view__card--draggable` (cursor: grab/move) and `.calendar-view__card--dragging` (opacity/visual), mirroring `kanban.scss:58–62`. Optional `dragover` highlight on `.calendar-view__day` (track a `dragOverKey` in data if added) — keep minimal; no new dependency.
- [x] Task 5: Frontend unit tests — extend `web-frontend/test/unit/database/components/view/calendar/calendarView.spec.js` (method/computed-level only; NO `testApp.mount(CalendarView)` — premium store override → OOM)
  - [x] `dateValueForDay`: date-only returns `dayKey`; datetime preserves `HH:mm:ss` and `rowDateKey(result) === dayKey` (assert the round-trip invariant directly — this is the correctness keystone).
  - [x] `onDropDay` dispatches `updateValue` with the right `{ field, value, oldValue }` for day→day; no-op when dropped on the current day; bails when `canDragDate` is false.
  - [x] `onDropUnscheduled` dispatches `value: null`; no-op when already unscheduled.
  - [x] `canDragDate` false when `readOnly` and when `dateField` is null; true via stubbed registry `canWriteFieldValues → true`.
- [x] Task 6: E2E — extend `e2e-tests/tests/database/calendar_view.spec.ts`
  - [x] Scenario: create calendar view w/ date field + a scheduled row, drag the card from its day cell to another day cell, assert the row's Date Field updated (re-open row / DB read) and the card now renders under the new day. Use the existing `createCalendarView` fixture. **Author only — do NOT run locally** (requires Docker stack). [Source: 3-2 test-run note]
- [x] Task 7: Clean-room provenance (Bucket A — hard CI merge gate)
  - [x] Create `docs/clean-room/provenance/3-5-reschedule-a-calendar-entry-by-drag.md` attesting all sources are core/MIT (core Kanban drag 3.2, MIT `utils/date.js`, core Calendar 3.4) — **never** `premium/`/`enterprise/`. Mirror the 3-4 provenance file structure.
- [x] Task 8: Lint + verify (OSS-only profile)
  - [x] Frontend unit: `yarn vitest run web-frontend/test/unit/database/components/view/calendar/calendarView.spec.js` (or `just f test ...`). ESLint 9 must be invoked from **repo root** with `web-frontend/node_modules/.bin/eslint` (fails with "No files matching" from inside `web-frontend/`). Prettier + Stylelint on touched files.
  - [x] Lint branch-touched only: `just b run pre-commit run --files $(git diff --name-only origin/develop...HEAD)`.

## Dev Notes

### 🧭 Single most important constraint: ZERO backend code

This is a **pure frontend** story (same shape as Story 3.2 for Kanban). Rescheduling = changing one Date cell value. The full backend path already exists and is load-bearing:

- `updateValue` → `view/calendar/updateRowValue` → `bufferedRows.updateRowValue` → `RowService.batchUpdate` → backend `RowHandler` → Postgres + **permission check** → **WebSocket `rows_updated` broadcast** → **Redis model-cache invalidation**. All of this is free **only because** the existing handler path is reused. A new/direct path would bypass the permission boundary and the broadcast. [Source: architecture.md:223–226,342,259]
- **If you find yourself editing `backend/`, stop — you've left the story.** No new endpoint, "move entry" view, signal, or migration. [Source: 3-2 Dev Notes]

### Everything you need is already in `CalendarView.vue` — extend, don't rebuild

Story 3.4 shipped the calendar already wired for this:

- **`updateValue({ field, row, value, oldValue })`** (CalendarView.vue methods) already dispatches `view/calendar/updateRowValue` with `notifyIf` on failure. The drop handlers just call it with `field = this.dateField`. This single call satisfies AC #1 (set value), AC #2 (broadcast, automatic backend), AC #3 (rollback + error), AC #5 (clear → tray). **Do not** add a calendar-specific store action or service.
- **`row._.dragging`** is pre-seeded `false` by `store/view/calendar.js populateRow` (3.4 anticipated drag) — reuse it for the visual state; don't re-add it.
- **`rowsByDay` / `unscheduledRows`** are computeds derived from the store via `groupRowsByDate`. When `updateRowValue` optimistically rewrites `field_${dateField.id}`, `grouped` recomputes → the card moves to the target day instantly; rollback reverts the cell → card returns. **Never** maintain a separate per-day array or splice cards manually — that desyncs from the store and breaks rollback/realtime. [Source: 3-2 "Why the card visually moves with no extra code"]
- **`rowDateKey(value)`** (exported pure fn) is the canonical "which day key does this value fall on" — use it for the no-op guard and the `dateValueForDay` round-trip invariant. It parses with **local** `moment(value)` (not `moment.utc`), so the new datetime value must be built in the same frame (see Task 3) or the card could land a day off near midnight.

### Date value shape (the one net-new bit of logic)

`BaseDateFieldType.formatValue(field, value)` returns `field.date_include_time ? moment.utc(value).format() : moment.utc(value).format('YYYY-MM-DD')` (fieldTypes.js ~2588) — that is the canonical store shape for a Date cell. So:

- **Date-only field** → target value is just the `'YYYY-MM-DD'` day key.
- **Datetime field** → preserve the existing time-of-day and only change the date. Build it so `rowDateKey(newValue) === dayKey` (Task 3 snippet). If `oldValue` is empty (scheduling from the tray), default the time to start-of-day.

`DateFieldType` (`getType() === 'date'`) extends `BaseDateFieldType` → `FieldType`; `prepareValueForUpdate` is the **identity default** — the formatted string is sent as-is. Don't over-convert.

### Permission / read-only (AC #4)

- `canDragDate` mirrors `KanbanView.canDrag:230`: `readOnly` OR no date field → not draggable; otherwise gate on `fieldRegistry.get('field', dateField.type).canWriteFieldValues(dateField)`. **Reuse this existing predicate — do not invent a new permission check.** [Source: 3-2 Dev Notes "Field permissions"]
- Epic 1's central field-permission layer enforces server-side regardless; a forbidden update returns an error → `updateRowValue` rolls back and re-throws → `notifyIf` surfaces it. UI gating is UX, the server is the backstop. [Source: architecture.md:316]

### Multi-day events — scope boundary

A multi-day row (start + `end_date_field`) renders a card on **each** spanned visible day (`groupRowsByDate` repeats it). Per the epic AC, a drag updates **only the configured `date_field`** (the start). Do **not** shift `end_date_field` to preserve span — that is out of scope for 3.5. `groupRowsByDate` already guards `rawEnd > start` (else single-day), so moving start past end degrades gracefully to a single-day card without error. (Span-preserving moves are a possible future enhancement; note it in the Change Log if you touch it, but the default story scope updates start only.)

### Clean-room reminder (the porous boundary)

Bucket A `[A]` story. The clean-room boundary **leaks under debugging** — prior agents drifted into `premium/`/`enterprise/` while "just checking how X works". Hold the line: every file you read is under `web-frontend/modules/{database,core}/...`, `web-frontend/test/...`, or `e2e-tests/...`. Your only references for "what drag looks like" are the **core Kanban** drag (3.2, MIT-derived) and the **core Calendar** (3.4). Premium calendar directories exist **only so you know what NOT to open**. A contaminated Bucket A PR cannot merge. [Source: memory clean-room-isolation-porous; baserow-open-core-license-constraint; 1-1 provenance gate]

### Anti-patterns (forbidden)

- ❌ Any backend file change (endpoint/handler/serializer/signal/migration) — the row-update + broadcast path already exists.
- ❌ Opening/reading/adapting anything under `premium/` or `enterprise/` (clean-room contamination → PR cannot merge).
- ❌ A bespoke "reschedule" store action or service instead of the existing `updateRowValue` / `updateValue`.
- ❌ Manually splicing cards between per-day arrays instead of letting `grouped`/`rowsByDay` re-bucket from the store (breaks rollback + realtime).
- ❌ Building the new datetime value with `moment.utc(...)` for the date swap so it disagrees with `rowDateKey`'s local parse (card lands a day off near midnight).
- ❌ Shifting `end_date_field` on drag (out of scope) or adding intra-day ordering.
- ❌ Adding a calendar/date library — bundled `moment` (`@baserow/modules/core/moment`) suffices.
- ❌ `testApp.mount(CalendarView)` in unit tests (premium store override → mock-miss + OOM) — method/computed-level only.
- ❌ Running tests in the default (open-core) profile — premium calendar shadows core. Use the OSS-only profile (`.env.oss-test`) for any backend run; this story is frontend-only so backend tests should not need changes.
- ❌ Marking a task `[x]` without the cited verification / passing test ("lying about completion").
- ❌ Merging a Bucket A PR without a passing provenance record (CI gate blocks it).

### Project Structure Notes

**New files (core):**
- `docs/clean-room/provenance/3-5-reschedule-a-calendar-entry-by-drag.md`

**Modified files (core):**
- `web-frontend/modules/database/components/view/calendar/CalendarView.vue` (drag UI + `onDragStart`/`onDragEnd`/`onDragOver`/`onDropDay`/`onDropUnscheduled` + `dateValueForDay` + `canDragDate`)
- `web-frontend/modules/core/assets/scss/components/views/calendar.scss` (`--draggable` / `--dragging` states, optional dragover highlight)
- `web-frontend/test/unit/database/components/view/calendar/calendarView.spec.js` (drag/value/permission tests)
- `e2e-tests/tests/database/calendar_view.spec.ts` (drag-to-reschedule scenario)

No backend files. No new migration. Naming follows existing conventions: `.vue` PascalCase, methods camelCase, BEM SCSS. [Source: architecture.md:192–208; AGENTS.md Coding Style]

### References

- [Source: epics.md#Epic 3 → Story 3.5] — user story + AC (drop on another date → Date Field updates + realtime NFR-1; fail → rollback + error NFR-3).
- [Source: epics.md NFR-1 (realtime broadcast), NFR-3 (optimistic + rollback, LWW per field)].
- [Source: architecture.md:223–226,259,316,342] — mutation→Handler→broadcast→cache path; "direct ORM mutation skips broadcast/cache"; permission boundary; optimistic+rollback grid pattern.
- [Source: web-frontend/modules/database/components/view/calendar/CalendarView.vue] — `updateValue` (drop target method to reuse), `rowDateKey`/`groupRowsByDate`/`rowsByDay`/`unscheduledRows` (reactive re-bucket), `dateField`/`endDateField` computeds. (Story 3.4)
- [Source: web-frontend/modules/database/components/view/kanban/KanbanView.vue:230 (`canDrag`), :310 (`onDragStart`), :330 (`onDragEnd`), :336 (`onDragOver`), :360 (`onDrop`)] — the verbatim drag mechanics + permission gate to mirror. (Story 3.2)
- [Source: web-frontend/modules/database/store/view/calendar.js `populateRow`] — `row._.dragging` already pre-seeded; bufferedRows store factory.
- [Source: web-frontend/modules/database/store/view/bufferedRows.js:858 (`updateRowValue`), :775 (`updatePreparedRowValues`)] — optimistic commit + `batchUpdate` + rollback/re-throw path.
- [Source: web-frontend/modules/database/fieldTypes.js — `BaseDateFieldType.formatValue` (~2588), `DateFieldType`:2655] — canonical Date cell value shape (date-only vs datetime); identity `prepareValueForUpdate`.
- [Source: web-frontend/modules/database/realtime.js (`rows_updated`)] + [viewTypes.js (`rowUpdated` mixin)] — inbound realtime re-bucket path (verify-only, no new code).
- [Source: web-frontend/modules/core/assets/scss/components/views/kanban.scss:58–62] — `--draggable`/`--dragging` SCSS precedent.
- [Source: 3-2-drag-a-kanban-card-between-columns.md] — the drag-story precedent (ZERO backend, reuse `updateValue`, let computed re-bucket, OSS-only test note, provenance gate).
- [Source: 3-4-create-and-configure-a-calendar-view.md] — calendar build (files, OSS-only `.env.oss-test`, method/computed-level unit pattern/no-mount-OOM, ESLint-from-repo-root, provenance hard gate).
- [Source: 1-1-establish-the-clean-room-process-gate.md] — provenance = hard merge gate; "influenced by" = contamination.
- [Source: memory clean-room-isolation-porous] — clean-room drift during verify/debug; hold the line.
- [Source: memory baserow-open-core-license-constraint] — paid features need clean-room reimplement; PE/EE forbids copying.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (BMAD dev-story workflow)

### Debug Log References

- Frontend unit run: `yarn vitest run web-frontend/test/unit/database/components/view/calendar/calendarView.spec.js` → **60 passed** (34 pre-existing 3.4 + 26 new 3.5: `dateValueForDay`, `onDropDay`, `onDropUnscheduled`, `canDragDate`, `onDragStart`, `onDragEnd`, `onDragOver`). One initial failure (`moment is not defined` in the time-of-day assertion) fixed by importing `@baserow/modules/core/moment` into the spec.
- ESLint (from repo root via `web-frontend/node_modules/.bin/eslint`): clean on `CalendarView.vue` + spec.
- Prettier: `calendarView.spec.js` and `calendar_view.spec.ts` reformatted with `--write`; all touched files now pass `--check`. Stylelint clean on `calendar.scss`.
- Clean-room provenance gate (`docs/clean-room/scripts/check_provenance.py`, simulated Bucket A env): **PASS — valid provenance record: docs/clean-room/provenance/3-5-reschedule-a-calendar-entry-by-drag.md**.
- E2E (`calendar_view.spec.ts`): authored only — not run locally (requires the OSS-only Docker stack); wired to the OSS-only CI lane.

### Completion Notes List

- **Pure-frontend, ZERO backend.** Reschedule = one Date-cell change through the existing optimistic `updateValue` → `view/calendar/updateRowValue` path; no endpoint/handler/signal/migration added. WebSocket broadcast + cache invalidation (AC #2) and rollback + `notifyIf` (AC #3) come for free from the reused path.
- **Drag mechanics mirror the 3.2 Kanban verbatim.** Added `draggingRow` data, `canDragDate` computed (read-only / no-field / `canWriteFieldValues` gate — AC #4), and `onDragStart`/`onDragEnd`/`onDragOver`/`onDropDay`/`onDropUnscheduled`. `@dragover` bound WITHOUT `.prevent`; `onDragOver` guards `preventDefault` to an active permitted drag. Reused the pre-seeded `row._.dragging` flag from `store/view/calendar.js populateRow`.
- **`dateValueForDay` is the one net-new bit of logic.** Date-only → `YYYY-MM-DD` key; datetime → preserve time-of-day, swap date in the local `moment` frame `rowDateKey` parses with (never `moment.utc`), serialize UTC ISO. Unit tests assert the round-trip invariant `rowDateKey(dateValueForDay(...)) === dayKey` across midnight-boundary cases (AC #1).
- **AC #5 both directions.** Drop on a day cell schedules/reschedules; drop on the unscheduled tray clears to `null`. Both via the single `updateValue` call; cards re-bucket reactively from `rowsByDay`/`unscheduledRows` (no manual splicing → rollback/realtime intact). No-op guards on self-day drop and already-unscheduled drop.
- **Scope held.** Multi-day `end_date_field` not shifted on drag (out of scope). No backend, no `premium/`/`enterprise/` reads, no new dependency.

### File List

- `web-frontend/modules/database/components/view/calendar/CalendarView.vue` (modified) — drag UI binds + `draggingRow` data + `canDragDate` computed + `dateValueForDay` pure fn + `onDragStart`/`onDragEnd`/`onDragOver`/`onDropDay`/`onDropUnscheduled` handlers
- `web-frontend/modules/core/assets/scss/components/views/calendar.scss` (modified) — `.calendar-view__card--draggable` / `--dragging` states
- `web-frontend/test/unit/database/components/view/calendar/calendarView.spec.js` (modified) — 26 new method/computed-level tests (`dateValueForDay`, `onDropDay`, `onDropUnscheduled`, `canDragDate`, `onDragStart`, `onDragEnd`, `onDragOver`) + `moment` import
- `e2e-tests/tests/database/calendar_view.spec.ts` (modified) — 4 authored scenarios (day→day reschedule + reload-persist, scheduled→tray unschedule, unscheduled→day schedule, self-day-drop no-op; OSS-only CI lane)
- `docs/clean-room/provenance/3-5-reschedule-a-calendar-entry-by-drag.md` (new) — Bucket A provenance record

## Change Log

| Date | Version | Description |
|------|---------|-------------|
| 2026-06-10 | 1.0 | Implemented drag-to-reschedule for the core Calendar view (pure frontend, reusing the existing optimistic row-update path). All 8 tasks complete; 60 frontend unit tests pass; provenance gate passes. Status → review. |
| 2026-06-10 | 1.1 | Senior Developer Review (AI): adversarial review + auto-fix. Synced stale test counts (52→60 unit, 18→26 new, 2→4 E2E scenarios) across Debug Log, File List, Change Log, and the provenance record to match git reality. No code defects, AC gaps, or clean-room contamination found. 0 CRITICAL → Status → done. |

## Senior Developer Review (AI)

**Reviewer:** gabenidolcs (BMAD story-automator-review, adversarial profile)
**Date:** 2026-06-10
**Outcome:** ✅ **Approve** — Status → done (0 CRITICAL)

### Scope verified

- **Git ↔ File List:** All source-file changes match the File List exactly — `CalendarView.vue`, `calendar.scss`, `calendarView.spec.js`, `calendar_view.spec.ts`, and the new provenance record. No undocumented source changes; no claimed-but-absent files. (`_bmad-output/` artifacts excluded from review per workflow rule.)
- **ZERO backend:** Confirmed — no `backend/` files touched, no endpoint/handler/signal/migration. Reschedule rides the existing `updateValue` → `view/calendar/updateRowValue` optimistic path (verified `updateValue` signature `{ field, row, value, oldValue }` matches the drop-handler calls).
- **Clean-room:** Diff touches only `web-frontend/modules/{database,core}/…`, `web-frontend/test/…`, `e2e-tests/…`, and `docs/clean-room/…`. No `premium/`/`enterprise/` reads. Bucket A provenance gate: **PASS** (`check_provenance.py`, simulated CI env).

### Acceptance Criteria

| AC | Verdict | Evidence |
|----|---------|----------|
| #1 day→day reschedule + self-day no-op | ✅ IMPLEMENTED | `onDropDay` computes `dateValueForDay`, calls `updateValue`; no-op guard `rowDateKey(oldValue) === day.key`. Unit + E2E cover both. |
| #2 realtime broadcast (NFR-1) | ✅ IMPLEMENTED | Reuses shared row-update path; no new code. E2E reload-persist asserts server state. |
| #3 optimistic + rollback (NFR-3) | ✅ IMPLEMENTED | `updateValue` → `bufferedRows.updateRowValue` rollback + `notifyIf`. |
| #4 permission / read-only gate | ✅ IMPLEMENTED | `canDragDate` gates on `readOnly`/no-field/`canWriteFieldValues`; `onDragStart`/`onDragOver` re-guard the native drop target. Unit-tested 4 ways. |
| #5 unscheduled tray, both directions | ✅ IMPLEMENTED | `onDropUnscheduled` clears to `null`; `onDropDay` schedules from `null`. Unit + 2 E2E. |

### Findings

- 🟡 **MEDIUM (fixed):** Dev Agent Record + provenance reported stale test counts — "52 passed / 18 new / 2 E2E scenarios". Git reality is **60 unit (34 pre-existing + 26 new)** and **4 E2E scenarios**; the QA workflow added `onDragStart`/`onDragEnd`/`onDragOver` unit tests and the schedule + self-drop-no-op E2E after dev-story without syncing the record. Counts corrected in Debug Log, File List, Change Log, and the provenance Notes.
- 🟢 **LOW (fixed):** Provenance "Reviewer confirmation" checkboxes were unchecked — verified implementer eligibility + allowed-source list and checked them.

### Validation run this review

- `vitest run …/calendarView.spec.js` → **60 passed**.
- ESLint (repo root, `web-frontend/node_modules/.bin/eslint`) → clean. Prettier `--check` (vue/spec/e2e/scss) → clean. Stylelint → clean.
- Provenance gate (Bucket A sim) → **PASS** (re-confirmed after doc edits).

No CRITICAL or HIGH findings. `dateValueForDay` round-trip invariant (`rowDateKey(dateValueForDay(...)) === dayKey`) is directly asserted across midnight-boundary cases — the one net-new bit of logic is correctly tested. Code faithfully mirrors the proven 3.2 Kanban drag.
