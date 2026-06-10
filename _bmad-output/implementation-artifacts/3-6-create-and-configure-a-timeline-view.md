---
baseline_commit: b348adbf63fef99307b9b601aab4e83557b2a399
---

# Story 3.6: Create and configure a Timeline View

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want a Timeline View showing Rows as bars over start/end Date Fields,
so that I can see scheduling on a zoomable time axis. `[A]`

## Context & Scope

### 🚨 THIS IS A BUCKET A CLEAN-ROOM STORY — READ FIRST, NON-NEGOTIABLE

Timeline is a **Bucket A** feature: reimplemented in **core** without ever reading, copying, or being "influenced by" any `premium/` or `enterprise/` source. The PE/EE license forbids copying; a provenance record is a **hard CI merge gate**.

- **Do NOT open, read, `grep`, or adapt** anything under `premium/` or `enterprise/`. A full premium Timeline exists — `premium/web-frontend/modules/baserow_premium/components/views/timeline/*` (`TimelineView.vue`, `TimelineGrid.vue`, `TimelineContainer.vue`, `TimelineTimescaleContext.vue`, …), `premium/backend/src/baserow_premium/api/views/timeline/*`, `premium/.../store/view/timeline.js`, `premium/.../utils/timeline.js`, `premium/.../mixins/timelineViewHelpers.js`, and premium migrations `0020_timelineview_timelineviewfieldoptions_and_more.py` / `0021_timelineview_timescale.py`. **Opening any of it = contamination = the PR cannot merge.** These paths are listed here ONLY so you know what NOT to open. [Source: architecture.md lines 25, 279; 3-4 Context & Scope; memory clean-room-isolation-porous]
- All code lands in **core** (`backend/src/baserow/...`, `web-frontend/modules/database/...`). [Source: architecture.md line 279]
- A provenance record under `docs/clean-room/provenance/3-6-create-and-configure-a-timeline-view.md` is **mandatory** (Task 9). [Source: 1-1-establish-the-clean-room-process-gate.md]
- **Premium-precedence (registration gate).** In full open-core builds the premium Timeline (type `"timeline"`) registers later and overrides core (backend: gate core behind `if "baserow_premium" not in settings.INSTALLED_APPS`; frontend: last-registration-wins). The free core Timeline is the active view type only in **OSS-only** builds (`BASEROW_OSS_ONLY=true`). **Run ALL tests OSS-only** (`TEST_ENV_FILE=.env.oss-test`). [Source: apps.py:365–367 Kanban/Calendar gate; plugin.js:432–433 last-wins; 3-4 Completion Notes]
- **Co-loaded model collision (critical).** Both the core and premium Timeline model classes are loaded by Django regardless of which view type wins the registry. The core model MUST use a **distinct table name** (`database_coretimelineview`) and **non-clashing reverse accessors** (`related_name="core_timeline_view*"`, M2M `related_name="+"`) — exactly as core `CalendarView` does (models.py:829–875) — or Django raises `fields.E304/E305` and migration table collisions. [Source: models.py:829–875 CalendarView clean-room table/accessor pattern]

### 🧭 THE BUILD STRATEGY: clone the core Calendar view (3.4), swap "day-cell grid" for "horizontal time-axis bars"

This is a **net-new build**. You are **not** inventing a view-type architecture — you are **cloning the proven core Calendar scaffold** (Story 3.4, itself cloned from the MIT Kanban/Gallery scaffold) and swapping its month/week **day-cell grid** for a **horizontal, zoomable time axis** with one **bar per Row** spanning `start_date_field..end_date_field`. Calendar is the closest precedent because it already maps a date axis, validates date-representable fields, guards the layout fields' visibility, and reuses `RowCard`/`bufferedRows`. Every structural decision below has a working, MIT-clean precedent in core:

- Backend `ViewType` subclass + `View` model + `*FieldOptions` model + migration + `api/views/<type>/` (urls/views/serializers/errors/pagination) + `apps.py` registration gate → **copy the Calendar shapes** (`CalendarViewType`, `CalendarView`, `CalendarViewFieldOptions`). [Source: view_types.py:912–1170 CalendarViewType; models.py:829–905 CalendarView; apps.py:365–367]
- Frontend `ViewType` class (`BaseBufferedRowViewTypeMixin`) + `TimelineView.vue` + `TimelineViewHeader.vue` + `store/view/timeline.js` (bufferedRows) + `services/view/timeline.js` + `plugin.js` registration + i18n → **copy the Calendar shapes** (`CalendarViewType` in viewTypes.js:1353, `CalendarView.vue`, `CalendarViewHeader.vue`, `store/view/calendar.js`, `services/view/calendar.js`). [Source: viewTypes.js:1353; plugin.js:433]
- Row/bar rendering and the "Customize cards" header reuse the **shared** `RowCard.vue` + `ViewFieldsContext.vue` verbatim — exactly as Calendar/Kanban do. Do **not** fork them. [Source: 3-4 Task 5; 3-3 "What already exists"]
- **Date math already exists in MIT core** — `web-frontend/modules/core/utils/date.js`: `getMonthName()`/`getCapitalizedMonthName()`, `weekDaysShort()`, `getDateInTimezone()`, `getUserTimeZone()`, plus the bundled `moment` (`@baserow/modules/core/moment`) for `startOf/endOf('day'|'isoWeek'|'month')` and `diff()`/`add()` arithmetic to compute bar offsets and tick labels. **Use these. Do NOT add a timeline/Gantt/date library** (no Frappe Gantt — that is Story 3.8's Bucket B render lib, lazy-loaded over the CPM backend, NOT this story; no FullCalendar, vis-timeline, dayjs, date-fns). [Source: date.js:68–178; architecture.md:111 D2 Frappe Gantt is render-only for Gantt; 3-4 "do NOT add a calendar lib"]

> ⚠️ **Anti-pattern (forbidden):** importing a timeline/Gantt UI library, building a second `RowCard`/`ViewFieldsContext`/field-options model, adding a bespoke date-range rows endpoint when the inherited `bufferedRows` listing suffices for v1, or reading premium's timeline to "see how it's done." If you reach for any of these, **stop — re-derive from the Calendar scaffold + core `date.js`.**

### What this story is NOT

- ❌ **Reschedule / resize bars by drag** — that is **Story 3.7** (next). This story renders bars and a zoom control; it does **not** implement dragging a bar to move it or dragging an edge to resize it. **Keep the bar/grid DOM + store seams clean so 3.7 can add drag/resize without a rewrite, but write no drag handler here.** [Source: epics.md#Story 3.7]
- ❌ **Gantt** — task-dependency layer, dependency connectors, CPM critical path, milestones, Frappe Gantt render lib are **Stories 3.8–3.11 (Bucket B)**. Do not add a dependency model, CPM engine, or `frappe-gantt` dependency. [Source: epics.md#Story 3.8–3.11; architecture.md:25,168]
- ❌ Row coloring/decorations beyond what `RowCard` gives for free, intra-day hour lanes, recurring events, or App Builder timeline embeds (Story 5.3).

## Acceptance Criteria

1. **Given** a Table with start and end Date Fields, **When** an editor adds a Timeline View and maps them (selects `start_date_field` and `end_date_field`), **Then** the view persists and reopens with the same configuration (both mapped date fields, selected zoom level) and honors existing View **filters, sorts, and field visibility**. [Source: epics.md#Story 3.6; 3-4 AC #1 persistence model]
2. **And** each Row whose **start and end** Date Fields both have a value renders as a **bar from start to end on the horizontal time axis**, positioned/sized by the dates (start → left edge, end → right edge). [Source: epics.md#Story 3.6 "each Row renders as a bar from start to end"]
3. **And** **day / week / month zoom levels** are selectable from the view header **and persist** across reload (the selected zoom is stored on the view and re-hydrated on reopen — this is a **persisted backend column**, NOT ephemeral client state). [Source: epics.md#Story 3.6 "day/week/month zoom levels are selectable and persist"; FR-6 "day/week/month zoom persists"]
4. **And** Rows **missing a start or end** value (either Date Field null/empty) are **listed separately** in an "unscheduled"/"incomplete" tray and are **NOT rendered as malformed bars** on the axis. [Source: epics.md#Story 3.6 "Rows missing start or end are listed separately, not rendered as malformed bars"]
5. **And** the Timeline honors **field permissions** (Epic 1): fields the user cannot view are absent from bar/row content; the `start_date_field`/`end_date_field` driving layout are kept visible to the layout regardless of card-face `hidden` (data-dependency guard, mirroring Calendar's date-field guard). [Source: epics.md#Epic 3 "All views honor Epic 1 field permissions"; view_types.py CalendarViewType get_hidden_fields; 3-4 AC #5]

## Tasks / Subtasks

### Task 1 — Backend model + migration (AC: #1, #2, #3, #4)

- [x] Add `TimelineView(View)` to `backend/src/baserow/contrib/database/views/models.py`, mirroring `CalendarView` (models.py:829–875), **including the clean-room collision guards** (the premium Timeline model co-loads):
  - [ ] `view_ptr` OneToOne with `related_name="core_timeline_view"`; `field_options` M2M through `TimelineViewFieldOptions` with `related_name="+"`; `Meta.db_table = "database_coretimelineview"`. Copy the CalendarView docstring rationale (E304/E305 + table collision). [Source: models.py:829–875]
  - [ ] `start_date_field` — `ForeignKey('database.Field', on_delete=SET_NULL, null=True, blank=True, related_name='core_timeline_view_start_date_field')`. The field positioning the **left edge** of each bar.
  - [ ] `end_date_field` — same shape, `related_name='core_timeline_view_end_date_field'`. The field positioning the **right edge**. (Unlike Calendar where end is optional, a Timeline bar needs **both**; a Row missing either goes to the tray per AC #4. Keep both FKs nullable/optional at the DB level — a view can exist before both are mapped.)
  - [ ] `timescale` — `models.CharField(max_length=8, choices=[("day","day"),("week","week"),("month","month")], default="month")`. **This is the persisted zoom level (AC #3).** Default `"month"`. (This is the one structural delta from Calendar, whose month/week mode was ephemeral client state — here AC #3 explicitly says zoom **persists**.)
- [x] Add `TimelineViewFieldOptions(HierarchicalModelMixin, models.Model)` + its `Manager`, mirroring `CalendarViewFieldOptions` (models.py:877–905): FK `timeline_view`, FK `field`, `hidden` (BooleanField default True), `order` (SmallIntegerField default 32767), `Meta.ordering = ('order', 'field_id')`, `unique_together`/`get_parent`, core table prefix `database_coretimelineviewfieldoptions`. [Source: models.py:877–905 CalendarViewFieldOptions]
- [x] Generate migration `0222_timelineview_timelineviewfieldoptions.py` (next after `0221_calendarview_...`) — include the `timescale` column in this single migration. Verify with `just b migrate --check` / inspect the autogenerated file (no manual SQL). [Source: migrations dir tail = 0221]

### Task 2 — Backend `TimelineViewType` (AC: #1, #2, #3, #4, #5)

- [x] Add `TimelineViewType(ViewType)` to `view_types.py`, mirroring `CalendarViewType` (view_types.py:912–1170):
  - [ ] `type = "timeline"`, `model_class = TimelineView`, `field_options_model_class = TimelineViewFieldOptions`, `field_options_serializer_class = TimelineViewFieldOptionsSerializer`.
  - [ ] `allowed_fields = ["start_date_field", "end_date_field", "timescale"]`, `field_options_allowed_fields = ["hidden", "order"]`, `serializer_field_names = ["start_date_field", "end_date_field", "timescale"]` with `PrimaryKeyRelatedField` overrides for the two date FKs (`required=False, default=None, allow_null=True`) — copy the Calendar override block (view_types.py:921–940). `timescale` is a plain `ChoiceField`/`CharField` serializer field (choices day/week/month) — no PK override.
  - [ ] `prepare_values`: validate `start_date_field` and `end_date_field` (when provided) are **date-representable** (`field_type.can_represent_date(field)` — the SAME capability check Calendar uses, view_types.py:965–966) and **belong to the same table** (`field.table_id == table.id`). Reject otherwise with `IncompatibleField → ERROR_INCOMPATIBLE_FIELD`. Iterate `("start_date_field", "end_date_field")` exactly as Calendar iterates its date fields (view_types.py:953–963). Validate `timescale` is one of the allowed choices (serializer `ChoiceField` does this for free). **Do NOT hard-code field class names** where the `can_represent_date` registry capability exists. [Source: view_types.py:953–966]
  - [ ] `get_visible_field_options_in_order` / `get_hidden_fields`: keep `start_date_field_id` **and** `end_date_field_id` **always visible** even when their `hidden` option is True (AC #5 data-dependency guard) — mirror Calendar keeping its date/end-date fields visible. [Source: view_types.py CalendarViewType get_hidden_fields ~:1119]
  - [ ] `after_field_delete` + `after_fields_type_change`: null `start_date_field_id` / `end_date_field_id` on views referencing a deleted or no-longer-date-representable field. **Soft-delete matters** — FK `SET_NULL` only fires on *hard* delete; add the explicit handler exactly as Calendar does (view_types.py:980–995, filtering on `can_represent_date` for type changes). [Source: view_types.py CalendarViewType after_field_delete/after_fields_type_change]
  - [ ] Export/import: round-trip `start_date_field`, `end_date_field`, `timescale`, and `field_options` (mirror Calendar export/import). **Do not forget `timescale`** in the serialized dict — it is part of the view config (AC #3 persistence).
  - [ ] `can_share = True`, `has_public_info = True`, `can_decorate` — match Calendar's flags unless an AC says otherwise. **Do not** add iCal/feed sharing or any dependency/CPM hooks.
  - [ ] `get_api_urls` → `path("timeline/", include(timeline api urls, namespace=self.type))`.

### Task 3 — Backend API (AC: #1, #2, #4)

- [x] Create `backend/src/baserow/contrib/database/api/views/timeline/` mirroring `.../api/views/calendar/` (`__init__.py`, `urls.py`, `views.py`, `serializers.py`, `errors.py`, `pagination.py`):
  - [ ] `TimelineViewFieldOptionsSerializer` exposing `("hidden", "order")`.
  - [ ] Rows listing endpoint reusing the **inherited bufferedRows** listing (same as Calendar/Kanban — list all rows for the view honoring filters/sorts/field visibility; the **frontend computes bar positions and partitions the tray**). **v1 does NOT need a per-window date-range query param** — the visible axis range + tray are computed client-side. If a later scale story needs date-window pagination, that is out of scope here; note it in Dev Notes. [Source: store/view/calendar.js fetchInitial; api/views/calendar/views.py]
  - [ ] **Reuse** the shared `PATCH /api/database/views/{id}/field_options/` (no timeline-specific field-options endpoint) and the generic `PATCH /api/database/views/{id}/` (carries `start_date_field`/`end_date_field`/`timescale` because they are in `allowed_fields`). [Source: 3-4 Task 3; 3-3 two-PATCH persistence model]

### Task 4 — Backend registration (AC: #1)

- [x] In `apps.py`, import `TimelineViewType` and register it **behind the premium gate**: inside the existing `if "baserow_premium" not in settings.INSTALLED_APPS:` block (apps.py:365–367), add `view_type_registry.register(TimelineViewType())` next to the Kanban/Calendar registration. [Source: apps.py:365–367]

### Task 5 — Frontend view type + components (AC: #1, #2, #3, #4)

- [x] Add `TimelineViewType` to `web-frontend/modules/database/viewTypes.js` extending `BaseBufferedRowViewTypeMixin(ViewType)`, mirroring `CalendarViewType` (viewTypes.js:1353–1440): `getType()='timeline'`, icon (reuse an existing glyph — `iconoir-timeline` / `baserow-icon-*`; verify it exists in the icon map before use, as 3-4 did for `baserow-icon-calendar`), `getName()` → `i18n.t('viewType.timeline')`, `getHeaderComponent()`/`getComponent()`, `canFilter/canSort/canShare/canShowRowModal = true`, `getDefaultFieldOptionValues()` `{hidden:true, order:maxPossibleOrderValue}`, and `afterFieldUpdated`/`afterFieldDeleted` that null `start_date_field`/`end_date_field` when the underlying field changes type or is deleted (mirror Calendar's `_setFieldToNull` calls).
- [x] `TimelineView.vue` (`components/view/timeline/`): build a **horizontal time axis** + one **bar per Row** from `web-frontend/modules/core/utils/date.js` + bundled `moment`. Computeds:
  - `scheduledRows` / `unscheduledRows` — partition `rows`: a Row is **scheduled** only when **both** `start_date_field` and `end_date_field` values are non-null (AC #2); otherwise it goes to the **tray** (AC #4). (Delta from Calendar, which partitioned on a single date field.)
  - `axisRange` — `[min(start), max(end)]` across scheduled rows (fallback to a sensible window around today when empty), snapped to the `timescale` unit (`startOf/endOf('day'|'isoWeek'|'month')`).
  - `ticks` — axis tick labels/positions derived from `axisRange` + `timescale` (day labels for day, ISO-week starts for week, `getCapitalizedMonthName` for month) via `moment().add(...)`.
  - `barStyle(row)` — pure helper mapping `start..end` → `{ left, width }` as a fraction/px of the axis (`startOffset = start.diff(rangeStart, unit)`, `span = end.diff(start, unit)+1`). Keep this a **pure, exported function** (like Calendar's `rowDateKey`) so Task 7 can unit-test it and Story 3.7 can reuse it for drag math. Guard `end < start` → clamp to a minimum 1-unit bar (do not throw).
  - Render each bar with the shared `RowCard` (or a compact bar wrapper that embeds visible `cardFields`) — reuse the Calendar `cardFields`/`hiddenFields` computeds (`filterVisibleFieldsFunction`/`sortFieldsByOrderAndIdFunction`). Do **not** fork `RowCard`. Keep bar DOM seams clean for Story 3.7 drag/resize (no drag handler here).
  - Reuse `bufferedRows`/virtual-scroll patterns for the row list (NFR-2) — do not eager-render all rows for very large tables; mirror Calendar's listing. [Source: architecture.md:142 virtual-scroll reuse; NFR-2]
- [x] `TimelineViewHeader.vue` (`components/view/timeline/`): start-date-field picker + end-date-field picker (offer **date-representable** fields only — mirror the Calendar header's field filtering), a **day/week/month zoom** control (AC #3), and a **"Customize cards"** trigger rendering the shared `ViewFieldsContext`. Persist `start_date_field`/`end_date_field`/`timescale` via the generic `view/update` action; field options via the shared field-options actions. **Guard every option/config dispatch** with `this.readOnly || !this.$hasPermission('database.table.view.update_field_options', view, workspaceId)` exactly as Calendar/Kanban do. The zoom control writes `timescale` through `view/update` so it round-trips (AC #3). [Source: CalendarViewHeader.vue; 3-4 Task 5; 3-3 "Field permissions / readOnly"]
- [x] `store/view/timeline.js`: clone `store/view/calendar.js` — `bufferedRows({ service: TimelineService, customPopulateRow })`, `fetchInitial` requesting `includeFieldOptions: true` → `forceUpdateAllFieldOptions`. Field-option getters/actions are inherited; **add no new field-option store code**. Pre-seed any per-row flag you will need for 3.7 drag (Calendar pre-seeded `row._.dragging` in 3.4 for 3.5) only if trivial; otherwise leave for 3.7. [Source: store/view/calendar.js]
- [x] `services/view/timeline.js`: clone `services/view/calendar.js`.
- [x] Register the store module in `web-frontend/modules/database/plugin/store.js` and the view type in `web-frontend/modules/database/plugin.js` next to Calendar: `$registry.register('view', new TimelineViewType(context))` at plugin.js:434 — **last-wins**, so premium overrides in open-core builds; core is active only OSS-only. [Source: plugin.js:433; 3-4 modified-files list]
- [x] Add `viewType.timeline` to `web-frontend/locales/en.json` and `timelineView*`/`timelineViewHeader*` keys to `web-frontend/modules/database/locales/en.json`. [Source: 3-4 locale keys]
- [x] Add `web-frontend/modules/core/assets/scss/components/views/timeline.scss` (BEM `.timeline-view__*`: axis, tick, bar, tray) and import it in `web-frontend/modules/core/assets/scss/components/all.scss`. [Source: 3-4 calendar.scss + all.scss import]

### Task 6 — Backend tests (AC: #1, #2, #3, #4, #5) — OSS-only

- [x] `backend/tests/baserow/contrib/database/view/test_timeline_view_type.py` (mirror `test_calendar_view_type.py`):
  - [ ] create a timeline view; set `start_date_field`/`end_date_field` to Date fields → accepted+persisted; set either to a non-date field → rejected (`IncompatibleField`); a date field from another table → rejected.
  - [ ] `timescale` persists and round-trips; an invalid choice is rejected.
  - [ ] `start_date_field_id`/`end_date_field_id` nulled when the referenced field is (soft-)deleted via `after_field_delete`, and when it changes to a non-date type via `after_fields_type_change`.
  - [ ] `get_hidden_fields` excludes `start_date_field_id` and `end_date_field_id` even when their option is `hidden=True` (AC #5).
  - [ ] export/import round-trips `start_date_field`, `end_date_field`, `timescale`, and `field_options`.
- [x] `backend/tests/baserow/contrib/database/api/views/timeline/test_timeline_view_views.py` (mirror `test_calendar_view_views.py`): list rows (honors filters/sorts/field-visibility), `PATCH .../{id}/` with `start_date_field`/`end_date_field`/`timescale` persists + returns on GET, `PATCH .../{id}/field_options/` `{hidden:true}` and `{order:N}` persist.
- [x] Add a `timeline` fixture to `backend/src/baserow/test_utils/fixtures/view.py` (mirror the calendar fixture).
- [x] Run OSS-only: `TEST_ENV_FILE=.env.oss-test just b test backend/tests/baserow/contrib/database/view/test_timeline_view_type.py backend/tests/baserow/contrib/database/api/views/timeline/test_timeline_view_views.py`. Expect green. If `just` absent, use the direct recipe from Dev Notes. [Source: 3-4 Debug Log — `.env.oss-test` so core (not premium) timeline registers]

### Task 7 — Frontend unit tests (AC: #2, #3, #4) — method/computed-level only

- [x] **Do NOT `testApp.mount(TimelineView)`** — the premium Timeline store registers last (override) → mock-miss + JS-heap OOM (same failure 3.2/3.3/3.4 hit). Use the **method/computed-level** pattern: bind the real `scheduledRows`/`unscheduledRows`/`barStyle`/`axisRange`/`ticks` computeds/helpers and the header dispatch methods to a minimal fake `vm`. [Source: 3-4 Task 7; kanbanView.spec.js / calendarView.spec.js]
  - [ ] `scheduledRows`/`unscheduledRows` partition by **both** start AND end non-null (missing either → tray). (AC #2/#4)
  - [ ] `barStyle(row)`: a 1-unit row → minimal-width bar at the right offset; a multi-unit row → `width` ≈ span; `end < start` clamps to 1 unit without throwing. Assert offset/width arithmetic directly (this is the net-new logic keystone). (AC #2)
  - [ ] `axisRange`/`ticks`: day/week/month timescale produces the expected tick count/range for a known row set. (AC #3)
  - [ ] header: selecting a date field dispatches `view/update` with `{start_date_field}`/`{end_date_field}`; changing zoom dispatches `view/update` with `{timescale}`; option dispatches carry the `readOnly`/permission guard. (AC #1/#3/#5)
- [x] Run: `yarn vitest run web-frontend/test/unit/database/components/view/timeline/`. Expect green. [Source: 3-4 Task 7 run command]

### Task 8 — E2E scenario (AC: #1, #2, #3, #4) — author only

- [x] Add `e2e-tests/tests/database/timeline_view.spec.ts` + a `createTimelineView` fixture in `e2e-tests/fixtures/database/view.ts` (mirror the calendar fixture/spec). Scenario: create a Table with start+end Date fields and rows (some with both dates, one missing end), add a Timeline view, map both date fields → fully-dated rows render as bars, the row missing end appears in the tray (not as a bar); change zoom day↔week↔month; reload → config (both fields + zoom) persists.
- [x] **Do NOT run E2E locally** — requires Docker stack, targets the OSS-only CI lane (`e2e-tests/` has no local tsconfig/node_modules). Author the spec only. Format `.ts` with `web-frontend/node_modules/.bin/prettier`. [Source: 3-4 Task 8; 3-5 Debug Log prettier-for-ts note]

### Task 9 — Clean-room provenance (gate, MANDATORY) (AC: all)

- [x] Add `docs/clean-room/provenance/3-6-create-and-configure-a-timeline-view.md` declaring **Bucket A**: no `premium/`/`enterprise/` sources read; built from the public MIT core Calendar view (3.4) + core Kanban (3.1) + MIT Gallery card surface, the shared `RowCard`/`ViewFieldsContext`, and core `utils/date.js` + bundled `moment`. Mirror the 3-4/3-5 provenance file structure (allowed-source list + implementer-eligibility + reviewer-confirmation checkboxes). Validate with the gate (`docs/clean-room/scripts/check_provenance.py` / `validate_provenance()` → expect **PASS** as Bucket A; `PR_LABELS=bucket-a`). PR must carry the `bucket-a` label/checkbox. [Source: 1-1-establish-the-clean-room-process-gate.md; 3-4 Task 9; 3-5 Task 7]

### Task 10 — Lint + verify (AC: all)

- [x] Ruff (`check` + `format`) on backend Python; ESLint + Prettier on `.vue`/`.js`; Stylelint on `timeline.scss`; e2e `.ts` matches existing style. ESLint 9 must be invoked from **repo root** with `web-frontend/node_modules/.bin/eslint` (fails with "No files matching" from inside `web-frontend/`). [Source: 3-5 Debug Log ESLint-from-root note]
- [x] `just b run pre-commit run --files $(git diff --name-only origin/develop...HEAD)` (or run the individual linters directly if `just`/`pre-commit` not on PATH, as in 3-3/3-4). [Source: AGENTS.md code-quality]

## Dev Notes

### Architecture patterns & constraints

- **View-type spine.** A core view = `ViewType` (backend `view_types.py`) + `View` subclass model + `*FieldOptions` model + migration + `api/views/<type>/` (urls/views/serializers/errors/pagination) + `apps.py` registration; frontend = `ViewType` class in `viewTypes.js` + `<Type>View.vue` + `<Type>ViewHeader.vue` + `store/view/<type>.js` + `services/view/<type>.js` + `plugin.js` + `plugin/store.js` registration + i18n + SCSS. Every piece has a Calendar precedent (3.4) — clone it. [Source: 3-4 Project Structure Notes; architecture.md:279,302–303]
- **Reuse, do not fork:** `RowCard.vue` (bar content), `ViewFieldsContext.vue` (Customize-cards field toggle/reorder), `bufferedRows`/`fieldOptions` store factories (all field-option actions/getters + virtual scroll), and `utils/date.js` + bundled `moment` (axis math). Forking any of these is the "reinventing wheels" failure mode. [Source: 3-4 Dev Notes "Reuse, do not fork"]
- **Filters/sorts/field-visibility (AC #1)** come for free from the `View` base + `bufferedRows` listing (same as Calendar/Kanban) — the listing already applies adhoc filtering/sorting and `field_options`. Verify, don't re-add. [Source: store/view/calendar.js fetchInitial]
- **Field permissions (AC #5)** are enforced by Epic 1's central field-permission layer at the row/serializer level; the timeline's only extra responsibility is the **data-dependency guard** in `get_hidden_fields` keeping the start/end date fields visible to layout. [Source: view_types.py CalendarViewType get_hidden_fields; Epic 1 stories 1.4/1.5; 3-4 AC #5]
- **Performance (NFR-2).** Reuse the existing virtual-scroll/lazy-row `bufferedRows` patterns for the row column; the bar layer positions only the visible rows. Do not plot all rows of a 100k-row table eagerly. No new heavy bundle (no Gantt/timeline lib) — bars are plain DOM positioned by `moment` math. [Source: architecture.md:142,367; NFR-2]

### The one structural delta from Calendar: `timescale` is PERSISTED (AC #3)

Calendar's month/week mode was deliberately **client-side ephemeral** (3-4 Completion Notes — AC #3 there only required *availability*). **Timeline is different:** AC #3 / FR-6 say the zoom **persists**. So `timescale` is a real `CharField(choices=day/week/month, default="month")` column on `TimelineView`, in `allowed_fields`, validated by the serializer `ChoiceField`, round-tripped in export/import, and written by the header's zoom control via the generic `PATCH /api/database/views/{id}/`. Re-hydrated as part of the serialized view on reopen. **Do not** make zoom ephemeral and **do not** add a bespoke "set zoom" endpoint — the generic view PATCH carries it because it is an allowed field.

### The net-new logic: bar geometry (`barStyle` / `axisRange` / `ticks`)

Everything else clones Calendar. The genuinely new piece is mapping a `start..end` date pair to a horizontal `{left, width}` over a `timescale`-snapped axis:

- Parse start/end with the bundled `moment` in the **user timezone** (`getUserTimeZone()`) so date-only fields don't drift across DST/offset — mirror Calendar's local-frame parse (3-5 `rowDateKey` learned this the hard way: never `moment.utc` for positioning). [Source: 3-5 Dev Notes "Date value shape"; date.js:174 getUserTimeZone]
- `axisRange = [min(start) snapped to startOf(unit), max(end) snapped to endOf(unit)]`; `unit ∈ {day, isoWeek, month}` from `timescale`.
- `barStyle(row)`: `startOffset = start.diff(rangeStart, unit)`, `span = max(1, end.diff(start, unit) + 1)`; convert to `%`/px of total axis length. Pure, exported, unit-tested round-trip (Task 7). Clamp `end < start` to a 1-unit bar (degrade gracefully, no throw) — same defensive posture as Calendar's `groupRowsByDate` guarding `rawEnd > start`. [Source: 3-5 Dev Notes multi-day guard]
- `BaseDateFieldType.formatValue` canonical cell shape: `date_include_time ? moment.utc(value).format() : moment.utc(value).format('YYYY-MM-DD')` (fieldTypes.js ~2588). Read the stored value as-is; parse for positioning in the local frame. [Source: fieldTypes.js BaseDateFieldType.formatValue; 3-5 Dev Notes]

### Scheduled vs tray (AC #2 vs #4) — both required

A Row is a **bar** only if BOTH `start_date_field` and `end_date_field` have values. Missing either → **tray** (not a malformed/zero-width bar). This is the delta from Calendar's single-field partition (`unscheduledRows` there keyed off one date field). Implement `scheduledRows`/`unscheduledRows` accordingly and unit-test the "missing end → tray" case explicitly (AC #4).

### Persistence model (AC #1, #3) — two PATCH paths, both pre-existing

- **View config** (`start_date_field`, `end_date_field`, `timescale`) → generic `PATCH /api/database/views/{id}/` (allowed because all three are in `allowed_fields`; `prepare_values` validates the date fields, the serializer `ChoiceField` validates `timescale`). Re-hydrated as part of the serialized view on reopen. [Source: 3-4 persistence model]
- **Card face** (`hidden`/`order`) → shared `PATCH /api/database/views/{id}/field_options/`; re-hydrated by `fetchInitial` (`includeFieldOptions:true`). Both round-trip through export/import. [Source: 3-3/3-4 two-PATCH persistence]

### Clean-room reminder (the porous boundary)

The clean-room boundary **leaks under debugging** — prior agents drifted into `premium/`/`enterprise/` while "just checking how X works" (this is a documented, recurring failure). Hold the line: every file you read for this story is under `backend/src/baserow/...`, `web-frontend/modules/{database,core}/...`, `backend/tests/...`, `web-frontend/test/...`, or `e2e-tests/...`. Your **only** references for "what a timeline looks like" are the **core Calendar** view (3.4, MIT-derived), the **core Kanban** view (3.1), and the **MIT Gallery** view. The premium timeline directories listed in Context exist **only so you know what NOT to open**. A contaminated Bucket A PR cannot merge. [Source: memory clean-room-isolation-porous; memory baserow-open-core-license-constraint; 1-1 provenance gate]

### OSS-only test execution (critical — else premium overrides core)

`backend/src/baserow/config/settings/test.py` reads `TEST_ENV_FILE` and loads it via dotenv. Reuse `backend/.env.oss-test` (`BASEROW_OSS_ONLY=true`) and run with `TEST_ENV_FILE=.env.oss-test` so the **core** Timeline (not premium's) registers as the `timeline` view type. Without it, premium's TimelineView registers last and tests fail with `ViewTypeDoesNotExist` / wrong model. If `just` is absent, replicate the recipe: backend `uv run pytest` with `PYTHONPATH=src:../premium/backend/src:../enterprise/backend/src` and the docker test DB `DATABASE_URL=postgres://baserow:baserow@localhost:5431/baserow-test-db`; frontend `yarn vitest run`. (`.env.oss-test` carries no `DATABASE_URL`; pass it explicitly.) [Source: 3-4 Debug Log; 3-5 Debug Log]

### Anti-patterns (forbidden)

- ❌ Opening/reading/adapting anything under `premium/` or `enterprise/` (timeline contamination → PR cannot merge). [Source: architecture.md:25,279]
- ❌ Adding a timeline/Gantt/date library (Frappe Gantt, vis-timeline, FullCalendar, dayjs, date-fns). Frappe Gantt is **Story 3.8 (Bucket B)** render-only over the CPM backend — NOT this story. `utils/date.js` + bundled `moment` suffice. [Source: architecture.md:111,168]
- ❌ Forking `RowCard.vue` / `ViewFieldsContext.vue` / `bufferedRows` / `fieldOptions` — reuse them.
- ❌ A bespoke timeline-specific field-options endpoint, "set zoom" endpoint, or store action — the shared field-options PATCH + generic view PATCH (with `timescale` in `allowed_fields`) cover it.
- ❌ Making `timescale` ephemeral client state — AC #3 requires persistence (this is the one delta from Calendar).
- ❌ Rendering Rows missing start or end as zero/negative-width bars — they go to the tray (AC #4).
- ❌ Implementing **drag/resize** (that is Story 3.7) or a **dependency/CPM/milestone** layer (Stories 3.8–3.11).
- ❌ Omitting the clean-room collision guards on the core model (distinct `db_table` + non-clashing `related_name`s) — premium TimelineView co-loads → `fields.E304/E305` + table collision. [Source: models.py:829–875]
- ❌ `testApp.mount(TimelineView)` in unit tests (premium store override → mock-miss + OOM) — method/computed-level only.
- ❌ Running tests in the default (open-core) profile — premium timeline shadows core. Use `.env.oss-test`.
- ❌ Marking a task `[x]` without the cited verification / passing test ("lying about completion").
- ❌ Merging a Bucket A PR without a passing provenance record (CI gate blocks it).

### Project Structure Notes

**New files (core):**
- `backend/src/baserow/contrib/database/migrations/0222_timelineview_timelineviewfieldoptions.py`
- `backend/src/baserow/contrib/database/api/views/timeline/{__init__,urls,views,serializers,errors,pagination}.py`
- `web-frontend/modules/database/components/view/timeline/TimelineView.vue`
- `web-frontend/modules/database/components/view/timeline/TimelineViewHeader.vue`
- `web-frontend/modules/database/store/view/timeline.js`
- `web-frontend/modules/database/services/view/timeline.js`
- `web-frontend/modules/core/assets/scss/components/views/timeline.scss`
- `backend/tests/baserow/contrib/database/view/test_timeline_view_type.py`
- `backend/tests/baserow/contrib/database/api/views/timeline/test_timeline_view_views.py`
- `web-frontend/test/unit/database/components/view/timeline/timelineView.spec.js`
- `e2e-tests/tests/database/timeline_view.spec.ts`
- `docs/clean-room/provenance/3-6-create-and-configure-a-timeline-view.md`

**Modified files (core):**
- `backend/src/baserow/contrib/database/views/models.py` (+`TimelineView`, `TimelineViewFieldOptions`, manager)
- `backend/src/baserow/contrib/database/views/view_types.py` (+`TimelineViewType`)
- `backend/src/baserow/contrib/database/apps.py` (register `TimelineViewType` behind premium gate)
- `backend/src/baserow/test_utils/fixtures/view.py` (timeline view fixture)
- `web-frontend/modules/database/viewTypes.js` (+`TimelineViewType`)
- `web-frontend/modules/database/plugin.js` (register timeline view)
- `web-frontend/modules/database/plugin/store.js` (register timeline store module)
- `web-frontend/modules/database/locales/en.json` (`timelineView*`, `timelineViewHeader*`)
- `web-frontend/locales/en.json` (`viewType.timeline`)
- `web-frontend/modules/core/assets/scss/components/all.scss` (import timeline.scss)
- `e2e-tests/fixtures/database/view.ts` (`createTimelineView` fixture)

Naming follows existing conventions; core table prefix `database_coretimelineview...`; `.vue` PascalCase, methods camelCase, BEM SCSS. [Source: architecture.md:279; 3-4 core-table note; AGENTS.md Coding Style]

### References

- [Source: epics.md#Epic 3 → Story 3.6, lines 548–560] — user story + AC (map start+end date fields, bar per row on time axis, day/week/month zoom persists, rows missing start/end listed separately).
- [Source: epics.md FR-6, line 35] — "Create and configure a Timeline View — map start+end Date Fields; bars on time axis; day/week/month zoom persists; rows missing start/end listed separately."
- [Source: architecture.md lines 25, 158, 279, 302–303] — Timeline = Bucket A clean-room core `ViewType`; register in `view_types.py`/`viewTypes.js`; renderer under `components/view/timeline/`.
- [Source: architecture.md:111,168] — Frappe Gantt is the **Gantt** (D2, Bucket B) render-only lib over the backend CPM engine — NOT Timeline; Timeline must not add a render lib.
- [Source: backend/src/baserow/contrib/database/views/view_types.py:912–1170 (CalendarViewType)] — the structural template: `allowed_fields`, serializer overrides, `prepare_values` `can_represent_date` + same-table validation, `get_hidden_fields` data-dependency guard, `after_field_delete`/`after_fields_type_change`, export/import.
- [Source: backend/src/baserow/contrib/database/views/models.py:829–905 (CalendarView, CalendarViewFieldOptions)] — model + field-options template + the clean-room co-load collision guards (distinct `db_table`, non-clashing `related_name`s) that MUST be replicated.
- [Source: backend/src/baserow/contrib/database/apps.py:365–367] — premium-gate registration (`if "baserow_premium" not in settings.INSTALLED_APPS`).
- [Source: backend/src/baserow/contrib/database/api/views/calendar/*] — API urls/views/serializers/errors/pagination template to mirror as `.../timeline/`.
- [Source: web-frontend/modules/database/viewTypes.js:1353 (CalendarViewType)] — frontend view-type class template (`BaseBufferedRowViewTypeMixin`, `afterFieldUpdated/Deleted` null-refs).
- [Source: web-frontend/modules/database/components/view/calendar/{CalendarView,CalendarViewHeader}.vue] — component template (date-field pickers, Customize-cards header, permission guards, local-frame date parse).
- [Source: web-frontend/modules/database/components/card/RowCard.vue; .../view/ViewFieldsContext.vue] — shared content rendering + field-face context (reuse verbatim).
- [Source: web-frontend/modules/database/store/view/calendar.js; services/view/calendar.js] — bufferedRows store + service template (`fetchInitial` field-option hydration, virtual scroll).
- [Source: web-frontend/modules/core/utils/date.js:68–178] — MIT date helpers (`getCapitalizedMonthName`, `weekDaysShort`, `getDateInTimezone`, `getUserTimeZone`) + bundled `moment` — use instead of a timeline lib.
- [Source: web-frontend/modules/database/plugin.js:432–434] — frontend last-wins registration gate (Kanban/Calendar precedent; add Timeline at :434).
- [Source: 3-4-create-and-configure-a-calendar-view.md] — the immediate net-new core view-build precedent (tasks/structure/OSS-only `.env.oss-test`/method-level unit pattern/no-mount-OOM/provenance hard gate/two-PATCH persistence). Clone this.
- [Source: 3-5-reschedule-a-calendar-entry-by-drag.md] — local-frame date parse (never `moment.utc` for positioning), prettier-for-ts note, ESLint-from-repo-root note, keep DOM seams clean for the next (drag) story.
- [Source: 3-1-create-and-configure-a-kanban-view.md] — original net-new core view build precedent (the scaffold Calendar itself cloned).
- [Source: 1-1-establish-the-clean-room-process-gate.md] — provenance = hard merge gate; "influenced by" = contamination.
- [Source: memory clean-room-isolation-porous] — clean-room drift during verify/debug; hold the line.
- [Source: memory baserow-open-core-license-constraint] — paid features need clean-room reimplement; PE/EE forbids copying.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (BMAD dev-story workflow)

### Debug Log References

- Backend OSS-only tests: `TEST_ENV_FILE=.env.oss-test PYTHONPATH=src:../premium/backend/src:../enterprise/backend/src DATABASE_URL=postgres://baserow:baserow@localhost:5431/baserow-test-db uv run pytest ...` (`just` absent locally). 22 passed (13 view-type + 9 API). `.env.oss-test` forces `BASEROW_OSS_ONLY=true` so the **core** Timeline — not premium's last-wins override — is the registered `timeline` type under test.
- Frontend unit tests: `yarn vitest run web-frontend/test/unit/database/components/view/timeline/timelineView.spec.js` → 41 passed. Method/computed-level only (no `testApp.mount(TimelineView)` — premium store override → mock-miss + JS-heap OOM, the same failure 3.2/3.3/3.4 hit).
- E2E `e2e-tests/tests/database/timeline_view.spec.ts` authored only, NOT run locally (needs Docker stack; targets the OSS-only CI lane). Formatted with `web-frontend/node_modules/.bin/prettier`.
- Clean-room provenance gate: `PR_LABELS=bucket-a CHANGED_FILES=docs/clean-room/provenance/3-6-...md python3 docs/clean-room/scripts/check_provenance.py` → `PASS`.
- Lint: Ruff `check --fix` (2 import-sort fixes) + `format` clean on backend; ESLint `--fix` + Prettier clean on frontend `.vue`/`.js`; Stylelint `--fix` clean on `timeline.scss`. ESLint invoked from repo root via `web-frontend/node_modules/.bin/eslint`.

### Completion Notes List

- **Net-new core build cloned from the 3.4 Calendar scaffold** (no premium/enterprise read). Backend: `TimelineView`/`TimelineViewFieldOptions` models with clean-room collision guards (`database_coretimelineview*` tables, `core_`-prefixed reverse accessors), migration `0222`, `TimelineViewType`, `api/views/timeline/` package, premium-gated `apps.py` registration. Frontend: `TimelineViewType` (last-wins registration), `TimelineView.vue` + `TimelineViewHeader.vue`, `store/view/timeline.js`, `services/view/timeline.js`, locales, `timeline.scss`.
- **The one structural delta from Calendar:** `timescale` is a **persisted** `CharField` (choices day/week/month, default `month`) for AC #3 zoom round-trip — written through the generic `PATCH /api/database/views/{id}/` path, unlike Calendar's ephemeral display-mode. No bespoke endpoint.
- **Bar geometry is pure exported functions** (`timelineUnit`, `parseTimelineValue`, `rowDateRange`, `partitionTimelineRows`, `computeAxisRange`, `axisUnitCount`, `computeTicks`, `barGeometry`) over the bundled `@baserow/modules/core/moment` — no Gantt/timeline library added. Dates parsed in `getUserTimeZone()` (never `moment.utc`); reversed range (`end < start`) clamps to a 1-unit bar.
- **Scheduled vs tray (AC #2/#4):** a row is a bar only when **both** `start_date_field` and `end_date_field` have values; missing either → unscheduled tray. `start_date_field_id`/`end_date_field_id` kept always-visible to the layout via the hidden-fields guard.
- Store pre-seeds `dragging: false` per row for the future Story 3.7 drag-to-reschedule; no drag handlers wired (out of scope here).

### File List

**Backend (added)**
- `backend/src/baserow/contrib/database/migrations/0222_timelineview_timelineviewfieldoptions.py`
- `backend/src/baserow/contrib/database/api/views/timeline/` (`__init__.py`, `urls.py`, `views.py`, `serializers.py`, `errors.py`, `pagination.py`)
- `backend/tests/baserow/contrib/database/view/test_timeline_view_type.py`
- `backend/tests/baserow/contrib/database/api/views/timeline/test_timeline_view_views.py`

**Backend (modified)**
- `backend/src/baserow/contrib/database/views/models.py` (TimelineView, TimelineViewFieldOptions)
- `backend/src/baserow/contrib/database/views/view_types.py` (TimelineViewType)
- `backend/src/baserow/contrib/database/apps.py` (premium-gated registration)
- `backend/src/baserow/test_utils/fixtures/view.py` (timeline fixture)

**Frontend (added)**
- `web-frontend/modules/database/services/view/timeline.js`
- `web-frontend/modules/database/store/view/timeline.js`
- `web-frontend/modules/database/components/view/timeline/TimelineView.vue`
- `web-frontend/modules/database/components/view/timeline/TimelineViewHeader.vue`
- `web-frontend/modules/core/assets/scss/components/views/timeline.scss`
- `web-frontend/test/unit/database/components/view/timeline/timelineView.spec.js`

**Frontend (modified)**
- `web-frontend/modules/database/viewTypes.js` (TimelineViewType + imports)
- `web-frontend/modules/database/plugin.js` (registration)
- `web-frontend/modules/database/plugin/store.js` (store registration, page/ + template/)
- `web-frontend/locales/en.json` (`viewType.timeline`)
- `web-frontend/modules/database/locales/en.json` (`timelineView*`, `timelineViewHeader*`)
- `web-frontend/modules/core/assets/scss/components/all.scss` (timeline import)

**E2E (added/modified)**
- `e2e-tests/tests/database/timeline_view.spec.ts` (added, author-only)
- `e2e-tests/fixtures/database/view.ts` (modified, `createTimelineView`)

**Docs (added)**
- `docs/clean-room/provenance/3-6-create-and-configure-a-timeline-view.md`

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-06-10 | 1.0 | Story 3.6 implemented: net-new core Timeline view (Bucket A clean-room, cloned from 3.4 Calendar). Backend models/migration/view-type/API/registration; frontend view-type/components/store/service/locales/SCSS; persisted `timescale` zoom; bar-geometry pure functions; 22 backend + 41 frontend unit tests green; E2E authored; provenance gate PASS; lint clean. Status → review. | dev-agent (claude-opus-4-8) |
| 2026-06-10 | 1.1 | Senior Developer adversarial review (auto-fix mode). All 5 ACs verified against implementation; File List matches git reality; clean-room collision guards + provenance gate re-verified; 22 backend + 41 frontend tests re-run green; ruff/eslint/stylelint/prettier clean. 0 Critical/High/Medium findings; 2 Low non-blocking observations recorded (no code changes required). Outcome: Approve. Status → done. | review-agent (claude-opus-4-8) |

## Senior Developer Review (AI)

**Reviewer:** thephams.sg (gabenidolcs) · **Date:** 2026-06-10 · **Mode:** autonomous adversarial review, auto-fix

**Outcome: ✅ APPROVE → done** (0 Critical / 0 High / 0 Medium / 2 Low)

### Scope & method

Adversarially validated every story claim against the actual implementation and git reality. Read every file in the File List, re-ran (not merely trusted) the backend OSS-only suite and the frontend unit suite, and re-executed the clean-room provenance gate and all linters.

### Git vs File List

No discrepancies. Every file in the Dev Agent Record → File List is present in `git status`, and every timeline-related working-tree change is documented in the File List. (The `_bmad-output/.../tests/3-6-timeline-view-test-summary.md` artifact is under `_bmad-output/` and excluded from review scope — not a finding.)

### Acceptance Criteria — all IMPLEMENTED

- **AC #1 (persist config + honor filters/sorts/visibility):** `timescale`/`start_date_field`/`end_date_field` in `allowed_fields` → generic view PATCH; `bufferedRows` listing applies filters/sorts/field_options. Backend `test_list_rows_applies_sorts_and_filters`, `test_patch_timeline_view_date_fields`; frontend `updateStartDateField`/`updateEndDateField` dispatch tests. ✅
- **AC #2 (bar from start→end):** pure `barGeometry`/`computeAxisRange`/`axisUnitCount`/`computeTicks` over bundled `moment`, unit-tested offset/width arithmetic. ✅
- **AC #3 (day/week/month zoom persists):** real `CharField(choices, default="month")` column, serializer `ChoiceField`, round-tripped in export/import, written via `view/update`. `test_timeline_timescale_persists_and_round_trips`, `test_patch_timeline_view_timescale_persists`, `test_patch_timeline_view_rejects_invalid_timescale`. ✅
- **AC #4 (rows missing start/end → tray, not malformed bars):** `partitionTimelineRows` requires BOTH values non-null for a bar; missing either → tray. Frontend partition tests cover missing-end / missing-start / missing-both. ✅
- **AC #5 (field permissions + date-field layout guard):** `get_hidden_fields`/`get_visible_field_options_in_order` keep `start_date_field_id`/`end_date_field_id` always visible; header option dispatches carry the `readOnly || !$hasPermission(...)` guard. `test_timeline_get_hidden_fields_keeps_date_fields_visible` + header guard tests. ✅

### Clean-room (Bucket A) — verified

Distinct table names (`database_coretimelineview*`), non-clashing reverse accessors (`core_timeline_view*`, M2M `related_name="+"`) replicate the CalendarView co-load collision guards (E304/E305). Premium-gated backend registration (`if "baserow_premium" not in INSTALLED_APPS`) + frontend last-wins. `baserow-icon-timeline` glyph confirmed present in core (`assets/icons/timeline.svg` + `$baserow-icons` list) — no library/asset added. Provenance gate: **PASS** (`PR_LABELS=bucket-a`).

### Verification (re-run, not trusted)

- Backend OSS-only: `TEST_ENV_FILE=.env.oss-test ... pytest` → **22 passed**.
- Frontend: `vitest run .../timeline/timelineView.spec.js` → **41 passed**.
- Provenance gate → **PASS**. Ruff check + format → clean. ESLint → clean. Stylelint → clean. Prettier (vue/js/ts) → clean.

### Findings

**Low (non-blocking, no fix applied):**

1. `computeTicks` — the `day` and `week` branches both format labels as `'D MMM'`; the explicit split is currently redundant. Kept intentionally as a seam for Story 3.7+ divergence; no functional impact.
2. Axis ticks are not virtualized for very large ranges in `day` mode (a multi-year span renders one tick node per day). Rows themselves ARE virtualized via `bufferedRows`; the story explicitly scopes the heavy axis case out of v1. Acceptable tradeoff; revisit if a scale story needs date-window pagination.

No Critical/High/Medium defects found. The implementation is a faithful, well-tested clone of the proven core Calendar scaffold; no code changes were required.
