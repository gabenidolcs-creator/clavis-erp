# Provenance record — Story 3.6 Create and configure a Timeline View

- **PR / branch:** feat(story-3.6) create and configure a timeline view (branch: develop)
- **Story:** 3.6 Create and configure a Timeline View
- **Bucket:** A (clean-room reimplement)
- **Implementer:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-10

## Sources Consulted

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | Public Airtable/Baserow "Timeline / Gantt" UX — positioning rows as horizontal bars on a time axis by a start and end date field, a day/week/month zoom control, an "unscheduled" tray for rows missing a date, a wider bar for a longer span | public SaaS UI / public docs | https://baserow.io/docs , https://airtable.com |
| 2 | The Story 3.4 free-core Calendar view — the proven net-new free-core `ViewType` scaffold this story clones (backend `CalendarViewType` + `CalendarView` model + `CalendarViewFieldOptions` + migration + `api/views/calendar/*` + premium-gated `apps.py` registration; frontend `CalendarViewType` in `viewTypes.js` + `CalendarView.vue` + `CalendarViewHeader.vue` + `store/view/calendar.js` + `services/view/calendar.js` + `plugin.js`). Timeline swaps the "position on a month/week grid" axis for a "position a bar between a start and end date on a time axis" axis, and persists the zoom level as a `timescale` column. | this repo (core, MIT free-core, authored in 3.4) | `backend/src/baserow/contrib/database/views/view_types.py` (CalendarViewType), `backend/src/baserow/contrib/database/views/models.py` (CalendarView, CalendarViewFieldOptions), `backend/src/baserow/contrib/database/api/views/calendar/*`, `web-frontend/modules/database/viewTypes.js`, `web-frontend/modules/database/components/view/calendar/*`, `web-frontend/modules/database/store/view/calendar.js`, `web-frontend/modules/database/services/view/calendar.js` |
| 3 | Free-core `GalleryViewType` — the MIT reference whose card-face `get_hidden_fields` (keep layout-dependency fields always visible), `view_created` (first-N fields visible), and export/import round-trip the Calendar scaffold (and now Timeline) mirror | MIT free-core | `backend/src/baserow/contrib/database/views/view_types.py` (GalleryViewType) |
| 4 | Field-type capability `can_represent_date` (backend) / `canRepresentDate` (frontend) — the registry capability used to validate the start / end date fields instead of hard-coding field classes | MIT free-core | `backend/src/baserow/contrib/database/fields/registries.py`, `backend/src/baserow/contrib/database/fields/field_types.py`, `web-frontend/modules/database/fieldTypes.js` |
| 5 | Core MIT date helpers + bundled moment — bar-geometry time math (snap to `startOf`/`endOf` unit, `diff` in day/isoWeek/month units, parse in the user timezone) used instead of a Gantt/timeline UI library | MIT free-core | `web-frontend/modules/core/utils/date.js` (`getUserTimeZone`, `getCapitalizedMonthName`), `web-frontend/modules/core/moment` |
| 6 | Shared `RowCard.vue` entry renderer + `ViewFieldsContext.vue` "Customize cards" body + `bufferedRows`/`fieldOptions` store factories — reused unchanged for entry rendering, the card-face field toggle/reorder, and the row listing | MIT free-core | `web-frontend/modules/database/components/card/RowCard.vue`, `web-frontend/modules/database/components/view/ViewFieldsContext.vue`, `web-frontend/modules/database/store/view/bufferedRows.js`, `web-frontend/modules/database/utils/view.js` |
| 7 | Two shared persistence paths reused unchanged: view config (`start_date_field`, `end_date_field`, `timescale`) via the generic `PATCH /api/database/views/{id}/` view update; card face (`hidden`/`order`) via the generic `PATCH /api/database/views/{id}/field_options/` endpoint | MIT free-core | `backend/src/baserow/contrib/database/api/views/views.py` |
| 8 | Free-core Calendar view-type + API tests — reference shape for the Timeline backend test suites | MIT free-core | `backend/tests/baserow/contrib/database/view/test_calendar_view_type.py`, `backend/tests/baserow/contrib/database/api/views/calendar/test_calendar_view_views.py` |
| 9 | Baserow test harness for OSS-only view-type registration (`BASEROW_OSS_ONLY=true`, `TEST_ENV_FILE`) so the core Timeline — not the open-core override — is the registered `timeline` type under test | this repo (core) | `backend/src/baserow/config/settings/test.py`, `backend/.env.oss-test` |
| 10 | Playwright locator/assertion API for the authored E2E timeline scenario | general public knowledge | https://playwright.dev |

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

- **Net-new free-core build, cloned from the 3.4 Calendar scaffold.** Timeline is a
  premium feature with no free-core scaffold of its own, so this story builds the full
  view-type spine in core: backend `TimelineView` / `TimelineViewFieldOptions` models
  (distinct table `database_coretimelineview...`, `core_`-prefixed reverse accessors to
  avoid clashing with premium's `database_timelineview`), migration `0222`,
  `TimelineViewType`, the `api/views/timeline/` package, and the frontend view-type,
  components, store, service, and registration. Every structural decision mirrors the
  proven free-core Calendar from 3.4, swapping its month/week grid positioning for a
  `start_date_field` + `end_date_field` bar-on-a-time-axis positioning.
- **No Gantt/timeline library — core date math only.** The axis range, tick stops, and
  per-bar `{left, width}` geometry are computed by pure exported functions over the
  bundled `@baserow/modules/core/moment` (snap to `startOf`/`endOf` of the active unit,
  `diff` in `day`/`isoWeek`/`month`, parse in `getUserTimeZone()`). No
  FullCalendar/Frappe-Gantt/dhtmlx/vis-timeline/date-fns/dayjs dependency was added.
- **Zoom (`timescale`) is a persisted column — the one structural delta from Calendar.**
  Calendar's display-mode toggle is client-side ephemeral; AC #3 here requires the
  day/week/month zoom to *survive a reload*, so `timescale` is a migration-backed
  `CharField` (choices day/week/month, default `month`) on `TimelineView`, written through
  the same generic `PATCH /api/database/views/{id}/` view-update path as the date fields.
  No bespoke endpoint. View config and the card face (`hidden`/`order`) round-trip through
  export/import alongside it.
- **Scheduled-vs-tray data guard (AC #2 / #4).** A row renders as a bar only when **both**
  its `start_date_field` and `end_date_field` carry a value; a row missing either lands in
  the unscheduled tray. A reversed range (`end < start`) clamps to a single-unit bar rather
  than throwing. `get_hidden_fields` / `get_visible_field_options_in_order` keep
  `start_date_field_id` and `end_date_field_id` always visible to the layout even when their
  card-face option is `hidden=True`, mirroring Calendar's date-field guard. Soft-delete is
  handled by an explicit `after_field_delete` (FK `SET_NULL` only fires on hard delete) plus
  `after_fields_type_change` to null references when a field stops being date-representable.
- **No premium/enterprise contamination.** Premium ships its own Timeline view
  (`premium/.../views/timeline/*`, `database_timelineview`, type `"timeline"`); it was
  **not** opened, read, grepped, or recalled at any point. Every source consulted is the
  free-core 3.4 Calendar, the MIT Gallery it mirrors, the shared card/field-options
  components, core `utils/date.js` + bundled moment, or public docs. The free-core Timeline
  is the registered `timeline` view type only in OSS-only builds
  (`BASEROW_OSS_ONLY=true`); in a full open-core build premium's Timeline registers later
  and overrides it (last-registration-wins). All Story 3.6 tests therefore run OSS-only.
- **Out of scope (held the line):** drag-to-reschedule / drag-to-resize a bar (Story 3.7)
  and any premium dependency-line / milestone overlay were not implemented; the store
  pre-seeds a `dragging: false` row flag for 3.7 but no drag handlers were wired.
- **Clean-room test execution.** Backend tests run with `TEST_ENV_FILE=.env.oss-test`
  (22 passed: 13 view-type + 9 API) and frontend unit tests run method/computed-level
  (no full mount, to avoid the premium-store-override OOM) in the OSS context
  (41 passed). The E2E scenario in `e2e-tests/tests/database/timeline_view.spec.ts` is
  authored to run in the OSS-only CI lane and is not run locally (requires the Docker
  stack).
