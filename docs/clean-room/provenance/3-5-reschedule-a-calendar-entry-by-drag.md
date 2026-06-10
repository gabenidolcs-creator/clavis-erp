# Provenance record — Story 3.5 Reschedule a Calendar Entry by Drag

- **PR / branch:** feat(story-3.5) reschedule a calendar entry by drag (branch: develop)
- **Story:** 3.5 Reschedule a Calendar Entry by Drag
- **Bucket:** A (clean-room reimplement)
- **Implementer:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-10

## Sources Consulted

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | Public Airtable/Baserow "Calendar" UX — dragging an entry from one day onto another reschedules its date field; dragging to/from an "unscheduled" tray schedules/unschedules it | public SaaS UI / public docs | https://baserow.io/docs , https://airtable.com |
| 2 | The Story 3.2 free-core **Kanban drag** between columns — the proven net-new free-core drag mechanic this story mirrors verbatim: `canDrag` permission gate, `onDragStart`/`onDragEnd`/`onDragOver` (no `.prevent` modifier; guarded `preventDefault`), `onDrop` no-op guard + reuse of the existing optimistic `updateValue` path, and the `--draggable`/`--dragging` SCSS states. Calendar swaps the single-select grouping axis for the date positioning axis. | this repo (core, MIT free-core, authored in 3.2) | `web-frontend/modules/database/components/view/kanban/KanbanView.vue` (`canDrag`, `onDragStart`, `onDragEnd`, `onDragOver`, `onDrop`), `web-frontend/modules/core/assets/scss/components/views/kanban.scss` (`--draggable`/`--dragging`) |
| 3 | The Story 3.4 free-core **Calendar view** — the view being extended: `updateValue` (existing optimistic `updateRowValue` dispatch with `notifyIf`), `rowDateKey`/`groupRowsByDate`/`rowsByDay`/`unscheduledRows` (reactive re-bucket from the store), `dateField`/`endDateField` computeds, and `store/view/calendar.js populateRow` (already pre-seeds `row._.dragging = false`) | this repo (core, MIT free-core, authored in 3.4) | `web-frontend/modules/database/components/view/calendar/CalendarView.vue`, `web-frontend/modules/database/store/view/calendar.js` |
| 4 | Field-type capability `canWriteFieldValues` — the registry predicate reused (unchanged) to gate drag on Date-Field writability, routing through the Epic 1 field-permission layer rather than hard-coding field classes | MIT free-core | `web-frontend/modules/database/fieldTypes.js` |
| 5 | `BaseDateFieldType.formatValue` / `DateFieldType` — the canonical store value shape for a date cell (`YYYY-MM-DD` for date-only, UTC ISO for datetime) and the identity `prepareValueForUpdate` default that the new `dateValueForDay` value-builder targets | MIT free-core | `web-frontend/modules/database/fieldTypes.js` (`BaseDateFieldType.formatValue` ~2588, `DateFieldType`) |
| 6 | Core MIT date helper — bundled `moment` used for the datetime date-swap (preserving time-of-day in the same local frame `rowDateKey` parses with); no calendar/date library added | MIT free-core | `web-frontend/modules/core/moment` |
| 7 | Shared optimistic row-update + broadcast path reused unchanged: `view/calendar/updateRowValue` → `bufferedRows.updateRowValue` → `RowService.batchUpdate` → backend `RowHandler` → Postgres + permission check → WebSocket `rows_updated` broadcast → Redis model-cache invalidation. No new endpoint, handler, signal, or migration. | MIT free-core | `web-frontend/modules/database/store/view/bufferedRows.js` (`updateRowValue` ~858), `backend/src/baserow/contrib/database/api/rows/*` (existing batch-update path) |
| 8 | Shared `RowCard.vue` entry renderer — reused unchanged as the draggable card | MIT free-core | `web-frontend/modules/database/components/card/RowCard.vue` |
| 9 | Free-core Story 3.4 Calendar frontend unit-test suite — the method/computed-level pattern (no full mount, to avoid the premium-store-override OOM) the new drag tests extend | this repo (core) | `web-frontend/test/unit/database/components/view/calendar/calendarView.spec.js` |
| 10 | Free-core Story 3.2 Kanban E2E drag spec — the manual HTML5 DnD mouse sequence (down → stepped move → up) the authored Calendar drag E2E mirrors | this repo (core) | `e2e-tests/tests/database/kanban_view.spec.ts` |
| 11 | Playwright locator/assertion API for the authored E2E drag scenario | general public knowledge | https://playwright.dev |

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

- **Pure-frontend story — ZERO backend code.** Rescheduling is a single Date-cell value
  change. The full backend path (permission check + WebSocket broadcast + cache
  invalidation) already exists from earlier stories and is reused unchanged via the
  existing `updateValue` → `view/calendar/updateRowValue` dispatch. No new endpoint,
  "move entry" view, handler, signal, serializer, or migration was added. Real-time
  re-bucket on other clients (inbound `rows_updated`) is the shared Grid/Gallery path and
  needs no new code.
- **Mirrors the 3.2 Kanban drag verbatim.** `canDragDate` is the calendar analogue of
  Kanban's `canDrag` (read-only OR no date field → not draggable; else gate on
  `canWriteFieldValues(dateField)`). `onDragStart`/`onDragEnd`/`onDragOver` are copied
  (guarded `preventDefault`, `@dragover` bound WITHOUT `.prevent`). `onDropDay` /
  `onDropUnscheduled` resolve the new value then call the existing `updateValue`; the card
  re-buckets reactively because `rowsByDay`/`unscheduledRows` derive from the store — no
  manual card splicing, so rollback and realtime keep working.
- **The one net-new bit of logic — `dateValueForDay`.** Date-only fields take the
  `YYYY-MM-DD` day key directly (matching `formatValue`). Datetime fields preserve
  time-of-day and swap only the date in the **same local frame `rowDateKey` parses with**
  (plain `moment`, never `moment.utc`), so the round-trip invariant
  `rowDateKey(dateValueForDay(...)) === dayKey` holds even near midnight; the result is
  serialized as a UTC ISO string. The keystone invariant is asserted directly in the unit
  tests across midnight-boundary cases.
- **Multi-day events — held the scope line.** A drag updates only the configured
  `date_field` (the start); `end_date_field` is intentionally not shifted (out of scope
  for 3.5). `groupRowsByDate` already degrades a start-past-end span to a single-day card
  without error.
- **No premium/enterprise contamination.** Premium ships its own Calendar view; it was
  **not** opened, read, grepped, or recalled at any point. Every source consulted is the
  free-core 3.2 Kanban drag, the free-core 3.4 Calendar being extended, the shared
  card/field-registry/row-update plumbing, core `moment`, or public docs. The free-core
  Calendar is the registered `calendar` view type only in OSS-only builds
  (`BASEROW_OSS_ONLY=true`); in a full open-core build premium's Calendar registers later
  and overrides it (last-registration-wins). The E2E spec therefore runs OSS-only.
- **Clean-room test execution.** Frontend unit tests run method/computed-level (no full
  mount, to avoid the premium-store-override OOM): 60 passed (34 pre-existing 3.4 + 26
  new 3.5 drag/value/permission/lifecycle tests). The four new E2E drag scenarios in
  `e2e-tests/tests/database/calendar_view.spec.ts` are authored to run in the OSS-only CI
  lane and are not run locally (require the Docker stack). No backend tests were touched
  (frontend-only story).
