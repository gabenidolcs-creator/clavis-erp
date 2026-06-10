---
baseline_commit: 96b1f6dac35c9da6d9eec5dd11ca7af1ff0908c6
---
<!-- Powered by BMAD-CORE™ -->

# Story 3.2: Drag a Kanban card between columns

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to drag a card to another column,
so that moving a card updates the underlying grouping Field. Realizes UJ-1. `[A]`

## Context & Scope

### 🚨 THIS IS A BUCKET A CLEAN-ROOM STORY — READ FIRST, NON-NEGOTIABLE

Kanban is a **Bucket A** feature: it must be reimplemented in **core** without ever reading, copying, or being "influenced by" any `premium/` or `enterprise/` source. The PE/EE license forbids copying; a provenance record is a **hard CI merge gate**.

- **Do NOT open, read, `grep`, or adapt** anything under `premium/` or `enterprise/` — including premium's Kanban drag implementation. Reading it = contamination = the PR cannot merge. [Source: architecture.md line 268; memory clean-room-isolation-porous]
- All code lands in **core** (`backend/src/baserow/...`, `web-frontend/modules/database/...`). [Source: architecture.md line 205]
- A provenance record under `docs/clean-room/provenance/` is **mandatory** (Task: Clean-room provenance, below).
- Premium-precedence: in full open-core builds premium's Kanban overrides core (last-registration-wins / `if "baserow_premium" not in INSTALLED_APPS` backend gate). The free core Kanban (and this drag feature) is the active view type only in **OSS-only** builds (`BASEROW_OSS_ONLY=true`). Run tests OSS-only. [Source: 3-1 Completion Notes]

### Scope of THIS story (3.2 only)

Add **drag-and-drop of a card from one column to another** on the free core Kanban View built in Story 3.1. Dropping a card sets the row's grouping Single-select Field to the target column's option (or `null` for the Uncategorized column), optimistically, with rollback + error on failure, and broadcasts the change in real time to other clients.

**In scope:**
- Native HTML5 drag-and-drop on cards within `KanbanView.vue` (the 3.1 component).
- On drop: dispatch the **existing** `view/kanban/updateRowValue` action with the grouping field + the target option object (or `null`).
- Drag disabled when the view is `readOnly`, when there is no grouping field configured, or when the grouping field is not editable by the current user (Epic 1 field permissions).
- Optimistic move + rollback-on-failure + error notification (reuse the existing bufferedRows path — see Dev Notes).
- Frontend unit tests + E2E spec.

**Explicitly OUT of scope (do NOT build):**
- ❌ **Any backend change.** No new endpoint, serializer, view, handler, signal, or migration. The row-update REST API + WebSocket broadcast + Redis cache-invalidation already exist and fire from the shared handler. See "The single most important constraint" below.
- ❌ Manual card **ordering/position within a column** (single-select Kanban order follows the view's sort; drop only changes the group, not intra-column position).
- ❌ Card-appearance / cover-image configuration → that is Story 3.3.
- ❌ Creating a card by dropping into a column, multi-card selection drag, or cross-table drag.

## Acceptance Criteria

1. **Given** a Kanban card, **When** it is dropped in another column, **Then** the Row's grouping Single-select Field is set to the target option (or `null` for Uncategorized).
2. **And** the change broadcasts in real time to other connected clients without a refresh (NFR-1).
3. **Given** the update fails (server rejects it), **When** the server rejects it, **Then** the card rolls back to its origin column and an error surfaces (optimistic + rollback, NFR-3).
4. Drag is disabled (cards are not draggable / drops are no-ops) when the view is `readOnly`, when no grouping field is configured, or when the grouping Single-select Field is not editable by the current user (Epic 1 field-permission layer).
5. Dropping a card onto its **own** current column is a no-op (no API call, no flicker).

## Tasks / Subtasks

### Task 1 — Card drag-and-drop UI in `KanbanView.vue` (AC: #1, #4, #5)

- [x] In `web-frontend/modules/database/components/view/kanban/KanbanView.vue`, make each card draggable and each column a drop target using **native HTML5 DnD** (`draggable`, `@dragstart`, `@dragend`, `@dragover.prevent`, `@drop`). There is **no** reusable core card-drag component — file-upload dropzones are unrelated. Do not reinvent a generic DnD framework; keep it local to this component.
- [x] Compute a `canDrag` flag: `!readOnly && singleSelectField !== null && fieldIsEditable(singleSelectField)`. When false, do not set `draggable` and ignore drops (AC #4). For field editability reuse the existing field-writable check used by `RowCard` / grid editing (see Dev Notes "Field permissions / readOnly").
- [x] Track the dragged row in component state and use the existing pre-seeded `row._.dragging` flag (set in `store/view/kanban.js` `populateRow`) for the drag visual state; reset on `dragend`/`drop`.
- [x] On `@drop` over a column, resolve the **target option object** from the column (`{ id, value, color }` for a real column, `null` for Uncategorized) and call the `updateValue` path (Task 2). Compute `oldValue` from the row's current `field_${id}` cell.
- [x] **No-op guard (AC #5):** if the target column id equals the row's current option id (both `null` counts as equal), return without dispatching.

### Task 2 — Wire drop to the existing optimistic row-update action (AC: #1, #2, #3)

- [x] On drop, call the **existing** `updateValue({ field, row, value, oldValue })` method already present in `KanbanView.vue` (it dispatches `view/kanban/updateRowValue`). Pass `field = singleSelectField`, `value = targetOption` (the full option object, or `null`), `oldValue = currentOption`.
- [x] Do **NOT** add a new store action or service call for moving cards. `updateRowValue` → `updatePreparedRowValues` (in `store/view/bufferedRows.js`) already provides: optimistic commit (`UPDATE_ROW_VALUES`), backend `RowService.batchUpdate` (which broadcasts `rows_updated` + invalidates caches server-side), and **rollback on failure** (re-commits `oldValues` and re-throws). The existing `updateValue` already wraps it in `try/catch` with `notifyIf(error, 'field')` for the surfaced error (AC #3).
- [x] Because `columns` is a computed derived from `allRows` via `groupRowsBySingleSelect`, the optimistic value change **auto re-buckets** the card into the target column with no extra code; rollback auto-returns it. Verify this reactivity in the unit test rather than mutating columns directly.
- [x] `SingleSelectFieldType.prepareValueForUpdate(field, value)` returns `value.id` (or `null`), so passing the **full option object** as `value` is correct — the field type converts it to the option id for the request and keeps the option object in the store for display. Do not pre-convert to an id. [Source: fieldTypes.js:3802]

### Task 3 — Real-time inbound move (AC: #2) — verify-only, expect zero new code

- [x] Confirm (do not re-implement) that an inbound `rows_updated` WebSocket event re-buckets the card on **other** clients: `realtime.js` `rows_updated` → `KanbanViewType.rowUpdated` (inherited from `BaseBufferedRowViewTypeMixin`) → `view/kanban/afterExistingRowUpdated` → store value update → `columns` computed re-buckets. If this path already works (it should — it's the Gallery/Grid shared path), AC #2 needs **no** new code. Cover it with the E2E two-client assertion (Task 5). [Source: realtime.js:191; viewTypes.js:1099]

### Task 4 — Frontend unit tests (AC: #1, #3, #4, #5)

- [x] Extend `web-frontend/test/unit/database/components/view/kanban/kanbanView.spec.js`. Use the existing test harness/fixtures from 3.1. Assert:
  - Dropping a card on a different column dispatches `view/kanban/updateRowValue` once with `{ field: <singleSelectField>, row, value: <targetOption>, oldValue: <currentOption> }` (AC #1).
  - Dropping on Uncategorized passes `value: null` (AC #1).
  - Dropping on the row's own column does **not** dispatch (AC #5).
  - When `readOnly` is true (or no grouping field / field not editable), cards are not draggable and drop dispatches nothing (AC #4).
  - On a rejected dispatch, the error is caught and surfaced via `notifyIf` and the row value is unchanged after rollback (AC #3) — assert against the store optimistic/rollback behavior or a mocked dispatch that rejects.

### Task 5 — E2E spec (AC: #1, #2, #3)

- [x] Extend `e2e-tests/tests/database/kanban_view.spec.ts` (created in 3.1). Add a drag scenario: create a table with a single-select field + a Kanban view (reuse the 3.1 fixtures in `e2e-tests/fixtures/database/view.ts`), drag a card to another column, assert the card now renders under the target column **and** the row's single-select cell value changed (reopen/grid check). Use Playwright drag (`dragTo` / `mouse.down`/`move`/`up`) — native HTML5 DnD sometimes needs the manual mouse sequence.
- [x] Add a real-time assertion if the harness supports two browser contexts: a second connected client sees the card move without refresh (AC #2). If two-context is not feasible in this lane, document it in the spec and cover via the existing single-client reload assertion.
- [x] **Do NOT run E2E locally** — it requires the Docker stack and targets the OSS-only CI lane. Author the spec only. [Source: 3-1 Dev Notes "Test run commands"]

### Task 6 — Clean-room provenance (gate, MANDATORY)

- [x] Add `docs/clean-room/provenance/3-2-drag-a-kanban-card-between-columns.md` declaring Bucket A, no premium/enterprise sources read, built from public MIT Baserow row-update + DnD patterns. Validate with the gate (`check_provenance.py` → expect PASS as Bucket A). PR must carry the `bucket-a` label/checkbox. [Source: 1-1-establish-the-clean-room-process-gate.md; 3-1 Completion Notes]

### Task 7 — Lint (AC: all)

- [x] Run frontend Prettier + ESLint on changed `.vue`/`.js`/`.ts`, and Stylelint on any SCSS touched. No backend lint expected (no backend files change).
- [x] `just b run pre-commit run --files $(git diff --name-only origin/develop...HEAD)` to lint only branch-touched files.

## Dev Notes

### 🧭 The single most important constraint: ZERO backend code

Story 3.2 is a **pure frontend** story. Moving a card = changing one Single-select cell value. The full backend path already exists and is load-bearing:

- `RowService($client).batchUpdate(table.id, [...], null, viewId)` → backend `RowHandler` → Postgres + **permission check** → **WebSocket `rows_updated` broadcast** (subscribe-authorized, per-recipient filtered) → **Redis model-cache invalidation**. All of this comes **free only because** the existing handler path is used; a direct/new query path would bypass the permission boundary and the broadcast. [Source: architecture.md lines 223, 225–226, 342]
- **Anti-pattern (forbidden):** adding a "move card" endpoint, a Kanban-specific update view, a new signal, or any migration. If you find yourself editing `backend/`, stop — you've left the story. [Source: architecture.md line 259 "direct ORM mutation in API views (skips broadcast/cache-invalidation)"]

### Optimistic + rollback are already implemented — reuse, don't rebuild

`store/view/bufferedRows.js` `updateRowValue` → `updatePreparedRowValues` (lines 858–916, 775–857):

1. Optimistically commits the new value (`afterExistingRowUpdated` + `UPDATE_ROW_VALUES`).
2. Queues `RowService.batchUpdate` via `updateRowQueue` (serializes per-row updates → safe under rapid drags; last-write-wins per field — NFR-3).
3. On error: re-dispatches `afterExistingRowUpdated` with `oldValues`, re-commits `UPDATE_ROW_VALUES` old, and **re-throws** so the caller's `notifyIf` surfaces it.

`KanbanView.vue` already has:
```js
async updateValue({ field, row, value, oldValue }) {
  try {
    await this.$store.dispatch(this.storePrefix + 'view/kanban/updateRowValue',
      { table: this.table, view: this.view, fields: this.fields, row, field, value, oldValue })
  } catch (error) { notifyIf(error, 'field') }
}
```
**Drag just needs to call this method with the grouping field + target option.** That single call satisfies AC #1 (set value), AC #3 (rollback + error), and the optimistic move (because `columns` re-buckets reactively).

### Why the card visually moves with no extra code

`KanbanView.vue` `columns` is `groupRowsBySingleSelect(this.allRows, this.singleSelectField)` — a computed. When `updateRowValue` optimistically sets `field_${id}` on the row in the store, `allRows` changes → `columns` recomputes → the card appears under the target column instantly. Rollback reverts the cell → card returns to origin. **Do not** maintain a separate per-column array or splice cards manually; that would desync from the store and break rollback/realtime.

### Real-time inbound (AC #2)

Outbound broadcast is automatic (backend, above). Inbound on other clients: `realtime.js` `rows_updated` (line 191) loops all view types → `KanbanViewType.rowUpdated` (inherited from `BaseBufferedRowViewTypeMixin`, viewTypes.js:1099) → `afterExistingRowUpdated` → store value update → `columns` re-buckets. This is the same Gallery/Grid shared path; expect **no** new code. Just verify.

### Single-select value shape

- Store cell value for a single-select field is the **option object** `{ id, value, color }` or `null`. `groupRowsBySingleSelect` reads `value.id` to bucket (KanbanView.vue:134). Build the target value from the column: real column → `{ id: column.id, value: column.label, color: column.color }` (or look up the option on the field by `column.id`); Uncategorized column (`column.id === null`) → `null`.
- `SingleSelectFieldType.prepareValueForUpdate(field, value)` → `value.id` or `null` (fieldTypes.js:3802). So passing the option object is correct; the field type converts it for the request.

### Field permissions / readOnly (AC #4)

- `KanbanView.vue` already receives a `readOnly` prop — when `true`, never set `draggable` and ignore drops.
- The **Epic 1 field-permission layer** is enforced server-side regardless (a forbidden update returns an error → rollback). But also disable the UI: a card's grouping field must be editable for drag to be offered. Reuse the same field-writable predicate the row editing path uses (e.g., the `field._.permissions`/`canWriteFieldValues`-style check applied by `RowCard`/grid cells). Do **not** invent a new permission check — route through the existing one. [Source: architecture.md line 316 "permission boundary"; story 3.1 AC #2 reuse-the-pipeline guidance]

### Registration / files touched

- No new registration. `KanbanViewType` (frontend) and the `kanban` store module are already registered (Story 3.1).
- Expected to touch only: `KanbanView.vue` (drag UI + drop→updateValue), optionally `store/view/kanban.js` or a small util for drag state (only if cleaner — prefer keeping it in the component), the two existing test files, the E2E fixture if needed, SCSS for drag visuals (`web-frontend/modules/core/assets/scss/components/views/kanban.scss` from 3.1), and the new provenance doc.

### Test run commands

```bash
# Frontend unit (OSS context; i18n mocked as in 3.1)
EXTRA_VITEST_PARAMS="" just f test -- --reporter=verbose web-frontend/test/unit/database/components/view/kanban/kanbanView.spec.js
# E2E requires Docker stack — author spec, do NOT run locally
# Lint only branch-touched files
just b run pre-commit run --files $(git diff --name-only origin/develop...HEAD)
```

### Anti-patterns (forbidden)

- ❌ Any backend file change (new endpoint/handler/serializer/signal/migration). Row update + broadcast already exist.
- ❌ Opening/reading/adapting anything under `premium/` or `enterprise/` (clean-room contamination). [Source: architecture.md line 268]
- ❌ A bespoke "move card" store action or service instead of the existing `updateRowValue`.
- ❌ Manually splicing cards between per-column arrays instead of letting the `columns` computed re-bucket from the store (breaks rollback + realtime).
- ❌ Pre-converting the option to an id before calling `updateValue` (the field type does this).
- ❌ Building intra-column ordering, card-appearance (3.3), or drop-to-create.
- ❌ Merging a Bucket A PR without a provenance record (CI gate blocks it).

### Project Structure Notes

New files:
- `docs/clean-room/provenance/3-2-drag-a-kanban-card-between-columns.md`

Modified files:
- `web-frontend/modules/database/components/view/kanban/KanbanView.vue` (drag UI + drop→`updateValue`)
- `web-frontend/test/unit/database/components/view/kanban/kanbanView.spec.js` (drag tests)
- `e2e-tests/tests/database/kanban_view.spec.ts` (drag scenario + realtime assertion)
- (likely) `web-frontend/modules/core/assets/scss/components/views/kanban.scss` (drag/drop visual states)
- (only if cleaner) `web-frontend/modules/database/store/view/kanban.js` (drag-state helper)

No backend files. No new migration. Naming follows existing conventions: `.vue` PascalCase, store/util camelCase. [Source: architecture.md lines 192–208]

### References

- [Source: epics.md#Epic 3 → Story 3.2, lines 490–505] — user story + two AC blocks (set option/null + realtime broadcast; fail → rollback + error).
- [Source: epics.md lines 79–80] — NFR-2 (drag ≥ 50fps), NFR-3 (optimistic + rollback; LWW per field + snap-to-authoritative).
- [Source: architecture.md lines 32, 34, 142, 223–230, 244, 259, 316, 342] — realtime broadcast on mutations; optimistic + rollback grid patterns; handler-spine gives broadcast+cache free; permission boundary; data-flow mutation→Handler→broadcast→store.
- [Source: 3-1-create-and-configure-a-kanban-view.md] — Kanban view built from Gallery template; `KanbanView.vue`, `groupRowsBySingleSelect`, `store/view/kanban.js`, existing `updateValue`, premium-precedence + OSS-only test profile, clean-room provenance gate.
- [Source: web-frontend/modules/database/components/view/kanban/KanbanView.vue:155 (updateValue), :110 (groupRowsBySingleSelect), :134 (option-id bucketing)] — the drop target method + bucketing to extend.
- [Source: web-frontend/modules/database/store/view/bufferedRows.js:858 (updateRowValue), :775 (updatePreparedRowValues)] — optimistic commit + batchUpdate + rollback path.
- [Source: web-frontend/modules/database/realtime.js:191 (rows_updated)] + [viewTypes.js:1099 (rowUpdated mixin)] — inbound realtime re-bucket path (verify-only).
- [Source: web-frontend/modules/database/fieldTypes.js:3802 (SingleSelectFieldType.prepareValueForUpdate)] — value object → option id conversion.
- [Source: 1-1-establish-the-clean-room-process-gate.md] — provenance = hard merge gate; "influenced by" = contamination.
- [Source: memory clean-room-isolation-porous] — prior agents drifted into premium/enterprise during debug/verify; hold the line.
- [Source: memory baserow-open-core-license-constraint] — paid features need clean-room reimplement; PE/EE forbids copying.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8

### Debug Log References

- Frontend unit run (OSS context): `yarn vitest run test/unit/database/components/view/kanban/kanbanView.spec.js` → 17 passed.
- First unit-test attempt used a full `testApp.mount(KanbanView)`; in the open-core test build the **premium** Kanban store registers last and overrides core (`fetchInitial(kanbanId)` signature), producing `Could not find mock for GET /database/views/kanban/undefined/` and a JS-heap OOM. Rewrote the drag tests as **method-level units** (real `canDrag` computed + drag methods bound to a minimal fake instance) so they exercise the free-core surface without mounting the premium store — staying inside the clean room.

### Completion Notes List

- **Zero backend changes.** Drag is pure frontend: the drop dispatches the **existing** `view/kanban/updateRowValue` action (→ `bufferedRows.updatePreparedRowValues` → `RowService.batchUpdate`), which already provides the permission check, optimistic commit, `rows_updated` WebSocket broadcast, Redis cache invalidation, and rollback-on-failure. No new endpoint/serializer/view/handler/signal/migration.
- **Card movement is store-driven.** No per-column array is spliced; `columns` is a computed over the store rows (`groupRowsBySingleSelect`), so the optimistic value change auto re-buckets the card and rollback auto-returns it (preserves realtime + rollback).
- **AC #4 reuses the existing field-writable predicate** (`canWriteFieldValues` / `isReadOnlyField`) — honors the Epic 1 field-permission layer; `readOnly` view or non-editable grouping field disables drag and ignores drops.
- **AC #5 no-op guard** short-circuits when the target column id equals the row's current option id (both `null` counts as equal).
- **AC #3** rejection is caught by the existing `updateValue` try/catch → `notifyIf(error, 'field')`; the store rolls the value back. `onDrop` now returns the `updateValue` promise so the drop is awaitable in tests.
- **AC #2 (realtime)** verify-only — inbound `rows_updated` → `KanbanViewType.rowUpdated` (inherited from `BaseBufferedRowViewTypeMixin`) re-buckets on other clients with no new code. E2E two-context assertion is not feasible in this lane (`workspacePage` authenticates a single token), so it is documented and covered via a single-client reload assertion instead.
- **Clean-room:** no `premium/` or `enterprise/` source was opened, read, grepped, or recalled. Provenance record added; Bucket A.
- E2E spec authored, **not run locally** (requires the Docker stack; targets the OSS-only CI lane).

### File List

**Modified**
- `web-frontend/modules/database/components/view/kanban/KanbanView.vue` — draggable cards + column drop targets, `canDrag` computed, `onDragStart`/`onDragEnd`/`onDragOver`/`onDrop` handlers, drop → existing `updateValue`.
- `web-frontend/modules/core/assets/scss/components/views/kanban.scss` — `--draggable` (grab cursor) and `--dragging` (opacity/grabbing) visual states.
- `web-frontend/test/unit/database/components/view/kanban/kanbanView.spec.js` — method-level drag-and-drop unit tests (AC #1, #3, #4, #5).
- `web-frontend/test/fixtures/mockServer.js` — `createKanbanView` / `createKanbanRows` helpers.
- `e2e-tests/tests/database/kanban_view.spec.ts` — drag scenario (To do → Done, persists across reload).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — story 3-2 → review.

**New**
- `web-frontend/test/fixtures/kanban.js` — Kanban view + rows mock-server fixtures.
- `docs/clean-room/provenance/3-2-drag-a-kanban-card-between-columns.md` — Bucket A provenance record (mandatory merge gate).

**Backend:** none.

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-06-09 | 0.1 | Story drafted via create-story workflow. Key finding: 3.2 is frontend-only — drop reuses existing `updateRowValue` (optimistic+rollback+broadcast already implemented); zero backend changes. | Tinsu (create-story) |
| 2026-06-09 | 1.0 | Implemented native HTML5 drag-and-drop on the free-core Kanban view (drop → existing optimistic `updateRowValue`, `canDrag` permission/readOnly guard, AC #5 own-column no-op). Added method-level unit tests (17 passing), E2E drag scenario, and Bucket A provenance record. Zero backend changes. Status → review. | claude-opus-4-8 (dev-story) |
| 2026-06-09 | 1.1 | Adversarial review (auto-fix). Fixed MEDIUM: `@dragover.prevent` template modifier unconditionally called `preventDefault`, defeating the `onDragOver` drop-target guard (every column was a valid drop target even on a read-only board / with no drag in flight) — removed `.prevent` so the method is authoritative, and set `dataTransfer.dropEffect = 'move'` for correct drag-cursor affordance (NFR-2 UX). Added a unit assertion for the dropEffect/guard. 22 unit tests pass; Prettier + ESLint clean. Zero CRITICAL findings remain. Status → done. | claude-opus-4-8 (review) |

## Senior Developer Review (AI)

**Reviewer:** Tinsu (AI adversarial review) · **Date:** 2026-06-09 · **Outcome:** ✅ Approve (auto-fix applied)

### Scope & method
Reviewed against the 5 ACs and the 7 tasks. Cross-referenced the story File List with `git status` — **no discrepancy**: every changed source file (`KanbanView.vue`, `kanban.scss`, `kanbanView.spec.js`, `mockServer.js`, `kanban_view.spec.ts`, new `kanban.js`, new provenance doc) is documented; `_bmad/` and `_bmad-output/` excluded per policy. Verified the implementation against the real codebase (not just the story claims): `canWriteFieldValues` (`fieldTypes.js:927`), `populateRow` seeding `_.dragging` (`store/view/kanban.js:8`), `RowCard` single-root attr/listener fallthrough (`components/card/RowCard.vue`), and the e2e `setupKanban` return shape.

### Acceptance Criteria
- **AC #1** (drop sets option / null) — IMPLEMENTED. `onDrop` builds the full option object from `field.select_options` (or `null` for Uncategorized) and dispatches the existing `updateValue`. Unit-covered.
- **AC #2** (realtime broadcast) — IMPLEMENTED via the shared `bufferedRows` → `RowService.batchUpdate` handler path (zero new code); inbound re-bucket is the inherited `BaseBufferedRowViewTypeMixin.rowUpdated`. True two-client e2e not feasible in this lane (single-token `workspacePage` fixture) — documented and covered by a single-client reload assertion. Acceptable.
- **AC #3** (rollback + error) — IMPLEMENTED. Optimistic commit + rollback live in `bufferedRows`; `updateValue` try/catch → `notifyIf`. Component never mutates the cell directly (verified by the "value unchanged after reject" test).
- **AC #4** (drag disabled: readOnly / no field / non-editable) — IMPLEMENTED. `canDrag` computed + `onDragStart`/`onDrop` guards. Unit-covered for all three branches.
- **AC #5** (own-column no-op) — IMPLEMENTED. `currentOptionId === targetOptionId` short-circuit (both `null` equal). Unit-covered.

### Task audit
All tasks marked `[x]` verified as actually done. No false-completion findings. Zero backend files touched (confirmed via `git diff --name-only`) — the "ZERO backend code" constraint holds. Clean-room provenance doc present (Bucket A).

### Findings
- 🟡 **MEDIUM (fixed):** `@dragover.prevent` template modifier called `preventDefault()` unconditionally, defeating the `onDragOver` guard — at runtime every column was a valid drop target even on a read-only board or with no drag in flight, diverging from the unit-tested behavior. No data corruption (the `onDrop` guard still no-ops), but a real consistency/UX defect. **Fixed:** removed `.prevent`, made the method authoritative, set `dropEffect = 'move'`, added a unit assertion.
- 🟢 **LOW (accepted, not changed):** `MockServer.createKanbanView`/`createKanbanRows` + `test/fixtures/kanban.js` are not exercised by the current method-level unit tests (the suite intentionally avoids a full mount to dodge the premium-store override). Kept as scaffolding for future mount-based Kanban tests and because they are listed File-List deliverables; flagged so a follow-up either uses or removes them.
- 🟢 **LOW (accepted):** native DnD has no keyboard-accessible alternative — out of scope for 3.2; note for a later a11y pass.

### Verification
22/22 unit tests pass after the fix. Prettier + ESLint clean on changed files. E2E authored, not run locally (OSS-only Docker lane), per story.

### Action items
- [ ] [AI-Review][LOW] Either wire `createKanbanView`/`createKanbanRows` into a mount-based test or remove them + `test/fixtures/kanban.js`. [`web-frontend/test/fixtures/kanban.js`]
- [ ] [AI-Review][LOW] Keyboard-accessible card move (a11y) for Kanban DnD. [`KanbanView.vue`]
