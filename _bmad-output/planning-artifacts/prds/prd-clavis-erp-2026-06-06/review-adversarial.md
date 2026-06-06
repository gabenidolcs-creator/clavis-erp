# Adversarial Review — Clavis ERP Airtable Parity PRD

Reviewer stance: hostile. Goal is to find what makes this PRD fail in execution, not to praise it. Findings are tagged `[critical|high|medium|low]`, each with a § location, the problem, and a concrete fix. Several findings are backed by direct inspection of the actual Baserow/Clavis codebase (`backend/src`, `premium/backend`, `enterprise/backend`), which contradicts load-bearing claims in the PRD.

---

## A. Factual errors about the codebase that invalidate scope estimates

### A1. [critical] §1, §4.6, §8, §13, FR-14/16 — Dashboard is already in the FREE core; only chart widgets are premium. The PRD mis-buckets the whole module.
**Problem.** The PRD repeatedly calls the Dashboard a "Bucket A premium Dashboards module" to be "clean-room reimplemented" (§4.6, §8 licensing list, Glossary). The codebase says otherwise:
- `backend/src/baserow/contrib/dashboard/` (free core) already contains the full application type, handler, data sources, widgets framework, permission manager, ws layer, **and** `SummaryWidget` (the metric widget).
- Only the **chart widget types** (bar/pie/etc.) live in `premium/backend/src/baserow_premium/dashboard/widgets/` (Bucket A).

So FR-14 (create dashboard + arrange widgets) and FR-16 (metric widget) are **mostly already shipped in free**, and only FR-15 (chart widgets) is a genuine Bucket A clean-room reimplement. The PRD's framing inflates the clean-room/legal surface, miscounts effort, and will send architecture down a "rebuild the dashboard module" path that is wasted work — or worse, a clean-room team will needlessly rewrite free code they were allowed to read, creating provenance confusion.
**Fix.** Re-scope §4.6: FR-14/16 = "extend existing free Dashboard module + SummaryWidget"; FR-15 = the only Bucket A clean-room item (chart widget types). Correct the Glossary and §8 licensing list. Re-baseline §13 step 3.

### A2. [critical] FR-29 §4.9 / addendum "Commenter role ~1 wk" — The free tier has NO role hierarchy. There is no Viewer/Editor to put Commenter "between."
**Problem.** FR-29 says "Role ordering places Commenter between Viewer and Editor" and the addendum estimates "~1 wk" as a "`COMMENTER` constant between VIEWER and EDITOR." Inspection: free core (`backend/src/baserow/core/models.py`) only defines `WORKSPACE_USER_PERMISSION_ADMIN` and `WORKSPACE_USER_PERMISSION_MEMBER`. VIEWER / EDITOR / COMMENTER, the entire role-based permission manager, `default_roles.py`, and the role assignment model all live in `enterprise/backend/src/baserow_enterprise/role/` — i.e. the whole RBAC subsystem is **Bucket A enterprise code**. You cannot "insert a constant between Viewer and Editor" because Viewer and Editor do not exist in the tier you are shipping into. Delivering Commenter (and the granular role ordering UJ-4 depends on) requires clean-room reimplementing a substantial chunk of enterprise RBAC, not adding a constant. This is the single biggest under-estimate in the document.
**Fix.** Add an explicit FR (or pre-requisite) for a free-tier role framework (Viewer/Editor/Commenter) and acknowledge it as a large Bucket A clean-room effort with its own security review. Re-estimate Collaboration batch from "~1 wk" to a multi-week RBAC build. Flag in §11 as a second high risk alongside permission regression.

### A3. [high] FR-30 §4.9 / addendum "Field permissions (A): Enterprise field_permissions pattern" — this is enterprise (Bucket A) source the clean-room team must NOT read.
**Problem.** The addendum tells implementers to follow the "Enterprise `field_permissions` pattern" and to make it "inherit `FieldType.check_can_*`." That code is `enterprise/backend/src/baserow_enterprise/field_permissions/` — licensed Bucket A. Instructing the implementation team to mirror the enterprise pattern is exactly the clean-room contamination the PRD spends §8/§11 trying to prevent. The addendum quietly undermines the legal guardrail.
**Fix.** Strip code-path references to enterprise source from the addendum's clean-room (Bucket A) feature notes. Replace with "behavior spec from public docs only." Make explicit that field permissions also depend on the role framework from A2 (you can't say "minimum role to edit" without roles).

### A4. [medium] §4.2/§4.5 Glossary + FR-28 — Personal Views are partially scaffolded in free core but the PRD treats them as net-new ownership work; sequencing in §13 doesn't reflect it.
**Problem.** Free core `views/models.py` already has `owned_by` FK and `ownership_type` (currently only `collaborative`); the `personal` ownership type lives in `enterprise/.../view_ownership_types.py` (Bucket A). FR-28 / addendum "add `owner` FK + migration" is partly redundant (the FK exists) and partly clean-room (the personal ownership type behavior). The estimate and §13 step 2 don't distinguish "wire an existing FK" from "clean-room the enterprise ownership type."
**Fix.** Correct FR-28/addendum to "register a `personal` ownership type against the existing `owned_by`/`ownership_type` scaffolding (clean-room the enterprise behavior)."

---

## B. Untestable / hand-wavy "done" criteria

### B1. [critical] FR-11 §4.4 "Critical Path" — no definition of what produces the highlight; untestable as written.
**Problem.** "The longest dependency chain determining completion is visually distinguished." Critical path is undefined for the actual data model: tasks have arbitrary start/end **Date Fields** that users can set independently, plus FS dependencies. Is critical path computed from durations + dependencies (classic CPM forward/backward pass with slack=0), or just "longest chain by edge count"? What happens when user-entered dates contradict the dependency graph (a successor starts before its predecessor ends — allowed per FR-10 "declined" path)? Float/slack, calendars/working-days, and milestone (zero-duration) handling are all unspecified. "Visually distinguished" is not a testable assertion. No QA can write a pass/fail test.
**Fix.** Specify the algorithm (recommend CPM with slack==0 over the dependency DAG using each task's [start,end]); define behavior when dates violate dependencies (exclude from CP? flag?); define the testable assertion ("tasks with computed slack 0 carry the `critical` flag in API response"). Move "visually distinguished" to a UX criterion and keep a data-level assertion as the FR's testable consequence.

### B2. [high] SM-1 §7 / Open Q1 — Primary success metric ("parity ≥80%") is unmeasurable because the feature matrix and scoring rubric are undefined and self-graded.
**Problem.** The single primary metric is "re-score the research feature matrix after release." The matrix's weighting, what counts as "done," and who scores it are all open (Open Q1). A self-scored percentage with no rubric is gameable and cannot be a release gate. "≥80%" is also `[ASSUMPTION]`. The whole release is "validated" by a number nobody can compute objectively.
**Fix.** Freeze the feature matrix (line items + weights) as an appendix before architecture; define binary done-criteria per line; assign an independent scorer. Or demote SM-1 to a narrative and promote SM-2/3/4 (which are at least measurable from telemetry) to primary — but those also lack instrumentation (see B3).

### B3. [high] SM-2/SM-3/SM-4 §7 — adoption metrics assume telemetry that this PRD never scopes; for self-hosted OSS it may be uncollectable.
**Problem.** "% of active free-tier bases that create a new view within 60 days," "% of multi-member workspaces using comments," etc., require usage telemetry. Nothing in the FRs or NFRs scopes event instrumentation, and the product's headline differentiator is **self-hosting** — where you have no telemetry pipeline at all. These metrics are uninstrumented and, for the OSS audience, structurally uncollectable.
**Fix.** Add an instrumentation FR (or explicitly scope metrics to Clavis cloud only) and define the event schema. Otherwise mark SM-2/3/4 as cloud-only directional, not release gates.

### B4. [medium] FR-17 / FR-33 — "Revoking the link disables access" and "removing it reverts to open/closed as configured" are underspecified for cached/in-flight sessions.
**Problem.** Does revocation kill already-loaded public sessions, or only block new loads? Password-protected links (FR-33) + public dashboard (FR-17) interact: what's the state matrix of {public on/off} × {password set/unset}? "reverts to open/closed as configured" is ambiguous.
**Fix.** Specify the {public, password} state machine and whether revocation is immediate (session invalidation) or next-load.

### B5. [medium] Dashboard NFR §4.6 + §10 — perf budget is "[ASSUMPTION: 12] widgets / 100k rows within an acceptable budget (defined in §10)" but §10 never defines a number.
**Problem.** §4.6 NFR forwards the budget to §10; §10 says "render budgets do not regress beyond an agreed threshold" — no number anywhere. Same for SM-C3 ("agreed threshold"). Three places point at each other; none states a millisecond/byte figure. Untestable.
**Fix.** Put concrete numbers (initial paint ms target, JS bundle KB ceiling, grid render ms) in §10 before architecture, or explicitly defer with an owner+date.

---

## C. Hidden cross-feature dependencies / sequencing traps not in §13

### C1. [critical] §13 — The role/permission framework (Commenter + roles, A2) is a prerequisite for Field Permissions (FR-30), interface-only (FR-31), AND the embed permission behavior (FR-24), but §13 puts ALL of Collaboration LAST (step 5) and treats it as independent.
**Problem.** §13 sequences foundations → views → dashboard → app builder → collaboration. But FR-24 (step 4) says embeds enforce "the viewer's Role (see §4.9)" and FR-30 hidden-fields must apply "across all View Types and App Builder embeds." Those reference the role/permission system that doesn't get built until step 5. You cannot correctly build view embeds with role-scoped visibility before roles exist. The permission framework is a **foundation**, not a finale. Putting it last guarantees rework of embeds and views.
**Fix.** Split Collaboration: move the role framework + field-permission enforcement hooks into the foundations layer (step 1/2), before App Builder embeds. Keep comments/notifications/password-share late. Make §13 show the role framework as a cross-cutting dependency, not a leaf.

### C2. [high] §12/§13 — "Charting foundation, build once" is shared by Dashboard (step 3) and App Builder charts (step 4), but Dashboard chart widgets are Bucket A (clean-room) while App Builder chart elements are Bucket B (greenfield). A single shared foundation cannot be simultaneously clean-room-quarantined and freely authored.
**Problem.** §4.6 says dashboard charts are Bucket A clean-room; §4.8 says app-builder chart elements are Bucket B; §12 says they share one charting foundation built once. The clean-room separation (§8) requires the people building the Bucket A dashboard chart to be quarantined from premium source. If the same shared library is then consumed by Bucket B, you've blended provenance. Either the shared foundation is treated as Bucket B (safe) and the "dashboard charts are Bucket A" claim is wrong, or the quarantine forces two implementations.
**Fix.** Declare the charting foundation itself Bucket B (it's just a chart-rendering layer; ECharts is the actual engine). Then the only Bucket A part of dashboards is the widget *configuration/data-binding* behavior, which can be specced from public UI. Reconcile §4.6/§4.8/§8.

### C3. [high] FR-9–FR-11 Gantt depends on a new TaskDependency model AND on the Timeline renderer (FR-6) AND on the still-undefined critical-path algorithm; §13 lists them in one bullet ("step 2") as if co-equal.
**Problem.** §13 step 2 lists Timeline, personal-view ownership, Gantt + dependencies + critical path, and Map in a single line. Gantt is the riskiest item in the release (new model, cycle detection, cascade reschedule, CPM) and it depends on Timeline being done first. Flattening it into one bullet hides the internal ordering and the fact that Gantt alone is bigger than several other "features."
**Fix.** Expand §13 step 2 into ordered sub-steps; pull Gantt out as its own milestone with explicit dependency on Timeline and the CP algorithm spec from B1.

### C4. [medium] FR-26 comments / FR-27 notifications — addendum says "reimplement comment model" (Bucket A, premium `row_comments`) but @mentions ride the "existing in-app notification infrastructure." Comments are premium; the notification *triggers* for comments may also be premium. Provenance of the trigger code isn't addressed.
**Problem.** Notification framework is in free core (`backend/src/baserow/core/notifications/`), good — but the comment-mention notification *type* is premium. The clean-room boundary for "wire mentions into notifications" is fuzzy.
**Fix.** Confirm which notification types are free vs premium; spec the comment-mention notification type as a clean-room item if premium.

---

## D. Scope that's secretly much bigger than it reads

### D1. [critical] §4.6 "clean-room reimplement Dashboard, extended with line/scatter" reads as one feature; combined with A1 it's actually (a) chart widget clean-room, (b) two net-new chart types, (c) the shared charting foundation, (d) grouped-aggregate data source (premium has `grouped_aggregate_rows_data_source` — see premium tests). The grouped aggregation data source is not mentioned anywhere in the PRD.
**Problem.** Charts need a grouped/aggregated data source to produce category/series values; premium ships `GroupedAggregateRowsDataSource` (visible in `premium/backend/tests/.../dashboard/`). The PRD's FR-15 assumes "configurable category/value (and series) fields" but never scopes the aggregation data-source service that makes that possible. That service is itself Bucket A.
**Fix.** Add an explicit FR for the grouped-aggregate data source service (clean-room) feeding chart widgets/elements. Without it, FR-15/FR-22 are not buildable.

### D2. [high] FR-13 Map "geocode and interact" hides: a geocoding service, a provider abstraction (Google vs Nominatim), a cache model + invalidation, a throttled async queue, address-field-change re-geocoding, clustering (server or client). That's 5–6 subsystems behind one FR with a "~1–2 wks" addendum estimate.
**Problem.** The estimate is wildly optimistic for: provider-pluggable geocoding + persistent cache + rate-limited queue + re-geocode-on-edit + clustering + the legal Google/OSM split. Each is non-trivial; the legal split alone (FR-13 + §8) is a product decision with billing implications.
**Fix.** Decompose FR-12/13 into sub-FRs (provider abstraction, cache model, async geocode queue, clustering, re-geocode triggers) and re-estimate. Add an FR for "address field changes invalidate/refresh geocode."

### D3. [medium] FR-31 interface-only collaborator — "All Database/Table/View endpoints return 403" is a deny-everything-except-app-pages permission manager. With Baserow's large endpoint surface (data sources, search, exports, ws subscriptions, trash, snapshots, webhooks), enumerating and proving the deny-list is a large security task, not one FR.
**Fix.** Acknowledge in §11 and scope a dedicated endpoint-coverage audit (the addendum nods at this; the FR should too). Default-deny posture (allowlist app endpoints) is safer than deny-list and should be specified.

---

## E. Missing failure modes / edge cases

### E1. [critical] FR-2 / FR-5 / FR-7 / FR-10 — Concurrent drag + real-time broadcast: no conflict semantics. Two users drag the same card/bar simultaneously; optimistic UX (§10) says both roll back on failure, but the spec never defines who wins or what the other client sees.
**Problem.** "Failed update rolls back" assumes the server rejects one. But last-write-wins over WebSocket means both may "succeed" and stomp each other; or a card you just dropped jumps because a broadcast from another user arrives mid-drag. No FR covers: drag-in-progress receiving a remote update to the same row; two simultaneous moves of the same row; a remote delete of a row you're dragging.
**Fix.** Add a cross-cutting NFR/FR for concurrent-edit semantics on drag (define LWW vs version-check; define behavior when a remote update lands on a row with an in-flight local drag; lock or reconcile).

### E2. [high] FR-10 Gantt cascade reschedule — interaction with concurrent edits, partial failure, and undo across many rows is undefined.
**Problem.** A confirmed cascade shifts N successors as "a single undoable step" (good), but: what if one of the N row updates fails midway (partial cascade)? What if another user edits a successor's date during the cascade? What if the cascade would itself create a new violation downstream that wasn't in the prompt's count? The prompt names "count of cascaded dependents" — computed before or after re-evaluation?
**Fix.** Specify atomicity (all-or-nothing transaction), conflict handling during cascade, and that the cascade is computed transitively before prompting.

### E3. [high] FR-9 cycle detection only covers creation. Editing dates, importing rows, or bulk operations can also create logical contradictions; and a dependency referencing a deleted/trashed row is unaddressed.
**Problem.** "Creating a dependency that would form a cycle is rejected" — but dependencies are edges between Rows; deleting/trashing a predecessor row, restoring from trash, duplicating tasks, or CSV-importing dependency data can all produce cycles or dangling edges. Trash/restore interaction (Baserow trashes rows) with the dependency graph is unspecified.
**Fix.** Add consequences for: predecessor/successor row deletion (cascade-delete edges? orphan?), trash+restore of a task with edges, and cycle re-check on bulk/import paths.

### E4. [high] FR-30 field permissions × every read path — "not returned by the API to unauthorized members and does not render in any View, embed, or export." Export, formula fields referencing a hidden field, lookup/rollup through a hidden field, search, and grouping/sorting by a hidden field are all leak vectors not enumerated.
**Problem.** A hidden-by-permission field can leak via: a formula/lookup/rollup field that derives from it; sort/group/filter that exposes ordering; full-text search indexing; CSV/JSON export; snapshots/duplication. "Does not render in any View" is the easy part; the derived-data and export leaks are the hard part and unmentioned.
**Fix.** Enumerate every read/derive path (formula, lookup, rollup, search, export, snapshot, API filter/sort/group) as testable consequences; this is also why field permissions must land before App Builder embeds (C1).

### E5. [medium] FR-13 geocoding failure modes — provider outage, quota exhaustion, ambiguous/partial addresses, and rate-limit backpressure on a 100k-row table are only partially covered ("could not locate" tray + throttled queue). Cost-blowup on cloud (Google billing) from a bulk geocode is unaddressed.
**Fix.** Add consequences for provider error vs ambiguous result vs quota-exceeded (distinct states), and a guard against unbounded geocode cost (batch caps / admin opt-in for large tables).

### E6. [medium] FR-21 Autonumber concurrency — "next unused integer" + "monotonic per Table" under concurrent row creation needs a sequence/locking strategy; "stable on delete" + monotonic can conflict if implemented naively. Import of existing rows and row duplication behavior unspecified.
**Fix.** Specify DB sequence or `select_for_update` semantics; define autonumber on bulk import and on row duplication.

### E7. [low] FR-1 Kanban — single-select option add/rename/delete while a board is open: does a deleted option's column merge into Uncategorized? Real-time option changes from another user? Not covered.
**Fix.** Add consequence for option lifecycle changes reflecting on the board.

---

## F. Over-optimistic [ASSUMPTION]s that are load-bearing decisions

### F1. [high] §4.5 / FR-13 / §8 geocoding provider split is tagged `[ASSUMPTION: configurable-provider split confirmed]` but it is a product + legal + billing decision, not an assumption. The Google ToS no-cache constraint directly conflicts with the cached self-host model the architecture will assume.
**Fix.** Resolve before architecture (it's effectively two different data-flow architectures). Promote from `[ASSUMPTION]` to a decision in §8 with an owner. (Addendum already leans Nominatim/MapLibre, which contradicts "Google default" in §4.5 — reconcile the contradiction: §4.5 says Google default, addendum table recommends OSM/MapLibre with "no API key.")

### F2. [high] FR-15 `[ASSUMPTION: live-push to charts confirmed in addendum]` — pushing recomputed aggregates to charts on every real-time row event over a 100k-row table is a performance landmine and directly stresses SM-C1 (latency) and SM-C3 (perf). Treated as a settled assumption.
**Fix.** Define refresh strategy (debounced recompute, server-side incremental aggregation, or refresh-on-load only) as an explicit decision; an unbounded live-recompute will regress the realtime counter-metric it claims to protect.

### F3. [medium] §4.4 FR-10 `[ASSUMPTION: FS default; others configurable but only FS guaranteed]` — the FR offers SS/FF/SF as "configurable" but only specifies FS behavior. Shipping configurable-but-unspecified dependency types invites users to set SS/FF and get undefined reschedule behavior.
**Fix.** Either ship FS-only in v1 (hide other types) or fully specify all four. "Configurable but undefined" is a bug surface.

### F4. [medium] §10 a11y `[ASSUMPTION: WCAG 2.1 AA]` for drag-heavy views — keyboard-accessible Kanban/Gantt drag is genuinely hard and is hand-waved with "where feasible." This is either a real commitment (large) or vapor.
**Fix.** Decide per-view what keyboard interaction is in scope; "where feasible" is not a testable a11y bar.

### F5. [low] §4.7 FR-19 percent convention `[ASSUMPTION]` and FR-21B running-count scope `[ASSUMPTION]` are small but still unresolved data-model decisions that affect storage/migration.
**Fix.** Resolve before the field-type migrations are written (they're in §13 step 1, the earliest work).

---

## G. Counter-metrics that won't catch the regression they claim to

### G1. [high] SM-C1 "p95 WebSocket latency ≤ current baseline" won't catch FR-15's live-chart-push regression or FR-10's cascade-broadcast storm, because those add *new* high-volume broadcast traffic rather than slowing the existing path.
**Problem.** A cascade reschedule (FR-10) or live aggregate push (FR-15) can flood the WS layer with many messages while each individual broadcast's p95 stays flat. The counter-metric measures per-message latency, not message volume or client-side processing load. The regression hides in volume.
**Fix.** Add a counter-metric on broadcast *volume per mutation* and client apply-time, not just per-message latency.

### G2. [medium] SM-C3 "bundle/perf budget does not regress beyond an agreed threshold" — no number (see B5), and it measures initial load, but the heavy libs (ECharts, MapLibre, Gantt) should be lazy-loaded (§11 mitigation). If lazy-loaded, initial-load bundle won't move even if the per-view payload is huge. The metric will read green while Map/Gantt views are slow.
**Fix.** Measure per-view (route-level) chunk size and time-to-interactive for each new view, not just app initial load.

### G3. [medium] SM-C2 "record limits stay unlimited" is trivially true (no FR adds a cap) and so catches nothing — it's a guardrail dressed as a counter-metric. The real risk is a feature that *performs unusably* at high row counts (geocoding 100k rows, charting 100k rows, Gantt with thousands of dependencies), which SM-C2 does not measure.
**Fix.** Replace/augment with a high-row-count performance counter per new view (defined thresholds at, e.g., 100k rows).

---

## H. Things that will bite during architecture / epics breakdown

### H1. [high] Glossary/§8 mislabel which features are Bucket A vs B (per A1–A4). Architecture and the clean-room legal process key off these labels. Wrong labels → wrong quarantine → either wasted clean-room effort or actual contamination.
**Fix.** Produce a verified Bucket A/B table from the codebase (Dashboard framework=free, chart widgets=A, RBAC/roles=A, field perms=A, personal-view type=A, comments=A; Gantt/Map/new fields/chart-elements/interface-only/password-share=B) and replace the PRD's claims.

### H2. [medium] §4.8 FR-24 embeds "wrap the Batch 1 view renderers" — but Batch 1 renderers are Vuex/Nuxt grid components; App Builder pages have their own runtime/data-source model. "Thin wrapper" is optimistic; the data-source plumbing and permission context differ. Plus FR-24 read-vs-interactive is still Open Q6.
**Fix.** Resolve Open Q6 before architecture; spec the data-source bridge between view renderers and the builder runtime as real work, not a wrapper.

### H3. [medium] FR-32 Locked Views vs FR-28 Personal Views vs FR-30 Field Permissions — the interaction matrix (locked + personal? field-perm on a locked personal view? who can unlock?) is unspecified. UJ-4 stacks several of these on one base.
**Fix.** Add an interaction matrix for view ownership × lock × field-permission × role.

### H4. [low] §6.2 / Open Q4 contradiction — §6.2 says field hide-by-permission is "confirm whether v1 or follow-on" while Open Q4 says it's RESOLVED as in-v1 (FR-30). The document contradicts itself.
**Fix.** Delete the §6.2 line (it's resolved in §14 Q4 and FR-30).

### H5. [low] Release gate = "feature-complete, not phased-ship" (§11) across 5 batches with the largest under-estimates (A2/D1/D2) — a single all-or-nothing release of this size is itself the top schedule risk, and the mitigation ("dependency-ordered sequence") reduces rework, not scope. The risk register rates Scope "medium"; given A2/D1/D2 it's high.
**Fix.** Re-rate Scope risk to high; consider a phased internal gate even if shipped together.

---

## Summary of severities
- **Critical (6):** A1 (dashboard mis-bucketed), A2 (no free role hierarchy / Commenter under-estimate), B1 (critical-path undefined), C1 (permission framework sequenced last but needed early), D1 (charting hides grouped-aggregate data source), E1 (concurrent-drag conflict semantics missing).
- **High (12):** A3, B2, B3, C2, C3, D2, E2, E3, E4, F1, F2, G1, H1.
- **Medium/Low (remainder):** see inline.

The two findings most likely to blow the schedule: **A2** (Commenter/roles is a whole RBAC clean-room, not a constant) and the **A1/D1** cluster (dashboard charting is bigger and differently-bucketed than written). The finding most likely to ship a security bug: **E4/C1** (field-permission leak paths + permission framework built after the embeds that must honor it).
