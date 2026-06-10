---
baseline_commit: c116b4feb4543d039a79d4f552212eabdc7d1a26
---

# Story 3.8: Render a Gantt View

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want a Gantt View building on the Timeline with a dependency layer,
so that I can plan a project on a time axis. `[B]`

## Context & Scope

### 🟦 THIS IS A BUCKET B STORY — read the bucket distinction first

Gantt is a **Bucket B** feature, **NOT** Bucket A. The distinction changes the rules:

- **No clean-room contamination gate.** Baserow ships **no** premium/enterprise Gantt view — there is nothing to clean-room around. `grep -rn gantt premium/ enterprise/` returns only an unrelated `website_export.csv` row. The CI provenance gate (`check_provenance.py`) **only fires for PRs labelled `bucket-a`** — this PR is **not** `bucket-a`, so the hard provenance merge-gate does not apply. [Source: architecture.md:25 "Gantt + Map (Bucket B)"; docs/clean-room/scripts/check_provenance.py:10-13 gate fires only on bucket-a; epics.md:174 "Gantt/Map are Bucket B"]
- **But you still build on a Bucket A artifact.** This view is rendered "like Timeline (Story 3.6)" and its config (start/end Date Field + zoom) mirrors the **core Timeline** (3.6/3.7), which is MIT-clean core. Reusing core Timeline is fine and expected. You may freely read `web-frontend/modules/database/components/view/timeline/*`, `web-frontend/modules/database/store/view/timeline.js`, `backend/.../views/view_types.py` (TimelineViewType), `backend/.../views/models.py` (TimelineView) — **all core, all allowed.**
- **Still do NOT read `premium/` or `enterprise/`.** A premium **Timeline** exists (`premium/web-frontend/modules/baserow_premium/components/views/timeline/*`, `premium/backend/.../api/views/timeline/*`). It is irrelevant to Gantt and off-limits regardless of bucket — license hygiene. Your only "what does a timeline/gantt look like" reference is the **core** Timeline (3.6) + the third-party **Frappe Gantt** docs. [Source: memory clean-room-isolation-porous; memory baserow-open-core-license-constraint]
- **Provenance is recommended hygiene, not a CI blocker (Task 10).** Author a light Bucket B attribution record (Frappe Gantt = MIT third-party render lib; view derives from core Timeline = MIT; no PE/EE read). It documents the third-party license but is NOT the bucket-a hard gate. Do **not** add the `bucket-a` label.

### 🧭 THE BUILD STRATEGY: clone the core Timeline view-type spine (3.6), swap the plain-DOM bar layer for the lazy-loaded Frappe Gantt SVG renderer

This is a **net-new core view build**, structurally a **near-twin of the Timeline view (3.6)** with **one render delta**: instead of drawing bars as plain positioned `<div>`s, the Gantt view hands its scheduled rows to the **Frappe Gantt** library (MIT, `1.2.2`, lazy-loaded) which draws an SVG of bars **plus a dependency-connector layer**. Everything else — config model, date-field validation, zoom persistence, filters/sorts/field-visibility, tray for unscheduled rows, `bufferedRows` listing, `RowCard`/`ViewFieldsContext` reuse — is the Timeline spine. [Source: epics.md:576-588 Story 3.8; architecture.md:97 AR-4 "Frappe Gantt 1.2.2 (MIT), render-only"; architecture.md:111 D2]

Every structural piece has a working core precedent — clone the **Timeline (3.6)** shapes, which themselves cloned Calendar (3.4):

- Backend `GanttViewType(ViewType)` + `GanttView(View)` model + `GanttViewFieldOptions` model + migration + `api/views/gantt/` package + `apps.py` registration → **copy the Timeline shapes** (`TimelineViewType` view_types.py:1181-~1320; `TimelineView`/`TimelineViewFieldOptions` models.py:916-1005; `api/views/timeline/`; `apps.py`). [Source: backend/.../views/view_types.py:1181; models.py:916]
- Frontend `GanttViewType` (`BaseBufferedRowViewTypeMixin`) + `GanttView.vue` + `GanttViewHeader.vue` + `store/view/gantt.js` + `services/view/gantt.js` + `plugin.js`/`plugin/store.js` registration + i18n + `gantt.scss` → **copy the Timeline shapes** (`TimelineViewType` viewTypes.js:1447; `TimelineView.vue`, `TimelineViewHeader.vue`, `store/view/timeline.js`, `services/view/timeline.js`). [Source: viewTypes.js:1447; plugin.js:438]
- Bar geometry / scheduled-vs-tray partition / zoom math: **reuse the core Timeline pure helpers** verbatim where the Frappe Gantt mapping needs them (Frappe Gantt computes its own bar X/width from `start`/`end` dates + `view_mode`, so you mostly need the **scheduled/unscheduled partition** and **date parsing in the user timezone**, not the px math). [Source: 3-6 Completion Notes "Bar geometry is pure exported functions"; TimelineView.vue partition computeds]

### ⚠️ The TWO real deltas from Timeline (everything else is a clone)

1. **No premium co-load → standard table names + unconditional registration.** Timeline needed clean-room collision guards (`database_coretimelineview` table, `core_timeline_view*` reverse accessors) and **premium-gated** registration (`if "baserow_premium" not in INSTALLED_APPS` + frontend last-wins) **because a premium Timeline co-loads**. **Gantt has no premium twin** → use **plain** table names (`database_ganttview`, `database_ganttviewfieldoptions`), **plain** `related_name`s (`gantt_view*`), and register **unconditionally** (backend: outside the premium gate, next to Grid/Form; frontend: a normal `$registry.register('view', new GanttViewType(context))`). **Run tests in the default profile — NOT `.env.oss-test`** (there is no premium override to dodge). [Source: models.py TimelineView clean-room guards exist only for premium co-load; apps.py premium gate; no premium gantt confirmed by grep]
2. **Frappe Gantt lazy-loaded SVG render replaces the plain-DOM bar layer.** Add `frappe-gantt@^1.2.2` to `web-frontend/package.json`. **Lazy-load it** with the cached-promise dynamic-`import()` pattern already used for `xlsx` (`web-frontend/modules/database/utils/excel.js:4 xlsxPromise = import('xlsx')`) so the lib + its CSS land **only when a Gantt view opens** (NFR-2 / SM-C3 ≤400KB gzip added bundle). [Source: architecture.md:79 NFR-2 bundle budget; architecture.md:143 "Frappe Gantt lazy-loaded only on routes that need them"; excel.js:4 cached-promise lazy pattern]

### What this story IS — render only

- A new selectable **"Gantt" view type** with the same configuration UX as Timeline (map start + end Date Fields, day/week/month zoom).
- Scheduled rows drawn by Frappe Gantt as bars on a time axis, **with the library's dependency-connector layer present** (the renderer is fed a `dependencies` array). In 3.8 that array is **empty** (no dependencies exist yet) — you wire the **seam**, not the data.
- Filters/sorts/field-visibility/zoom behavior matching Timeline (inherited from the same `bufferedRows` listing + persisted `view_mode`).
- Unscheduled rows (missing start or end) listed in a tray, not drawn as malformed bars (same rule as Timeline AC #4).

### What this story is NOT (hard scope fence — defer, do not build)

- ❌ **Defining task dependencies** (drawing predecessor→successor edges, persisting a `TaskDependency` model, cycle prevention) — that is **Story 3.9 (Bucket B)**. 3.8 renders the dependency **layer** from an (empty-for-now) dependencies array; it does **not** add the `TaskDependency` model, a draw-dependency interaction, or cycle detection. **Leave the `dependencies` mapping as a clean seam** (a computed returning `[]` today, swappable for real edges in 3.9). [Source: epics.md:590-604 Story 3.9; architecture.md:118 D8 TaskDependency]
- ❌ **Cascade / prompt-first reschedule** when a predecessor moves — **Story 3.10**. [Source: epics.md:606-625]
- ❌ **Milestones + CPM critical path** (zero-duration diamonds, forward/backward pass, zero-slack highlight) — **Story 3.11**. Do not add a CPM engine. [Source: epics.md:627-647]
- ❌ **Interactive bar drag-to-reschedule on the Gantt.** Frappe Gantt ships built-in drag/resize handlers (`on_date_change`). AR-4 says the lib is used **"drawing bars/connectors only"** — keep it render-only in 3.8: do **not** wire `on_date_change`/`on_progress_change` to a write path (Timeline already owns drag in 3.7; Gantt reschedule + cascade is the 3.10 surface). Disable interactivity via the library's read-only path (see Dev Notes "Frappe Gantt 1.2.2 API"). [Source: architecture.md:97 AR-4 "render-only"; epics.md:588]
- ❌ Reading anything under `premium/` or `enterprise/`.

## Acceptance Criteria

1. **Given** a Table with start and end Date Fields, **When** an editor adds a **Gantt View** and maps them (selects `start_date_field` and `end_date_field`), **Then** the view persists and reopens with the same configuration (both mapped date fields, selected zoom level) and honors existing View **filters, sorts, and field visibility** — identical config/persistence semantics to the Timeline view. [Source: epics.md:582-588 "bars render like Timeline (Story 3.6)"; 3-6 AC #1]
2. **And** each Row whose **start and end** Date Fields **both** have a value renders as a **bar on the horizontal time axis drawn by the Frappe Gantt renderer** (start → bar left, end → bar right); Rows **missing** a start or end value are listed in an **unscheduled tray** and are **NOT** drawn as malformed bars. [Source: epics.md:586 "bars render like Timeline"; 3-6 AC #2/#4 tray rule]
3. **And** a **dependency layer is overlaid** on the bars: the renderer is fed a `dependencies` array and draws connector lines for it. In this story the array is **empty** (no dependencies exist until Story 3.9), so **no connectors are drawn yet**, but the seam is present and a non-empty array would render connectors. [Source: epics.md:586 "with a dependency layer overlaid"; 3.9 owns the data]
4. **And** **day / week / month zoom** is selectable from the view header and **persists** across reload (mapped to the Frappe Gantt `view_mode`), and **filter/sort** behavior matches Timeline. [Source: epics.md:587 "zoom and filter/sort behavior match Timeline"; FR-8 line 37]
5. **And** the render uses the **Frappe Gantt lazy-loaded renderer** (`frappe-gantt@^1.2.2`, MIT) — the heavy lib + its CSS load **only when a Gantt view is opened** (dynamic `import()`), not on the landing route, honoring the bundle budget (NFR-2/SM-C3). The view honors **field permissions** (Epic 1): fields the user cannot view are absent from bar/row content; `start_date_field`/`end_date_field` driving layout stay visible to the layout regardless of card-face `hidden`. [Source: architecture.md:97 AR-4, 143 lazy-load, 79 NFR-2; epics.md:474 "All views honor Epic 1 field permissions"; 3-6 AC #5]

## Tasks / Subtasks

### Task 1 — Backend model + migration (AC: #1, #2, #4)

- [x] Add `GanttView(View)` to `backend/src/baserow/contrib/database/views/models.py`, mirroring `TimelineView` (models.py:916-970) **but WITHOUT the clean-room collision guards** (no premium GanttView co-loads):
  - [x] `view_ptr` OneToOne with `related_name="gantt_view"` (plain, not `core_*`); `field_options` M2M through `GanttViewFieldOptions`; **standard** `Meta.db_table` (let Django default to `database_ganttview`, or set it explicitly — do NOT prefix `core`). Do **not** copy TimelineView's E304/E305 collision docstring — it does not apply here.
  - [x] `start_date_field` — `ForeignKey('database.Field', on_delete=SET_NULL, null=True, blank=True, related_name='gantt_view_start_date_field')`. Positions the **left** edge of each bar.
  - [x] `end_date_field` — same shape, `related_name='gantt_view_end_date_field'`. Positions the **right** edge. Both nullable/optional (a Gantt view can exist before both are mapped; a Row missing either goes to the tray, AC #2).
  - [x] `timescale` — `models.CharField(max_length=8, choices=[("day","day"),("week","week"),("month","month")], default="month")`. The **persisted zoom level** (AC #4), mapped to Frappe Gantt `view_mode` on the frontend. Mirror Timeline's persisted `timescale` exactly.
- [x] Add `GanttViewFieldOptions(HierarchicalModelMixin, models.Model)` + its `Manager`, mirroring `TimelineViewFieldOptions` (models.py:972-1005): FK `gantt_view`, FK `field`, `hidden` (default True), `order` (SmallIntegerField default 32767), `Meta.ordering=('order','field_id')`, `unique_together`/`get_parent`. **Standard** table name `database_ganttviewfieldoptions` (no `core` prefix).
- [x] Generate the next sequential migration (`python -m … makemigrations database` — it will be `0223_*` or higher; **do not hard-code the number**, run makemigrations and use what it produces). Include the `timescale` column. Verify with `just b migrate --check` / inspect the autogenerated file (no manual SQL). [Source: 3-6 Task 1; migrations dir]

### Task 2 — Backend `GanttViewType` (AC: #1, #2, #4, #5)

- [x] Add `GanttViewType(ViewType)` to `view_types.py`, mirroring `TimelineViewType` (view_types.py:1181-~1320):
  - [x] `type = "gantt"`, `model_class = GanttView`, `field_options_model_class = GanttViewFieldOptions`, `field_options_serializer_class = GanttViewFieldOptionsSerializer`.
  - [x] `allowed_fields = ["start_date_field", "end_date_field", "timescale"]`, `field_options_allowed_fields = ["hidden", "order"]`, `serializer_field_names = ["start_date_field", "end_date_field", "timescale"]` with the two `PrimaryKeyRelatedField` date-FK overrides (`required=False, default=None, allow_null=True`) + the `timescale` `ChoiceField` (choices day/week/month, default `"month"`) — **copy the Timeline override block** (view_types.py:1188-1216).
  - [x] `prepare_values`: validate `start_date_field`/`end_date_field` (when provided) are **date-representable** (`field_type.can_represent_date(field)`) and **belong to the same table** (`field.table_id == table.id`), iterating `("start_date_field","end_date_field")` exactly as Timeline does (view_types.py:1230-1250). Reject with `IncompatibleField → ERROR_INCOMPATIBLE_FIELD` / `FieldNotInTable → ERROR_FIELD_NOT_IN_TABLE`. The serializer `ChoiceField` validates `timescale`. **Do NOT hard-code field class names** — use the `can_represent_date` registry capability.
  - [x] `get_visible_field_options_in_order` / `get_hidden_fields`: keep `start_date_field_id` **and** `end_date_field_id` **always visible** even when `hidden=True` (AC #5 data-dependency guard) — mirror Timeline. [Source: view_types.py TimelineViewType hidden-fields guard]
  - [x] `after_field_delete` + `after_fields_type_change`: null `start_date_field_id`/`end_date_field_id` on views referencing a deleted or no-longer-date-representable field (SET_NULL only fires on hard delete — add the explicit handlers as Timeline does). [Source: view_types.py:1264-1280 TimelineViewType after_fields_type_change]
  - [x] Export/import: round-trip `start_date_field`, `end_date_field`, `timescale`, and `field_options` (mirror Timeline export/import; do **not** forget `timescale`).
  - [x] `can_share = True`, `has_public_info = True`, `can_decorate = True` — match Timeline's flags. `get_api_urls` → `path("gantt/", include(gantt api urls, namespace=self.type))`.

### Task 3 — Backend API (AC: #1, #2)

- [x] Create `backend/src/baserow/contrib/database/api/views/gantt/` mirroring `.../api/views/timeline/` (`__init__.py`, `urls.py`, `views.py`, `serializers.py`, `errors.py`, `pagination.py`):
  - [x] `GanttViewFieldOptionsSerializer` exposing `("hidden", "order")`.
  - [x] Rows listing endpoint reusing the **inherited bufferedRows** listing (same as Timeline/Calendar — list all rows honoring filters/sorts/field-visibility; the **frontend** maps rows → Frappe Gantt tasks and partitions the tray). **No per-window date-range query param** in v1.
  - [x] **Reuse** the shared `PATCH /api/database/views/{id}/field_options/` and the generic `PATCH /api/database/views/{id}/` (carries `start_date_field`/`end_date_field`/`timescale` via `allowed_fields`). No gantt-specific config endpoint. [Source: 3-6 Task 3]

### Task 4 — Backend registration (AC: #1)

- [x] In `apps.py`, import `GanttViewType` and register it **unconditionally** — `view_type_registry.register(GanttViewType())` next to Grid/Gallery/Form (the **un-gated** registrations), **NOT** inside the `if "baserow_premium" not in settings.INSTALLED_APPS:` block (that gate exists only to dodge premium overrides, which Gantt has none of). [Source: apps.py registration; delta-from-Timeline note above]

### Task 5 — Frontend view type + lazy-loaded Frappe Gantt renderer (AC: #1, #2, #3, #4, #5)

- [x] **Add the dependency:** `frappe-gantt@^1.2.2` to `web-frontend/package.json` (MIT). Do **not** import it statically anywhere that loads on the landing route.
- [x] Add `GanttViewType` to `web-frontend/modules/database/viewTypes.js` extending `BaseBufferedRowViewTypeMixin(ViewType)`, mirroring `TimelineViewType` (viewTypes.js:1447-1534): `getType()='gantt'`, `getIconClass()` (see icon note below), `getColorClass()` (pick an unused color class, e.g. `color-neutral`/reuse Timeline's `color-success` — verify the class exists), `getName()` → `i18n.t('viewType.gantt')`, `getHeaderComponent()`/`getComponent()`, `canFilter/canSort/canShare/canShowRowModal = true`, `getDefaultFieldOptionValues()` `{hidden:true, order:maxPossibleOrderValue}`, and `afterFieldUpdated`/`afterFieldDeleted` nulling `start_date_field`/`end_date_field` via `_setFieldToNull` (mirror Timeline).
- [x] **Icon:** there is **no** `baserow-icon-gantt` glyph (only `calendar.svg`, `timeline.svg` exist under `web-frontend/modules/core/assets/icons/`). Either (a) add a `gantt.svg` glyph + register it in the icon font (`web-frontend/modules/core/assets/scss/icons.scss` / `variables.scss`, mirroring how `timeline` is registered) and use `baserow-icon-gantt`, or (b) **reuse `baserow-icon-timeline`** if adding a glyph is heavy. **Verify the chosen icon class exists in the icon map before use** (3-4/3-6 verified `baserow-icon-calendar`/`-timeline`). Prefer (a) for UX clarity; (b) is an acceptable fallback. [Source: icon dir listing; 3-6 Task 5 icon-verify note]
- [x] `GanttView.vue` (`web-frontend/modules/database/components/view/gantt/`): **lazy-load and drive Frappe Gantt.**
  - [x] **Lazy import** via a module-level cached promise mirroring `excel.js`: `let ganttLibPromise; const loadGantt = () => (ganttLibPromise ??= import('frappe-gantt'))`. Also import the lib CSS lazily (`import('frappe-gantt/dist/frappe-gantt.css')` or the path the installed `1.2.2` ships — **verify the exact dist path** in `node_modules/frappe-gantt/` after install). Load in `mounted()`/when the view becomes active, never at module top level. [Source: excel.js:4; architecture.md:143 lazy-load]
  - [x] Computeds (reuse the core **Timeline** partition + date parsing — import the pure helpers from the Timeline component/util if exported, else re-derive the same logic; do NOT fork a second copy if a shared export exists):
    - `scheduledRows` / `unscheduledRows` — partition `rows`: scheduled only when **both** `start_date_field` and `end_date_field` are non-null (AC #2); otherwise tray.
    - `ganttTasks` — map each `scheduledRow` → a Frappe Gantt task `{ id: String(row.id), name: <primary/visible field value>, start: <YYYY-MM-DD>, end: <YYYY-MM-DD>, progress: 0, dependencies: '' }`. Parse start/end with the bundled `moment` in the **user timezone** (`getUserTimeZone()`, never `moment.utc` for positioning — same lesson as 3.5/3.6). Frappe Gantt expects `YYYY-MM-DD` (or `YYYY-MM-DD HH:mm:ss`) strings.
    - `dependencies` (the AC #3 seam) — a computed that returns the dependency edges per task. **Today it returns empty** (`''` per task / no edges). Structure it so Story 3.9 swaps in real `TaskDependency` edges (`dependencies: 'predecessorId,...'`) without touching the render call. Add a code comment marking this the 3.9 seam.
  - [x] **view_mode mapping:** map `timescale` → Frappe Gantt `view_mode` (`day→'Day'`, `week→'Week'`, `month→'Month'`). On `timescale` change, call the instance's `change_view_mode(...)` (or re-render) — verify the exact 1.2.2 method name (`change_view_mode` in 1.x).
  - [x] **Render-only:** instantiate `new Gantt(svgEl, ganttTasks, options)` into a `ref`'d container. Set the library's **read-only** option so bars are not interactively draggable (verify the 1.2.2 option — see Dev Notes; if `readonly` is unsupported in 1.2.2, leave `on_date_change`/`on_progress_change` **unwired / as no-ops**). Wire `on_click(task)` → open the row modal (`canShowRowModal`) reusing the existing row-modal path (mirror Timeline's `rowClick`). **Do not** wire any write/drag path (that is 3.10).
  - [x] **Re-render discipline:** rebuild/refresh the Gantt instance when `ganttTasks`, `dependencies`, or `view_mode` change (watch them). Destroy/clean up the instance + remove listeners in `beforeUnmount` to avoid leaks (3.7 added a `beforeUnmount` leak-guard for the same reason).
  - [x] Render the **unscheduled tray** with the shared `RowCard` (reuse Timeline's tray markup/computeds — `cardFields`/`hiddenFields`/`coverImageField`). Do **not** fork `RowCard`/`ViewFieldsContext`.
  - [x] Reuse `bufferedRows`/virtual-scroll for the row data (NFR-2) — same as Timeline.
- [x] `GanttViewHeader.vue`: start-date + end-date pickers (date-representable fields only), a **day/week/month zoom** control (writes `timescale` via generic `view/update` so it round-trips, AC #4), and a **"Customize cards"** trigger rendering the shared `ViewFieldsContext`. **Guard every config/option dispatch** with `this.readOnly || !this.$hasPermission('database.table.view.update_field_options', view, workspaceId)` exactly as Timeline/Calendar. Mirror `TimelineViewHeader.vue`.
- [x] `store/view/gantt.js`: clone `store/view/timeline.js` — `bufferedRows({ service: GanttService })`, `fetchInitial` with `includeFieldOptions:true` → `forceUpdateAllFieldOptions`. (You do **not** need the `dragging:false` pre-seed Timeline added for 3.7 — Gantt is render-only. Omit it, or keep a minimal `populateRow` returning `row._ = { metadata }`.)
- [x] `services/view/gantt.js`: clone `services/view/timeline.js` → `bufferedRowService(client, 'gantt')`.
- [x] Register the store module in `web-frontend/modules/database/plugin/store.js` and the view type in `web-frontend/modules/database/plugin.js`: `$registry.register('view', new GanttViewType(context))` — **plain registration**, next to Timeline/Calendar (no last-wins gating needed; no premium override).
- [x] Add `viewType.gantt` to `web-frontend/locales/en.json` and `ganttView*`/`ganttViewHeader*` keys to `web-frontend/modules/database/locales/en.json`.
- [x] Add `web-frontend/modules/core/assets/scss/components/views/gantt.scss` (BEM `.gantt-view__*`: container, svg host, tray) and import it in `.../scss/components/all.scss`. **Do not** restyle Frappe Gantt's internal SVG beyond container layout — let the lib own bar/connector styling; import its CSS (lazily) for that.

### Task 6 — Backend tests (AC: #1, #2, #4, #5) — DEFAULT profile (NOT oss-test)

- [x] `backend/tests/baserow/contrib/database/view/test_gantt_view_type.py` (mirror `test_timeline_view_type.py`):
  - [x] create a gantt view; set `start_date_field`/`end_date_field` to Date fields → accepted+persisted; either to a non-date field → `IncompatibleField`; a date field from another table → `FieldNotInTable`.
  - [x] `timescale` persists and round-trips; an invalid choice is rejected.
  - [x] `start_date_field_id`/`end_date_field_id` nulled when the referenced field is (soft-)deleted (`after_field_delete`) and when it changes to a non-date type (`after_fields_type_change`).
  - [x] `get_hidden_fields` excludes `start_date_field_id`/`end_date_field_id` even when their option is `hidden=True` (AC #5).
  - [x] export/import round-trips `start_date_field`, `end_date_field`, `timescale`, `field_options`.
- [x] `backend/tests/baserow/contrib/database/api/views/gantt/test_gantt_view_views.py` (mirror `test_timeline_view_views.py`): list rows (honors filters/sorts/field-visibility), `PATCH .../{id}/` with the three config fields persists + returns on GET, `PATCH .../{id}/field_options/` `{hidden:true}`/`{order:N}` persist.
- [x] Add a `gantt` fixture to `backend/src/baserow/test_utils/fixtures/view.py` (mirror the timeline fixture).
- [x] Run in the **default** profile (NOT `.env.oss-test` — no premium Gantt to dodge): `just b test backend/tests/baserow/contrib/database/view/test_gantt_view_type.py backend/tests/baserow/contrib/database/api/views/gantt/test_gantt_view_views.py`. If `just` is absent, use the direct `uv run pytest` recipe from Dev Notes. Expect green.

### Task 7 — Frontend unit tests (AC: #2, #3, #4) — method/computed-level, mock Frappe Gantt

- [x] `web-frontend/test/unit/database/components/view/gantt/ganttView.spec.js`. **Do NOT mount `GanttView` and do NOT instantiate the real Frappe Gantt lib in jsdom** (it manipulates real SVG/DOM and will fail/leak). Use the **method/computed-level** pattern (bind real computeds to a minimal fake `vm`), and where the render call is exercised, **mock the `frappe-gantt` dynamic import** (`vi.mock('frappe-gantt', ...)`).
  - [x] `scheduledRows`/`unscheduledRows` partition by **both** start AND end non-null (missing either → tray). (AC #2)
  - [x] `ganttTasks` maps a scheduled row → `{id,name,start,end,...}` with `start`/`end` formatted `YYYY-MM-DD` parsed in the user timezone (assert the string shape; assert a date-only value does not drift a day). (AC #2)
  - [x] `dependencies` seam returns **empty** today (assert no edges) — documents the 3.9 seam. (AC #3)
  - [x] `timescale` → `view_mode` mapping (`day→Day`, `week→Week`, `month→Month`); header zoom change dispatches `view/update` with `{timescale}`; date-field pickers dispatch `{start_date_field}`/`{end_date_field}`; option dispatches carry the `readOnly`/permission guard. (AC #4/#5)
- [x] Run: `yarn vitest run web-frontend/test/unit/database/components/view/gantt/`. Expect green.

### Task 8 — E2E scenario (AC: #1, #2, #4) — author only

- [x] Add `e2e-tests/tests/database/gantt_view.spec.ts` + a `createGanttView` fixture in `e2e-tests/fixtures/database/view.ts` (mirror the timeline fixture/spec). Scenario: create a Table with start+end Date fields and rows (some fully dated, one missing end), add a Gantt view, map both date fields → fully-dated rows render as Frappe Gantt bars (assert the `.gantt`/`.bar` SVG nodes the lib emits), the row missing end appears in the tray (not as a bar); change zoom day↔week↔month; reload → config (both fields + zoom) persists.
- [x] **Do NOT run E2E locally** (needs the Docker stack; `e2e-tests/` has no local tsconfig/node_modules). Author only. Format `.ts` with `web-frontend/node_modules/.bin/prettier`. [Source: 3-6 Task 8]

### Task 9 — Verify bundle/lazy-load (AC: #5)

- [x] Confirm `frappe-gantt` is **not** statically imported on any landing-route module — it is reached only through the cached dynamic `import()` in `GanttView.vue`. Grep the bundle/import graph: `grep -rn "frappe-gantt" web-frontend/modules` should show **only** the lazy `import('frappe-gantt')` (and the spec mock), never a top-level `import ... from 'frappe-gantt'`. Note the result in Dev Notes (the SM-C3 budget is validated with the heavy code actually loaded; a full bundle-size measurement is CI/perf-story scope, but the lazy-only invariant is enforceable here). [Source: architecture.md:79 SM-C3, 143 lazy-load]

### Task 10 — Bucket B provenance / third-party attribution (recommended hygiene, NOT a CI gate) (AC: all)

- [x] Add `docs/clean-room/provenance/3-8-render-a-gantt-view.md` declaring **Bucket B**: third-party render lib **Frappe Gantt 1.2.2 (MIT)**; view spine derived from the **core MIT Timeline (3.6)** + core Calendar/Kanban precedents + shared `RowCard`/`ViewFieldsContext` + core `utils/date.js`/bundled `moment`; **no `premium/`/`enterprise/` source read**. Mirror the 3-6 provenance structure (sources list + attestation). **Do NOT add the `bucket-a` label** — the hard CI provenance gate (`check_provenance.py`) fires only on `bucket-a` and must stay green/untriggered for this PR. This record is license-hygiene documentation, not the gate. [Source: docs/clean-room/scripts/check_provenance.py:10-13 gate scope; docs/clean-room/merge-gate.md]

### Task 11 — Lint + changelog + verify (AC: all)

- [x] Ruff (`check` + `format`) on backend Python; ESLint + Prettier on `.vue`/`.js` (invoke ESLint from **repo root** via `web-frontend/node_modules/.bin/eslint` — fails with "No files matching" from inside `web-frontend/`); Stylelint on `gantt.scss`; e2e `.ts` matches existing style. [Source: 3-6 Task 10 ESLint-from-root note]
- [x] Add a changelog entry if the repo requires one for new view types (check `changelog/` / `docs` convention; mirror what 3.6 did or omit if not required). [Source: AGENTS.md "add a changelog entry when required"]
- [x] `just b run pre-commit run --files $(git diff --name-only origin/develop...HEAD)` (or run linters directly if `just`/`pre-commit` absent). [Source: AGENTS.md code-quality]

## Dev Notes

### Architecture patterns & constraints

- **View-type spine.** A core view = backend `ViewType` + `View` subclass model + `*FieldOptions` model + migration + `api/views/<type>/` package + `apps.py` registration; frontend = `ViewType` class in `viewTypes.js` + `<Type>View.vue` + `<Type>ViewHeader.vue` + `store/view/<type>.js` + `services/view/<type>.js` + `plugin.js`/`plugin/store.js` registration + i18n + SCSS. Every piece has a **Timeline (3.6)** precedent — clone it, applying the two deltas (standard table/registration; Frappe Gantt render). [Source: architecture.md:279,302-303; 3-6 Dev Notes]
- **Reuse, do not fork:** `RowCard.vue` (tray content), `ViewFieldsContext.vue` (Customize-cards), `bufferedRows`/`fieldOptions` store factories, `utils/date.js` + bundled `moment` (date parsing), and the **core Timeline** partition/parse logic. Forking any of these is the "reinventing wheels" failure mode. [Source: 3-6 Dev Notes]
- **Filters/sorts/field-visibility (AC #1/#4)** come free from the `View` base + `bufferedRows` listing — verify, don't re-add.
- **Field permissions (AC #5)** are enforced by Epic 1's central layer at the row/serializer level; Gantt's only extra responsibility is the data-dependency guard in `get_hidden_fields` keeping start/end date fields visible. [Source: 3-6 Dev Notes; Epic 1 stories 1.4/1.5]
- **Performance (NFR-2 / SM-C3):** reuse virtual-scroll `bufferedRows` for row data; **lazy-load Frappe Gantt** (cached dynamic import) so the heavy SVG lib + CSS never hit the landing route. [Source: architecture.md:79,143]

### The two deltas from Timeline (do not over-clone)

1. **Standard table names + unconditional registration.** Timeline's `database_coretimelineview` table, `core_timeline_view*` reverse accessors, premium-gated backend registration, and frontend last-wins all exist **solely because a premium Timeline co-loads**. Gantt has **no** premium twin (`grep -rn gantt premium/ enterprise/` → none relevant). So: plain `database_ganttview*` tables, plain `gantt_view*` accessors, **unconditional** backend registration (outside the premium gate), plain frontend registration, and tests run in the **default** profile (no `.env.oss-test`). Copying Timeline's collision guards here would be cargo-culting.
2. **Frappe Gantt replaces the plain-DOM bar layer.** Timeline draws bars as positioned `<div>`s and owns its own `barStyle`/`ticks`/axis math. Gantt **delegates** bar X/width + the axis + the dependency connectors to the Frappe Gantt SVG renderer — you feed it `tasks` (`{id,name,start,end,dependencies}`) + `view_mode` and it draws. You keep only the **scheduled/unscheduled partition** and the **user-timezone date parsing**; you do NOT need the px geometry.

### Frappe Gantt 1.2.2 API (verify against the installed package)

Frappe Gantt is MIT, ~zero-dep, ~50kB. Construct with `new Gantt(wrapperElementOrSelector, tasks, options)`:
- `tasks`: `[{ id: 'Task 1', name: '…', start: 'YYYY-MM-DD', end: 'YYYY-MM-DD', progress: 0, dependencies: 'idA,idB' }]`. **`dependencies` is a comma-separated string of predecessor task ids** — this is exactly the AC #3 seam (empty in 3.8, populated by 3.9's `TaskDependency` graph).
- `options`: `{ view_mode: 'Day'|'Week'|'Month'|…, date_format: 'YYYY-MM-DD', on_click, on_date_change, on_progress_change, … }`. Instance methods include `change_view_mode(mode)` and `refresh(tasks)`.
- **Read-only / render-only:** AR-4 mandates render-only. Newer Frappe Gantt exposes a `readonly` (or `readonly_dates`/`readonly_progress`) option — **but 1.2.2 may not**. **Verify in `node_modules/frappe-gantt/` after install.** If a read-only flag exists, use it; if not, **leave `on_date_change`/`on_progress_change` unwired (no-ops)** so a drag has no persisted effect (Gantt reschedule + cascade is Story 3.10). Do not wire any write path in 3.8.
- **CSS:** the bars/connectors need the lib's stylesheet. Import it **lazily** alongside the JS (`import('frappe-gantt/dist/frappe-gantt.css')` — verify the exact dist filename in the installed 1.2.2). Do not inline-reimplement the lib's SVG styles.
- Pin `^1.2.2` to match the architecture decision (D2, AR-4). If a newer 1.x is installed by the resolver, confirm the `view_mode`/`dependencies`/read-only API still matches before relying on it. [Source: architecture.md:97 AR-4, 111 D2]

### Date parsing (reuse the Timeline lesson)

Parse start/end with bundled `@baserow/modules/core/moment` in `getUserTimeZone()` — **never `moment.utc` for positioning** — so date-only fields (`YYYY-MM-DD`) do not drift a day across DST/offset, then format back to `YYYY-MM-DD` for Frappe Gantt. This is the exact lesson 3.5/3.6 learned (`rowDateKey`/`parseTimelineValue`). `BaseDateFieldType.formatValue` canonical cell shape: `date_include_time ? moment.utc(v).format() : moment.utc(v).format('YYYY-MM-DD')` — read as-is, parse for positioning in the local frame. [Source: 3-6 Dev Notes "net-new logic: bar geometry"; fieldTypes.js BaseDateFieldType.formatValue]

### Scheduled vs tray (AC #2) — same rule as Timeline

A Row is a Gantt **bar** only if **both** `start_date_field` and `end_date_field` have values. Missing either → **tray** (not a malformed/zero-width bar). Unit-test the "missing end → tray" case explicitly.

### The dependency-layer seam (AC #3) — wire it, don't fill it

3.8 renders the dependency **layer** (Frappe Gantt draws connectors from each task's `dependencies` string), but **no dependencies exist** until Story 3.9 adds the `TaskDependency` model + draw interaction + cycle prevention. So the `dependencies` computed returns **empty** today. Make it a single, clearly-commented seam (`// Story 3.9 swaps in real TaskDependency edges here`) so 3.9 is a localized change, not a render rewrite. Do **not** add a `TaskDependency` model, a CPM engine, milestones, or cascade logic in this story. [Source: epics.md:590-647 Stories 3.9/3.10/3.11; architecture.md:118 D8]

### Persistence model (AC #1/#4) — two PATCH paths, both pre-existing

- **View config** (`start_date_field`, `end_date_field`, `timescale`) → generic `PATCH /api/database/views/{id}/` (all three in `allowed_fields`; `prepare_values` validates the date fields, serializer `ChoiceField` validates `timescale`). Re-hydrated on reopen.
- **Card face** (`hidden`/`order`) → shared `PATCH /api/database/views/{id}/field_options/`; re-hydrated by `fetchInitial` (`includeFieldOptions:true`). Both round-trip through export/import. [Source: 3-6 persistence model]

### Default-profile test execution (the delta from Timeline)

Timeline tests ran OSS-only (`.env.oss-test`) to force the **core** Timeline to win over premium's last-registration override. **Gantt has no premium override**, so run in the **default** profile. Direct recipe if `just` is absent: `PYTHONPATH=src:../premium/backend/src:../enterprise/backend/src DATABASE_URL=postgres://baserow:baserow@localhost:5431/baserow-test-db uv run pytest <paths>` (no `TEST_ENV_FILE`). Frontend: `yarn vitest run`. [Source: 3-6 Debug Log recipe, minus the oss-test flag]

### Anti-patterns (forbidden)

- ❌ Opening/reading/adapting anything under `premium/` or `enterprise/` (license hygiene — irrelevant to Gantt anyway; the premium Timeline is not your reference). [Source: memory baserow-open-core-license-constraint]
- ❌ Cargo-culting Timeline's clean-room collision guards (`core_*` table/accessors, premium-gated registration, `.env.oss-test`) onto Gantt — there is no premium Gantt to collide with. Use standard names + unconditional registration + default-profile tests.
- ❌ **Static-importing `frappe-gantt`** anywhere on the landing route — it MUST be a cached dynamic `import()` (SM-C3 budget). [Source: architecture.md:143]
- ❌ Wiring Frappe Gantt's `on_date_change`/`on_progress_change` to a write path — render-only in 3.8; reschedule + cascade is Story 3.10. [Source: architecture.md:97 AR-4]
- ❌ Adding a `TaskDependency` model, CPM engine, milestone markers, or cycle detection — Stories 3.9/3.10/3.11.
- ❌ Forking `RowCard.vue` / `ViewFieldsContext.vue` / `bufferedRows` / `fieldOptions` — reuse them.
- ❌ A bespoke gantt-specific field-options or "set zoom" endpoint — the shared field-options PATCH + generic view PATCH (with `timescale` in `allowed_fields`) cover it.
- ❌ Making `timescale` ephemeral client state — AC #4 requires persistence (mirror Timeline's persisted column).
- ❌ Rendering Rows missing start or end as zero/negative-width bars — they go to the tray (AC #2).
- ❌ Reimplementing Frappe Gantt's SVG bar/connector drawing in custom DOM — the whole point of D2/AR-4 is to delegate rendering to the lib.
- ❌ Instantiating the real Frappe Gantt lib inside a jsdom unit test (real SVG/DOM → failure/leak) — mock the dynamic import; test computeds/methods only.
- ❌ Marking a task `[x]` without the cited verification / passing test ("lying about completion").

### Project Structure Notes

**New files (core):**
- `backend/src/baserow/contrib/database/migrations/0223_ganttview_ganttviewfieldoptions.py` *(actual number from `makemigrations` — do not hard-code)*
- `backend/src/baserow/contrib/database/api/views/gantt/{__init__,urls,views,serializers,errors,pagination}.py`
- `web-frontend/modules/database/components/view/gantt/GanttView.vue`
- `web-frontend/modules/database/components/view/gantt/GanttViewHeader.vue`
- `web-frontend/modules/database/store/view/gantt.js`
- `web-frontend/modules/database/services/view/gantt.js`
- `web-frontend/modules/core/assets/scss/components/views/gantt.scss`
- `web-frontend/modules/core/assets/icons/gantt.svg` *(if adding a distinct glyph; else reuse `baserow-icon-timeline`)*
- `backend/tests/baserow/contrib/database/view/test_gantt_view_type.py`
- `backend/tests/baserow/contrib/database/api/views/gantt/test_gantt_view_views.py`
- `web-frontend/test/unit/database/components/view/gantt/ganttView.spec.js`
- `e2e-tests/tests/database/gantt_view.spec.ts`
- `docs/clean-room/provenance/3-8-render-a-gantt-view.md` *(Bucket B hygiene record)*

**Modified files (core):**
- `backend/src/baserow/contrib/database/views/models.py` (+`GanttView`, `GanttViewFieldOptions`, manager)
- `backend/src/baserow/contrib/database/views/view_types.py` (+`GanttViewType`)
- `backend/src/baserow/contrib/database/apps.py` (register `GanttViewType` **unconditionally**)
- `backend/src/baserow/test_utils/fixtures/view.py` (gantt fixture)
- `web-frontend/package.json` (+`frappe-gantt@^1.2.2`)
- `web-frontend/modules/database/viewTypes.js` (+`GanttViewType`)
- `web-frontend/modules/database/plugin.js` (register gantt view — plain)
- `web-frontend/modules/database/plugin/store.js` (register gantt store module)
- `web-frontend/modules/database/locales/en.json` (`ganttView*`, `ganttViewHeader*`)
- `web-frontend/locales/en.json` (`viewType.gantt`)
- `web-frontend/modules/core/assets/scss/components/all.scss` (import `gantt.scss`)
- `web-frontend/modules/core/assets/scss/{icons,variables}.scss` (register `gantt` glyph — only if adding `gantt.svg`)
- `e2e-tests/fixtures/database/view.ts` (`createGanttView` fixture)

Naming follows existing conventions; **standard** table prefix `database_ganttview...` (NO `core` prefix); `.vue` PascalCase, methods camelCase, BEM SCSS. [Source: architecture.md:192,279; AGENTS.md Coding Style]

### References

- [Source: epics.md:576-588 (Story 3.8)] — user story + AC: Gantt view, bars render like Timeline, dependency layer overlaid, zoom + filter/sort match Timeline, Frappe Gantt lazy-loaded renderer drawing bars/connectors only.
- [Source: epics.md:37 FR-8] — "Render a Gantt View — map start/end Date Fields, task bars on time axis with dependency layer; zoom/filter/sort match Timeline."
- [Source: epics.md:174,474] — Gantt is **Bucket B**; all views honor Epic 1 field permissions.
- [Source: epics.md:590-647 (Stories 3.9/3.10/3.11)] — scope fence: dependencies + cycle prevention (3.9), cascade/prompt reschedule (3.10), milestones + CPM (3.11) are NOT this story.
- [Source: architecture.md:97 AR-4; :111 D2] — Frappe Gantt 1.2.2 (MIT), render-only; dependencies/CPM/cascade computed in backend (D8); DHTMLX rejected (GPLv2).
- [Source: architecture.md:79 NFR-2 (SM-C3 ≤400KB gzip); :143 "Frappe Gantt lazy-loaded only on routes that need them"] — bundle budget + lazy-load mandate.
- [Source: architecture.md:25,279,282,302-303] — Gantt = Bucket B core `ViewType`; backend `gantt/` package; frontend renderer under `components/view/gantt/` (FrappeGantt lazy).
- [Source: docs/clean-room/scripts/check_provenance.py:10-13,28; docs/clean-room/merge-gate.md] — the hard provenance gate fires **only** on `bucket-a`; Bucket B (this PR) is not gated.
- [Source: 3-6-create-and-configure-a-timeline-view.md] — the immediate clone target: backend model/migration/view-type/API/registration shapes, frontend view-type/components/store/service/locales/SCSS, persisted `timescale`, scheduled-vs-tray partition, method-level no-mount unit pattern, two-PATCH persistence. Clone, applying the two deltas.
- [Source: 3-7-reschedule-and-resize-timeline-bars.md] — `beforeUnmount` leak-guard + `rowClick` suppress pattern (reuse for the Gantt instance lifecycle + on_click).
- [Source: backend/.../views/view_types.py:1181 (TimelineViewType)] — structural template (`allowed_fields`, serializer overrides, `prepare_values` `can_represent_date`+same-table, `get_hidden_fields` guard, `after_field_delete`/`after_fields_type_change`, export/import).
- [Source: backend/.../views/models.py:916-1005 (TimelineView, TimelineViewFieldOptions)] — model + field-options template (drop the clean-room collision guards; use standard table/accessor names).
- [Source: backend/.../views/apps.py] — register `GanttViewType` **outside** the `if "baserow_premium" not in INSTALLED_APPS` gate (unconditional).
- [Source: backend/.../api/views/timeline/*] — API package template to mirror as `.../gantt/`.
- [Source: web-frontend/modules/database/viewTypes.js:1447 (TimelineViewType)] — frontend view-type class template.
- [Source: web-frontend/modules/database/components/view/timeline/{TimelineView,TimelineViewHeader}.vue] — component template (date pickers, zoom control, Customize-cards header, permission guards, tray, local-frame date parse). Replace the plain-DOM bar layer with the Frappe Gantt render.
- [Source: web-frontend/modules/database/store/view/timeline.js; services/view/timeline.js] — bufferedRows store + service clone targets.
- [Source: web-frontend/modules/database/utils/excel.js:4] — cached-promise dynamic-`import()` lazy-load pattern to mirror for `frappe-gantt`.
- [Source: web-frontend/modules/core/utils/date.js] — MIT date helpers + bundled `moment` (`getUserTimeZone()`); parse in local frame, format `YYYY-MM-DD` for Frappe Gantt.
- [Source: web-frontend/modules/database/plugin.js:438] — frontend view registration (plain, no last-wins gate for Gantt).
- [Source: memory clean-room-isolation-porous; memory baserow-open-core-license-constraint] — do not read premium/enterprise; the premium Timeline is not your reference.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (BMAD create-story workflow)

### Debug Log References

- `makemigrations --check` initially failed with "DJANGO_SETTINGS_MODULE not set" → re-ran
  with `DJANGO_SETTINGS_MODULE=baserow.config.settings.dev`. Then hit a **pre-existing**
  core/enterprise `FieldPermission` reverse-accessor clash (`fields.E304/E305`) in the
  full open-core stack — **unrelated to Gantt** (Gantt uses standard `gantt_view*`
  accessors with no twin). Confirmed harmless: the 22 Gantt backend tests pass in the
  default profile, proving migration `0223` is valid.
- Ruff `I001` import-sort error in `view_types.py` introduced by the added Gantt
  serializer + model imports → fixed via `uv run ruff check --fix
  src/baserow/contrib/database/views/view_types.py` → "All checks passed!"; re-ran the 13
  view-type tests to confirm imports intact.
- `_isUnmounted` was used as the `ensureGantt` async-loader race guard but is **not** a
  valid Vue 3 public instance property (dead guard) → replaced with an explicit
  `isUnmounting` data flag set in `beforeUnmount` before `destroyGantt()`.

### Completion Notes List

- All 5 ACs implemented and verified. Gantt is a **net-new core view-type spine** cloned
  from the 3.6 core Timeline, with the two documented deltas: (1) standard table names
  (`database_ganttview*`) + **unconditional** `apps.py` registration (no premium twin), and
  (2) the plain-DOM bar layer replaced by the **lazy-loaded Frappe Gantt 1.2.2 (MIT)** SVG
  renderer (cached-promise dynamic `import()` of both JS and CSS, mirroring `excel.js`).
- **Render-only (AR-4):** Gantt constructed with `readonly: true`, `popup_on: 'click'`;
  the `popup` hook is repurposed to open the standard row modal (`openTaskRow`) and returns
  `false` to suppress Frappe's own popup. No `on_date_change` write path wired (Story 3.10).
- **AC #3 dependency seam:** `dependenciesForRow()` returns `''` unconditionally — the
  empty-today dependency array Story 3.9 swaps for real `TaskDependency` edges. Commented
  as the 3.9 seam.
- **AC #2 partition:** reuses core `partitionTimelineRows` / `rowDateRange` unchanged — a
  row is a bar only when both start + end date fields carry a value; otherwise the tray.
- **Lazy-load invariant (AC #5):** verified no static `frappe-gantt` import in the tree
  (`grep -rn "frappe-gantt" web-frontend/modules` shows only the cached dynamic `import()`
  and the spec mock).
- **Known third-party limitation (Story 3.10 follow-up):** Frappe Gantt 1.2.2 registers an
  anonymous `document` `mouseup` listener at construction and exposes no `destroy()`, so
  `destroyGantt()` cannot remove it (render-only, harmless here). Documented inline; the
  async-loader race is guarded by the `isUnmounting` flag.
- **Tests:** backend 22/22 (13 view-type + 9 API) in the **default** profile (no
  `.env.oss-test` — no premium override to dodge); frontend unit 30/30 (method/computed
  level, Frappe Gantt mocked). ESLint / Stylelint / Prettier / Ruff clean. E2E authored
  only (needs Docker stack).

### Senior Developer Review (AI)

**Reviewer:** AI adversarial review (bmad-story-automator-review, 2026-06-10)
**Outcome:** APPROVED — 0 CRITICAL → Status `done`.

5 findings, all resolved:

| ID | Sev | Finding | Resolution |
|----|-----|---------|------------|
| M1 | MEDIUM | Story file: empty File List, all tasks `[ ]`, empty Dev Agent Record despite complete implementation | Fixed — File List populated, tasks checked, Dev Agent Record + this review filled, Status → done |
| M2 | MEDIUM | Task 10 Bucket B provenance record missing | Fixed — created `docs/clean-room/provenance/3-8-render-a-gantt-view.md` (Bucket B; Frappe Gantt MIT + core Timeline derivation; no PE/EE read) |
| M3 | MEDIUM | Ruff `I001` import-sort violation in `view_types.py` from the added Gantt imports | Fixed — `ruff check --fix`; re-verified 13 view-type tests pass |
| L1 | LOW | `ensureGantt` guard referenced non-existent Vue 3 `_isUnmounted` (dead guard) | Fixed — explicit `isUnmounting` data flag set in `beforeUnmount` |
| L2 | LOW | Frappe Gantt 1.2.2 anonymous `document` mouseup listener leak (no lib `destroy()`) | Documented inline as a known limitation + Story 3.10 follow-up (render-only, harmless in 3.8) |

Verified: 5/5 ACs genuinely implemented; lazy-load invariant holds; backend 22/22 + frontend 30/30 green; lint clean.

### File List

**New (core):**
- `backend/src/baserow/contrib/database/migrations/0223_ganttview_ganttviewfieldoptions.py`
- `backend/src/baserow/contrib/database/api/views/gantt/{__init__,urls,views,serializers,errors,pagination}.py`
- `web-frontend/modules/database/components/view/gantt/GanttView.vue`
- `web-frontend/modules/database/components/view/gantt/GanttViewHeader.vue`
- `web-frontend/modules/database/store/view/gantt.js`
- `web-frontend/modules/database/services/view/gantt.js`
- `web-frontend/modules/core/assets/scss/components/views/gantt.scss`
- `web-frontend/modules/core/assets/icons/gantt.svg`
- `backend/tests/baserow/contrib/database/view/test_gantt_view_type.py`
- `backend/tests/baserow/contrib/database/api/views/gantt/test_gantt_view_views.py`
- `web-frontend/test/unit/database/components/view/gantt/ganttView.spec.js`
- `e2e-tests/tests/database/gantt_view.spec.ts`
- `docs/clean-room/provenance/3-8-render-a-gantt-view.md`

**Modified (core):**
- `backend/src/baserow/contrib/database/views/models.py` (+`GanttView`, `GanttViewFieldOptions`, manager)
- `backend/src/baserow/contrib/database/views/view_types.py` (+`GanttViewType`)
- `backend/src/baserow/contrib/database/apps.py` (register `GanttViewType` unconditionally)
- `backend/src/baserow/test_utils/fixtures/view.py` (gantt fixture)
- `web-frontend/package.json` + `web-frontend/yarn.lock` (+`frappe-gantt@^1.2.2`)
- `web-frontend/modules/database/viewTypes.js` (+`GanttViewType`)
- `web-frontend/modules/database/plugin.js` (register gantt view — plain)
- `web-frontend/modules/database/plugin/store.js` (register gantt store module)
- `web-frontend/modules/database/locales/en.json` (`ganttView*`, `ganttViewHeader*`)
- `web-frontend/locales/en.json` (`viewType.gantt`)
- `web-frontend/modules/core/assets/scss/components/all.scss` (import `gantt.scss`)
- `web-frontend/modules/core/assets/scss/variables.scss` (register `gantt` glyph)
- `e2e-tests/fixtures/database/view.ts` (`createGanttView` fixture)

QA (bmad-qa-generate-e2e-tests, 2026-06-10) — E2E gap closed:
- `e2e-tests/tests/database/gantt_view.spec.ts` (NEW — 5 scenarios, AC #1/#2/#4/#5)
- `e2e-tests/fixtures/database/view.ts` (added `createGanttView` helper)
- `_bmad-output/implementation-artifacts/tests/3-8-gantt-view-test-summary.md` (NEW)

Verified green: frontend unit 30/30, backend 22/22 (default profile). E2E authored only (Task 8 — needs Docker stack).

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-06-10 | 1.0 | Story 3.8 implemented: Gantt view-type spine (backend model/migration/view-type/API + frontend view-type/components/store/service), lazy-loaded Frappe Gantt 1.2.2 (MIT) render-only SVG renderer, AC #3 dependency seam. | dev-agent |
| 2026-06-10 | 1.1 | Adversarial review (bmad-story-automator-review): 5 findings resolved (M1 story doc, M2 provenance, M3 ruff import-sort, L1 isUnmounting guard, L2 listener-leak doc). Status → done. | review-agent |
