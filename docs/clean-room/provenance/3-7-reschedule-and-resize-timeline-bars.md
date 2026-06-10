# Provenance record — Story 3.7 Reschedule and resize Timeline bars

- **PR / branch:** feat(story-3.7) reschedule and resize timeline bars (branch: develop)
- **Story:** 3.7 Reschedule and resize Timeline bars
- **Bucket:** A (clean-room reimplement)
- **Implementer:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-10

## Sources Consulted

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | Public Airtable/Baserow "Timeline / Gantt" UX — dragging a bar body along the time axis moves the task (shifts both its start and end date, preserving duration); dragging a bar edge resizes (shifts only the dragged endpoint); a bar cannot be resized below a single time unit | public SaaS UI / public docs | https://baserow.io/docs , https://airtable.com |
| 2 | The Story 3.6 free-core **Timeline view** — the view being extended: `barGeometry`/`barStyle` (pure `{left,width}` bar math over the active timescale), `parseTimelineValue` (parse a cell in the user timezone via bundled moment, never `moment.utc` for arithmetic), `startField`/`endField` computeds, `timescaleUnit` (`day`/`isoWeek`/`month`), and `store/view/timeline.js populateRow` (already pre-seeds `row._.dragging = false` for this story) | this repo (core, MIT free-core, authored in 3.6) | `web-frontend/modules/database/components/view/timeline/TimelineView.vue`, `web-frontend/modules/database/store/view/timeline.js` |
| 3 | The Story 3.2 free-core **Kanban drag** + Story 3.5 free-core **Calendar drag** — the proven net-new free-core drag mechanics this story mirrors: a `canDrag*` permission gate, drag lifecycle (start → move → commit), a no-op guard when nothing changed, reuse of the existing optimistic update path, and the `--draggable`/`--dragging` SCSS states. Timeline swaps HTML5 DnD for a `mousedown` → document-level `mousemove` → `mouseup` pointer-drag (a bar moves continuously along a pixel axis rather than snapping between discrete drop zones). | this repo (core, MIT free-core, authored in 3.2 / 3.5) | `web-frontend/modules/database/components/view/kanban/KanbanView.vue`, `web-frontend/modules/database/components/view/calendar/CalendarView.vue` (`canDragDate`, `dateValueForDay`, `updateValue`), `web-frontend/modules/core/assets/scss/components/views/kanban.scss` |
| 4 | Field-type capability `canWriteFieldValues` — the registry predicate reused (unchanged) to gate drag on Date-Field writability, routing through the Epic 1 field-permission layer rather than hard-coding field classes. `canDragBars` requires **both** the start and end date field writable. | MIT free-core | `web-frontend/modules/database/fieldTypes.js` |
| 5 | `BaseDateFieldType.formatValue` / `DateFieldType` — the canonical store value shape for a date cell (`YYYY-MM-DD` for date-only, UTC ISO for datetime) that the new `shiftDateValue` value-builder produces after adding the unit delta | MIT free-core | `web-frontend/modules/database/fieldTypes.js` |
| 6 | Core MIT date helper — bundled `moment` used for the unit-delta date arithmetic (`add(deltaUnits, unit)`, `startOf(unit)`, `diff` in the active unit) in the same local frame `parseTimelineValue` parses with; no Gantt/timeline library added | MIT free-core | `web-frontend/modules/core/moment` |
| 7 | Two shared optimistic row-update paths reused unchanged: **MOVE** dispatches the plural `view/timeline/updateRowValues` (one atomic `batchUpdate` carrying both date fields → single broadcast / single rollback); **RESIZE** dispatches the single `view/timeline/updateRowValue` for the one dragged endpoint. Both flow through `bufferedRows` → `RowService.batchUpdate` → backend `RowHandler` → Postgres + permission check → WebSocket `rows_updated` broadcast → Redis model-cache invalidation. No new endpoint, handler, signal, serializer, or migration. | MIT free-core | `web-frontend/modules/database/store/view/bufferedRows.js` (`updateRowValue`, `updateRowValues`), `backend/src/baserow/contrib/database/api/rows/*` (existing batch-update path) |
| 8 | Shared `RowCard.vue` entry renderer — reused unchanged as the bar face | MIT free-core | `web-frontend/modules/database/components/card/RowCard.vue` |
| 9 | Free-core Story 3.6 Timeline frontend unit-test suite — the method/computed-level pattern (no full mount, to avoid the premium-store-override OOM) the new drag/resize tests extend | this repo (core) | `web-frontend/test/unit/database/components/view/timeline/timelineView.spec.js` |
| 10 | Free-core Story 3.2/3.5 E2E drag specs — the manual mouse sequence (down → stepped move → up) the authored Timeline move/resize E2E mirrors | this repo (core) | `e2e-tests/tests/database/kanban_view.spec.ts`, `e2e-tests/tests/database/calendar_view.spec.ts` |
| 11 | Playwright locator/assertion API for the authored E2E move/resize scenarios | general public knowledge | https://playwright.dev |

## Implementer Attestation

- [x] I affirm that this Bucket A reimplementation was produced **clean-room**: I did
      **not** read, copy, adapt, or rely on memory of any `premium/` or `enterprise/`
      (PE/EE) source for this feature, and I was not *influenced by* it. Every source I
      used is listed above and is on the allowed-source list.

**Implementer signature / handle:** AI dev-agent (isolation model (a))   **Date:** 2026-06-10

## Reviewer confirmation (filled at review)

- [x] Reviewer verified implementer eligibility per implementer-isolation.md.
- [x] Reviewer verified all sources above are on the allowed-source list.

## Notes

- **Pure-frontend story — ZERO backend code.** A move/resize is one (move) or two (resize)
  Date-cell value changes. The full backend path (permission check + WebSocket broadcast +
  cache invalidation) already exists from earlier stories and is reused unchanged via the
  existing `bufferedRows` update dispatches. No new endpoint, "move bar"/"resize bar" view,
  handler, signal, serializer, or migration was added. Real-time re-layout on other clients
  (inbound `rows_updated`) is the shared path and needs no new code.
- **Pointer-drag, not HTML5 DnD.** Unlike Kanban/Calendar (discrete drop zones, native
  `dragstart`/`drop`), a Timeline bar slides continuously along a pixel axis, so the
  mechanic is a `mousedown` on the bar/edge → `document`-level `mousemove` (track `clientX`
  delta) → `mouseup` commit. The pixel delta is converted to whole timescale units by the
  pure `pixelsToUnits(deltaPx, axisWidthPx, totalUnits)` (round to nearest unit). Window
  listeners are torn down in `beforeUnmount` to avoid a leak.
- **MOVE shifts both fields atomically; RESIZE shifts one.** A bar-body drag shifts BOTH
  the start and end date by the same unit delta (`shiftDateValue` per field, preserving the
  span) and commits them in a single plural `updateRowValues` → one `batchUpdate` → one
  broadcast / one rollback. An edge drag shifts ONLY the dragged endpoint via the single
  `updateRowValue`. `shiftDateValue` re-uses the canonical `formatValue` shape (`YYYY-MM-DD`
  for date-only; UTC ISO preserving time-of-day for datetime), computed in the same local
  frame `parseTimelineValue` parses with (plain `moment`, never `moment.utc` for the
  arithmetic) so the geometry round-trips with no boundary/DST off-by-one.
- **Resize clamp — minimum one-unit bar.** `clampResizeUnits(mode, oldStart, oldEnd,
  deltaUnits, unit)` bounds an edge drag so a `resize-start` cannot pass the end and a
  `resize-end` cannot pass the start; the floor is the same single-unit span `barGeometry`
  renders for a reversed/zero range. The `-0`→`0` normalization (`+ 0` on both branches)
  keeps the no-op case a true no-op so the commit short-circuits.
- **Permission gating.** `canDragBars` returns false when the view is read-only or either
  date field is unset; otherwise it gates on `canWriteFieldValues` for **both** date fields
  (a bar with one non-writable date field is not draggable at all). The drag affordances
  (`grab` cursor, edge handles) only render when `canDragBars` is true, and the commit
  re-checks permission so a mid-drag permission loss aborts without a write.
- **No premium/enterprise contamination.** Premium ships its own Timeline view with its own
  drag/resize; it was **not** opened, read, grepped, or recalled at any point. Every source
  consulted is the free-core 3.2 Kanban drag, the free-core 3.5 Calendar drag, the free-core
  3.6 Timeline being extended, the shared card/field-registry/row-update plumbing, core
  bundled `moment`, or public docs. The free-core Timeline is the registered `timeline` view
  type only in OSS-only builds (`BASEROW_OSS_ONLY=true`); in a full open-core build premium's
  Timeline registers later and overrides it (last-registration-wins). The E2E spec therefore
  runs OSS-only.
- **Clean-room test execution.** Frontend unit tests run method/computed-level (no full
  mount, to avoid the premium-store-override OOM): 70 passed (41 pre-existing 3.6 + 29 new
  3.7 pixelsToUnits/shiftDateValue/clampResizeUnits/canDragBars/commit/lifecycle tests). The
  five new E2E scenarios in `e2e-tests/tests/database/timeline_view.spec.ts` (move a bar →
  both date cells shift, span preserved; resize the right edge → only the end date shifts;
  resize the left edge → only the start date shifts; resize past the opposite edge → clamps
  to a 1-unit bar; zero-unit release → no-op) are authored to run in the OSS-only CI lane and
  are not run locally (require the Docker stack). No backend tests were touched (frontend-only
  story).
