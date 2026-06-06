# Adversarial Review — Pass 2 (re-check of revised PRD)

Reviewer stance: hostile. Goal: (1) confirm whether the prior pass-1 criticals/highs are actually closed in the revision, and (2) find NEW problems the revision introduced. Codebase claims re-verified against `backend/src`, `premium/`, `enterprise/`.

## Codebase re-verification (all pass-1 factual claims confirmed)
- `backend/src/baserow/core/models.py:72-73` — only `WORKSPACE_USER_PERMISSION_ADMIN`/`MEMBER`. No Viewer/Editor/Commenter in free. ✔
- `backend/src/baserow/contrib/dashboard/` exists in free core, incl. `widgets/` and `SummaryWidget`/`SummaryWidgetType`. ✔
- Chart widgets are premium-only (`premium/.../dashboard/widgets/widget_types.py`). ✔
- RBAC roles, `default_roles.py`, role permission manager are enterprise (`enterprise/.../role/`). ✔
- Field permissions are enterprise (`enterprise/.../field_permissions/`). ✔
- Grouped-aggregate data source is premium (`LocalBaserowGroupedAggregateRows`, premium migration 0025 + service_types + tests). ✔
- Personal-view scaffolding: free-core `views/models.py:54-136` has `owned_by` FK + `ownership_type` (only `collaborative`); `personal` type is enterprise (`view_ownership_types.py`). ✔
- Premium `row_comments/` module exists (incl. `notification_types.py`). ✔

The revision's corrected factual framing is accurate. The PRD now matches the repo.

---

## PART 1 — Status of prior findings

### Critical
- **A1 (dashboard mis-bucketed) → CLOSED.** §4.6 now states the module + `SummaryWidgetType` already ship free and are out-of-scope/non-regression; FR-14 = grouped-aggregate data source, FR-15 = chart widgets (bar/pie Bucket A, line/scatter Bucket B), FR-16 = non-goal/non-regression. Glossary, §8, §9, §13 step 4 all reconciled.
- **A2 (no free role hierarchy / Commenter under-estimate) → CLOSED.** FR-29 now an explicit "RBAC role foundation" clean-room item; Glossary/§4.9/§8/§12 call it the load-bearing prerequisite; addendum re-estimates to "weeks, not ~1 wk — largest single item"; §11 lists permission regression as a second CRITICAL risk.
- **B1 (critical path undefined) → CLOSED.** FR-11 now specifies CPM forward/backward pass, zero-slack definition, recompute trigger, an explicit contradiction rule for manual dates violating dependencies, and an out-of-scope list (no resource leveling/lag/SS-FF-SF). Glossary defines Critical Path as zero-slack CPM chain. Testable.
- **C1 (permission framework sequenced last) → CLOSED.** §13 re-sequenced: step 0 clean-room gate, step 1 RBAC foundation, step 2 permission enforcement layer (field perms, IDOR, ws filtering, exports, share hardening) — all before view embeds (step 5). Explicit "sequencing correction from review" note.
- **D1 (charting hides grouped-aggregate data source) → CLOSED.** FR-14 added as a standalone deliverable and prerequisite for FR-15; called out in §4.6, §6.1, §9, §13 step 4.
- **E1 (concurrent-drag conflict semantics) → CLOSED.** §10 "Optimistic UX + concurrent edits" now defines LWW-per-field, snap-to-authoritative reconciliation, and row acquisition for Gantt cascades so overlapping cascades can't interleave.

### High
- **A3 (addendum told implementers to follow enterprise field_permissions code) → CLOSED.** Addendum field-permissions note now says "describe enterprise *behavior* from public sources, do not copy enterprise modules" and references only free-core `FieldType` hooks. §8 adds symbol-hygiene rule.
- **B2 (parity metric self-graded) → PARTIAL.** SM-1 now says re-score by a named reviewer against a fixed checklist (not self-graded), but the matrix/weights/binary done-criteria are still not frozen (Open Q1/Q9 remain). Improved, not closed.
- **B3 (telemetry uninstrumented / uncollectable for self-host) → CLOSED (by scoping).** §7 measurement note + each SM now scoped to cloud; self-host treated as opt-in directional. No instrumentation FR, but the metrics no longer over-claim.
- **B5 (perf budget = no number) → OPEN.** §4.6 NFR still forwards to "the §10 budget"; §10 still has no millisecond/KB number; SM-C3 still says "agreed threshold." The three-way pointer is unchanged. (Open Q-style deferral not even assigned an owner/date.)
- **C2 (shared charting foundation: Bucket A vs B conflict) → PARTIAL.** §4.6/§12 still say the charting foundation is "built once, consumed by both," while dashboard bar/pie charts remain Bucket A and app chart elements Bucket B. The PRD never declares the *foundation itself* Bucket B to resolve the quarantine contradiction (pass-1 C2 fix). The provenance ambiguity persists.
- **C3 (Gantt flattened into one §13 bullet) → PARTIAL.** §13 step 3 now lists Gantt with its sub-parts (Task Dependency + CPM) but still co-lists Kanban/Calendar/Timeline/Map in one step without pulling Gantt out as its own milestone or stating Gantt-depends-on-Timeline ordering. Slightly better, internal ordering still implicit.
- **D2 (Map geocoding = 5-6 hidden subsystems) → PARTIAL/OPEN.** FR-12/13 still bundle geocoding, caching, clustering, throttling under two FRs; addendum still "~1-2 wks." No decomposition into sub-FRs, no explicit "address change re-geocodes" requirement (pass-1 E5 also). Risk register acknowledges it (medium) but the FR is not decomposed.
- **E2 (cascade reschedule atomicity/partial failure) → PARTIAL.** §10 adds row acquisition against interleaving cascades; FR-10 still does not state all-or-nothing transaction on partial failure, nor whether the cascaded-dependent count is computed transitively before prompting. Concurrency addressed; atomicity + transitive-count still unspecified.
- **E3 (cycle detection only on create; trash/import/delete edges) → OPEN.** FR-9 still only "creating a dependency that would form a cycle is rejected." No consequence for predecessor/successor row delete/trash/restore, duplication, or import re-check. Unaddressed.
- **E4 (field-permission leak via formula/lookup/rollup/export/search) → CLOSED.** FR-30 now enumerates every read/derive path (all view types, embeds, chart/metric data sources, formulas/lookups/rollups, search/filter, exports via FR-33B, websocket) and adds null-redaction for transitive aggregate reads + cache invalidation. FR-33B added for exports. §11 adds an inference-leak risk.
- **F1 (geocoding provider = decision, not assumption; Google-cache contradiction) → CLOSED.** §4.5/§8 now state Google default on cloud + configurable OSM/Nominatim for self-host, explaining the ToS cache conflict; addendum table reconciled to match (no longer contradicts). Still tagged `[ASSUMPTION]` for the "forced-Google-everywhere" fallback only — acceptable.
- **F2 (live-chart-push perf landmine treated as settled) → PARTIAL.** FR-15 assumption reworded to "refresh on load + real-time row events; confirm live-push interval/strategy in architecture." Acknowledged as open, but no debounce/incremental-aggregation decision; deferred to architecture rather than decided.
- **G1 (SM-C1 won't catch volume regression) → CLOSED.** SM-C1 reworded to require same row-count/concurrent-client load as baseline so bigger payloads/permission filtering can't hide behind a lighter test. (Per-mutation broadcast-volume metric still not added, but the load-matching clause covers the main hole.)
- **H1 (Bucket A/B mislabels) → CLOSED.** §8, Glossary, §13 step 0 now carry a verified bucket list matching the repo (dashboard framework free, chart widgets A, RBAC A, field perms A, personal-view type A, comments A; Gantt/Map/fields/chart-elements/password-share B; interface-only + Commenter = A-dependent).

### Medium/Low (spot-check)
- **B4 (public/password state machine) → OPEN.** FR-17/FR-33 still don't give the {public on/off}×{password set/unset} matrix or immediate-vs-next-load revocation precisely (FR-17 says "immediately"; interaction with password unset is still implicit).
- **E6 (autonumber concurrency) → OPEN.** FR-21 still says "next unused integer / monotonic per Table" with no sequence/lock strategy, no import/duplication behavior.
- **F3 (SS/FF/SF configurable-but-unspecified) → PARTIAL.** FR-11/§9 now scope CPM + auto-reschedule to FS only and list SS/FF/SF out of scope for CPM, but FR-8/Glossary still say other types are "configurable," leaving the non-FS reschedule behavior a bug surface (pass-1 fix was "hide them in v1").
- **F4 (a11y "where feasible") → OPEN.** §10 still "keyboard navigation … where feasible" + `[ASSUMPTION: WCAG 2.1 AA]`. Not a testable bar.
- **H3 (locked × personal × field-perm × role interaction matrix) → CLOSED.** §11 now mandates an enumerated/tested role-interaction matrix: {Viewer,Commenter,Editor,Admin,interface-only}×{field-perm}×{personal/locked}×{public/password} with precedence rules, as a release gate.
- **H4 (§6.2 vs Open Q4 contradiction) → CLOSED.** §6.2 now lists field permissions cleanly as in-scope; Open Q4 marked RESOLVED. No contradiction.
- **H5 (scope risk rated medium) → OPEN.** §11 still rates Scope "medium" despite the now-acknowledged weeks-long RBAC + Map + dashboard-charting load. Pass-1 fix (re-rate to high) not applied.

---

## PART 2 — NEW problems introduced by the revision

### N1. [CRITICAL] Broken UJ→FR cross-references — UJ-3 and UJ-4 cite FR numbers that do not exist.
The max FR is FR-33B, but:
- UJ-3 resolution (prd.md:63): "Realizes UJ via **FR-34, FR-38**, FR-31." FR-34 and FR-38 do not exist. UJ-3 is the App-Builder gallery + status chart + comment journey — should be FR-22 (chart element) / FR-24 (embed) / FR-26 (comments) / FR-31 (interface-only).
- UJ-4 resolution (prd.md:70): "Realizes UJ via **FR-40, FR-35, FR-37, FR-36**." None exist. UJ-4 is locked view + Commenter + field perm + personal view — should be FR-32 / FR-29 / FR-30 / FR-28.
These look like a stale FR-numbering scheme from a pre-revision draft that wasn't renumbered when FRs were consolidated. Two of the five headline user journeys now trace to nonexistent requirements — downstream epics/stories generation will break or hallucinate.

### N2. [HIGH] UJ-1 traceability is wrong even where FR numbers exist.
UJ-1 resolution (prd.md:49): "Realizes UJ via FR-1, **FR-26, FR-30**." UJ-1 is Maya building a Kanban then a dashboard with a bar chart + "Total won this month" metric and sharing a public link. That journey is FR-1 (Kanban) + FR-15 (chart widget) + FR-16 (metric) + FR-17 (dashboard public share). FR-26 (comments) and FR-30 (field permissions) appear nowhere in the UJ-1 narrative. The inline `Realizes UJ-1` tag on FR-15/FR-17 is correct, so the mismatch is one-directional and confusing — the UJ→FR map and FR→UJ tags disagree.

### N3. [MEDIUM] RBAC migration risk to existing ADMIN/MEMBER users is asserted but unspecified — and underestimated for the MEMBER mapping.
FR-29 says "existing ADMIN/MEMBER assignments migrate to equivalent Roles with no loss of access" and the addendum says "a migration mapping existing ADMIN/MEMBER." But there is no "equivalent Role" for MEMBER: today MEMBER is effectively a full editor (can create/edit rows, fields, views). The new tiers are Viewer/Commenter/Editor/Admin. MEMBER must map to **Editor** to avoid access loss — but the PRD never states this, and if anyone maps MEMBER→Viewer/Commenter (the literal "member" connotation) every existing non-admin user silently loses write access on upgrade. This is a data-access regression hiding inside a one-line migration claim. The migration also needs a reverse/rollback path (RBAC is Bucket A, security-sensitive) which is unspecified. Pin MEMBER→Editor explicitly as a testable consequence and add a downgrade/rollback story.

### N4. [MEDIUM] New contradiction: §13 step 2 builds Field Permissions (FR-30) before the View layer (step 3), but FR-30's testable consequences enumerate enforcement across "all View Types" and "App Builder embeds" that don't exist until steps 3 and 5.
The revision correctly moved the permission *enforcement layer* early, but FR-30 can only be **fully tested** once the surfaces it must guard (Kanban/Calendar/Timeline/Gantt/Map views, embeds, chart data sources) exist later. So step 2's "every-surface enforcement" is not actually completable at step 2 — enforcement hooks land early but per-surface verification necessarily trails each surface's build. §13 presents FR-30 as a step-2 deliverable; in reality it is a cross-cutting obligation that must be re-verified at steps 3/4/5. This is a milder restatement of pass-1 C1 that the new sequencing partially re-introduces by labeling FR-30 as "done at step 2."

### N5. [LOW] FR-33B numbering ("B" suffix) plus FR-21B creates two non-sequential FR IDs.
FR-21B (Running Count) and FR-33B (Exports honor field perms) use a "B" suffix to avoid renumbering. Harmless individually, but combined with N1's stale FR-34..FR-40 references it signals the FR list was edited by insertion/suffixing rather than renumbered, which is exactly how the N1 dangling references survived. Recommend a single clean renumber pass (and it would surface N1 automatically).

### N6. [LOW] §4.9 Glossary/description drift on Commenter ordering vs the resolved tier set.
Pass-1 flagged "Commenter between Viewer and Editor." The revision fixed the tier list to Viewer/Commenter/Editor/Admin everywhere, but FR-26 still says "at least Commenter Role" to comment while FR-29 says Viewer "cannot comment" — consistent — yet the Glossary lists tiers as "Viewer, Commenter, Editor, Admin" implying Commenter > Viewer but the relative comment/edit capability of Editor vs Commenter on *comments* is unstated (can an Editor comment? presumably yes, but never asserted). Minor: state that all tiers ≥ Commenter may comment.

---

## Severity roll-up (pass 2)

Prior findings status:
- **CLOSED: 14** (A1, A2, A3, B1, B3, C1, D1, E1, E4, F1, G1, H1, H3, H4)
- **PARTIAL: 8** (B2, C2, C3, D2-partial, E2, F2, F3)  + count D2 once
- **OPEN: 7** (B4, B5, E3, E6, F4, H5, and D2's decomposition leg)

Prior criticals specifically: all 6 (A1, A2, B1, C1, D1, E1) are CLOSED. The two pass-1 "schedule-killer" clusters (A2 RBAC, A1/D1 dashboard) and the "ship a security bug" cluster (E4/C1) are resolved at the spec level.

New findings: **1 critical (N1), 1 high (N2), 2 medium (N3, N4), 2 low (N5, N6).**

## Bottom line
The revision genuinely closes every prior critical and most highs; the factual re-bucketing is accurate against the repo. However the revision introduced a CRITICAL traceability regression (N1: UJ-3/UJ-4 cite nonexistent FR-34/35/36/37/38/40) and a real MEMBER→Role migration access-loss risk (N3) that must be fixed before architecture/epics. Remaining OPEN items (perf budget numbers B5, cycle-detection edge cases E3, autonumber concurrency E6, scope re-rating H5) are pre-existing carry-overs, not blockers, but should be resolved before build.
