---
baseline_commit: d277a2f1e0e6ad126b34ea1608024df43d438740
---

# Story 3.1: Create and configure a Kanban View

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to add a Kanban View grouped by a Single-select Field,
so that I can see Rows as a board with one column per option plus an "Uncategorized" column for empty values.

## Context & Scope

### 🚨 THIS IS A BUCKET A CLEAN-ROOM STORY — READ FIRST, NON-NEGOTIABLE

Kanban is a **paid feature in upstream Baserow**. A complete implementation already exists under `premium/backend/src/baserow_premium/` and `premium/web-frontend/modules/baserow_premium/`. That code is licensed **PE/EE** and **MUST NOT be copied, adapted, opened, read, or recalled** while implementing this story. The PE/EE license forbids work that is even *"influenced by"* that source. [Source: prd.md §8; architecture.md lines 45, 205, 239–268; memory baserow-open-core-license-constraint]

**Hard rules for the dev agent:**

1. **Do NOT open any file under `premium/` or `enterprise/`.** Not for reference, not "just to check the shape", not for tests. The clean-room gate (Story 1.1, done) treats "influenced by" as contamination. [Source: 1-1-establish-the-clean-room-process-gate.md AC#2, line 60]
2. **Build the free Kanban View in core dirs** (`backend/src/baserow/contrib/database/...`, `web-frontend/modules/database/...`) — **NEVER** in `premium/`/`enterprise/`. [Source: architecture.md line 205]
3. **Build from the public template: the free `GalleryViewType`.** Gallery is already a license-clean, card-based view with `field_options` (hidden/order) and an optional cover-image field. Kanban = Gallery + a `single_select_field` grouping. Derive everything from `GalleryViewType`/`GalleryView` and the public acceptance criteria below — not from the paid Kanban. [Source: backend/src/baserow/contrib/database/views/view_types.py:373; models.py:694]
4. **Attach a provenance record to the PR** (sources consulted = public Baserow MIT core + this story; implementer attestation = no premium/enterprise source read/used/recalled). No provenance → CI merge gate blocks the PR. This is the standard Bucket A definition-of-done. [Source: 1-1-...-clean-room-process-gate.md AC#3; architecture.md lines 239–241]

> The only public symbol name carried over is `single_select_field` (a free-core / public field-model symbol describing the grouping config). Field/view **registry symbol names** are public MIT; **behavior** must be reconstructed from Gallery + the AC. Do not name premium internal symbols as replication targets. [Source: architecture.md line 268]

### Scope of THIS story (3.1 only)

In scope: create a Kanban view, configure its grouping Single-select Field, render columns (one per select option + "Uncategorized" for null), persist + reopen config, and have existing filters/sorts/field-visibility apply.

**Out of scope (later stories — do not build):**
- Drag a card between columns / write-back of the grouping field → **Story 3.2**.
- Card-face field selection + cover image toggle → **Story 3.3**. (You MAY add the nullable `card_cover_image_field` column to the model now to avoid a second migration, but no card-appearance UI here.)
- Realtime broadcast of card moves, optimistic rollback → **Story 3.2** (NFR-1/NFR-3).

This is the first story in Epic 3 ("Visualize Data Multiple Ways"). Epic 3 transitions backlog → in-progress with this story.

## Acceptance Criteria

1. **Given** any Table, **when** an editor adds a Kanban View and chooses a Single-select Field, **then** columns render one per option **plus an "Uncategorized" column** for empty (null) values.
2. **And** existing View filters, sorts, and field visibility apply to the Rows shown on the board.
3. **And** the View persists and reopens with the same configuration (grouping field, filters, sorts, field options).

[Source: epics.md#Epic 3 → Story 3.1, lines 476–488]

## Tasks / Subtasks

### Task 1 — Backend model + migration (AC: #1, #3)
- [x] Add `KanbanView(View)` to `backend/src/baserow/contrib/database/views/models.py`, modeled on `GalleryView` (models.py:694). Fields:
  - [x] `field_options = models.ManyToManyField(Field, through="KanbanViewFieldOptions")`.
  - [x] `single_select_field = models.ForeignKey(Field, blank=True, null=True, on_delete=models.SET_NULL, related_name="kanban_view_single_select_field", help_text=...)` — the grouping field. Nullable so a Kanban view can exist before a field is chosen.
  - [x] (Optional, pre-stage 3.3) `card_cover_image_field` FK mirroring `GalleryView.card_cover_image_field` (models.py:696) — `related_name="kanban_view_card_cover_field"`. No UI this story.
- [x] Add `KanbanViewFieldOptions` + `KanbanViewFieldOptionsManager`, copying the `GalleryViewFieldOptions` shape (models.py:707–741): `kanban_view` FK (CASCADE), `field` FK (CASCADE), `hidden` BooleanField(default=True), `order` SmallIntegerField(default=32767), `get_parent()` returns `self.kanban_view`, `Meta.ordering=("order","field_id")`, `unique_together=("kanban_view","field")`. Manager filters out trashed views/fields via `~(Q(kanban_view__trashed=True)|Q(field__trashed=True))`.
- [x] Generate migration: `just b run python src/baserow/manage.py makemigrations database` → expect `0220_kanbanview_*.py` (next after `0219_runningcountfield_alter_formview_mode.py`). Review it (no per-user-table changes — this is metadata only, dynamic-model pattern). [Source: architecture.md "Data boundaries"]
- [x] `just b migrate`.

### Task 2 — Backend `KanbanViewType` (AC: #1, #2, #3)
- [x] Add `KanbanViewType(ViewType)` to `backend/src/baserow/contrib/database/views/view_types.py`, modeled on `GalleryViewType` (view_types.py:373). Set:
  - [x] `type = "kanban"`, `model_class = KanbanView`, `field_options_model_class = KanbanViewFieldOptions`, `field_options_serializer_class = KanbanViewFieldOptionsSerializer`.
  - [x] `allowed_fields = ["single_select_field"]` (+ `"card_cover_image_field"` if model col added).
  - [x] `field_options_allowed_fields = ["hidden", "order"]`.
  - [x] `serializer_field_names = ["single_select_field"]` (+ cover if added).
  - [x] `serializer_field_overrides` = `single_select_field` → `PrimaryKeyRelatedField(queryset=Field.objects.all(), required=False, default=None, allow_null=True, help_text=...)`.
  - [x] `can_filter`/`can_sort`/`can_decorate`/`can_share` — match the existing `ViewType` defaults so AC #2 (filters/sorts/visibility) flows through the standard view pipeline. `has_public_info = True` like Gallery.
  - [x] `api_exceptions_map` for `FieldNotInTable → ERROR_FIELD_NOT_IN_TABLE`, `IncompatibleField → ERROR_INCOMPATIBLE_FIELD` (reuse same imports Gallery uses).
- [x] `prepare_values(self, values, table, user)`: validate `single_select_field` (mirror Gallery's `prepare_values` at view_types.py:399). If provided: resolve int→`Field`, assert `field_type_registry.get_by_model(field.specific).type == "single_select"` else raise `IncompatibleField`; assert `field.table_id == table.id` else raise `FieldNotInTable`. Then `super().prepare_values(...)`.
- [x] `after_field_type_change` / field-delete handling: when the grouping field changes away from single-select or is deleted, null out `single_select_field` (mirror `GalleryViewType.after_fields_type_change` at view_types.py:438 which nulls `card_cover_image_field`). Prevents a dangling grouping field. The `on_delete=SET_NULL` already covers deletion; the type-change guard covers conversion to an incompatible type.
- [x] `export_serialized` / `import_serialized`: copy the Gallery pattern (view_types.py:447+) for `single_select_field_id` + `field_options`. Keep `id_mapping` key namespaced `database_kanban_view_field_options`.
- [x] `get_api_urls`: return `path("kanban/", include(api_urls, namespace=self.type))`.

### Task 3 — Backend API (AC: #1, #2)
- [x] Create `backend/src/baserow/contrib/database/api/views/kanban/` mirroring `api/views/gallery/` (`__init__.py`, `serializers.py`, `urls.py`, `views.py`, `errors.py`, `pagination.py`).
- [x] `KanbanViewFieldOptionsSerializer` mirroring the Gallery field-options serializer (hidden/order).
- [x] Row-listing endpoint: reuse the **same** paginated, filter/sort/field-visibility-aware row listing Gallery uses — do **not** invent a new query path (AC #2 depends on going through the standard view row pipeline + the Epic 1 field-permission layer). Grouping into columns is done on the frontend by reading each row's `single_select_field` value (see Task 5). The board does NOT need a server-side per-column "stacks" endpoint for this story.
- [x] Register URLs so `view_type_registry` picks them up via `get_api_urls`.

### Task 4 — Backend registration (AC: #1)
- [x] In `backend/src/baserow/contrib/database/apps.py` (~line 348–352), import `KanbanViewType` and add `view_type_registry.register(KanbanViewType())` next to `GalleryViewType`.

### Task 5 — Frontend view type + components (AC: #1, #2, #3)
- [x] Add `KanbanViewType` to `web-frontend/modules/database/viewTypes.js`, modeled on `GalleryViewType` (viewTypes.js:1147, which extends `BaseBufferedRowViewTypeMixin(ViewType)`). `static getType()` → `'kanban'`; `getName()`, `getIconClass()`, `canFilter()`/`canSort()`/`canGroupBy()` consistent with Gallery; `getHeaderComponent()` → `KanbanViewHeader`; `getComponent()` → `KanbanView`.
- [x] Register in `web-frontend/modules/database/plugin.js` (~line 424, beside `GalleryViewType`): `$registry.register('view', new KanbanViewType(context))`.
- [x] Frontend store: add `web-frontend/modules/database/store/view/kanban.js` modeled on `store/view/gallery.js` (buffered rows + field options + view id/fetchInitial). Register the store module the same way Gallery's is wired.
- [x] Frontend service: add `web-frontend/modules/database/services/view/kanban.js` modeled on `services/view/gallery.js` (fetch rows, field options).
- [x] Components in `web-frontend/modules/database/components/view/kanban/`:
  - [x] `KanbanView.vue` — board container. Group buffered rows into columns: one column per option of the selected `single_select_field`, in the field's option order, **plus a trailing/leading "Uncategorized" column** holding rows whose grouping value is null. Read option list from the field metadata already in the store; read each row's value from its cell data. Read-only cards this story (no drag — 3.2).
  - [x] `KanbanViewHeader.vue` — header with the grouping-field picker (Single-select fields only). Selecting/clearing it dispatches the view-update that persists `single_select_field` (AC #3).
- [x] If no `single_select_field` is set yet, render an empty-state prompting the editor to pick one (do not crash on null).

### Task 6 — Backend tests (AC: #1, #2, #3)
- [x] Create `backend/tests/baserow/contrib/database/view/test_kanban_view_type.py`. Pattern: the existing `backend/tests/baserow/contrib/database/view/test_view_types.py` (shared core view-type tests) for view-type/handler assertions, and `backend/tests/baserow/contrib/database/api/views/gallery/test_gallery_view_views.py` for the API round-trip. Put view-type/model/handler tests in the new `test_kanban_view_type.py`; put HTTP/API tests in `backend/tests/baserow/contrib/database/api/views/kanban/test_kanban_view_views.py`. Minimum tests:
  1. `test_kanban_view_type_registered` — `view_type_registry.get("kanban")` returns `KanbanViewType`.
  2. `test_create_kanban_view` — `ViewHandler().create_view(..., type_name="kanban")` creates a `KanbanView`; default `single_select_field` is null.
  3. `test_kanban_set_single_select_field` — set `single_select_field` to a single-select field in the table; persists; reload shows same value (AC #3).
  4. `test_kanban_rejects_non_single_select_field` — setting `single_select_field` to a text field raises `IncompatibleField`.
  5. `test_kanban_rejects_field_from_other_table` — field from another table raises `FieldNotInTable`.
  6. `test_kanban_single_select_field_nulled_on_delete` — deleting the grouping field sets `single_select_field` to null (SET_NULL).
  7. `test_kanban_export_import_round_trip` — `export_serialized`/`import_serialized` preserves `single_select_field` + field_options.
- [x] Run: `EXTRA_VITEST_PARAMS="" just b test backend/tests/baserow/contrib/database/view/test_kanban_view_type.py`.

### Task 7 — Frontend unit tests (AC: #1, #3)
- [x] Create `web-frontend/test/unit/database/components/view/kanban/kanbanView.spec.js` (mirrors the existing `web-frontend/test/unit/database/components/view/gallery/` location). Minimum:
  1. `KanbanViewType` registers under type `'kanban'` with correct name/icon.
  2. Rows group into columns by `single_select_field` option order with a null bucket = "Uncategorized".
  3. A row whose grouping value is null lands in the Uncategorized column.
- [x] Use the `write-frontend-unit-test` skill conventions. Run: `EXTRA_VITEST_PARAMS="" just f test -- --reporter=verbose web-frontend/test/unit/database/components/view/kanban/kanbanView.spec.js`.

### Task 8 — E2E (AC: #1, #3)
- [x] Create `e2e-tests/tests/database/kanban_view.spec.ts`. Pattern: existing view-flow specs under `e2e-tests/tests/database/`. Cover: create a Kanban view on a table that has a single-select field → pick the grouping field → assert one column per option + an "Uncategorized" column → reload page → config persists.
- [x] Note: E2E requires the Docker stack — author the spec but do **not** run it locally (per prior-story convention, e.g. 2-5 Task notes).

### Task 9 — Clean-room provenance (gate, MANDATORY)
- [x] Add a provenance record under `docs/clean-room/provenance/` per `docs/clean-room/templates/provenance-record-template.md`: sources consulted = public Baserow MIT core (`GalleryViewType`, `GalleryView`, core view pipeline) + this story; implementer attestation = no `premium/`/`enterprise/` source read, used, or recalled.
- [x] Mark the PR as Bucket A (label `bucket-a` and/or the PR-template checkbox) so `clean-room-provenance-gate` CI runs. [Source: 1-1-...-clean-room-process-gate.md AC#3]

### Task 10 — Lint
- [x] `just b run pre-commit run --files $(git diff --name-only origin/develop...HEAD)` and fix Ruff/ESLint/Prettier issues before opening the PR.

## Dev Notes

### Gallery is the template — Kanban = Gallery + grouping
`GalleryViewType` (view_types.py:373) and `GalleryView` (models.py:694) are the license-clean blueprint. They already provide: a card view, `field_options` (hidden/order) with a trash-aware manager, an optional `card_cover_image_field`, `prepare_values` field-validation pattern, `after_fields_type_change` null-out pattern, and `export_serialized`/`import_serialized`. The **only** net-new concept is the `single_select_field` grouping FK and the frontend column-bucketing. Everything else is a structural copy of Gallery with `gallery`→`kanban` renames.

### Grouping logic — columns + Uncategorized
- The grouping field is a Single-select field (`SingleSelectField` model at `fields/models.py:621`; type `"single_select"` from `SingleSelectFieldType` at `fields/field_types.py:4309`). Its options have a defined order — render one column per option in that order.
- Rows whose single-select cell is **null** go into a dedicated **"Uncategorized"** column. This is AC #1 explicit — do not drop null rows.
- For 3.1, do the bucketing **on the frontend** from already-fetched row cell values + the field's option metadata in the store. No server-side stacks endpoint is needed this story. Card moves / write-back are 3.2.

### AC #2 — filters/sorts/visibility must reuse the standard pipeline
Do **not** write a bespoke row query. Route Kanban's row listing through the same view row pipeline Gallery/Grid use so view filters, sorts, and `field_options.hidden` (field visibility) — including the **Epic 1 field-permission layer** (`core/field_permissions/`) — apply automatically. Any custom query path risks bypassing the load-bearing permission boundary. [Source: architecture.md "Permission boundary"]

### Registration points (exact)
- Backend register: `backend/src/baserow/contrib/database/apps.py:348–352` (next to `GalleryViewType`).
- Frontend register: `web-frontend/modules/database/plugin.js:424` (`$registry.register('view', new KanbanViewType(context))`).
- Backend API URLs auto-wire via `KanbanViewType.get_api_urls()` (mirror Gallery's `get_api_urls` at view_types.py:401).

### Migration
- Next migration number: **0220** (latest is `0219_runningcountfield_alter_formview_mode.py`). Metadata-only — no per-user-table migration (dynamic-model pattern). Let `makemigrations` generate it; review before committing.

### Epic 1 integration — no special action, but do not bypass
- Field visibility (Story 1.5) and field permissions (Story 1.4/1.5) are enforced by the shared view row pipeline. By reusing it (AC #2 guidance above) Kanban inherits them for free. Do not re-implement visibility on the board.

### Test run commands
```bash
# Backend
EXTRA_VITEST_PARAMS="" just b test backend/tests/baserow/contrib/database/view/test_kanban_view_type.py
EXTRA_VITEST_PARAMS="" just b test backend/tests/baserow/contrib/database/api/views/kanban/
# Frontend unit
EXTRA_VITEST_PARAMS="" just f test -- --reporter=verbose web-frontend/test/unit/database/components/view/kanban/kanbanView.spec.js
# E2E requires Docker stack — author spec, do NOT run locally
```

### Anti-patterns (forbidden)
- Opening/reading/adapting anything under `premium/` or `enterprise/` (clean-room contamination). [Source: architecture.md line 268]
- Placing Kanban code in `premium/`/`enterprise/` instead of core. [Source: architecture.md line 205]
- A custom row query that bypasses the view filter/sort/field-permission pipeline.
- Building drag/move (3.2) or card-appearance (3.3) into this story.
- Merging a Bucket A PR without a provenance record (CI gate blocks it).

### Project Structure Notes

New files:
- `backend/src/baserow/contrib/database/api/views/kanban/{__init__,serializers,urls,views,errors,pagination}.py`
- `backend/src/baserow/contrib/database/migrations/0220_kanbanview_*.py` (generated)
- `backend/tests/baserow/contrib/database/view/test_kanban_view_type.py`
- `backend/tests/baserow/contrib/database/api/views/kanban/test_kanban_view_views.py`
- `web-frontend/modules/database/store/view/kanban.js`
- `web-frontend/modules/database/services/view/kanban.js`
- `web-frontend/modules/database/components/view/kanban/KanbanView.vue`
- `web-frontend/modules/database/components/view/kanban/KanbanViewHeader.vue`
- `web-frontend/test/unit/database/components/view/kanban/kanbanView.spec.js`
- `e2e-tests/tests/database/kanban_view.spec.ts`
- `docs/clean-room/provenance/<this-pr>.md`

Modified files:
- `backend/src/baserow/contrib/database/views/models.py` (add `KanbanView`, `KanbanViewFieldOptions`, manager)
- `backend/src/baserow/contrib/database/views/view_types.py` (add `KanbanViewType`)
- `backend/src/baserow/contrib/database/apps.py` (register `KanbanViewType`)
- `web-frontend/modules/database/viewTypes.js` (add `KanbanViewType`)
- `web-frontend/modules/database/plugin.js` (register `KanbanViewType`)

Naming: backend `snake_case` files, `PascalCase` classes (`KanbanViewType`, `KanbanView`); frontend `.vue` `PascalCase`, registry file `viewTypes.js` camelCase symbols. [Source: architecture.md lines 192–208]

### References

- [Source: epics.md#Epic 3 → Story 3.1, lines 476–488] — user story + three ACs (columns per option + Uncategorized; filters/sorts/visibility apply; persists/reopens).
- [Source: architecture.md lines 25, 158, 205, 221, 239–268, 279, 302–318] — Kanban is Bucket A clean-room; ViewType registry-extension pattern; core-dir placement; provenance mandatory; component-to-location map; permission boundary.
- [Source: 1-1-establish-the-clean-room-process-gate.md] — clean-room gate is live; provenance record = hard merge gate; "influenced by" = contamination; anti-patterns.
- [Source: backend/src/baserow/contrib/database/views/view_types.py:373 (GalleryViewType)] — backend view-type template.
- [Source: backend/src/baserow/contrib/database/views/models.py:694 (GalleryView / GalleryViewFieldOptions)] — view model + field-options template.
- [Source: backend/src/baserow/contrib/database/apps.py:348–352] — `view_type_registry.register` site.
- [Source: web-frontend/modules/database/viewTypes.js:1147 (GalleryViewType)] — frontend view-type template.
- [Source: web-frontend/modules/database/plugin.js:424] — frontend `$registry.register('view', ...)` site.
- [Source: web-frontend/modules/database/store/view/gallery.js + services/view/gallery.js] — store/service templates.
- [Source: backend/src/baserow/contrib/database/fields/models.py:621 (SingleSelectField); field_types.py:4309 (SingleSelectFieldType)] — grouping field model/type.
- [Source: memory baserow-open-core-license-constraint] — paid features need clean-room reimplement; PE/EE forbids copying.
- [Source: memory clean-room-isolation-porous] — prior BMAD agents drifted into reading premium/enterprise during debug/verify; hold the line here.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (BMAD dev-story, clean-room Bucket A walled-off writer).

### Debug Log References

- **Clean-room test execution.** Backend pytest could not see the OSS-only profile when
  `.env.testing-cleanroom` was shell-sourced: `settings/test.py` patches `os.getenv` so
  non-allowlisted vars (incl. `BASEROW_OSS_ONLY`) are read only from `TEST_ENV_FILE`.
  Fixed by exporting `TEST_ENV_FILE=.env.testing-cleanroom` and adding
  `premium/backend/src:enterprise/backend/src` to `PYTHONPATH` (importable but kept out
  of `INSTALLED_APPS` by `BASEROW_OSS_ONLY=true`).
- **`test_kanban_single_select_field_nulled_on_delete` failed** (`assert 4 is None`):
  field deletion is a soft trash, so the FK `SET_NULL` does not fire. Fixed by explicitly
  nulling `single_select_field_id` (and `card_cover_image_field_id`) in
  `KanbanViewType.after_field_delete`.
- **Frontend name/icon test** initially read the premium Kanban from the registry (TestApp
  loads premium → premium overrides core, confirming the precedence design). Fixed by
  asserting against the core `KanbanViewType` class directly; i18n is mocked so `getName()`
  returns the key `viewType.kanban`.

### Completion Notes List

- Built the **free Kanban view in core** from the public MIT `GalleryViewType`/`GalleryView`
  template. Kanban = Gallery + a `single_select_field` grouping FK; frontend buckets rows
  into one column per option + a trailing **Uncategorized** column for null values
  (`groupRowsBySingleSelect`). No `premium/`/`enterprise/` file was read, copied, or
  modified.
- **Premium-precedence guard:** core registers the Kanban view in backend
  (`view_type_registry`, gated by `if "baserow_premium" not in settings.INSTALLED_APPS`)
  and frontend (last-registration-wins). The free core Kanban is the active view type only
  in OSS-only builds (`BASEROW_OSS_ONLY=true`); premium's Kanban overrides it in full
  open-core builds.
- **AC #1** — columns render one per single-select option plus Uncategorized (backend
  round-trip + frontend `groupRowsBySingleSelect` unit tests). **AC #2** — row listing
  reuses the standard Gallery view row pipeline, so filters/sorts/field-visibility +
  Epic 1 field permissions apply (no bespoke query). **AC #3** — `single_select_field` +
  field_options persist and survive export/import (backend round-trip test) and reload
  (E2E spec).
- Tests green: **backend 13 passed** (`test_kanban_view_type.py` + `api/views/kanban/`),
  **frontend 7 passed** (`kanbanView.spec.js`), both run OSS-only. E2E spec authored
  (`kanban_view.spec.ts`) but **not run locally** — it targets the OSS-only CI lane.
- **Clean-room provenance:** `docs/clean-room/provenance/3-1-create-and-configure-a-kanban-view.md`
  added and validated by the gate (`check_provenance.py` → PASS as Bucket A). PR must carry
  the `bucket-a` label / checkbox.
- Lint clean: Ruff check + format (backend), Prettier + ESLint (frontend JS/Vue/TS),
  Stylelint (scss — fixed an `overflow` longhand→shorthand).

### File List

**New — backend**
- `backend/src/baserow/contrib/database/migrations/0220_kanbanview_kanbanviewfieldoptions.py`
- `backend/src/baserow/contrib/database/api/views/kanban/` (`__init__.py`, `serializers.py`, `urls.py`, `views.py`, `errors.py`, `pagination.py`)
- `backend/tests/baserow/contrib/database/view/test_kanban_view_type.py`
- `backend/tests/baserow/contrib/database/api/views/kanban/` (test module)

**New — frontend**
- `web-frontend/modules/database/store/view/kanban.js`
- `web-frontend/modules/database/services/view/kanban.js`
- `web-frontend/modules/database/components/view/kanban/KanbanView.vue`
- `web-frontend/modules/database/components/view/kanban/KanbanViewHeader.vue`
- `web-frontend/modules/core/assets/scss/components/views/kanban.scss`
- `web-frontend/test/unit/database/components/view/kanban/kanbanView.spec.js`

**New — e2e**
- `e2e-tests/tests/database/kanban_view.spec.ts`
- `e2e-tests/fixtures/database/view.ts`

**New — docs**
- `docs/clean-room/provenance/3-1-create-and-configure-a-kanban-view.md`

**Modified — backend**
- `backend/src/baserow/contrib/database/views/models.py` (add `KanbanView`, `KanbanViewFieldOptions`, manager)
- `backend/src/baserow/contrib/database/views/view_types.py` (add `KanbanViewType`)
- `backend/src/baserow/contrib/database/apps.py` (register `KanbanViewType`, OSS-only gated)
- `backend/src/baserow/test_utils/fixtures/view.py` (Kanban view fixture)

**Modified — frontend**
- `web-frontend/modules/database/viewTypes.js` (add `KanbanViewType`)
- `web-frontend/modules/database/plugin.js` (register `KanbanViewType`)
- `web-frontend/modules/database/plugin/store.js` (register kanban store module)
- `web-frontend/modules/core/assets/scss/components/all.scss` (import kanban styles)
- `web-frontend/locales/en.json`, `web-frontend/modules/database/locales/en.json` (translations)

**Modified — docs**
- `docs/development/running-tests.md` (dev DB port `5433`→`5431` to match justfile default; verified correct)

**Modified — review (post-review fix)**
- `backend/src/baserow/contrib/database/views/models.py` (core `KanbanView`/`KanbanViewFieldOptions` given distinct identity: `db_table="database_corekanbanview"`/`database_corekanbanviewfieldoptions` + non-clashing `related_name`s — resolves model clash with premium Kanban in full open-core builds)
- `backend/src/baserow/contrib/database/migrations/0220_kanbanview_kanbanviewfieldoptions.py` (regenerated to match new `db_table`/`related_name`s; dropped unrelated `formview.mode` drift)

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-06-09 | 0.1 | Story 3.1 Kanban view implemented (Bucket A clean-room from Gallery template); backend 13 + frontend 7 tests green; E2E spec authored; provenance recorded; lint clean. Status → review. | claude-opus-4-8 (dev-agent) |
| 2026-06-09 | 0.2 | Adversarial review (1 CRITICAL fixed, 1 MEDIUM documented). CRITICAL: core/premium `KanbanView` Django model clash broke `manage.py check` in full open-core builds (8× E304/E305/W035/W344) — fixed via distinct `db_table` + `related_name`s + regenerated migration 0220. MEDIUM: `docs/development/running-tests.md` port change added to File List. Re-verified: full-build check clean of Kanban errors, OSS-only 13 backend + 7 frontend tests green, ruff clean. Status → done. | gabenidolcs (review-agent) |

## Senior Developer Review (AI)

**Reviewer:** gabenidolcs · **Date:** 2026-06-09 · **Model:** claude-opus-4-8 (BMAD story-automator-review, adversarial)
**Outcome:** Approved → **done** (0 CRITICAL remaining after auto-fix).

### Summary

Implementation is a faithful Bucket A clean-room reconstruction of Kanban from the public `GalleryViewType`/`GalleryView` template — `single_select_field` grouping FK + frontend `groupRowsBySingleSelect` bucketing with an Uncategorized null column. All 3 ACs are met and the row listing correctly reuses the standard view pipeline (AC #2 permission/filter/sort inheritance intact). Provenance recorded. One ship-blocking defect was found and auto-fixed.

### Findings

#### CRITICAL-1 — Core/premium `KanbanView` Django model clash breaks full open-core builds *(FIXED)*

The dev agent gated **registry registration** behind `if "baserow_premium" not in settings.INSTALLED_APPS` (`apps.py`), but Django model classes load regardless of registry gating. In a full open-core build (premium in `INSTALLED_APPS`), core `KanbanView` and premium `KanbanView` both mapped to `db_table="database_kanbanview"` with identical reverse accessors. `manage.py check` failed with **8 errors**: `fields.E304`/`E305` (reverse accessor / query name clashes on `single_select_field`, `card_cover_image_field`, `field_options`, `view_ptr`) and `models.W035`/`W344` (duplicate `db_table`). The OSS-only test lane never exercised this path, so the dev tests stayed green while the real merge target was broken.

**Fix applied** (`models.py` + migration `0220`):
- Core models given distinct tables: `db_table="database_corekanbanview"` / `database_corekanbanviewfieldoptions`.
- `view_ptr` `related_name="core_kanban_view"`; `single_select_field` → `core_kanban_view_single_select_field`; `card_cover_image_field` → `core_kanban_view_card_cover_field`; `field_options` / field-options `field` FK → `related_name="+"`.
- Migration `0220` regenerated to match (also dropped an unrelated `formview.mode` alter that `makemigrations` swept in — pre-existing drift, out of scope).

**Verification:** full-build `manage.py check` now reports only 4 pre-existing `FieldPermission`↔enterprise errors (Epic 1 baseline, unrelated to 3.1) — all Kanban clashes gone. OSS-only **13 backend + 7 frontend** tests still green. `ruff check`/`ruff format` clean.

#### MEDIUM-1 — `docs/development/running-tests.md` modified but omitted from File List *(FIXED — documented)*

Dev changed the documented dev-DB port `5433`→`5431` (correct; matches the justfile default) but did not list the file. Added to File List under **Modified — docs**. No code impact.

### Lower-severity / out-of-scope (NOT fixed — outside story 3.1)

- **LOW** — `apps.py` premium-precedence gate is now *defense-in-depth* only (distinct tables already prevent the clash). Harmless; left as-is.
- **OUT OF SCOPE** — 4× `FieldPermission`↔enterprise `manage.py check` errors: Epic 1 baseline, predate this story.
- **OUT OF SCOPE** — `formview.mode` migration drift (pre-existing, obs 4528).
- **OUT OF SCOPE** — `fieldTypes.spec.js` 77 failures: `running_count` field missing from `mockedFields` (story 2.5 regression, not Kanban).

### Verification commands run

```bash
# Full open-core build — confirms clash resolved
just b run python src/baserow/manage.py check
# OSS-only backend (clean-room profile)
TEST_ENV_FILE=.env.testing-cleanroom EXTRA_VITEST_PARAMS="" just b test \
  tests/baserow/contrib/database/view/test_kanban_view_type.py \
  tests/baserow/contrib/database/api/views/kanban/
# Frontend unit
cd web-frontend && EXTRA_VITEST_PARAMS="" yarn test:core \
  test/unit/database/components/view/kanban/kanbanView.spec.js
# Lint
just b run ruff check ... && just b run ruff format ...
```
