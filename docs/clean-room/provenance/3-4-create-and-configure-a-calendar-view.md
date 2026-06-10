# Provenance record — Story 3.4 Create and configure a Calendar View

- **PR / branch:** feat(story-3.4) create and configure a calendar view (branch: develop)
- **Story:** 3.4 Create and configure a Calendar View
- **Bucket:** A (clean-room reimplement)
- **Implementer:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-10

## Sources Consulted

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | Public Airtable/Baserow "Calendar" UX — positioning rows on a month/week grid by a date field, an "unscheduled" tray for rows with no date, an optional end-date field for multi-day events | public SaaS UI / public docs | https://baserow.io/docs , https://airtable.com |
| 2 | The Story 3.1 free-core Kanban view — the proven net-new free-core `ViewType` scaffold this story clones (backend `KanbanViewType` + `KanbanView` model + `KanbanViewFieldOptions` + migration + `api/views/kanban/*` + premium-gated `apps.py` registration; frontend `KanbanViewType` in `viewTypes.js` + `KanbanView.vue` + `KanbanViewHeader.vue` + `store/view/kanban.js` + `services/view/kanban.js` + `plugin.js`). Calendar swaps the "group by single-select" axis for a "position by date" axis. | this repo (core, MIT free-core, authored in 3.1) | `backend/src/baserow/contrib/database/views/view_types.py` (KanbanViewType), `backend/src/baserow/contrib/database/views/models.py` (KanbanView, KanbanViewFieldOptions), `backend/src/baserow/contrib/database/api/views/kanban/*`, `web-frontend/modules/database/viewTypes.js`, `web-frontend/modules/database/components/view/kanban/*`, `web-frontend/modules/database/store/view/kanban.js`, `web-frontend/modules/database/services/view/kanban.js` |
| 3 | Free-core `GalleryViewType` — the MIT reference whose card-face `get_hidden_fields` (keep layout-dependency fields always visible), `view_created` (first-N fields visible), and export/import round-trip the Kanban scaffold (and now Calendar) mirror | MIT free-core | `backend/src/baserow/contrib/database/views/view_types.py` (GalleryViewType) |
| 4 | Field-type capability `can_represent_date` (backend) / `canRepresentDate` (frontend) — the registry capability used to validate the date / end-date fields instead of hard-coding field classes | MIT free-core | `backend/src/baserow/contrib/database/fields/registries.py`, `backend/src/baserow/contrib/database/fields/field_types.py`, `web-frontend/modules/database/fieldTypes.js` |
| 5 | Core MIT date helpers — month/week grid math used instead of a calendar UI library | MIT free-core | `web-frontend/modules/core/utils/date.js` (`getMonthlyTimestamps`, `weekDaysShort`, `getUserTimeZone`), `web-frontend/modules/core/moment` |
| 6 | Shared `RowCard.vue` entry renderer + `ViewFieldsContext.vue` "Customize cards" body + `bufferedRows`/`fieldOptions` store factories — reused unchanged for entry rendering, the card-face field toggle/reorder, and the row listing | MIT free-core | `web-frontend/modules/database/components/card/RowCard.vue`, `web-frontend/modules/database/components/view/ViewFieldsContext.vue`, `web-frontend/modules/database/store/view/bufferedRows.js`, `web-frontend/modules/database/utils/view.js` |
| 7 | Two shared persistence paths reused unchanged: view config (`date_field`, `end_date_field`) via the generic `PATCH /api/database/views/{id}/` view update; card face (`hidden`/`order`) via the generic `PATCH /api/database/views/{id}/field_options/` endpoint | MIT free-core | `backend/src/baserow/contrib/database/api/views/views.py` |
| 8 | Free-core Kanban view-type + API tests — reference shape for the Calendar backend test suites | MIT free-core | `backend/tests/baserow/contrib/database/view/test_kanban_view_type.py`, `backend/tests/baserow/contrib/database/api/views/kanban/test_kanban_view_views.py` |
| 9 | Baserow test harness for OSS-only view-type registration (`BASEROW_OSS_ONLY=true`, `TEST_ENV_FILE`) so the core Calendar — not the open-core override — is the registered `calendar` type under test | this repo (core) | `backend/src/baserow/config/settings/test.py`, `backend/.env.oss-test` |
| 10 | Playwright locator/assertion API for the authored E2E calendar scenario | general public knowledge | https://playwright.dev |

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

- **Net-new free-core build, cloned from the 3.1 Kanban scaffold.** Calendar is a
  premium feature with no free-core scaffold of its own, so this story builds the full
  view-type spine in core: backend `CalendarView` / `CalendarViewFieldOptions` models
  (distinct table `database_corecalendarview...`, `core_`-prefixed reverse accessors to
  avoid clashing with premium's `database_calendarview`), migration `0221`,
  `CalendarViewType`, the `api/views/calendar/` package, and the frontend view-type,
  components, store, service, and registration. Every structural decision mirrors the
  proven free-core Kanban from 3.1, swapping its single-select grouping axis for a
  `date_field` (+ optional `end_date_field`) positioning axis.
- **No calendar library — core date math only.** The month grid is built from the MIT
  `getMonthlyTimestamps` helper and the week grid from `moment(...).startOf('isoWeek')`
  via the bundled `@baserow/modules/core/moment`. No FullCalendar/Frappe/date-fns/dayjs
  dependency was added.
- **Display mode is client-side ephemeral.** AC #3 only requires the month/week toggle
  to be *available*, so the mode lives in the Vuex calendar store (`displayMode`), not as
  a migration-backed column — no schema risk. View config (`date_field`,
  `end_date_field`) and the card face (`hidden`/`order`) persist through the two existing
  shared PATCH paths; both round-trip through export/import.
- **AC #5 data-dependency guard.** `get_hidden_fields` / `get_visible_field_options_in_order`
  keep `date_field_id` and `end_date_field_id` always visible to the layout even when
  their card-face option is `hidden=True`, mirroring Kanban's grouping-field guard. Field
  permissions themselves come from Epic 1's central layer. Soft-delete is handled by an
  explicit `after_field_delete` (FK `SET_NULL` only fires on hard delete) plus
  `after_fields_type_change` to null references when a field stops being date-representable.
- **No premium/enterprise contamination.** Premium ships its own Calendar view
  (`premium/.../views/calendar/*`, `database_calendarview`, type `"calendar"`); it was
  **not** opened, read, grepped, or recalled at any point. Every source consulted is the
  free-core 3.1 Kanban, the MIT Gallery it mirrors, the shared card/field-options
  components, core `utils/date.js`, or public docs. The free-core Calendar is the
  registered `calendar` view type only in OSS-only builds (`BASEROW_OSS_ONLY=true`); in a
  full open-core build premium's Calendar registers later and overrides it
  (last-registration-wins). All Story 3.4 tests therefore run OSS-only.
- **Out of scope (held the line):** drag-to-reschedule (Story 3.5) and iCal / public
  calendar feed sharing (premium-only) were not implemented; no `ical_slug` was ported.
- **Clean-room test execution.** Backend tests run with `TEST_ENV_FILE=.env.oss-test`
  (21 passed: 13 view-type + 8 API) and frontend unit tests run method/computed-level
  (no full mount, to avoid the premium-store-override OOM) in the OSS context
  (34 passed). The E2E scenario in `e2e-tests/tests/database/calendar_view.spec.ts` is
  authored to run in the OSS-only CI lane and is not run locally (requires the Docker
  stack).
