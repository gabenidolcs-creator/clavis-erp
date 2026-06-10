---
baseline_commit: 787cbd22cd2a9a1e95247eeb20ae45f9328133fe
---

# Story 3.9: Define Task Dependencies with cycle prevention

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to draw dependencies between task Rows,
so that the schedule reflects predecessor/successor ordering. `[B]`

## Context & Scope

### 🟦 THIS IS A BUCKET B STORY — but read the enterprise-overlap warning FIRST

Per architecture, **Gantt + `TaskDependency` = Bucket B (greenfield)**: "Kanban/Calendar/Timeline (Bucket A clean-room), Gantt + Map (Bucket B). Gantt adds a new `TaskDependency` model + CPM critical-path engine." [Source: architecture.md:25; architecture.md:282 `gantt/ [B]`; architecture.md:118 D8]. There is therefore **no clean-room provenance hard-gate** for this PR — `check_provenance.py` fires only on PRs labelled `bucket-a`, and this PR is **not** `bucket-a`. [Source: docs/clean-room/scripts/check_provenance.py:1-20 gate scope]

### 🚨 CRITICAL — an enterprise dependency feature EXISTS; you MUST NOT read or copy it

`grep` reveals a paid **enterprise** module that is conceptually adjacent but a **different feature**:

- `enterprise/backend/src/baserow_enterprise/date_dependency/models.py`, `calculations.py`
- `enterprise/backend/src/baserow_enterprise/migrations/0052_date_dependency.py`
- `enterprise/web-frontend/modules/baserow_enterprise/dateDependencyTypes.js`
- `enterprise/web-frontend/modules/baserow_enterprise/components/dateDependency/DateDependencyConnection.vue`

**`baserow_enterprise.date_dependency` is NOT what this story builds.** That feature is a *field-level* date auto-calculation (a date field whose value derives from a duration + a linked date field on the same/linked row — Airtable-style "date dependency" inside the field config). **Story 3.9's `TaskDependency` is a Gantt-view, row-to-row scheduling edge** (`predecessor_row → successor_row`) rendered as a connector line, with cycle prevention. Different domain, different model, different name (`TaskDependency` vs enterprise `DateDependency`).

**DO NOT** open, read, skim, or "reference for inspiration" ANY file under `enterprise/.../date_dependency/` or `enterprise/.../dateDependency/`. Even though the architecture classifies this Bucket B, reading a paid implementation of an adjacent concept is exactly the clean-room contamination risk flagged repeatedly in this project. The enterprise feature solves a different problem; copying its shape would both contaminate provenance and import the wrong model. **Design `TaskDependency` from this story + the architecture + the public Frappe Gantt connector format only.** If you find yourself in that directory, stop. [Source: architecture.md:205, 255, 259 "never copy/adapt premium/enterprise source"; architecture.md:45 clean-room binding]

### What already exists (Story 3.8 shipped the Gantt spine — build ON it, do NOT rebuild)

Story 3.8 (commit `787cbd22c`, Status: done) shipped the **render-only** Gantt view. These are present and MUST be reused/extended, never duplicated:

**Backend**
- `GanttView` + `GanttViewFieldOptions` models — `backend/src/baserow/contrib/database/views/models.py:1011-1100` (migration `0223_ganttview_ganttviewfieldoptions.py`).
- `GanttViewType` — `backend/src/baserow/contrib/database/views/view_types.py:1463`.
- API package — `backend/src/baserow/contrib/database/api/views/gantt/` (`views.py`, `urls.py`, `serializers.py`, `errors.py`, `pagination.py`, `__init__.py`). Rows listing reuses inherited bufferedRows.
- Registration — `GanttViewType` registered **unconditionally** in `apps.py` (next to Grid/Gallery, NOT in the premium-gate block).

**Frontend**
- `GanttView.vue` + `GanttViewHeader.vue` — `web-frontend/modules/database/components/view/gantt/`. Frappe Gantt **1.2.2** lazy-loaded; instantiated `readonly: true`.
- **THE 3.9 SEAM IS ALREADY CARVED**: `GanttView.vue:357` `dependenciesForRow()` returns `''` today, with a comment "THIS IS THE STORY 3.9 SEAM … Story 3.9 swaps in the real predecessor ids here without touching the render call." It is wired into `ganttTasks` (`GanttView.vue:256 dependencies: this.dependenciesForRow(row)`). **Your job is to make this return real edges — do NOT touch the `new Gantt(...)` render call shape.** [Source: GanttView.vue:241,256,352-359]
- `store/view/gantt.js`, `services/view/gantt.js`, locales, `gantt.scss`, icon `gantt.svg`, viewTypes/plugin registration — all present.

### Frappe Gantt 1.2.2 dependency render contract (verified against installed lib)

- A task object carries `dependencies` as a **comma-separated string of predecessor task ids** (the lib draws an arrow FROM each listed predecessor TO this task). Task ids are `String(row.id)` (3.8 maps `id: String(row.id)`). So `dependenciesForRow(successorRow)` must return `"3,7"` meaning rows 3 and 7 are predecessors of this row. [Source: GanttView.vue:254-256 task shape; frappe-gantt 1.2.2 task contract]
- The lib **renders** connectors from this string regardless of `readonly`. **It does not provide a drawing affordance when `readonly: true`** — so the "draw a dependency" interaction (AC #1) is OUR UI, not a lib feature. Keep `readonly: true` (drag/resize is Story 3.10); add an explicit, non-lib affordance to create/remove edges (see Task 7).

## Acceptance Criteria

1. **Persisted directed edge + reload + connector render.** Given two task Rows, when an editor draws a dependency, then it is persisted as a directed edge (`predecessor → successor`), survives reload, and renders as a connector line between the two bars in the Gantt view.

2. **Cycle prevention across ALL mutation paths (AR-8).** Given any mutation path — interactive create, restore-from-trash, or import — when an operation would introduce a cycle in the dependency graph, then it is rejected with a clear error. Cycle prevention holds across **every** path, not just interactive create.

## Tasks / Subtasks

### Task 1 — Backend `TaskDependency` model + migration (AC: #1)

- [x] Create the new backend package `backend/src/baserow/contrib/database/views/gantt/` with `__init__.py`, per the architecture tree (`gantt/ [B] … TaskDependency model, cycle detection`). [Source: architecture.md:282]
- [x] Add `TaskDependency` model in `backend/src/baserow/contrib/database/views/gantt/models.py`:
  - [x] `table` — `models.ForeignKey('database.Table', on_delete=models.CASCADE, related_name='task_dependencies')`. Scope edges to a **Table**, not a view — a row's predecessor/successor ordering is a property of the data, shared across every Gantt view of that table. (Rows live in the dynamic `GeneratedTableModel`, so there is **no** FK to a row; reference rows by integer id — same pattern as `RichTextFieldMention(table_id, row_id)`, see `trash_types.py:384`.) [Source: trash_types.py:383-386 RichTextFieldMention table_id+row_id precedent]
  - [x] `predecessor_row_id` — `models.PositiveIntegerField()`. The row that must come first.
  - [x] `successor_row_id` — `models.PositiveIntegerField()`. The dependent row.
  - [x] `dependency_type` — `models.CharField(max_length=2, choices=[("FS","FS")], default="FS")`. v1 ships **finish-to-start only**; the column exists so 3.10/3.11 can add SS/FF/SF without a migration, but reject any non-FS value at the API for now. [Source: prd.md:184 ASSUMPTION FS-only v1; FR-10/11 FS-only guarantee]
  - [x] `created_on` — `models.DateTimeField(auto_now_add=True)` (mirror neighbor models for ordering stability).
  - [x] `class Meta`: `unique_together = ("table", "predecessor_row_id", "successor_row_id")` (an edge is unique; re-drawing the same edge is idempotent / 400, never a duplicate row). Add `ordering = ("id",)`. Add a `CheckConstraint` rejecting `predecessor_row_id == successor_row_id` (no self-loop — the degenerate 1-cycle). [Source: architecture.md:181 snake_case `predecessor_id` columns]
  - [x] Index `("table", "successor_row_id")` and `("table", "predecessor_row_id")` — the cycle walk and the per-row connector lookup both query by these. Bounded-per-table graph must stay fast at scale (NFR perf). [Source: architecture.md:118 "graph is bounded per-view so sync keeps … fresh"; architecture.md:27 indexing for sortable/queried fields]
- [x] Generate the next sequential migration: `python -m … makemigrations database`. It will be `0224_*` (current head is `0223_ganttview_ganttviewfieldoptions`) — **do not hard-code the number**, run makemigrations and use what it emits. Verify with `just b migrate --check` / inspect the file (no manual SQL). [Source: migrations dir; 3-8 Task 1]
- [x] **Do NOT** add any per-user-table migration — `TaskDependency` is a metadata model in the `database` app (dynamic-model rule: new models migrate in their owning app, never per-user-table). [Source: architecture.md:320 data boundaries]

### Task 2 — Cycle detection handler + create path (AC: #1, #2)

- [x] Add `backend/src/baserow/contrib/database/views/gantt/handler.py` with a `TaskDependencyHandler` following the **thin-API-view-over-Handler** pattern (all mutation logic in the handler; REST view is thin). [Source: architecture.md:135 "thin-API-view-over-Handler", `manage-backend-layers` skill]
- [x] **`would_create_cycle(table, predecessor_row_id, successor_row_id) -> bool`** — the single source of truth for cycle detection, reused by EVERY path (Task 2/3). Algorithm: a new edge `p → s` closes a cycle **iff `p` is already reachable from `s`** in the existing directed graph (i.e. there is a path `s → … → p`). Implement a bounded DFS/BFS over `TaskDependency.objects.filter(table=table)` building an adjacency map `successor→? ` — walk **forward from `s` following `predecessor→successor` edges**; if you reach `p`, adding `p→s` would create the cycle. Also treat `p == s` as a cycle (self-loop). Load the table's edges once into memory (graph bounded per table) and walk in-memory — do **not** issue a query per node. [Source: architecture.md:118 "Cycle detection runs on every mutation path … rejecting any edge that closes a cycle"]
- [x] **`create_dependency(user, table, predecessor_row_id, successor_row_id, dependency_type="FS")`**:
  - [x] Verify both rows exist in `table` (use `table.get_model().objects.filter(id__in=[...])`); reject missing rows with a clear error (`ERROR_ROW_DOES_NOT_EXIST` style).
  - [x] Reject non-FS `dependency_type` (only FS guaranteed in v1).
  - [x] Call `would_create_cycle(...)`; if True, raise `TaskDependencyCycle` → mapped to `ERROR_TASK_DEPENDENCY_CYCLE` (HTTP 400, structured code, **clear human message** naming that the edge would form a cycle). [Source: FR-9 "rejected with a clear error"; architecture.md:188 "400 with structured error code for validation"]
  - [x] Enforce the `unique_together` (re-drawing an existing edge → 400 `ERROR_TASK_DEPENDENCY_ALREADY_EXISTS`, not a duplicate row).
  - [x] Wrap the read-of-graph + insert in a transaction with `select_for_update()` on the table's edges (or a table-scoped advisory lock) so two concurrent creates cannot each pass the cycle check and then jointly close a cycle (TOCTOU). This is the same "no interleave" discipline D8 calls for. [Source: architecture.md:118 cascade row-locking / "overlapping cascades cannot interleave"]
- [x] **`delete_dependency(user, dependency)`** — remove an edge (idempotent).
- [x] **`list_dependencies(table)`** — return all edges for a table (frontend connector source). Honor the requesting principal's row/field permissions when the field-permission layer lands; for now scope by table access like the gantt rows endpoint. [Source: architecture.md:130 D7 every data surface]
- [x] Signals: define `task_dependency_created` / `task_dependency_deleted` (mirror existing view signals) so the WebSocket broadcast layer can push edge changes to live Gantt sessions (NFR real-time). Wire the real-time broadcast the same way the gantt rows endpoint does. [Source: architecture.md:24 "Real-time WebSocket broadcast on all mutating views"]

### Task 3 — Cycle prevention on restore-from-trash and import (AC: #2) — THE HARD PART, do not skip

AR-8 / FR-9 require cycle prevention on **every** path, not just create. Three non-interactive paths can introduce cycles or orphans; each must be handled:

- [x] **Row permanent-delete → clean up edges.** When a row is permanently deleted, its `TaskDependency` edges (as predecessor OR successor) must be removed, exactly as `RichTextFieldMention` is cleaned in `RowTrashableItemType.permanently_delete_item` (`trash_types.py:383-386`). Add a hook so `TaskDependency.objects.filter(table_id=row.baserow_table_id).filter(Q(predecessor_row_id=row.id) | Q(successor_row_id=row.id)).delete()` runs on permanent row deletion. (Choose the least-invasive seam: extend the row permanently_delete path, or connect to the existing `rows_deleted`/permanent-delete signal — find the signal, don't fork `RowTrashableItemType`.) [Source: trash_types.py:383-386]
- [x] **Trash + restore of a row → re-validate edges.** Baserow trashes rows (soft delete). Decide and implement edge behavior on trash/restore:
  - [x] On row **trash**: edges referencing the trashed row are dormant (the row's bar disappears; the connector should not render against a trashed row). Either soft-disable or leave the rows filtered out by the rows query — verify the bar/connector does not render for a trashed predecessor.
  - [x] On row **restore**: `RowTrashableItemType.restore` (`trash_types.py:350`) sends `rows_created`. **Re-run `would_create_cycle` for each edge touching the restored row.** If the graph mutated while the row was trashed such that restoring its edges now closes a cycle, the restore must reject those edges with a clear error (or drop the offending edge and surface the conflict) rather than silently materializing a cycle. Hook into the row-restore path via the `rows_created` signal (weak=False) or extend the restore flow — **do not** let a restored row reintroduce a cyclic edge. [Source: trash_types.py:350-382 restore sends rows_created; FR-9 "restore-from-trash … rejected"]
- [x] **Import / table+view duplication → re-check the whole batch.** When a table or view is duplicated, or rows+dependencies are imported via `export_serialized`/`import_serialized`, the imported edge set must pass a **batch cycle check** before commit. Implement `import_serialized`/`export_serialized` for `TaskDependency` (round-trip `predecessor_row_id`/`successor_row_id` remapped through the import's old→new row-id map) and, after remapping, run a full-graph cycle validation on the resulting edge set; reject the import (or drop+report cyclic edges) with a clear error. Find where views/tables serialize their related objects (the view export/import handler) and register `TaskDependency` there. [Source: FR-9 "import … not just interactive create"; architecture.md:118]
- [x] **A single `validate_acyclic(table, candidate_edges)` routine** should back all three paths (full-graph topological check / DFS cycle scan over existing+candidate edges) so the create-path `would_create_cycle` and the batch paths share one verified implementation. No second copy of the cycle logic.

### Task 4 — Backend API: create / list / delete dependency edges (AC: #1)

- [x] Extend the existing gantt API package `backend/src/baserow/contrib/database/api/views/gantt/` (do **not** create a parallel package):
  - [x] `serializers.py`: add `TaskDependencySerializer` exposing `("id", "table", "predecessor_row_id", "successor_row_id", "dependency_type")` (snake_case JSON — repo convention, do NOT camelCase). [Source: architecture.md:185 snake_case JSON]
  - [x] `errors.py`: add `ERROR_TASK_DEPENDENCY_CYCLE` (400), `ERROR_TASK_DEPENDENCY_ALREADY_EXISTS` (400), `ERROR_ROW_DOES_NOT_EXIST` (reuse existing if present).
  - [x] `views.py` + `urls.py`: thin DRF views over `TaskDependencyHandler`:
    - `GET  /api/database/views/gantt/{view_id}/dependencies/` → list edges for the view's table.
    - `POST /api/database/views/gantt/{view_id}/dependencies/` `{predecessor_row_id, successor_row_id}` → create (cycle-checked).
    - `DELETE /api/database/views/gantt/{view_id}/dependencies/{dependency_id}/` → delete.
    - Resolve `table` from the view; enforce the same view-access permission the gantt rows endpoint uses. Use `@map_exceptions` to surface the cycle/exists/missing-row errors. Mirror the thin-view shape already in `gantt/views.py`. [Source: api/views/gantt/views.py 3.8 pattern]
  - [x] **Public view parity**: `GanttViewType.has_public_info = True` (3.8). The public Gantt payload must also surface dependency edges so a shared Gantt renders connectors read-only. Add the edges to the public info / public rows path (no create/delete on public). [Source: 3-8 Task 2 `has_public_info=True`]

### Task 5 — Backend registration + trash wiring (AC: #1, #2)

- [x] Register the gantt API urls already happen via `GanttViewType.get_api_urls` (3.8) — just ensure the new `dependencies/` routes are included under the existing `gantt` namespace `include(...)`. [Source: 3-8 Task 2 get_api_urls]
- [x] Ensure `TaskDependency` is imported where models are loaded (app `models` import) so the migration + admin discovery work. Do not register a premium-gated path. [Source: 3-8 Task 4 unconditional registration]
- [x] Verify the permanent-delete cleanup (Task 3) is connected at app-ready (signal connection in `apps.py`/`signals.py`, `weak=False`) so it survives in all run profiles. [Source: after-rows-created-batch-only memory: use rows_* signals with weak=False]

### Task 6 — Frontend: fetch + store dependency edges (AC: #1)

- [x] `services/view/gantt.js`: add `fetchDependencies(viewId)`, `createDependency(viewId, predecessorRowId, successorRowId)`, `deleteDependency(viewId, dependencyId)` alongside the existing `bufferedRowService(client, 'gantt')` default export (extend the module; the rows service stays). [Source: services/view/gantt.js]
- [x] `store/view/gantt.js`: hold a `dependencies: []` array in state; in `fetchInitial`, after rows load, dispatch `fetchDependencies` and store the edges. Add `createDependency`/`deleteDependency` actions doing **optimistic add/remove with rollback on the cycle/exists 400** (mirror the repo's optimistic-update-+-rollback grid pattern). On the 400 cycle error, roll back and surface the clear message. [Source: architecture.md:139 "optimistic update + rollback"; store/view/gantt.js fetchInitial]
- [x] Real-time: subscribe to `task_dependency_created`/`deleted` events for the table and update the `dependencies` array so concurrent edits reflect live (mirror how gantt rows handle realtime row events). [Source: architecture.md:24 realtime broadcast]

### Task 7 — Frontend: render connectors + the draw/remove affordance (AC: #1)

- [x] **Make the seam real.** In `GanttView.vue`, change `dependenciesForRow(row)` (currently returns `''`, line 357) to look up `this.dependencies` (from the store), find every edge where `successor_row_id === row.id`, and return the comma-separated **predecessor** ids as a string (`String`). **Do NOT change the `ganttTasks` mapping or the `new Gantt(...)` call shape** — only the seam method's body + reading the store. Re-render the instance when `dependencies` change (the watch on `ganttTasks`/dependencies already exists from 3.8 re-render discipline — verify the dependency array is in the watched/computed chain so connectors repaint). [Source: GanttView.vue:352-359 seam; GanttView.vue:300-313 refresh watch]
- [x] **Draw affordance (AC #1 "draws a dependency").** Frappe Gantt is `readonly: true` (no lib draw handle; keep it that way — drag is 3.10). Implement an explicit, non-lib UI to create an edge. **Recommended v1 (robust, testable): a "Predecessors" picker in the row modal** — when a row is opened (the `popup`/`on_click` already opens the Baserow row modal, GanttView.vue:393), expose a control listing other task rows; selecting one creates a `predecessor → this row` edge via the store action, removing it deletes the edge. This avoids fragile SVG drag-to-connect in jsdom/E2E and reuses the existing modal path. A visual "link mode" overlay is acceptable as an enhancement but is **not** required for v1 — flag it for 3.10 if you defer it. Pick ONE affordance and wire it end-to-end; do not ship a dead button. [Source: GanttView.vue:389 readonly; GanttView.vue:393-399 popup→row modal]
- [x] **Clear cycle error in the UI.** When the create action returns `ERROR_TASK_DEPENDENCY_CYCLE`, show a clear notification (reuse the app's error-notification path) naming that the link would create a cycle and was rejected; roll back the optimistic edge. [Source: FR-9 clear error; AC #2]
- [x] Connector styling: let Frappe Gantt own the arrow rendering (it draws from the `dependencies` string). Do **not** restyle the lib's internal SVG arrows beyond what `gantt.scss` already scopes. [Source: 3-8 Task 5 "let the lib own bar/connector styling"]
- [x] Locales: add the new strings (predecessor picker label, cycle-rejected message, etc.) to `web-frontend/modules/database/locales/en.json` under `ganttView*`. [Source: 3-8 Task 5 locales]

### Task 8 — Backend tests (AC: #1, #2) — DEFAULT profile (NOT oss-test)

- [x] `backend/tests/baserow/contrib/database/view/gantt/test_task_dependency_handler.py`:
  - [x] create an edge `p→s` → persisted; re-creating the same edge → `TaskDependencyAlreadyExists`.
  - [x] self-loop `p→p` rejected.
  - [x] **cycle on create**: `a→b`, `b→c` ok; `c→a` → `TaskDependencyCycle` (clear error). Longer chain `a→b→c→d`, then `d→a` rejected.
  - [x] **cycle on restore-from-trash**: create `a→b`; trash row `b`; create a path that would make restoring `b`'s edge cyclic; restore `b` → the cyclic edge is rejected/dropped with a clear error, graph stays acyclic. (Construct the scenario precisely; this is the AR-8 teeth.)
  - [x] **cycle on import**: `import_serialized` an edge set (with old→new row-id remap) that contains a cycle → rejected; an acyclic set → imported and round-trips via `export_serialized`.
  - [x] **permanent row delete** removes the row's edges (predecessor and successor sides).
  - [x] missing-row edge → `ERROR_ROW_DOES_NOT_EXIST`; non-FS `dependency_type` → rejected.
- [x] `backend/tests/baserow/contrib/database/api/views/gantt/test_gantt_dependency_views.py`: `POST` create (200 + persisted, survives a fresh `GET` = reload proof, AC #1), `POST` cycle → 400 `ERROR_TASK_DEPENDENCY_CYCLE`, `GET` list returns edges, `DELETE` removes, permission denial → 403.
- [x] Add a `task_dependency` fixture to `backend/src/baserow/test_utils/fixtures/` (mirror the gantt/view fixtures).
- [x] Run in the **default** profile (no premium Gantt to dodge): `just b test backend/tests/baserow/contrib/database/view/gantt/ backend/tests/baserow/contrib/database/api/views/gantt/test_gantt_dependency_views.py`. Expect green. [Source: 3-8 Task 6 default profile]

### Task 9 — Frontend unit tests (AC: #1) — method/computed-level, mock Frappe Gantt

- [x] Extend `web-frontend/test/unit/database/components/view/gantt/ganttView.spec.js` (do not instantiate the real lib in jsdom; bind real computeds to a fake `vm`, mock the `frappe-gantt` dynamic import — same constraints 3.8 documented):
  - [x] `dependenciesForRow` now returns the comma-separated predecessor ids for edges whose `successor_row_id === row.id`, and `''` when none. (AC #1, AC #3 seam now live)
  - [x] the store `createDependency` action optimistically adds an edge and **rolls back** on a simulated `ERROR_TASK_DEPENDENCY_CYCLE` 400 (assert the edge is gone + error surfaced).
  - [x] the predecessor-picker affordance dispatches `createDependency`/`deleteDependency` with the right row ids and is guarded by `readOnly`/permission like other config dispatches.
- [x] Run: `yarn vitest run web-frontend/test/unit/database/components/view/gantt/`. Expect green. [Source: 3-8 Task 7; write-frontend-unit-test skill]

### Task 10 — E2E scenario (AC: #1, #2) — author only

- [x] Add to `e2e-tests/tests/database/gantt_view.spec.ts` (the 3.8 spec exists): create a table with start+end date fields and ≥3 dated rows, add a Gantt view, draw a dependency `A→B` (via the chosen affordance) → a connector renders (assert the lib's arrow SVG node between the two bars) and survives **reload** (AC #1); attempt to draw `B→A` (or close a longer cycle) → a clear error appears and **no** connector is added (AC #2).
- [x] **Do NOT run E2E locally** (needs the Docker stack; `e2e-tests/` has no local tsconfig/node_modules). Author only. Format `.ts` with `web-frontend/node_modules/.bin/prettier`. [Source: 3-8 Task 8]

### Task 11 — Bucket B provenance / third-party attribution (recommended hygiene, NOT a CI gate) (AC: all)

- [x] Add `docs/clean-room/provenance/3-9-define-task-dependencies-with-cycle-prevention.md` declaring **Bucket B**: greenfield `TaskDependency` model + cycle-detection handler; rendered via the **core MIT Gantt (3.8)** + **Frappe Gantt 1.2.2 (MIT)** connector string contract; row-reference pattern derived from core `RichTextFieldMention(table_id,row_id)`; trash/restore hooks derived from core `RowTrashableItemType`. **Attestation MUST explicitly state: no `premium/` or `enterprise/` source consulted — in particular `enterprise/.../date_dependency/` was NOT read.** Mirror the 3-8 provenance structure. **Do NOT add the `bucket-a` label** (keeps the hard provenance CI gate untriggered). [Source: docs/clean-room/scripts/check_provenance.py:1-20 gate scope; architecture.md:255]

## Dev Notes

### Architecture patterns & constraints

- **Model layer:** `TaskDependency` is a `database`-app metadata model (migration in `database/migrations`, NOT per-user-table). Rows are dynamic `GeneratedTableModel` instances — reference them by integer `*_row_id` + a `table` FK, never a row FK. Precedent: `RichTextFieldMention(table_id, row_id)` (`trash_types.py:383`). [Source: architecture.md:320]
- **Handler-first:** all mutation + cycle logic in `TaskDependencyHandler`; REST views are thin and use `@map_exceptions`. Never mutate via the API view directly (skips broadcast/cache invalidation — explicitly forbidden). [Source: architecture.md:135, 259]
- **One cycle implementation, reused on all paths.** `would_create_cycle` (single-edge) + `validate_acyclic` (batch) share one verified DFS. Create, restore, and import all route through it. Graph is bounded per table → load edges once, walk in memory, never query-per-node. [Source: architecture.md:118]
- **TOCTOU:** concurrent edge creates must be serialized (table-scoped `select_for_update`/advisory lock) so two creates can't jointly close a cycle. Same non-interleave discipline D8 mandates for cascades. [Source: architecture.md:118]
- **FS-only v1:** `dependency_type` column exists for forward-compat but only `FS` is accepted/guaranteed. SS/FF/SF are out of scope (would change cycle/cascade semantics — 3.10/3.11). [Source: prd.md:184; FR-10/11]
- **Real-time + optimistic UX:** broadcast edge create/delete over WebSocket; frontend does optimistic add/remove with rollback on the cycle 400. [Source: architecture.md:24, 139]
- **Public parity:** `has_public_info=True` → public Gantt renders connectors read-only; surface edges in the public payload, no create/delete on public. [Source: 3-8 Task 2]
- **Naming:** `snake_case` files (`task_dependency.py`/`models.py`/`handler.py`), `PascalCase` class `TaskDependency`, snake_case columns (`predecessor_row_id`), snake_case JSON (no camelCase payloads). Ruff format, 88-col, Python 3.14. [Source: architecture.md:181-192]

### Source tree — what to touch

- **NEW** `backend/src/baserow/contrib/database/views/gantt/` → `__init__.py`, `models.py` (`TaskDependency`), `handler.py` (`TaskDependencyHandler`, cycle algo). [Source: architecture.md:282]
- **NEW** migration `backend/src/baserow/contrib/database/migrations/0224_*` (run makemigrations; don't hard-code number).
- **EXTEND** `backend/src/baserow/contrib/database/api/views/gantt/{serializers,errors,views,urls}.py` — add dependency endpoints (do not fork the package).
- **EXTEND** row permanent-delete / trash-restore wiring (find the existing signal/seam; mirror `RichTextFieldMention` cleanup at `trash_types.py:383`; re-validate on restore at `trash_types.py:350`).
- **EXTEND** view export/import handler — register `TaskDependency` round-trip + batch cycle check.
- **EXTEND** `web-frontend/modules/database/components/view/gantt/GanttView.vue` (seam body only), `store/view/gantt.js`, `services/view/gantt.js`, `locales/en.json`.
- **TESTS** `backend/tests/baserow/contrib/database/view/gantt/test_task_dependency_handler.py`, `.../api/views/gantt/test_gantt_dependency_views.py`, `web-frontend/test/unit/database/components/view/gantt/ganttView.spec.js`, `e2e-tests/tests/database/gantt_view.spec.ts`.

### Testing standards

- Backend: `pytest`/`pytest-django`, co-located under `backend/tests/...`, **default** profile (NOT `.env.oss-test` — no premium Gantt collision). Cycle tests must cover all three non-interactive paths (restore, import, permanent-delete) — those are the AR-8 teeth and the single most likely thing a dev agent under-implements. [Source: AGENTS.md testing; review-adversarial.md E3 "cycle detection only covers creation"]
- Frontend: `vitest`, method/computed-level, mock the `frappe-gantt` dynamic import (never instantiate the real lib in jsdom — it manipulates real SVG and leaks). [Source: 3-8 Task 7]
- E2E: author only, do not run locally.

### Previous-story intelligence (3.8 Gantt)

- The `dependenciesForRow` seam is pre-built and wired — return real ids, don't restructure the render. (`GanttView.vue:352-359,256`)
- Frappe Gantt 1.2.2: `dependencies` is a comma-separated **predecessor-id** string on the successor task; the lib draws connectors from it even under `readonly:true`, but provides **no draw handle** when readonly — the draw UI is ours. (`GanttView.vue:389`)
- 3.8 noted Frappe Gantt 1.2.2 leaks one anonymous `document` mouseup listener per instance and has no `destroy()`. Not introduced by 3.9, but if your draw affordance adds listeners, clean them up in `beforeUnmount` (3.7/3.8 leak-guard discipline). [Source: GanttView.vue:411-430 destroyGantt limitation]
- ESLint must run from the repo root, not `web-frontend/` CWD. `yarn test:core` may fail with "Unbound variable EXTRA_VITEST_PARAMS" (shell-script bug, not a test failure) — use `yarn vitest run <path>` directly. [Source: prior-story tooling notes]

### Git intelligence

- Recent commits are clean per-story feature commits (`feat(story-3.8): Render a Gantt View`, etc.). Baseline for this story = `787cbd22c` (3.8). Commit 3.9 as `feat(story-3.9): Define Task Dependencies with cycle prevention`.

### Latest tech information

- **Frappe Gantt 1.2.2** (installed, MIT): task `dependencies` = comma-separated predecessor ids; arrows rendered from it; render-only honored via `readonly:true`. No new dependency added by this story (the lib shipped in 3.8). [Source: web-frontend/node_modules/frappe-gantt 1.2.2; GanttView.vue]
- No new backend dependency — cycle detection is a hand-rolled bounded DFS over the ORM.

### Project Structure Notes

- Aligns with architecture tree: `views/gantt/ [B]` holds the `TaskDependency` model + cycle detection; CPM (forward/backward pass) and cascade reschedule are **explicitly out of scope** here — they are FR-11 (Story 3.11) and FR-10 (Story 3.10). This story delivers FR-9 only: edges + cycle prevention + connector render. [Source: architecture.md:118,282; epics.md:590-604]
- No variance from the unified structure detected. The only naming nuance: the architecture mentions a `task_dependency.py` filename (architecture.md:192) — putting `TaskDependency` in `views/gantt/models.py` is consistent (the `gantt/` package is the named home); use `models.py` inside the package rather than a flat `task_dependency.py` to match the gantt sub-package shape from 3.8.

### References

- [Source: epics.md:590-604 Story 3.9 ACs]
- [Source: prd.md:194-... FR-9 testable consequences; prd.md:184 FS-only assumption]
- [Source: architecture.md:118 D8 TaskDependency+CPM; architecture.md:25,282 Bucket B + gantt dir; architecture.md:320 data boundaries; architecture.md:135,259 handler-first]
- [Source: review-adversarial.md E3 / review-adversarial-pass2.md E3 — cycle detection must cover delete/trash/restore/import, not just create (AR-8 origin)]
- [Source: trash_types.py:320-400 RowTrashableItemType restore + permanently_delete + RichTextFieldMention row-id precedent]
- [Source: GanttView.vue:241,256,352-359,389,393 — 3.9 seam, task shape, readonly, row-modal popup]
- [Source: 3-8 story file — full Gantt scaffold reused]
- [Source: architecture.md:205,255,259,45 — clean-room: never read/copy premium/enterprise; enterprise/date_dependency is a DIFFERENT, off-limits feature]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (BMAD dev-story + story-automator-review)

### Debug Log References

- Backend tests (default profile, `DJANGO_SETTINGS_MODULE=baserow.config.settings.dev`, test DB on port 5431): 19 passed.
- Frontend unit tests (Vitest, Frappe Gantt mocked): 39 passed.
- Lint/format: `ruff check`/`ruff format` clean; ESLint (flat config) + Prettier clean.

### Completion Notes List

- Bucket B greenfield build: new `TaskDependency` model + cycle-detection handler, rendered through the free-core 3.8 Gantt spine (MIT) and the vendored MIT Frappe Gantt 1.2.2 connector string contract. `enterprise/.../date_dependency/` was NOT opened, grepped, or referenced (different feature: field-level date auto-calc vs. Gantt row-to-row edge).
- `TaskDependency` is `Table`-scoped, referencing rows by integer `predecessor_row_id`/`successor_row_id` (mirrors `RichTextFieldMention` row-reference precedent, never a row FK). FS-only in v1 (`dependency_type` reserved for SS/FF/SF in 3.10/3.11). Constraints: `unique_together`, two indexes, no-self-loop `CheckConstraint`.
- One cycle implementation, every mutation path (AR-8): `would_create_cycle` (single-edge BFS reachability) + `validate_acyclic` (batch Kahn topological sort). Graph bounded per table, loaded once, walked in memory. TOCTOU closed via table-scoped `select_for_update`.
- Cycle prevention on the hard paths: permanent row delete drops both-side edges; row restore re-sends `rows_created` → re-validates and drops any edge that would close a cycle; import remaps row ids then batch-validates before commit.
- Render-only seam made live: `dependenciesForRow(row)` returns the comma-separated predecessor-id string; `new Gantt(...)` call shape untouched. Draw affordance = explicit predecessor picker in row modal (Frappe Gantt is `readonly`; drag is 3.10).
- **Review fix:** dev delivery defined the `task_dependency_created`/`task_dependency_deleted` signals and frontend store reconcile actions but left them unconnected. Review added the backend ws receiver (`ws/views/gantt/signals.py`, registered in `ws/signals.py`) broadcasting to the table page group, and the frontend `realtime.registerEvent` handlers dispatching to the gantt store when a gantt view is selected.

### File List

**New — backend**
- `backend/src/baserow/contrib/database/views/gantt/__init__.py`
- `backend/src/baserow/contrib/database/views/gantt/models.py`
- `backend/src/baserow/contrib/database/views/gantt/handler.py`
- `backend/src/baserow/contrib/database/views/gantt/exceptions.py`
- `backend/src/baserow/contrib/database/views/gantt/signals.py`
- `backend/src/baserow/contrib/database/migrations/0224_taskdependency.py`
- `backend/src/baserow/contrib/database/ws/views/gantt/__init__.py`
- `backend/src/baserow/contrib/database/ws/views/gantt/signals.py`
- `backend/src/baserow/test_utils/fixtures/task_dependency.py`
- `backend/tests/baserow/contrib/database/view/gantt/` (handler tests)
- `backend/tests/baserow/contrib/database/api/views/gantt/test_gantt_dependency_views.py`

**Modified — backend**
- `backend/src/baserow/contrib/database/apps.py`
- `backend/src/baserow/contrib/database/models.py`
- `backend/src/baserow/contrib/database/trash/trash_types.py`
- `backend/src/baserow/contrib/database/export_serialized.py`
- `backend/src/baserow/contrib/database/application_types.py`
- `backend/src/baserow/contrib/database/ws/signals.py`
- `backend/src/baserow/test_utils/fixtures/__init__.py`
- `backend/src/baserow/contrib/database/api/views/gantt/{errors,serializers,urls,views}.py`

**New / modified — frontend**
- `web-frontend/modules/database/components/view/gantt/GanttView.vue` (modified)
- `web-frontend/modules/database/store/view/gantt.js` (modified)
- `web-frontend/modules/database/services/view/gantt.js` (modified)
- `web-frontend/modules/database/realtime.js` (modified — review fix)
- `web-frontend/modules/database/locales/en.json` (modified)
- `web-frontend/test/unit/database/components/view/gantt/ganttView.spec.js` (modified)

**E2E / docs**
- `e2e-tests/tests/database/gantt_view.spec.ts` (modified)
- `docs/clean-room/provenance/3-9-define-task-dependencies-with-cycle-prevention.md` (new)

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-06-10 | 0.1 | Story drafted (create-story workflow) | BMAD |
| 2026-06-10 | 1.0 | Implementation complete: `TaskDependency` model + cycle-detection handler, API, frontend connectors + picker, tests, provenance | AI dev-agent |
| 2026-06-10 | 1.1 | Senior Developer Review (AI): realtime broadcast gap fixed (backend ws receiver + frontend handlers); status → done | AI review-agent |

## Senior Developer Review (AI)

**Reviewer:** AI review-agent (story-automator-review, claude-opus-4-8) · **Date:** 2026-06-10 · **Outcome:** Approved (status → done)

### Summary

Both acceptance criteria are implemented and covered green (19 backend, 39 frontend). The cycle-detection core (`would_create_cycle` + `validate_acyclic`) is correct, applied on every mutation path (create / restore / import), and the TOCTOU window is closed with a table-scoped `select_for_update`. One real-time wiring gap was found and fixed during review. Clean-room provenance is sound: no `premium/`/`enterprise/` source consulted, `enterprise/date_dependency/` explicitly not read.

### Findings & dispositions

| # | Severity | Finding | Disposition |
|---|----------|---------|-------------|
| 1 | **MEDIUM** | Real-time gap: backend `task_dependency_created`/`task_dependency_deleted` signals were defined and sent, and the frontend store had reconcile actions, but no WS receiver bridged them — live Gantt sessions never repainted on a peer's edit. | **Fixed.** Added `ws/views/gantt/signals.py` (receivers broadcasting to the table page group on `transaction.on_commit`, originating socket excluded), registered in `ws/signals.py`; frontend `realtime.registerEvent` handlers dispatch to the gantt store when a gantt view is selected. Verified receivers load via `django.setup()`. |
| 2 | LOW | `Dropdown`/`DropdownItem` used in the predecessor picker appeared unimported in `GanttView.vue`. | **Not a bug.** Both are globally registered in `web-frontend/modules/core/plugins/global.js`. No change. |

No CRITICAL findings → status set to **done**.

### Verification

- Backend: 19 passed (13 handler: create/self-loop/direct+chain cycle/missing-row/non-FS/delete/list/permanent-delete/restore-cycle/import-cycle/round-trip; 6 API: create+reload/cycle-400/duplicate/delete/404/permission).
- Frontend: 39 passed (method/computed-level, Frappe Gantt mocked).
- Lint/format clean (ruff, ESLint flat config, Prettier).
- E2E scenario authored for the CI lane; not run locally.
