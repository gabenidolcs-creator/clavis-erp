---
baseline_commit: 143ba77d5ce0b6ee9b52cbc2b8ebe076ff7efd9a
---

# Story 3.11: Milestones and Critical Path (CPM)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want milestones and an automatically-highlighted critical path,
so that I can spot the zero-slack chain and key dates.

Bucket B (greenfield Gantt module). Realizes UJ-2. No clean-room provenance gate (`check_provenance.py` only fires on `bucket-a` PRs). **Enterprise overlap warning**: `enterprise/.../date_dependency/` files are a field-level date auto-calculation feature (different problem) — never read them.

## Acceptance Criteria

1. **Milestone rendering**: Given a task, when an editor sets its start date equal to its end date (zero-duration), then it renders as a diamond marker at its date on the Gantt chart (not a horizontal bar).

2. **CPM critical path highlight**: Given the FS dependency graph, when the system computes scheduling, then a CPM forward pass (earliest start/finish) and backward pass (latest start/finish) run, tasks with zero total float form the Critical Path and are visually distinguished from normal tasks (e.g., red/orange bar color), and the Critical Path recomputes whenever any dependency or date changes.

3. **CPM conflict detection**: Given user-entered dates that violate a dependency (i.e., a successor's start date is before its predecessor's CPM-implied finish), when CPM runs, then the affected task is flagged as a scheduling conflict and excluded from the Critical Path until resolved; the conflict flag is surfaced visually (distinct color/style) and recomputes on every dependency/date change.

4. **Out of scope**: Resource leveling, lag/lead times, SS/FF/SF dependency types in CPM — FS only.

## Tasks / Subtasks

- [x] Task 1 (AC: #2, #3) — Add `CpmResult` dataclass and `compute_cpm()` to `TaskDependencyHandler`
  - [x] 1.1 — Add `CpmResult` dataclass with `critical_task_ids: List[int]` and `conflict_task_ids: List[int]` near top of `handler.py` (alongside the existing `CascadePlan` dataclass)
  - [x] 1.2 — Add `compute_cpm(self, table, start_date_field, end_date_field, model=None) -> CpmResult` method to `TaskDependencyHandler`
  - [x] 1.3 — Forward pass: load FS edges via `_load_fs_edges`, build adjacency + in-degree map, Kahn's BFS topological sort, compute `ES[node]` = max(EF of predecessors) for dependent nodes (root nodes use their stored start date), `EF[node]` = `ES[node]` + duration; flag `conflict_task_ids` where stored `start < ES[node]` (user date contradicts dependency-implied earliest start)
  - [x] 1.4 — Backward pass: set `project_end = max(EF.values())`, then in reverse-topological order: `LF[node]` = min(`LS` of successors) or `project_end` for leaf nodes; `LS[node]` = `LF[node]` - duration; total float = `LF[node]` - `EF[node]`
  - [x] 1.5 — `critical_task_ids` = nodes in dependency network where float == 0 (timedelta zero) and node is not in `conflict_task_ids`; nodes with no edges (isolated rows) are never on critical path
  - [x] 1.6 — Reuse `_load_fs_edges` and `_load_row_dates` — do not duplicate date-reading logic; pass `node_ids = set(p for p,_ in edges) | set(s for _,s in edges)` to `_load_row_dates`; skip unscheduled nodes (start or end is None) from CPM computation entirely

- [x] Task 2 (AC: #2, #3) — Extend `GanttViewDependenciesView.get()` to include CPM data
  - [x] 2.1 — In `GanttViewDependenciesView.get()` (file: `api/views/gantt/views.py`), after building the dependency queryset, call `handler.compute_cpm(table, start_date_field, end_date_field)` synchronously — same pattern as `_violated_edge_set()` helper called in the same view
  - [x] 2.2 — Add `CpmResultSerializer` to `serializers.py` with `critical_task_ids = serializers.ListField(child=serializers.IntegerField())` and `conflict_task_ids = serializers.ListField(child=serializers.IntegerField())`
  - [x] 2.3 — Return response shape: `{ "dependencies": [...existing...], "cpm": { "critical_task_ids": [...], "conflict_task_ids": [...] } }` — serialize using `CpmResultSerializer(cpm_result).data`
  - [x] 2.4 — Guard: if `view.start_date_field_id is None` or `view.end_date_field_id is None`, return `cpm: { "critical_task_ids": [], "conflict_task_ids": [] }` (same guard pattern as `_require_gantt_date_fields` for other endpoints)
  - [x] 2.5 — Public dependencies endpoint (`PublicGanttViewDependenciesView`) must also return `cpm` with the same structure — do not add CPM to public endpoint (public views are read-only, no dependency writes, but DO include CPM so public share users see critical path highlighting)

- [x] Task 3 (AC: #1) — Frontend: `ganttTasks` computed adds `custom_class` for milestone and CPM state
  - [x] 3.1 — In `GanttView.vue` `ganttTasks` computed (currently ~line 330): for each task object built from a row, set `custom_class` to a space-joined string of applicable classes:
    - `'gantt-view__milestone'` if start date == end date (zero-duration)
    - `'gantt-view__critical'` if row id is in `this.criticalTaskIds` (new store getter)
    - `'gantt-view__conflict'` if row id is in `this.conflictTaskIds` (new store getter)
    - Empty string `''` if none apply (do not pass `undefined`)
  - [x] 3.2 — Add `criticalTaskIds` and `conflictTaskIds` computed properties in `GanttView.vue` that read from store state: `this.$store.getters['view/gantt/criticalTaskIds']` and `'view/gantt/conflictTaskIds'`

- [x] Task 4 (AC: #2, #3) — Frontend store: add CPM state and update `fetchDependencies`
  - [x] 4.1 — In `store/view/gantt.js` state: add `criticalTaskIds: []` and `conflictTaskIds: []`
  - [x] 4.2 — Extend `SET_DEPENDENCIES` mutation to also accept and commit `cpm` payload: `state.criticalTaskIds = cpm.critical_task_ids ?? []`, `state.conflictTaskIds = cpm.conflict_task_ids ?? []`
  - [x] 4.3 — In `fetchDependencies` action: after `ganttService.listDependencies(viewId)` resolves, pass `{ data: response.data.dependencies, cpm: response.data.cpm }` to `commit('SET_DEPENDENCIES', ...)`
  - [x] 4.4 — Add Vuex getters `criticalTaskIds` and `conflictTaskIds` that return the respective state arrays

- [x] Task 5 (AC: #2, #3) — Frontend: `markCriticalPath()` method re-paints bar CSS after every render
  - [x] 5.1 — Add `markCriticalPath()` method to `GanttView.vue` (alongside `markViolatedConnectors`): iterate `this.$store.getters['view/gantt/criticalTaskIds']` and query `.bar-wrapper[data-id="${id}"]` in the gantt host, add/remove `gantt-view__critical` class; do the same for `conflictTaskIds` with class `gantt-view__conflict`
  - [x] 5.2 — Call `this.markCriticalPath()` in `this.$nextTick()` at the end of `refreshGantt()` and `ensureGantt()` — exactly as `markViolatedConnectors` is currently called in those places
  - [x] 5.3 — Add a watcher on `criticalTaskIds` and `conflictTaskIds` store getters (same watcher pattern as the `dependencies` watcher already in `GanttView.vue`) that calls `this.$nextTick(() => this.markCriticalPath())`

- [x] Task 6 (AC: #1, #2, #3) — Frontend CSS: `gantt.scss` diamond + critical/conflict bar styles
  - [x] 6.1 — Milestone diamond: `.gantt .bar-wrapper.gantt-view__milestone .bar { clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%); transform-box: fill-box; transform-origin: center; }` — clip-path works on SVG rect elements in modern browsers; the rect will visually become a diamond. For zero-duration bars Frappe Gantt renders a near-zero-width rect; also add `min-width: 14px` override and centering offset via `x` adjustment if needed.
  - [x] 6.2 — Critical path bar: `.gantt .bar-wrapper.gantt-view__critical .bar { fill: #e74c3c; }` (or project design-system critical color if one exists in existing SCSS variables)
  - [x] 6.3 — Conflict bar: `.gantt .bar-wrapper.gantt-view__conflict .bar { fill: #f39c12; }` (warning color — distinct from violated arrow `--violated` orange/red)
  - [x] 6.4 — Milestone bar label: hide the default bar label for milestones that would overlap the diamond: `.gantt-view__milestone .bar-label { display: none; }`

- [x] Task 7 (AC: #1, #2, #3) — i18n: add translation keys for any new tooltip/aria strings
  - [x] 7.1 — In `locales/en.json`, under `ganttView` block, add keys: `milestoneLabel`, `criticalPathLabel`, `conflictLabel` (used for ARIA labels on diamond/critical/conflict bars if needed)
  - [x] 7.2 — Only add keys that are actually referenced in templates; do not add unused i18n strings

- [x] Task 8 (AC: #2, #3) — Backend tests: `test_task_dependency_handler.py`
  - [x] 8.1 — `test_cpm_no_edges_returns_empty_result`: table with rows and dates but no dependencies → `CpmResult([], [])`
  - [x] 8.2 — `test_cpm_linear_chain_critical_path`: A → B → C linear chain, dates aligned perfectly (no slack) → all three in `critical_task_ids`
  - [x] 8.3 — `test_cpm_parallel_paths_only_longest_is_critical`: A → C and A → B → C; A=1d, B=3d, C=1d → path A→B→C is critical (longer); A→C path has slack
  - [x] 8.4 — `test_cpm_conflict_detection`: A end = day 5; B start = day 3 (violates FS); B in `conflict_task_ids`, excluded from critical path
  - [x] 8.5 — `test_cpm_isolated_nodes_not_critical`: rows with no dependencies never appear in `critical_task_ids`
  - [x] 8.6 — `test_cpm_unscheduled_nodes_skipped`: row with no start/end date in dependency chain → skipped (not in conflict or critical)
  - [x] 8.7 — Use same `_make_rows` helper + `data_fixture.create_database_table` pattern as existing tests; set row dates via `model.objects.filter(id=row.id).update(field_N=value)` pattern used in `test_gantt_reschedule_handler.py`

- [x] Task 9 (AC: #2, #3) — Backend tests: `test_gantt_dependency_views.py`
  - [x] 9.1 — `test_list_dependencies_includes_cpm_keys`: GET dependencies endpoint returns response with top-level `cpm` key containing `critical_task_ids` and `conflict_task_ids`
  - [x] 9.2 — `test_list_dependencies_cpm_correct_values`: endpoint with a 2-task chain returns both task IDs in `critical_task_ids`
  - [x] 9.3 — `test_list_dependencies_cpm_empty_when_no_date_fields`: view without `start_date_field` / `end_date_field` returns empty CPM lists

- [x] Task 10 — Frontend unit tests: extend `ganttView.spec.js`
  - [x] 10.1 — `ganttTasks milestone class (AC #1)`: when start == end, task object has `custom_class` containing `'gantt-view__milestone'`
  - [x] 10.2 — `ganttTasks critical class (AC #2)`: when row id is in `criticalTaskIds` store state, task object has `custom_class` containing `'gantt-view__critical'`
  - [x] 10.3 — `ganttTasks conflict class (AC #3)`: when row id is in `conflictTaskIds` store state, task object has `custom_class` containing `'gantt-view__conflict'`
  - [x] 10.4 — Use existing `makeVm` + `method.bind(vm)` pattern from `ganttView.spec.js` (confirmed in 3.8/3.9/3.10 tests)

- [x] Task 11 — E2E tests: extend `gantt_view.spec.ts` (author-only — do not run locally, no Docker stack)
  - [x] 11.1 — Scenario: mark a task as zero-duration → verify diamond `.gantt-view__milestone` class on bar wrapper
  - [x] 11.2 — Scenario: create A → B dependency with aligned dates → verify `.gantt-view__critical` class on both bars
  - [x] 11.3 — Scenario: create A → B dependency where B.start < A.end → verify `.gantt-view__conflict` class on B

- [x] Task 12 — Provenance document
  - [x] 12.1 — Create `_bmad-output/implementation-artifacts/provenance/3-11-cpm-milestones-provenance.md` noting Bucket B (greenfield), no clean-room gate, no enterprise source read, algorithm is standard CPM (widely published in project management literature)

## Dev Notes

### Foundation from Prior Stories

Story 3.11 builds directly on stories 3.9 (TaskDependency model + cycle detection) and 3.10 (cascade reschedule). All dependency infrastructure is in place:

- **`TaskDependencyHandler`** at `backend/src/baserow/contrib/database/views/gantt/handler.py` — contains `_load_fs_edges()` and `_load_row_dates()` which are the exact building blocks needed for the CPM forward/backward pass. Reuse these methods without modification.
- **`TaskDependency` model** at `backend/src/baserow/contrib/database/views/gantt/models.py` — directed edge table with `predecessor_row_id`, `successor_row_id`, `dependency_type` (FS only). No new model or migration needed for story 3.11.
- **`GanttView` model** at `backend/src/baserow/contrib/database/views/models.py:1011` — has `start_date_field` and `end_date_field` FKs. No new fields needed.
- **`GanttViewDependenciesView`** at `api/views/gantt/views.py:611` — the GET handler that already includes `violated` state via `_violated_edge_set()`. Extend the response here (not a new endpoint).

### Milestone Design: Zero-Duration Rule

A milestone is a task where `start_date == end_date`. No separate boolean column, no extra migration. The user "marks" a task as a milestone by making it zero-duration. This matches the architecture spec ("zero-duration Milestone diamond" — AR-4/FR-11).

Frontend: in `ganttTasks` computed, detect zero-duration by comparing the `start` and `end` date string values (or parsed dates) from the row's date fields. Add `custom_class: 'gantt-view__milestone'` to the Frappe task object.

Frappe Gantt renders a near-zero-width `<rect class="bar">` for zero-duration tasks. Use CSS `clip-path: polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)` on that rect to turn it into a diamond shape. `clip-path` works on SVG elements in all modern browsers.

### CPM Algorithm Design

The CPM runs in `compute_cpm()` in `TaskDependencyHandler`. Key invariants:

1. **Scope**: only nodes that appear in at least one FS edge participate. Isolated rows (no dependencies) are never critical.
2. **Conflict detection**: compare each node's stored `start` date against `ES[node]` (the dependency-implied earliest start). If `start < ES[node]`, the node is in `conflict_task_ids`. Conflicts are excluded from critical path.
3. **Unscheduled nodes**: if a node's start or end is `None`, skip it entirely — do not include in critical, conflict, or forward/backward pass.
4. **Float precision**: use `timedelta` math. Float = `LF[node] - EF[node]`. Critical = `timedelta(0)` (exactly zero days float).
5. **Duration**: always non-negative: `duration = max(timedelta(0), end - start)` for each node.
6. **Algorithm**: Kahn's BFS topological sort (same pattern as `_graph_has_cycle` which uses DFS — Kahn's BFS is better for forward/backward pass since it naturally processes nodes level by level). No external library needed.

### API Response Extension

`GanttViewDependenciesView.get()` already builds the full dependency list and calls `_violated_edge_set()`. Add CPM computation after `_violated_edge_set`:

```python
handler = TaskDependencyHandler()
cpm_result = handler.compute_cpm(table, view.start_date_field, view.end_date_field)
# ... serialize
return Response({
    "dependencies": dependency_serializer.data,
    "cpm": CpmResultSerializer(cpm_result).data,
})
```

The existing `GanttViewDependencySerializer` serializes individual edges. The `CpmResultSerializer` is a new top-level result serializer (not a ModelSerializer — use plain `serializers.Serializer`).

### Frontend Store Pattern

Current `SET_DEPENDENCIES` mutation in `store/view/gantt.js:31` sets `state.dependencies = data`. Extend it to also accept CPM:

```javascript
SET_DEPENDENCIES(state, { data, cpm = {} }) {
  state.dependencies = data
  state.criticalTaskIds = cpm.critical_task_ids ?? []
  state.conflictTaskIds = cpm.conflict_task_ids ?? []
}
```

Update the `fetchDependencies` action call site to pass `{ data: ..., cpm: response.data.cpm }`.

### Frappe Gantt `custom_class` Behavior

Frappe Gantt 1.2.2 (`web-frontend/node_modules/frappe-gantt/`) applies `custom_class` to the `<g class="bar-wrapper">` SVG group element for each task. CSS targeting: `.bar-wrapper.gantt-view__milestone .bar { ... }`.

The existing `markViolatedConnectors()` in `GanttView.vue` (lines ~890-914) shows how to post-render class manipulation works on Frappe SVG elements. `markCriticalPath()` follows the same pattern but targets `[data-id="..."]` on `.bar-wrapper` elements (for critical/conflict classes that can't be set purely via `custom_class` — because `custom_class` is set at task-object build time, but CPM state can change without a full gantt rebuild).

**Note**: `custom_class` is stamped at Frappe render time. Since CPM state and critical/conflict classes may need to update without a full `ganttInstance.refresh()` call, the `markCriticalPath()` DOM manipulation approach (mirroring `markViolatedConnectors`) is the correct pattern — it can apply/remove classes after the fact.

### Existing File Locations

```
backend (EXTEND):
  backend/src/baserow/contrib/database/views/gantt/handler.py
    → add CpmResult dataclass, compute_cpm() method
  backend/src/baserow/contrib/database/api/views/gantt/serializers.py
    → add CpmResultSerializer
  backend/src/baserow/contrib/database/api/views/gantt/views.py
    → extend GanttViewDependenciesView.get() and PublicGanttViewDependenciesView.get()

backend (DO NOT MODIFY):
  backend/src/baserow/contrib/database/views/gantt/models.py  (no migration needed)
  backend/src/baserow/contrib/database/views/gantt/date_utils.py
  backend/src/baserow/contrib/database/rows/actions.py

frontend (EXTEND):
  web-frontend/modules/database/components/view/gantt/GanttView.vue
    → ganttTasks custom_class, markCriticalPath(), watchers
  web-frontend/modules/database/store/view/gantt.js
    → state, SET_DEPENDENCIES mutation, getters
  web-frontend/modules/core/assets/scss/components/views/gantt.scss
    → milestone diamond, critical/conflict bar colors
  web-frontend/modules/database/locales/en.json  (if i18n strings needed)

tests (NEW):
  backend/tests/baserow/contrib/database/view/gantt/test_task_dependency_handler.py
    → append CPM tests (file already exists from 3.9/3.10)
  backend/tests/baserow/contrib/database/api/views/gantt/test_gantt_dependency_views.py
    → append CPM response shape tests (file already exists from 3.9/3.10)
  web-frontend/test/unit/database/components/view/gantt/ganttView.spec.js
    → append custom_class tests

provenance (NEW):
  _bmad-output/implementation-artifacts/provenance/3-11-cpm-milestones-provenance.md
```

### Test Run Commands

```bash
# Backend (default profile — NOT .env.oss-test)
just b test backend/tests/baserow/contrib/database/view/gantt/ backend/tests/baserow/contrib/database/api/views/gantt/

# Frontend (bare vitest — not yarn test:core which errors on EXTRA_VITEST_PARAMS)
yarn vitest run web-frontend/test/unit/database/components/view/gantt/

# Lint (ESLint bare — legacy flags fail with flat config)
eslint web-frontend/modules/database/components/view/gantt/GanttView.vue web-frontend/modules/database/store/view/gantt.js
```

### Commit Convention

```
feat(story-3.11): Milestones and Critical Path (CPM)
```

### Project Structure Notes

- Alignment: all files follow existing Gantt module layout established in 3.8–3.10; no new app or module registration needed
- `CpmResult` dataclass belongs in `handler.py` alongside `CascadePlan` (line ~37) — both are computation result containers
- No new Django migration required: milestones are identified via zero-duration (computed from existing date fields), CPM is stateless (computed on request from existing edges + dates)
- `GanttViewDependenciesView` response format change is backward-compatible: adds new `cpm` top-level key, existing `dependencies` key is unchanged
- Public Gantt view endpoint must also return `cpm` for public share users — `PublicGanttViewDependenciesView` at `views.py:764`

### References

- [Source: epics.md#Story 3.11 — FR-11 Milestones and Critical Path]
- [Source: epics.md line 101 — AR-8 TaskDependency + CPM (D8): CPM computed synchronously in a backend handler; cascade reschedule with Row locking]
- [Source: architecture.md line 118 — D8 decision: CPM computed synchronously in a backend handler (forward/backward pass over the FS graph) on any dependency/date change; graph is bounded per-view so sync keeps Critical Path fresh (FR-11)]
- [Source: backend/src/baserow/contrib/database/views/gantt/handler.py — TaskDependencyHandler, CascadePlan, _load_fs_edges, _load_row_dates]
- [Source: backend/src/baserow/contrib/database/api/views/gantt/views.py:611 — GanttViewDependenciesView, _violated_edge_set helper]
- [Source: backend/src/baserow/contrib/database/api/views/gantt/serializers.py — TaskDependencySerializer with violated computed field (pattern for CpmResultSerializer)]
- [Source: web-frontend/modules/database/components/view/gantt/GanttView.vue:890 — markViolatedConnectors() (pattern for markCriticalPath())]
- [Source: web-frontend/modules/database/store/view/gantt.js:31 — SET_DEPENDENCIES mutation]
- [Source: web-frontend/modules/database/store/view/gantt.js:66 — fetchDependencies action]
- [Source: web-frontend/node_modules/frappe-gantt/src/bar.js — custom_class applied to bar-wrapper SVG group]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Pre-existing bug fixed in `_violated_edge_set`: `view.start_date_field` / `view.end_date_field` return base `Field` (MTI), not concrete `DateField`. Added `.specific` to both FK accesses so `date_include_time` attribute resolves correctly. Same fix applied to CPM calls in both dependency view endpoints.
- Response shape change: `GanttViewDependenciesView` now returns `{"dependencies": [...], "cpm": {...}}` — existing test `test_create_and_list_dependency_survives_reload` updated to unpack `body["dependencies"]` instead of treating the whole response as the list.
- Existing `ganttView.spec.js` task shape assertion updated to include `custom_class: ''` (new field added by this story's `ganttTasks` computed).
- i18n: no new keys added — Task 7 required keys only if referenced in templates; no template references were added.
- E2E tests authored only — no local Docker stack run (per story task spec).
- `compute_cpm()` uses `from collections import deque` inline (not top-level import) to avoid polluting handler.py module namespace.

### File List

- `backend/src/baserow/contrib/database/views/gantt/handler.py`
- `backend/src/baserow/contrib/database/api/views/gantt/serializers.py`
- `backend/src/baserow/contrib/database/api/views/gantt/views.py`
- `web-frontend/modules/database/components/view/gantt/GanttView.vue`
- `web-frontend/modules/database/store/view/gantt.js`
- `web-frontend/modules/core/assets/scss/components/views/gantt.scss`
- `backend/tests/baserow/contrib/database/view/gantt/test_task_dependency_handler.py`
- `backend/tests/baserow/contrib/database/api/views/gantt/test_gantt_dependency_views.py`
- `web-frontend/test/unit/database/components/view/gantt/ganttView.spec.js`
- `e2e-tests/tests/database/gantt_view.spec.ts`
- `_bmad-output/implementation-artifacts/provenance/3-11-cpm-milestones-provenance.md`

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-06-11 | Story implemented: CpmResult dataclass + compute_cpm() backend, CpmResultSerializer, extended dependency view endpoints, Vuex CPM state, ganttTasks custom_class, markCriticalPath() DOM method, milestone diamond + critical/conflict SCSS, backend unit tests (6 CPM handler + 3 view tests), frontend unit tests (7 ganttTasks tests), E2E tests authored, provenance doc created | claude-sonnet-4-6 |
