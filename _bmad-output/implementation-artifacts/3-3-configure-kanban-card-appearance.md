---
baseline_commit: 8bacef1fdad2f96aa47eaeca8d2483af4ce21488
---
<!-- Powered by BMAD-CORE™ -->

# Story 3.3: Configure Kanban card appearance

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to choose which Fields and the cover image show on a card,
so that cards display the right information. `[A]`

## Context & Scope

### 🚨 THIS IS A BUCKET A CLEAN-ROOM STORY — READ FIRST, NON-NEGOTIABLE

Kanban is a **Bucket A** feature: it is reimplemented in **core** without ever reading, copying, or being "influenced by" any `premium/` or `enterprise/` source. The PE/EE license forbids copying; a provenance record is a **hard CI merge gate**.

- **Do NOT open, read, `grep`, or adapt** anything under `premium/` or `enterprise/` — including premium's Kanban card-appearance / cover-image code. Reading it = contamination = the PR cannot merge. [Source: architecture.md line 268; 3-1 Context & Scope; memory clean-room-isolation-porous]
- All code lands in **core** (`backend/src/baserow/...`, `web-frontend/modules/database/...`). [Source: architecture.md line 205]
- A provenance record under `docs/clean-room/provenance/` is **mandatory** (Task 6). [Source: 1-1-establish-the-clean-room-process-gate.md]
- Premium-precedence: in full open-core builds premium's Kanban overrides core (last-registration-wins / `if "baserow_premium" not in INSTALLED_APPS` backend gate). The free core Kanban is the active view type only in **OSS-only** builds (`BASEROW_OSS_ONLY=true`). Run tests OSS-only. [Source: 3-1 Completion Notes; 3-2 Context & Scope]

### 🧭 THE SINGLE MOST IMPORTANT FACT: most of this feature already shipped in Story 3.1 — VERIFY, do not REINVENT

When the dev built the core Kanban view in **Story 3.1** by mirroring the public MIT `GalleryViewType`, the card-appearance surface came along for free, because Gallery already has `field_options` (`hidden`/`order`) + an optional `card_cover_image_field`. **The backend, store, header UI, and card rendering for this story are already present in core.** Your job is **NOT** to build a "Customize cards" feature — it exists. Your job is to:

1. **VERIFY** each AC against the existing code (cited below, with exact lines).
2. **CLOSE THE TEST GAP** — 3.1 shipped the feature but did **not** add tests targeting card-face field selection or the cover image. That is the bulk of this story.
3. Add the **Bucket A provenance** record (merge gate).
4. Fix only **genuine** defects found during verification.

> ⚠️ **Anti-pattern (forbidden):** re-creating `KanbanViewHeader.vue`, a second cover-image picker, a new `ViewFieldsContext`, a parallel `field_options` model/serializer/endpoint, or any new store action. These all exist. If you find yourself writing a new component or store action for card appearance, **stop — you have left the story.** The clean-room + "reinventing wheels" failure mode is the primary risk here. [Source: SKILL checklist §3.1; architecture.md "reuse the handler spine"]

### What already exists (reuse verbatim — cite these in your verification)

**Backend (core, already built in 3.1 — all clean MIT/Gallery-derived):**
- `KanbanView.card_cover_image_field` FK + `KanbanViewFieldOptions(hidden, order)` model. [Source: backend/src/baserow/contrib/database/views/models.py:741 (KanbanView), :799 (KanbanViewFieldOptions)]
- `KanbanViewType` wires it all: `allowed_fields = ["single_select_field", "card_cover_image_field"]` (view_types.py:618), `field_options_allowed_fields = ["hidden", "order"]` (:619), `serializer_field_names` incl. `card_cover_image_field` (:620, override :630), `prepare_values` validates the cover field can represent files (:654, cover branch :678), `get_visible_field_options_in_order` (:848) and `get_hidden_fields` (:859) keep the single-select **and** cover-image fields always visible (:873, :875), `after_field_delete` nulls `card_cover_image_field_id` when its file field is deleted (~:721), export/import round-trips `card_cover_image_field` (:744, :781, :844). [Source: view_types.py:613–890]
- `KanbanViewFieldOptionsSerializer` exposes `("hidden", "order")`. [Source: backend/src/baserow/contrib/database/api/views/kanban/serializers.py]
- The shared `PATCH /api/database/views/{view_id}/field_options/` endpoint already persists field options for any view type via `UpdateViewFieldOptionsActionType`. **No Kanban-specific endpoint exists or is needed.** [Source: backend/src/baserow/contrib/database/api/views/views.py — `ViewFieldOptionsView.patch`]
- The cover image field is persisted via the **generic** `PATCH /api/database/views/{view_id}/` (view update) carrying `card_cover_image_field`. No new endpoint.

**Frontend (core, already built in 3.1):**
- `KanbanViewHeader.vue` — a **"Customize cards"** context (icon `iconoir-settings`) renders the shared `ViewFieldsContext` with `:allow-cover-image-field="true"`, the field-visibility toggle list, drag-reorder, and the cover-image picker; wired to `updateAllFieldOptions` / `updateFieldOptionsOfField` / `orderFieldOptions` (→ store `view/kanban/updateFieldOptionsOrder`) / `updateCoverImageField` (→ generic `view/update` with `card_cover_image_field`). [Source: web-frontend/modules/database/components/view/kanban/KanbanViewHeader.vue:36–67 template, :147–227 methods]
- `ViewFieldsContext.vue` — shared core component (also used by Gallery's `GalleryViewHeader.vue`); cover-image dropdown filters to file-representable fields, hidden toggles + reorder. **Reused, not modified.** [Source: web-frontend/modules/database/components/view/ViewFieldsContext.vue]
- `KanbanView.vue` — `cardFields` computed = `fields.filter(filterVisibleFieldsFunction(fieldOptions)).sort(sortFieldsByOrderAndIdFunction(fieldOptions))`; `hiddenFields` computed; `coverImageField` computed resolves `view.card_cover_image_field` to the field object; passes `:fields="cardFields"` and `:cover-image-field="coverImageField"` to `RowCard`. [Source: web-frontend/modules/database/components/view/kanban/KanbanView.vue:28–33 RowCard binding, cardFields/hiddenFields/coverImageField computeds]
- `RowCard.vue` — renders the cover image block when `coverImageField !== null` (thumbnail `thumbnails.card_cover.url`, empty-state icon when no image) and renders only the fields passed in `fields`. [Source: web-frontend/modules/database/components/card/RowCard.vue:24–35 cover, :37–53 fields, `coverImageUrl` computed]
- Store: `store/view/kanban.js` `fetchInitial` requests `includeFieldOptions: true` and dispatches `forceUpdateAllFieldOptions`. The field-option getters/actions (`getAllFieldOptions`, `updateAllFieldOptions`, `updateFieldOptionsOfField`, `updateFieldOptionsOrder`, `forceUpdateAllFieldOptions`) are inherited from `bufferedRows` → `fieldOptionsStoreFactory`. **No new store code needed.** [Source: web-frontend/modules/database/store/view/kanban.js:31–41; store/view/bufferedRows.js:24,57–61,1297–1299; store/view/fieldOptions.js:46,96,121,128,168]

### Scope of THIS story (3.3 only)

**In scope:**
- **Verify** all ACs against the existing core implementation above (read the files, confirm the wiring, don't take this story's word for it).
- **Add tests** that pin the card-appearance behavior (the 3.1 work is currently untested for cover image + field-face selection):
  - Backend: `card_cover_image_field` set/persist/validate, cover field nulled on its file-field delete, `get_hidden_fields` keeps single-select + cover visible, `field_options` `hidden` toggle persists per view.
  - Frontend unit: `cardFields` excludes hidden fields and orders by option; `coverImageField` computed; `RowCard` renders the cover; header dispatches the cover-image + field-option updates.
  - E2E: toggle a field's visibility (it disappears from cards), set a cover image (it renders), and both persist on reopen.
- **Provenance** record (Task 6).
- Fix only **real** defects discovered during verification.

**Explicitly OUT of scope (do NOT build):**
- ❌ **Any net-new feature code for card appearance** — it exists (see above). No new component, store action, serializer, endpoint, model field, or migration unless verification surfaces a concrete bug.
- ❌ **Row coloring / conditional card colors.** The AC explicitly states "cards render **without dependency on row coloring** (out of scope this release)." Core has no Kanban row-coloring; do not add it and confirm cards render correctly without it.
- ❌ Opening/reading/adapting anything under `premium/` or `enterprise/`.
- ❌ Drag-and-drop (Story 3.2, done), grouping-field config (Story 3.1, done), Calendar/Timeline/etc.

## Acceptance Criteria

1. **Given** a Kanban View, **When** an editor selects card-face Fields (toggles a field's visibility) and toggles the cover image, **Then** hidden Fields do not render on cards and the cover image renders from the chosen file field. *(Verified against `cardFields`/`hiddenFields`/`coverImageField` in `KanbanView.vue` + `RowCard.vue` cover block; configured via `KanbanViewHeader.vue` "Customize cards" → `ViewFieldsContext`.)*
2. **And** the card-appearance setting **persists per View** and reopens with the same configuration — field-option `hidden`/`order` via the shared `field_options` PATCH; `card_cover_image_field` via the generic view PATCH; both re-hydrated by `fetchInitial`/export-import.
3. **And** cards render correctly **without any dependency on row coloring** (row coloring is out of scope this release) — the card renders from `cardFields` + cover only.
4. A field that is the **grouping single-select field** or the **cover image field** is always treated as visible by `get_hidden_fields` (cannot be accidentally hidden from the board's data dependencies). *(Regression guard already implemented in 3.1 — pin it with a test.)*

## Tasks / Subtasks

### Task 1 — Verify the existing implementation satisfies AC #1–#4 (AC: all)

- [x] **Read** (do not modify yet) the files listed in "What already exists" and confirm each AC's wiring end-to-end. Write your findings into Dev Notes / Completion Notes with exact line cites. This verification is a deliverable, not a formality — it is how we avoid "lying about completion."
- [x] Confirm the cover-image picker in `ViewFieldsContext.vue` only offers **file-representable** fields and that selecting one dispatches the generic `view/update` with `card_cover_image_field` (KanbanViewHeader `updateCoverImageField`). Confirm clearing it sets `null`.
- [x] Confirm `KanbanView.vue` `cardFields` excludes hidden fields and that the same `fieldOptions` drives `RowCard`'s rendered fields, and `coverImageField` resolves `view.card_cover_image_field` to the field object passed to `RowCard`.
- [x] Confirm there is **no** Kanban row-coloring code path and that `RowCard` renders from `fields` + `coverImageField` only (AC #3). If a decoration/coloring slot exists generically (`decorationsByPlace`), confirm it is unused/optional for core Kanban and requires no work.
- [x] If — and only if — a concrete defect is found (e.g., a binding that does not persist, cover not rendering, a hidden field still showing), fix it in **core** and document it. Otherwise record "verified, no change required." — **Verified, no change required.**

### Task 2 — Backend tests for card appearance (AC: #1, #2, #4)

- [x] Extend `backend/tests/baserow/contrib/database/view/test_kanban_view_type.py` (do **not** duplicate existing cases — it already covers create, single-select set/reject, single-select-nulled-on-delete, export/import round trip incl. `field_options`, and "first three fields visible"). **Add:**
  - [x] `card_cover_image_field` can be set on a Kanban view and persists; setting it to a file/attachment field is accepted, and a field that **cannot** represent files is rejected by `prepare_values` (mirror the single-select reject test at line 61). [Source: view_types.py:678 cover branch]
  - [x] `card_cover_image_field_id` is nulled when the referenced file field is deleted (`after_field_delete`), mirroring `test_kanban_single_select_field_nulled_on_delete` (line 88). [Source: view_types.py ~:721]
  - [x] `get_hidden_fields` returns a set that **excludes** the single-select field id and the cover-image field id even when their `hidden` option is True (AC #4 regression guard). [Source: view_types.py:859–890]
- [x] Extend `backend/tests/baserow/contrib/database/api/views/kanban/test_kanban_view_views.py` (already covers list rows, sorts/filters, include field_options, patch single-select set/reject). **Add:**
  - [x] `PATCH /api/database/views/{kanban_id}/` with `card_cover_image_field` persists and is returned on a subsequent GET (per-view persistence, AC #2).
  - [x] `PATCH /api/database/views/{kanban_id}/field_options/` with `{field_id: {"hidden": true}}` persists; a follow-up list with `include=field_options` reflects it (AC #2). Use the **shared** endpoint — do not expect a Kanban-specific one.
- [x] Run: `just b test backend/tests/baserow/contrib/database/view/test_kanban_view_type.py backend/tests/baserow/contrib/database/api/views/kanban/test_kanban_view_views.py` (OSS context). Expect green. — **22 passed (OSS-only, `TEST_ENV_FILE=.env.oss-test`).**

### Task 3 — Frontend unit tests for card appearance (AC: #1, #3)

- [x] Add focused unit coverage. **Heed the 3.2 lesson:** a full `testApp.mount(KanbanView)` registers the **premium** Kanban store last (override) → mock-miss + JS-heap OOM. Use the same **method/computed-level** pattern 3.2 used (`kanbanView.spec.js`) — bind the real `cardFields` / `hiddenFields` / `coverImageField` computeds to a minimal fake instance — to stay on the free-core surface and inside the clean room. [Source: 3-2 Dev Agent Record "Debug Log References"; kanbanView.spec.js]
  - [x] `cardFields` excludes fields whose `fieldOptions[id].hidden === true` and orders visible fields by `order` then `id` (use `filterVisibleFieldsFunction` / `sortFieldsByOrderAndIdFunction` indirectly via the computed). (AC #1)
  - [x] `coverImageField` returns the field object matching `view.card_cover_image_field`, and `null` when unset. (AC #1)
  - [x] (Optional, if cheaply mountable in isolation) a `RowCard` shallow test: passing `coverImageField` renders the `.card__cover` block; passing only a subset of `fields` renders only those `.card__field` rows (AC #1, #3 — no coloring dependency). — covered via the computed-level harness (no full mount).
- [x] Add a `KanbanViewHeader` method-level test (or extend the header's spec if one exists; otherwise method-level): `updateCoverImageField(value)` dispatches `view/update` with `{ card_cover_image_field: value }`; `updateFieldOptionsOfField` / `orderFieldOptions` dispatch the corresponding `view/kanban/...` actions with the `readOnly`-or-no-permission guard. (AC #2)
- [x] Run: `EXTRA_VITEST_PARAMS="" just f test -- --reporter=verbose web-frontend/test/unit/database/components/view/kanban/` (or the `yarn vitest run …` equivalent if `just` is not on PATH — see 3.2 notes). Expect green. — **33 passed (`yarn vitest run`).**

### Task 4 — E2E scenario: customize card appearance + persistence (AC: #1, #2)

- [x] Extend `e2e-tests/tests/database/kanban_view.spec.ts` (created 3.1, extended 3.2). Reuse the existing Kanban fixture in `e2e-tests/fixtures/database/view.ts`. Add a scenario that:
  - [x] Opens "Customize cards", toggles a non-grouping field's visibility off → assert that field no longer renders on any card; toggles it back on → it returns. (AC #1)
  - [x] Sets a cover image field (a file/attachment field with an image) → assert the card cover renders; clears it → cover disappears. (AC #1)
  - [x] Reloads the page → both the hidden-field state and the cover image persist. (AC #2)
- [x] **Do NOT run E2E locally** — requires the Docker stack and targets the OSS-only CI lane. Author the spec only. [Source: 3-1 Dev Notes "Test run commands"; 3-2 Task 5] — **Authored only; not run locally.** Added `updateFieldOptions` helper to `e2e-tests/fixtures/database/view.ts`.

### Task 5 — Lint (AC: all)

- [x] Run frontend Prettier + ESLint on changed `.vue`/`.js`/`.ts`; Ruff on any changed backend test files; Stylelint on any SCSS touched (none expected). — **Ruff `check`+`format` clean on both backend test files; ESLint + Prettier clean on `kanbanView.spec.js`; e2e `.ts` matches existing style (no static lint gate in `e2e-tests/`). No SCSS touched.**
- [x] `just b run pre-commit run --files $(git diff --name-only origin/develop...HEAD)` to lint only branch-touched files. — `just`/`pre-commit` not on PATH in this env; equivalent individual linters (Ruff, ESLint, Prettier) run directly and pass.

### Task 6 — Clean-room provenance (gate, MANDATORY) (AC: all)

- [x] Add `docs/clean-room/provenance/3-3-configure-kanban-card-appearance.md` declaring **Bucket A**, no `premium/`/`enterprise/` sources read, built/verified from public MIT Baserow Gallery card-appearance patterns + this story. Validate with the gate (`check_provenance.py` → expect PASS as Bucket A). PR must carry the `bucket-a` label/checkbox. [Source: 1-1-establish-the-clean-room-process-gate.md; 3-2 Task 6] — **Record created; `validate_provenance` → PASS ("valid provenance record"). PR must carry the `bucket-a` label.**

## Dev Notes

### Why this story is mostly verification + tests

Story 3.1 built the core Kanban view by deriving from the public `GalleryViewType`. Gallery's card model **is** the card-appearance feature: per-field `hidden`/`order` (`field_options`) plus a nullable `card_cover_image_field`. Mirroring Gallery therefore delivered 3.3's behavior at the same time. 3.1's own scope note even pre-staged the model field: *"You MAY add the nullable `card_cover_image_field` column now… but no card-appearance UI here"* — in practice the dev wired the full `ViewFieldsContext` "Customize cards" header too. The result: the feature works, but it is **untested** for the cover image and field-face selection, and it has no provenance record of its own. This story makes the behavior **provable** and **mergeable**.

The dominant failure mode to avoid is **reinvention** — adding a parallel component/action/endpoint for something that already exists. Verify first; cite lines; test the existing surface.

### Persistence model (AC #2) — two distinct PATCH paths, both pre-existing

- **Field face (`hidden`/`order`)** → shared `PATCH /api/database/views/{id}/field_options/` (`ViewFieldsContext` → header `updateFieldOptionsOfField`/`orderFieldOptions` → store `view/kanban/updateFieldOptionsOfField` / `updateFieldOptionsOrder` → `fieldOptions.js` → `ViewService.updateFieldOptions`). Optimistic with rollback (`fieldOptions.js:96–120`). [Source: store/view/fieldOptions.js]
- **Cover image (`card_cover_image_field`)** → generic `PATCH /api/database/views/{id}/` (`updateCoverImageField` → `view/update`). Allowed because `KanbanViewType.allowed_fields` includes it (view_types.py:618) and `prepare_values` validates representability (view_types.py:678).
- On reopen, `store/view/kanban.js` `fetchInitial` requests `includeFieldOptions: true` and re-hydrates options; `card_cover_image_field` is part of the serialized view. Export/import also round-trips both (view_types.py:744, :844).

### Field permissions / readOnly

- The header guards every field-option dispatch with `this.readOnly || !this.$hasPermission('database.table.view.update_field_options', view, workspaceId)` (KanbanViewHeader.vue methods). Don't add a second guard; verify this one and cover it in the header unit test.
- `get_hidden_fields` / `get_visible_field_options_in_order` already keep the single-select and cover-image fields visible regardless of their `hidden` option (view_types.py:848–890) — this protects the board's data dependencies (the grouping value and the cover thumbnail must be fetchable). AC #4 pins this.

### Clean-room reminder

The clean-room boundary is **porous under debugging** — prior agents drifted into `premium/`/`enterprise/` while "verifying". Hold the line: every file you read for this story is under `backend/src/baserow/...`, `web-frontend/modules/database/...`, `backend/tests/...`, `web-frontend/test/...`, or `e2e-tests/...`. The public reference for "what complete looks like" is the **Gallery** view (`GalleryViewType`, `GalleryViewHeader.vue`), which is MIT/core. [Source: memory clean-room-isolation-porous; memory baserow-open-core-license-constraint]

### Test run commands

```bash
# Backend (OSS context)
just b test backend/tests/baserow/contrib/database/view/test_kanban_view_type.py
just b test backend/tests/baserow/contrib/database/api/views/kanban/test_kanban_view_views.py
# Frontend unit (OSS context; i18n mocked as in 3.1/3.2)
EXTRA_VITEST_PARAMS="" just f test -- --reporter=verbose web-frontend/test/unit/database/components/view/kanban/
# E2E requires Docker stack — author spec, do NOT run locally
# Lint only branch-touched files
just b run pre-commit run --files $(git diff --name-only origin/develop...HEAD)
```

### Anti-patterns (forbidden)

- ❌ Building a new "Customize cards" component, cover-image picker, `ViewFieldsContext`, store action, serializer, endpoint, model field, or migration — all exist (see "What already exists"). Reuse + verify.
- ❌ Adding Kanban row coloring / conditional card colors (explicitly out of scope, AC #3).
- ❌ Opening/reading/adapting anything under `premium/` or `enterprise/` (clean-room contamination). [Source: architecture.md line 268]
- ❌ Mounting the full `KanbanView` in a unit test (premium store override → mock-miss + OOM). Use method/computed-level tests. [Source: 3-2 Debug Log]
- ❌ Marking tasks `[x]` without the cited verification or passing tests ("lying about completion").
- ❌ Merging a Bucket A PR without a provenance record (CI gate blocks it).

### Project Structure Notes

New files:
- `docs/clean-room/provenance/3-3-configure-kanban-card-appearance.md`

Modified files (tests + possibly a small verified-bug fix only):
- `backend/tests/baserow/contrib/database/view/test_kanban_view_type.py` (cover image + get_hidden_fields cases)
- `backend/tests/baserow/contrib/database/api/views/kanban/test_kanban_view_views.py` (cover image PATCH + field_options PATCH cases)
- `web-frontend/test/unit/database/components/view/kanban/kanbanView.spec.js` (cardFields/coverImageField + header dispatch tests; or a new `kanbanViewHeader.spec.js`)
- `e2e-tests/tests/database/kanban_view.spec.ts` (customize-cards scenario + persistence)
- (only if a concrete defect is found) the relevant **core** source file — `KanbanView.vue` / `KanbanViewHeader.vue` / `view_types.py`

No new feature source, no migration expected. Naming follows existing conventions. [Source: architecture.md lines 192–208]

### References

- [Source: epics.md#Epic 3 → Story 3.3, lines 507–518] — user story + AC (select card-face fields, toggle cover image, hidden fields don't render, persists per view, no row-coloring dependency).
- [Source: backend/src/baserow/contrib/database/views/models.py:741 (KanbanView), :799 (KanbanViewFieldOptions)] — model fields `card_cover_image_field`, `hidden`, `order`.
- [Source: backend/src/baserow/contrib/database/views/view_types.py:613–890 (KanbanViewType)] — `allowed_fields`(:618), `field_options_allowed_fields`(:619), `serializer_field_names`(:620) + override(:630), `prepare_values`(:654) cover branch(:678), cover-null-on-field-delete(~:721), export/import(:744,:781,:844), `get_visible_field_options_in_order`(:848), `get_hidden_fields`(:859,:873,:875).
- [Source: backend/src/baserow/contrib/database/api/views/kanban/serializers.py] — `KanbanViewFieldOptionsSerializer("hidden","order")`.
- [Source: backend/src/baserow/contrib/database/api/views/views.py — ViewFieldOptionsView.patch] — shared field-options PATCH endpoint (reused).
- [Source: web-frontend/modules/database/components/view/kanban/KanbanViewHeader.vue] — "Customize cards" → `ViewFieldsContext` wiring + `updateCoverImageField`/`updateFieldOptionsOfField`/`orderFieldOptions` with permission guards.
- [Source: web-frontend/modules/database/components/view/ViewFieldsContext.vue] — shared cover-image picker (file-representable fields) + hidden/reorder; also used by Gallery.
- [Source: web-frontend/modules/database/components/view/kanban/KanbanView.vue] — `cardFields`/`hiddenFields`/`coverImageField` computeds; `RowCard` binding `:fields="cardFields"` `:cover-image-field="coverImageField"`.
- [Source: web-frontend/modules/database/components/card/RowCard.vue:24–53] — cover block + `coverImageUrl` (`thumbnails.card_cover.url`) + field rendering.
- [Source: web-frontend/modules/database/store/view/kanban.js:31–41; store/view/bufferedRows.js:24,57–61,1297–1299; store/view/fieldOptions.js:46,96,121,128,168] — `fetchInitial` field-option hydration + inherited field-option actions/getters.
- [Source: web-frontend/modules/database/components/view/gallery/GalleryViewHeader.vue] — public MIT reference for the identical card-appearance UX (clean-room "what complete looks like").
- [Source: backend/tests/.../view/test_kanban_view_type.py; api/views/kanban/test_kanban_view_views.py] — existing Kanban tests to EXTEND (not duplicate); current gap = no cover-image / field-face-selection coverage.
- [Source: 3-1-create-and-configure-a-kanban-view.md] — Kanban derived from Gallery; cover field pre-staged; OSS-only test profile; provenance gate.
- [Source: 3-2-drag-a-kanban-card-between-columns.md Dev Agent Record] — method-level unit pattern to dodge the premium-store override/OOM; E2E author-only lane.
- [Source: 1-1-establish-the-clean-room-process-gate.md] — provenance = hard merge gate; "influenced by" = contamination.
- [Source: memory clean-room-isolation-porous] — clean-room drift during verify/debug; hold the line.
- [Source: memory baserow-open-core-license-constraint] — paid features need clean-room reimplement; PE/EE forbids copying.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (BMAD dev-story workflow)

### Debug Log References

- **OSS-only test execution.** `backend/src/baserow/config/settings/test.py` patches `os.getenv` so the real-env `BASEROW_OSS_ONLY` is ignored, but it still reads `TEST_ENV_FILE` from the real env then loads it via dotenv. Created `backend/.env.oss-test` (`BASEROW_OSS_ONLY=true`) and ran with `TEST_ENV_FILE=.env.oss-test` so the **core** Kanban (not premium's override) is the registered `kanban` view type under test. Without this, premium's KanbanView registers last and `test_kanban_view_type_registered` / cover-field tests fail with `ViewTypeDoesNotExist`.
- **Env wiring (no `just`):** `just` not on PATH; replicated justfile recipes directly — backend via `uv run pytest` with `PYTHONPATH=src:../premium/backend/src:../enterprise/backend/src` and `DATABASE_URL=postgres://baserow:baserow@localhost:5431/baserow-test-db` (docker `baserow-test-db`); frontend via `yarn vitest run`.
- **No full mount (3.2 lesson held).** Frontend tests bind the real `cardFields`/`hiddenFields`/`coverImageField` computeds and the header dispatch methods to a minimal fake `vm`; mounting the full `KanbanView` would register premium's Kanban store last → mock-miss + JS-heap OOM.

### Completion Notes List

- **Verify + close-test-gap + provenance, not a net-new build.** Every AC was verified against the existing Story 3.1 core implementation; no production code changed. Findings with line cites:
  - **AC #1 (field face + cover render).** `KanbanView.vue` `cardFields` = `fields.filter(filterVisibleFieldsFunction(fieldOptions)).sort(sortFieldsByOrderAndIdFunction(fieldOptions))`; `coverImageField` resolves `view.card_cover_image_field` → field object; both bound to `RowCard` (`:fields`, `:cover-image-field`). `RowCard.vue:24` renders `.card__cover` only when `coverImageField !== null` (empty-state icon `iconoir-media-image` when no image), and renders only fields in `fields` (`.card__field`). Configured from `KanbanViewHeader.vue` "Customize cards" → `ViewFieldsContext`. **Verified.**
  - **AC #2 (persist per view).** Two pre-existing PATCH paths: field face via shared `PATCH .../field_options/`; cover via generic `PATCH .../{id}/` carrying `card_cover_image_field` (`KanbanViewType.allowed_fields` includes it; `prepare_values` validates `can_represent_files`). Both re-hydrated by `fetchInitial` and round-trip through export/import. **Verified + new backend tests.**
  - **AC #3 (no row coloring).** `KanbanView.vue` passes no `decorationsByPlace` to `RowCard`; `decorationsByPlace` prop defaults undefined → `firstCellDecorations`/`wrapperDecorations` empty → no decorator components render. No Kanban row-coloring code path exists. **Verified.**
  - **AC #4 (grouping + cover always visible).** `KanbanViewType.get_hidden_fields` excludes the single-select field id and the cover-image field id even when their option is `hidden=True`. **Verified + new regression test.**
- **No defect found** during verification → no production code modified. Work is tests + provenance only.
- **Clean room held (Bucket A).** Nothing under `premium/`/`enterprise/` was opened, grepped, or recalled. All sources are the free-core 3.1 Kanban, the MIT Gallery it mirrors, the shared card/field-options components, or public docs. Provenance record validates PASS. PR must carry the `bucket-a` label.
- **Tests:** backend 22 passed (OSS-only), frontend 33 passed. E2E customize-cards scenario authored only (OSS-only CI lane; not run locally).

### File List

**New:**
- `docs/clean-room/provenance/3-3-configure-kanban-card-appearance.md`
- `backend/.env.oss-test`

**Modified (tests + test infra only — no production code):**
- `backend/tests/baserow/contrib/database/view/test_kanban_view_type.py` (cover-image set/persist/reject/other-table/null-on-delete, `get_hidden_fields` keeps single-select + cover visible, cover export/import round-trip)
- `backend/tests/baserow/contrib/database/api/views/kanban/test_kanban_view_views.py` (cover-image PATCH + persistence, non-file reject, `field_options` hidden PATCH persists)
- `web-frontend/test/unit/database/components/view/kanban/kanbanView.spec.js` (card-appearance computeds + `KanbanViewHeader` dispatch describe blocks)
- `e2e-tests/tests/database/kanban_view.spec.ts` (customize-cards + cover + persistence scenario)
- `e2e-tests/fixtures/database/view.ts` (added `updateFieldOptions` helper)

## Senior Developer Review (AI)

**Reviewer:** Tinsu (AI review-agent, claude-opus-4-8) · **Date:** 2026-06-10 · **Outcome:** ✅ Approve → done

### Scope & method
Adversarial review of a verify+test+provenance story. Every story claim was checked against live source (not the story's word), and the test suites were **re-run independently** rather than trusting the recorded counts.

### Verification results
- **AC #1 (field face + cover render)** — `KanbanView.vue:241–255` `cardFields`/`hiddenFields` use `filterVisibleFieldsFunction` (`utils/view.js:81`: `options && !options.hidden` → no-option ⇒ hidden) + `sortFieldsByOrderAndIdFunction`; `coverImageField` = `this.fields.find(... ) || null`. Bound to `RowCard` `:fields`/`:cover-image-field`. **Verified.**
- **AC #2 (persist per view)** — cover via generic `PATCH .../{id}/` (`allowed_fields` incl. `card_cover_image_field`, view_types.py:618); face via shared `field_options` PATCH; both re-hydrated by `fetchInitial`, export/import round-trips `card_cover_image_field_id` (view_types.py:744). **Verified.**
- **AC #3 (no row coloring)** — `KanbanView.vue` passes no `decorationsByPlace`; no Kanban coloring path. **Verified.**
- **AC #4 (grouping + cover always visible)** — `get_hidden_fields` skips `single_select_field_id` and `card_cover_image_field_id` even when `hidden=True` (view_types.py:873–875). Cover nulled on file-field delete via `after_field_delete` (view_types.py:894, soft-delete safe — FK `SET_NULL` only fires on hard delete). **Verified.**
- **Tests re-run:** backend `23 passed` (OSS-only, `TEST_ENV_FILE=.env.oss-test`, was 22 + 1 added), frontend `33 passed` (`yarn vitest run`). E2E selectors all resolve to real classes (`.hidings__cover`/`.hidings__item` in `ViewFieldsContext.vue`, `.card__cover`/`.card__field-name`/`.card__content` in `RowCard.vue`) and the "Customize cards" label matches `en.json:697`. **Author-only, not run (Docker lane) — as scoped.**
- **Provenance:** `validate_provenance()` → `Result(passed=True, 'valid provenance record')`; Bucket A, no `premium/`/`enterprise/` sources. **PASS.**
- **File List vs git:** accurate. Untracked `_bmad-output/.../test-summary-3-3.md`, story md, and modified `sprint-status.yaml`/orchestration md are excluded BMAD artifacts.

### Findings
- 🔴 CRITICAL: none · 🟠 HIGH: none · 🟡 MEDIUM: none
- 🟢 **LOW-1 (fixed):** AC #2 names `hidden`/**`order`** persistence but backend pinned only `hidden`. Added `test_patch_kanban_view_field_options_order_persists` (set/list round-trip of `order` through the shared endpoint). Green.
- 🟢 **LOW-2 (accepted, no change):** E2E AC #3 assertion is structural (`.card__content` count) and cannot prove decoration absence — acknowledged in-spec; AC #3 is pinned at the unit level (`RowCard` receives no decorations). No fix needed.

No production code was changed by the dev or the review — confirmed correct for a verify+test story.

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-06-09 | 0.1 | Story drafted via create-story workflow. Key finding: the card-appearance feature (field-face `hidden`/`order` + `card_cover_image_field` + "Customize cards" header) was already shipped in Story 3.1 by mirroring the public Gallery view — backend, store, header UI, and `RowCard` cover rendering all exist in core. Story 3.3 is therefore **verify + close the test gap + provenance**, not net-new feature build. Verified existing wiring at view_types.py:613–890, KanbanViewHeader.vue, KanbanView.vue, RowCard.vue. | Tinsu (create-story) |
| 2026-06-09 | 1.0 | dev-story executed. Verified AC #1–#4 against existing 3.1 core code (no defect found → no production code changed). Closed the test gap: backend 22 passed (OSS-only), frontend 33 passed. Authored OSS-only E2E customize-cards scenario (+`updateFieldOptions` fixture helper). Added Bucket A provenance record (validates PASS). Lint clean (Ruff/ESLint/Prettier). Status → review. | AI dev-agent (claude-opus-4-8) |
| 2026-06-10 | 1.1 | Adversarial senior-dev review (story-automator-review). Re-ran tests independently: backend 22→23 passed (OSS-only), frontend 33 passed, provenance `validate_provenance` → PASS. All ACs re-verified against live source (view_types.py:613–906 incl. `after_field_delete` cover-null at :894, `get_hidden_fields` guard :873–875; KanbanView.vue computeds; KanbanViewHeader.vue dispatch). No CRITICAL/HIGH/MEDIUM findings. LOW: AC #2 `order` persistence was unpinned (only `hidden`) → added `test_patch_kanban_view_field_options_order_persists`. Status → done. | AI review-agent (claude-opus-4-8) |
