# Provenance: Story 3.11 — Milestones and Critical Path (CPM)

## Classification

**Bucket B — Greenfield Gantt module**

No clean-room gate applies. The `check_provenance.py` script fires on `bucket-a` PRs
only. This story adds new functionality to the OSS Gantt module introduced in stories
3.8–3.10.

## Enterprise Overlap Declaration

`enterprise/.../date_dependency/` is a field-level date auto-calculation feature
(different problem domain). No files from that directory were read, referenced, or
copied at any stage of this implementation. The feature does not overlap with Gantt
CPM.

## Algorithm Source

The Critical Path Method (CPM) forward/backward pass algorithm implemented in
`compute_cpm()` is a standard, widely-published project management algorithm.
It is described in:

- PMBOK Guide (Project Management Institute)
- Moder & Phillips, "Project Management with CPM, PERT, and Precedence Diagramming"
- Numerous academic textbooks and Wikipedia (public domain)

No proprietary or licensed source code was read or copied. The implementation uses:

- **Kahn's BFS topological sort** (1962, publicly documented)
- Standard `timedelta` arithmetic (Python stdlib)
- No external library beyond Django/Python stdlib

## Files Created / Modified

### Backend (extend only)
- `backend/src/baserow/contrib/database/views/gantt/handler.py` — added `CpmResult` dataclass and `compute_cpm()` method
- `backend/src/baserow/contrib/database/api/views/gantt/serializers.py` — added `CpmResultSerializer`
- `backend/src/baserow/contrib/database/api/views/gantt/views.py` — extended `GanttViewDependenciesView.get()` and `PublicGanttViewDependenciesView.get()`

### Backend (not modified)
- `backend/src/baserow/contrib/database/views/gantt/models.py` — no migration needed
- `backend/src/baserow/contrib/database/views/gantt/date_utils.py` — not touched

### Frontend (extend only)
- `web-frontend/modules/database/components/view/gantt/GanttView.vue`
- `web-frontend/modules/database/store/view/gantt.js`
- `web-frontend/modules/core/assets/scss/components/views/gantt.scss`

### Tests (new/extended)
- `backend/tests/baserow/contrib/database/view/gantt/test_task_dependency_handler.py`
- `backend/tests/baserow/contrib/database/api/views/gantt/test_gantt_dependency_views.py`
- `web-frontend/test/unit/database/components/view/gantt/ganttView.spec.js`
- `e2e-tests/tests/database/gantt_view.spec.ts`

## No Migration Required

Milestones are identified via zero-duration (start == end) computed from existing date
fields. CPM is stateless — computed on request from existing `TaskDependency` edges and
row dates. No new model or migration was added.
