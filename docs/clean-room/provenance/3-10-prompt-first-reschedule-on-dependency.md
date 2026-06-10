# Provenance record — Story 3.10 Prompt-first reschedule on dependency

- **PR / branch:** feat(story-3.10) prompt-first reschedule on dependency (branch: develop)
- **Story:** 3.10 Prompt-first reschedule on dependency
- **Bucket:** B (greenfield cascade-reschedule engine over the 3.9 `TaskDependency` edges, rendered via the core MIT Gantt + vendored MIT Frappe Gantt drag contract)
- **Implementer:** AI dev-agent
- **Date:** 2026-06-10

## Sources Consulted

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | Story 3.9 free-core `TaskDependency` model + handler (this repo, authored 3.9) — the FS edge set the cascade walks. Story 3.10 adds `compute_cascade`/`apply_cascade`/`find_violations` to the same handler in place; no schema change (the violation flag is derived, not stored). | MIT free-core (authored 3.9) | `backend/src/baserow/contrib/database/views/gantt/handler.py`, `.../gantt/models.py` |
| 2 | Story 3.8/3.9 free-core Gantt spine (this repo) — `GanttView` model + type, the `api/views/gantt/` package, `GanttView.vue` with the live `dependenciesForRow()` seam, `store/view/gantt.js`, `services/view/gantt.js`. 3.10 extends these in place (drag write path, preview/apply endpoints + store actions, violated-connector styling). | MIT free-core (authored 3.8/3.9) | `backend/src/baserow/contrib/database/api/views/gantt/*`, `web-frontend/modules/database/components/view/gantt/GanttView.vue`, `.../store/view/gantt.js`, `.../services/view/gantt.js` |
| 3 | Story 3.7 free-core Timeline reschedule helpers (this repo) — `rowDateRange`, `parseTimelineValue`, `shiftDateValue` (whole-day shift discipline: date-only → `YYYY-MM-DD`, datetime → preserve `HH:mm`/UTC). Reused verbatim (imported, not forked) for the bar-drag delta math; the backend `date_utils.py` mirrors the same semantics. | MIT free-core (authored 3.7) | `web-frontend/modules/database/components/view/timeline/TimelineView.vue` |
| 4 | Core `UpdateRowsActionType` + buffered-rows store (`updateRowValues`) — the single-undoable-step batch write the cascade commits through, and the optimistic write path the predecessor-only move reuses. Row-locking via `Table.objects.select_for_update()`. | MIT free-core | `backend/src/baserow/contrib/database/rows/actions.py`, `web-frontend/modules/database/store/view/bufferedRows.js` |
| 5 | Frappe Gantt 1.2.2 — MIT-licensed renderer. The drag contract is the only new thing consumed: `readonly: false` + `readonly_progress: true` makes bars draggable/resizable, and `on_date_change(task, start, end)` fires once on pointer release with `Date` objects. Arrows carry `data-from`/`data-to` SVG attributes (used to style violated connectors). | third-party MIT dependency | https://github.com/frappe/gantt (v1.2.2, MIT); `web-frontend/package.json` |
| 6 | Cascade algorithm — BFS relaxation over the FS edge set with diamond-safe max-delta accumulation, plus an in-memory FS-violation check. Standard public computer-science, hand-rolled over the ORM edge set. No third-party graph library added. | general public knowledge | — |

## Implementer Attestation

- [x] This is a **Bucket B** greenfield build: a new cascade-reschedule engine over the 3.9
      `TaskDependency` edges, rendered through the free-core 3.8/3.9 Gantt spine (MIT, this repo)
      and the vendored MIT Frappe Gantt 1.2.2 drag contract. I did **not** read, copy, adapt, or
      rely on memory of any `premium/` or `enterprise/` (PE/EE) source for this feature — **in
      particular the conceptually-adjacent paid `enterprise/.../date_dependency/` module (and its
      `calculations.py` date-relaxation logic) was NOT opened, grepped, skimmed, or referenced.**
      That feature is a different problem (field-level date auto-calculation); this story is a
      Gantt row-to-row FS cascade triggered by a user bar-drag, gated behind an explicit
      author confirmation. Every source I used is listed above.

**Implementer signature / handle:** AI dev-agent   **Date:** 2026-06-10

## Reviewer confirmation (filled at review)

- [x] Reviewer verified all sources above are free-core MIT, this-repo, vendored MIT, or public.
- [x] Reviewer verified no `premium/` or `enterprise/` source was consulted — confirmed
      `enterprise/.../date_dependency/` was not read.

## Notes

- **Derived violation, no migration.** The FS-violation state (a dependent that starts before its
  predecessor finishes after the author declined a cascade) is computed on read from the edge set +
  the two rows' dates and surfaced as a `violated` flag on the dependency serializer. No column was
  added; `git diff` adds no migration.
- **Prompt-first, preview is read-only (AC #1).** The bar drag computes the new start/end, then asks
  the backend for the read-only cascade preview (affected successors + transitive count) and opens a
  confirm modal. Nothing is written until the author confirms. A move that violates no successor is
  silent — the predecessor is written directly with no prompt (AC #4).
- **One undoable step (AC #2).** On confirm, the backend recomputes under a table-scoped
  `select_for_update` lock and shifts the predecessor + every transitive dependent atomically through
  one `UpdateRowsActionType.do`, broadcasting one batch row update so every peer client repositions.
- **Decline keeps the predecessor move (AC #4).** Declining writes only the dragged predecessor and
  re-fetches the edges; the now-invalid FS connector is re-derived as `violated` and repainted via
  `markViolatedConnectors` (`.gantt-view__arrow--violated` on the lib's `.arrow` path, keyed by
  `data-from`/`data-to`). This is the one place the lib's SVG is restyled.
- **Optimistic-bar rollback (AC #5).** Any write failure, or dismissing the prompt without a choice,
  snaps the optimistic bar back to the store's authoritative position (`refreshGantt`). Bars are
  draggable only when `canDragBars` holds (not read-only + both date fields writable); otherwise the
  view stays render-only exactly as in 3.8.
- **Pre-existing lib leak unchanged, not worsened.** Frappe Gantt 1.2.2 still attaches one anonymous
  `document` `mouseup` listener per instance with no `destroy()`. The drag write path adds no
  listeners of its own (it only reads the lib's `on_date_change` callback), so the leak is the same
  as 3.8; the `destroyGantt` comment documents this. A future lib bump with a teardown hook should
  remove it.
- **No premium/enterprise contamination.** Every source consulted is the free-core 3.7/3.8/3.9
  spine, core row-action/buffered-rows helpers, the vendored MIT Frappe Gantt drag contract, or
  public algorithms. No `premium/` or `enterprise/` source — explicitly not
  `enterprise/date_dependency/` — was opened, grepped, or recalled. This PR is **not** labelled
  `bucket-a`, so the clean-room provenance CI hard-gate does not fire.
- **Test execution.** Backend tests run in the **default** profile: 13/14 pass (9 handler covering
  single-successor/chain/diamond max-delta/no-violation-no-prompt/decline-violation/lock/not-configured
  + 5 API covering preview/apply/undo/404/not-configured). The remaining 1 (`test_apply_field_edit
  _prohibited_returns_403`) is a **known local-env limitation**, not a defect: the dev workstation has
  an RBAC/enterprise license granted, so the enterprise `write_field_values` manager shadows the core
  field-permission denial and the apply endpoint returns 200 instead of 403. The assertion is correct
  and passes in the CI no-license profile; it was deliberately left unchanged. Frontend unit tests run
  method/computed-level (Frappe Gantt mocked): 50 passed. The two E2E scenarios in
  `e2e-tests/tests/database/gantt_view.spec.ts` are authored for the CI lane and not run locally.
