# Provenance record — Story 3.9 Define Task Dependencies with cycle prevention

- **PR / branch:** feat(story-3.9) define task dependencies with cycle prevention (branch: develop)
- **Story:** 3.9 Define Task Dependencies with cycle prevention
- **Bucket:** B (greenfield model + cycle-detection engine, rendered via the core MIT Gantt + vendored MIT Frappe Gantt connector contract)
- **Implementer:** AI dev-agent
- **Date:** 2026-06-10

## Sources Consulted

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | Core `RichTextFieldMention(table_id, row_id)` — the precedent for referencing a dynamic-table row by integer id from a `database`-app metadata model (no FK to a `GeneratedTableModel` row). `TaskDependency` mirrors this row-reference shape. | MIT free-core (this repo) | `backend/src/baserow/contrib/database/table/models.py` (RichTextFieldMention); `backend/src/baserow/contrib/database/trash/trash_types.py:383-386` (cleanup precedent) |
| 2 | Core `RowTrashableItemType` / `RowsTrashableItemType` — the permanent-delete and restore seams. The edge-cleanup hook mirrors the existing `RichTextFieldMention` cleanup in `permanently_delete_item`; restore re-validation hooks the `rows_created` signal that `restore` re-sends. | MIT free-core | `backend/src/baserow/contrib/database/trash/trash_types.py:320-545` |
| 3 | Story 3.8 free-core Gantt spine (this repo, authored 3.8) — `GanttView` model, `GanttViewType`, the `api/views/gantt/` package, `GanttView.vue` with the pre-carved `dependenciesForRow()` seam, `store/view/gantt.js`, `services/view/gantt.js`. Story 3.9 extends these in place (seam body, store edge state, service edge calls, new thin API views). | MIT free-core (authored 3.8) | `backend/src/baserow/contrib/database/views/view_types.py`, `backend/src/baserow/contrib/database/api/views/gantt/*`, `web-frontend/modules/database/components/view/gantt/GanttView.vue`, `web-frontend/modules/database/store/view/gantt.js`, `web-frontend/modules/database/services/view/gantt.js` |
| 4 | Frappe Gantt 1.2.2 — MIT-licensed renderer. The connector contract is the only thing consumed: a task's `dependencies` is a comma-separated string of predecessor task ids, from which the lib draws arrows (rendered even under `readonly: true`). | third-party MIT dependency | https://github.com/frappe/gantt (v1.2.2, MIT); `web-frontend/package.json` |
| 5 | Core realtime broadcast pattern — `page_registry.get("table").broadcast(...)` on `transaction.on_commit`, and the frontend `realtime.registerEvent(...)` registry. The `task_dependency_created` / `task_dependency_deleted` WebSocket wiring mirrors `ws/rows/signals.py` (backend) and the `view_*` handlers in `realtime.js` (frontend). | MIT free-core | `backend/src/baserow/contrib/database/ws/rows/signals.py`, `web-frontend/modules/database/realtime.js` |
| 6 | Core export/import structure — `DatabaseApplicationType` table serialize/deserialize and `DatabaseExportSerializedStructure.table(...)`. `TaskDependency` round-trips as a new `task_dependencies` table key, batch-cycle-validated on import. | MIT free-core | `backend/src/baserow/contrib/database/application_types.py`, `backend/src/baserow/contrib/database/export_serialized.py` |
| 7 | Cycle-detection algorithms (in-memory BFS reachability + Kahn topological sort) — standard public computer-science, hand-rolled over the ORM edge set. No third-party graph library added. | general public knowledge | — |

## Implementer Attestation

- [x] This is a **Bucket B** greenfield build: a new `TaskDependency` model + cycle-detection
      handler, rendered through the free-core 3.8 Gantt spine (MIT, this repo) and the vendored
      MIT Frappe Gantt 1.2.2 connector string contract. I did **not** read, copy, adapt, or rely
      on memory of any `premium/` or `enterprise/` (PE/EE) source for this feature — **in
      particular the conceptually-adjacent paid `enterprise/.../date_dependency/` module was NOT
      opened, grepped, skimmed, or referenced.** That feature is a different problem (field-level
      date auto-calculation); `TaskDependency` is a Gantt row-to-row scheduling edge. Every source
      I used is listed above.

**Implementer signature / handle:** AI dev-agent   **Date:** 2026-06-10

## Reviewer confirmation (filled at review)

- [x] Reviewer verified all sources above are free-core MIT, this-repo, vendored MIT, or public.
- [x] Reviewer verified no `premium/` or `enterprise/` source was consulted — confirmed `enterprise/.../date_dependency/` was not read.

## Notes

- **Greenfield model, not a derivation of an existing edge model.** `TaskDependency` lives in
  `backend/src/baserow/contrib/database/views/gantt/models.py`, scoped to a `Table` (edges are a
  property of the data, shared across every Gantt view of the table), referencing rows by integer
  `predecessor_row_id` / `successor_row_id` — the `RichTextFieldMention` row-reference precedent,
  never a row FK. FS-only in v1 (`dependency_type` column reserved for SS/FF/SF in 3.10/3.11).
- **One cycle implementation, every mutation path (AR-8).** `would_create_cycle` (single-edge
  reachability) and `validate_acyclic` (batch Kahn topological scan) are the same graph semantics;
  create, restore-from-trash, and import all route through them. The graph is bounded per table,
  loaded once and walked in memory (no query-per-node). Concurrent creates are serialized with a
  table-scoped `select_for_update` to close the TOCTOU window.
- **Cycle prevention on the hard paths.** Permanent row delete drops the row's edges (both sides);
  row restore re-sends `rows_created`, which re-validates and drops any edge that would now close a
  cycle; import remaps row ids then batch-validates before commit. Tested explicitly.
- **Render-only seam made live.** `dependenciesForRow(row)` now returns the comma-separated
  predecessor-id string for edges ending at the row; the `new Gantt(...)` call shape is untouched.
  The draw affordance is an explicit predecessor picker in the row modal (Frappe Gantt is
  `readonly`, exposes no draw handle — drag is 3.10).
- **Real-time wiring completed at review.** The dev delivery defined the `task_dependency_created` /
  `task_dependency_deleted` signals and the frontend store reconcile actions but left them
  unconnected. Review added the backend ws receiver (`ws/views/gantt/signals.py`, registered in
  `ws/signals.py`) broadcasting to the table page group, and the frontend `realtime.registerEvent`
  handlers that dispatch to the gantt store when a gantt view is selected.
- **No premium/enterprise contamination.** Every source consulted is the free-core 3.8 Gantt spine,
  core trash/mention/export helpers, the vendored MIT Frappe Gantt connector contract, or public
  algorithms. No `premium/` or `enterprise/` source — explicitly not `enterprise/date_dependency/` —
  was opened, grepped, or recalled. This PR is **not** labelled `bucket-a`, so the clean-room
  provenance CI hard-gate does not fire.
- **Test execution.** Backend tests run in the **default** profile: 19 passed (13 handler covering
  create/self-loop/direct+chain cycle/missing-row/non-FS/delete/list/permanent-delete/restore-cycle/
  import-cycle/round-trip + 6 API covering create+reload/cycle-400/duplicate/delete/404/permission).
  Frontend unit tests run method/computed-level (Frappe Gantt mocked): 39 passed. The E2E scenario in
  `e2e-tests/tests/database/gantt_view.spec.ts` is authored for the CI lane and not run locally.
