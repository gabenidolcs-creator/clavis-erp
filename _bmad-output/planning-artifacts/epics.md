---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-clavis-erp-2026-06-06/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/prds/prd-clavis-erp-2026-06-06/addendum.md
  - _bmad-output/planning-artifacts/prds/prd-clavis-erp-2026-06-06/review-adversarial.md
  - _bmad-output/planning-artifacts/prds/prd-clavis-erp-2026-06-06/review-adversarial-pass2.md
  - _bmad-output/planning-artifacts/prds/prd-clavis-erp-2026-06-06/review-security.md
  - _bmad-output/planning-artifacts/prds/prd-clavis-erp-2026-06-06/review-security-pass2.md
  - _bmad-output/planning-artifacts/prds/prd-clavis-erp-2026-06-06/review-licensing.md
project_name: clavis-erp
user_name: Tinsu
date: 2026-06-06
---

# clavis-erp - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for clavis-erp (Airtable Parity Release), decomposing requirements from the PRD, Architecture, and Addendum into implementable stories. No UX Design document exists yet (UX is a downstream BMad workflow); a11y/i18n requirements are carried from PRD §10 NFRs and stories will be revised if a UX spec is produced later.

## Requirements Inventory

### Functional Requirements

> 34 FRs across 5 batches. Bucket tags: `[A]` = clean-room reimplement of premium/enterprise (license-forbidden to copy); `[B]` = greenfield; `[X]` = extend existing free core. Full testable consequences live in PRD §4.

**Batch 1 — Views**
- **FR-1** `[A]`: Create and configure a Kanban View — add a Kanban view to any Table, choose the Single-select Field defining columns (one column per option + "Uncategorized"); filters/sorts/field-visibility apply; persists and reopens.
- **FR-2** `[A]`: Drag a card between columns — dropping updates the Row's grouping Field; broadcasts in real time; failed update rolls back with error.
- **FR-3** `[A]`: Configure card appearance — choose which Fields show on the card face and whether a cover image shows; persists per view. (Card appearance does not depend on row coloring; conditional row coloring is delivered separately by FR-34.)
- **FR-4** `[A]`: Create and configure a Calendar View — select the Date Field positioning Rows; month/week modes; unscheduled tray; optional start+end span as a multi-day bar; filters/sorts apply.
- **FR-5** `[A]`: Reschedule by drag (calendar) — drop updates the Date Field, broadcasts real time; failure rolls back.
- **FR-6** `[A]`: Create and configure a Timeline View — map start+end Date Fields; bars on time axis; day/week/month zoom persists; rows missing start/end listed separately.
- **FR-7** `[A]`: Reschedule and resize bars (timeline) — move preserves duration, resize updates dragged endpoint; broadcasts; failures roll back.
- **FR-8** `[B]`: Render a Gantt View — map start/end Date Fields, task bars on time axis with dependency layer; zoom/filter/sort match Timeline.
- **FR-9** `[B]`: Define Task Dependencies — persist directed edge (predecessor→successor); render connector lines; cycle prevention across ALL mutation paths (create, restore-from-trash, import).
- **FR-10** `[B]`: Reschedule on dependency (prompt-first) — predecessor move that violates FS prompts (naming successors + cascade count); confirm cascades preserving durations; decline keeps move but flags violation; whole shift is a single undoable step.
- **FR-11** `[B]`: Milestones and Critical Path — mark zero-duration Milestone diamond; CPM forward/backward pass over FS graph, zero-slack tasks distinguished; recompute on dependency/date change; contradiction rule flags conflicts. Out of scope: resource leveling, lag/lead, SS/FF/SF in CPM.
- **FR-12** `[B]`: Configure a Map View — choose address Field (or lat/lng pair); resolvable Rows render as pins, unresolvable to a "could not locate" tray; filters/sorts apply.
- **FR-13** `[B]`: Geocode and interact with pins — geocode address values (cached, not re-requested); click pin opens Row; pins cluster at low zoom; geocoding respects provider rate limits without blocking UI.
- **FR-34** `[A]`: Conditional row coloring (view decorations) — color rows by condition (view-filter semantics); first-matching ordered rule wins; both `left_border_color` and `background_color` decorator types; renders across Grid/Gallery/Kanban/Calendar/Timeline; persists per view. Single-select-field color deferred. Clean-room (decoration scaffold already MIT core).

**Batch 2 — Dashboard**
- **FR-14** `[B]`: Grouped-aggregate Data Source for charts — configurable group-by Field + aggregation (count/sum/avg/min/max) returning (category, value[, series]); honors requesting principal's field-hide + row permissions; own deliverable, prerequisite for FR-15.
- **FR-15** `[A/B]`: Chart Widgets (bar, line, pie/doughnut, scatter) — bar+pie clean-room `[A]`, line+scatter `[B]`; bound to FR-14 Data Source; update on data change; interoperate with existing free summary metric Widget.
- **FR-16** `[X]` (NON-GOAL — already free): Metric Widget baseline — existing summary metric Widget keeps working; non-regression acceptance check only, no new build.
- **FR-17** `[B]`: Dashboard public share with defined principal — read-only public link resolving Data under a deny-by-default least-privilege share principal (not sharer's permissions); revoke disables immediately server-side.

**Batch 3 — Field Types** (all `[B]`)
- **FR-18**: Currency Field — configurable symbol + precision; numeric sort/filter; config persists.
- **FR-19**: Percent Field — configurable precision, `%` suffix; correct numeric storage/sort (whole-number entry convention per Open Q8).
- **FR-20**: Barcode Field — render scannable code (QR/Code128) client-side; configurable symbology persists. Out of scope: camera scanning (display only).
- **FR-21**: Autonumber Field — auto-assign next integer in creation order, not user-editable; deletes don't renumber; monotonic + collision-free under concurrent insert/bulk import (DB-sequence-backed); gaps acceptable.
- **FR-21B**: Running Count Field — count Rows matching a configured condition, recompute on data change; existing relational Count unaffected; default whole-Table scope (Open Q11).

**Batch 4 — App Builder** (all `[B]`)
- **FR-22**: Chart Element — place bar/line/pie/doughnut/scatter chart Elements bound to a Data Source on a Page; render on published Page; respect Page-level filters/params.
- **FR-23**: Metric Element — place a summary metric Element; compute/render aggregation on published Page.
- **FR-24**: Kanban / Calendar / Timeline embed Elements — embed view layouts from a Data Source; read/interaction permissions follow viewer's Role; read-oriented in v1 (Open Q6). Depends on Batch-1 view renderers.
- **FR-25**: Record review layout — present one Row at a time with next/previous over a Data Source. AI-generated review layouts are a non-goal.

**Batch 5 — Collaboration**
- **FR-29** `[A]` (load-bearing prerequisite): RBAC role foundation + Commenter Role — assign Viewer/Commenter/Editor/Admin at workspace/database scope; migration ADMIN→Admin, MEMBER→Editor (reversible, test-verified, no write-loss); Commenter read+comment only (403 on edit, REST+WS); routed through `PERMISSION_MANAGERS`. Custom-role builder out of scope.
- **FR-26** `[A]`: Row comments with @mentions — threaded Comments per Row in thread order, broadcast only to recipients who can see the Row; no hidden-Field leak; @mention only members with Row access; edit/delete own + admin moderation.
- **FR-27** `[X]`: Comment notifications — @mention/subscribe generates in-app notification linking to Row/Comment only if recipient can access the Row. Email digest deferred.
- **FR-28** `[A]`: Personal Views — mark a View Personal (visible only to owner); filtered from others' list AND direct fetch-by-id by non-owner returns 403 (no IDOR); toggle back to shared; works across all View Types.
- **FR-30** `[A]`: Field Permissions — restrict edit + visibility of a Field by Role/member, enforced at EVERY data surface (all View Types, App Builder embeds, chart/metric Data Sources, formulas/lookups/rollups, search/filter, exports, WebSocket); inference-oracle guard (reject filter/sort ON a hidden Field); permission change invalidates row/field + aggregate/chart + Redis model caches and re-evaluates live sessions/subscriptions.
- **FR-31** `[A]` (builds on FR-29): Interface-only collaborator Role — access only App Builder Pages, never underlying Data, enforced data-scoped (deny DB/Table/View REST, Data Source dispatch, formula eval, WebSocket channels beyond granted Page); returns only the minimum Elements need; mandatory security review + exhaustive role-combination matrix before ship.
- **FR-32** `[A]`: Locked Views — lock a View's config (filters/sorts/fields/layout) read-only to non-owners (server-enforced); Data still editable per Role; unlock only by Admin or lock owner.
- **FR-33** `[B]`: Password-protected share links — add a password to a public link (View/Dashboard/App Page); correct password grants read under least-privilege share principal; modern KDF (Argon2id) + constant-time compare + high-entropy token; rate-limit/lockout; uniform error (no link-existence oracle).
- **FR-33B** `[X]`: Exports honor Field Permissions — all export paths (CSV/JSON/XLSX, Map, any download) return only Data the principal may see; hidden Fields + restricted Rows absent; public/interface-only cannot export beyond granted surface.

### NonFunctional Requirements

> From PRD §10 (Cross-Cutting NFRs), §7 counter-metrics, and Architecture NFR coverage. These are cross-cutting acceptance constraints that apply to relevant FRs, not standalone deliverables.

- **NFR-1 — Real-time:** all new mutating views/collaboration features broadcast over the existing WebSocket layer; no polling where realtime is expected. p95 broadcast latency ≤ current baseline under the same row-count/concurrent-client load (SM-C1).
- **NFR-2 — Performance budgets:** Kanban/Calendar/Timeline/Gantt use existing virtual-scroll/lazy-row patterns; new filterable/sortable Fields implement correct `get_order_by_field_string` + field indexing; Map clusters to avoid plotting all rows. Placeholder targets (architect to ratify against measured baselines): new-view FMP ≤ 2s on 100k-row Table; scroll/drag ≥ 50fps; 12-Widget Dashboard initial paint ≤ 3s; added charting+map+Gantt bundle ≤ 400KB gzip on routes that load them, measured with heavy code actually loaded (SM-C3).
- **NFR-3 — Optimistic UX + concurrent edits:** drag ops (cards, calendar entries, Gantt bars) apply optimistically with rollback on failure; concurrent edits = last-write-wins per field + real-time reconcile + snap-to-authoritative on supersede (no silent divergence); Gantt cascade reschedules lock affected Rows so overlapping cascades cannot interleave.
- **NFR-4 — Security (every-surface enforcement):** all role/permission FRs enforced server-side (never UI-only), 403 on unauthorized, routed through `PERMISSION_MANAGERS` (never a parallel path). Enforcement holds at REST, WebSocket (authorize at *subscribe* time, not only payload-filter), App Builder Data Source dispatch, formulas/lookups/rollups, chart/metric aggregation, filter/sort predicates (no inference oracle), search, and exports. Share links resolve under a deny-by-default least-privilege share principal; passwords use modern KDF + constant-time compare + rate-limit; share tokens high-entropy/unguessable. Geocoded lat/lng enforced under source-address Field permission at read time. Permission changes invalidate row/field + aggregate/chart + Redis model caches and re-evaluate live sessions/subscriptions.
- **NFR-5 — Accessibility:** new views and elements meet the existing a11y bar (keyboard navigation for board/calendar/gantt interactions where feasible); WCAG 2.1 AA target (confirm with UX).
- **NFR-6 — i18n:** all new UI strings added to translation catalogs (`en.json` + existing locales).
- **NFR-7 — Testing matrix:** each feature ships model → handler → serializer/API → frontend-registry → component tests (backend pytest, frontend Vitest) per the project test matrix.
- **NFR-8 — Counter-metrics (do not regress):** SM-C1 real-time latency, SM-C2 unlimited free-tier records (no feature introduces a row cap), SM-C3 frontend bundle/perf budget — all must not regress to achieve parity.

### Additional Requirements

> From Architecture (D1–D14, structure map, patterns) and Addendum. These are technical/process requirements that shape epic structure and Epic 1 (foundations).

**Process / Legal (gates implementation):**
- **AR-1 — Clean-room process gate (PRD §13 step 0, blocks ALL Bucket A `[A]` work):** assign owner + legal sign-off; implementer isolation (walled-off or external group with enforced no-access to `premium/`/`enterprise/`); behavior specs from allowed public sources only; per-feature provenance log as a hard merge gate (no provenance → no merge); symbol hygiene (no premium/enterprise internal symbol names in specs/tickets/code as the thing to replicate). Open Q7 — owner unassigned; must be resolved before any `[A]` story starts.
- **AR-2 — Security release gate (PRD §13 step 7, blocks release):** threat model + exhaustive role-combination test matrix ({Viewer,Commenter,Editor,Admin,interface-only} × field-permission state × personal/locked view × public/password share) with most-restrictive-wins precedence + security review covering FR-30/31/33/33B and all data surfaces.

**Architecture decisions (libraries / data / security):**
- **AR-3 — Charting foundation (D1):** Apache ECharts via vue-echarts (echarts 6.0 / vue-echarts 8.0.1, Apache-2.0), built once, lazy-loaded, consumed by FR-15 (Dashboard) + FR-22 (App Builder).
- **AR-4 — Gantt render layer (D2):** Frappe Gantt 1.2.2 (MIT), render-only; dependencies/CPM/cascade computed in backend (D8).
- **AR-5 — Map rendering (D3):** MapLibre GL JS 5.24 (BSD-3); tile source via provider abstraction.
- **AR-6 — Geocoding (D4/D13):** provider abstraction Google Geocoding (cloud) / Nominatim-OSM (self-host) via env var (Google ToS forbids long-term cache → self-host uses Nominatim); lat/lng cached in DB; Celery throttled queue respecting rate limits. New env vars via `add-django-config-env-var` skill (base.py + compose + env-remap + docs).
- **AR-7 — Barcode (D5):** qrcode.vue + Code128 (jsbarcode-class lib, MIT), client-side render.
- **AR-8 — TaskDependency + CPM (D8):** new `TaskDependency` model (directed edge, default FS); cycle detection on every mutation path; CPM computed synchronously in a backend handler; cascade reschedule with Row locking.
- **AR-9 — Grouped-aggregate Data Source (D9):** new service-type in `service_type_registry`, SQL GROUP BY, honors principal field-hide + row permissions; reused by FR-15 + FR-22.
- **AR-10 — Autonumber (D10):** Postgres sequence (`nextval`), collision-free under concurrency/bulk import, monotonic, gaps acceptable.
- **AR-11 — Personal/Locked View model (D14):** add `owner` FK + `locked` flag to free-core `View` model + migration; `ViewHandler` enforces personal-view list-filter + fetch-by-id 403 (no IDOR) and locked-view config read-only to non-owner/non-admin.
- **AR-12 — RBAC model (D6):** clean-room role layer in `core/rbac/`, fixed tiers, new PermissionManager registered into existing `PERMISSION_MANAGERS` chain (never parallel); reversible migration ADMIN→Admin / MEMBER→Editor, test-verified.
- **AR-13 — Field-permission enforcement layer (D7):** single central enforcement layer (`core/field_permissions/`) — one queryset/serializer redactor + one predicate guard — consumed by every data surface so no surface is missed; inference-oracle guard lives here; cache invalidation on permission change.
- **AR-14 — Password share KDF (D12):** Argon2id (Django Argon2 hasher), constant-time compare, rate-limit/lockout, high-entropy share tokens, uniform error; deny-by-default share principal (FR-17).
- **AR-15 — Chart data refresh (D11):** fetch-on-load + WebSocket row-event invalidation (debounced re-aggregate), no polling.

**Structural / pattern constraints (apply to every story):**
- **AR-16 — Brownfield registry extension:** every new type registers via singleton registry in Django `ready()` (backend) mirrored by `$registry.register` (frontend); thin DRF API views over Handler classes (REST + WebSocket + CLI share the handler); no core rewrites. Bucket A free reimplementations live in `backend/src`/`web-frontend` core — NEVER in `premium/`/`enterprise/` (reference shape only).
- **AR-17 — Naming/format conventions:** match nearest existing core file; snake_case JSON payloads (never camelCase); backend tests in `backend/tests/...` mirroring src path (not co-located); 403 for permission denial; ISO 8601 dates; Ruff 88-col Python 3.14; SCSS BEM; `h` from `vue`, JSX only in `.jsx`/`.tsx`.
- **AR-18 — No initialization story:** brownfield foundation exists (`just init`/`just dev up`); first implementation story is the §13 step-0 clean-room gate, then Bucket B foundations.

### UX Design Requirements

No UX Design Specification exists for this release. UX is a downstream BMad workflow (`bmad-ux`) not yet run. Interaction/a11y/i18n requirements are carried from PRD §10 NFRs (NFR-5/NFR-6) and applied per-story. If a UX spec is produced later, affected stories must be revised to add UX-DR-derived acceptance criteria (component specs, design tokens, interaction patterns).

### FR Coverage Map

- **FR-1** Kanban create/configure → Epic 3
- **FR-2** Kanban drag card → Epic 3
- **FR-3** Kanban card appearance → Epic 3
- **FR-4** Calendar create/configure → Epic 3
- **FR-5** Calendar reschedule by drag → Epic 3
- **FR-6** Timeline create/configure → Epic 3
- **FR-7** Timeline reschedule/resize → Epic 3
- **FR-8** Gantt render → Epic 3
- **FR-9** Task Dependencies → Epic 3
- **FR-10** Dependency reschedule (prompt-first) → Epic 3
- **FR-11** Milestones + Critical Path (CPM) → Epic 3
- **FR-12** Map View configure → Epic 3
- **FR-13** Geocode + pin interaction → Epic 3
- **FR-34** Conditional row coloring → Epic 3
- **FR-14** Grouped-aggregate Data Source → Epic 4
- **FR-15** Chart Widgets (bar/line/pie/scatter) → Epic 4
- **FR-16** Metric Widget (non-regression only) → Epic 4
- **FR-17** Dashboard public share w/ principal → Epic 4
- **FR-18** Currency Field → Epic 2
- **FR-19** Percent Field → Epic 2
- **FR-20** Barcode Field → Epic 2
- **FR-21** Autonumber Field → Epic 2
- **FR-21B** Running Count Field → Epic 2
- **FR-22** Chart Element → Epic 5
- **FR-23** Metric Element → Epic 5
- **FR-24** Kanban/Calendar/Timeline embed Elements → Epic 5
- **FR-25** Record review layout → Epic 5
- **FR-26** Row comments + @mentions → Epic 6
- **FR-27** Comment notifications → Epic 6
- **FR-28** Personal Views → Epic 1
- **FR-29** RBAC role foundation + Commenter → Epic 1
- **FR-30** Field Permissions → Epic 1
- **FR-31** Interface-only collaborator → Epic 6
- **FR-32** Locked Views → Epic 1
- **FR-33** Password-protected share links → Epic 1
- **FR-33B** Exports honor Field Permissions → Epic 1

*All 35 FR entries mapped. FR-16 is non-regression-only (no build story).*

## Epic List

### Epic 1: Trust & Access Foundation
Workspace admins can grant scoped Roles (Viewer/Commenter/Editor/Admin), restrict who edits or sees individual Fields, keep personal views private, lock shared views, and publish password-protected share links that never leak more than intended — the load-bearing permission layer every later surface enforces against (Realizes UJ-4). Opens with the clean-room process gate (AR-1) since most items are Bucket A clean-room reimplements.
**FRs covered:** FR-29, FR-30, FR-28, FR-32, FR-33, FR-33B
**Dependency note:** Bucket A `[A]` stories blocked until Open Q7 (clean-room owner + legal sign-off) is resolved. Establishes `core/rbac/` + `core/field_permissions/` enforcement layer (AR-12/AR-13) + Argon2id share principal (AR-14) + personal/locked view model (AR-11) that Epics 3–6 wire into.

### Epic 2: Richer Field Types
Editors can capture business data faithfully with five new typed Fields — Currency, Percent, Barcode (display), Autonumber, and Running Count — instead of free-text hacks.
**FRs covered:** FR-18, FR-19, FR-20, FR-21, FR-21B
**Dependency note:** All Bucket B / license-clean — unblocked immediately, parallel to Epic 1 (not gated on clean-room). Top quick wins (§13 step-1 foundation).

### Epic 3: Visualize Data Multiple Ways
Editors can flip one Table between Kanban board, Calendar, Timeline, Gantt (with task dependencies, CPM critical path, and milestones), and Map views — visualizing and rescheduling the same data without exporting or duplicating it (Realizes UJ-1, UJ-2, UJ-5).
**FRs covered:** FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, FR-7, FR-8, FR-9, FR-10, FR-11, FR-12, FR-13, FR-34
**Dependency note:** Kanban/Calendar/Timeline and conditional row coloring (FR-34) are Bucket A (gated on clean-room); Gantt/Map are Bucket B. FR-34 reuses the MIT decoration scaffold already in core — Calendar/Timeline need new render wiring. All views honor Epic 1's field-permission layer. Includes geocoding infra (AR-6) + TaskDependency/CPM backend engine (AR-8) + Frappe Gantt/MapLibre lazy-loaded renderers (AR-4/AR-5).

### Epic 4: Dashboards & Charts
Users can report on data by adding bar/line/pie/scatter chart Widgets and summary metrics to a Dashboard and sharing it via a least-privilege public link (Realizes UJ-1).
**FRs covered:** FR-14, FR-15, FR-16, FR-17
**Dependency note:** Builds the shared ECharts charting foundation (AR-3) + grouped-aggregate Data Source (AR-9) — both reused by Epic 5. Bar/pie chart widgets are Bucket A; line/scatter Bucket B. Dashboard module + metric Widget already free (FR-16 non-regression only). FR-17 share consumes Epic 1's share-principal/KDF.

### Epic 5: Build Apps & Embeds
Builders can assemble App Builder Pages with live chart and metric Elements, embedded Kanban/Calendar/Timeline views, and a record-review walkthrough — publishing internal tools and client apps over the same data (Realizes UJ-1, UJ-3).
**FRs covered:** FR-22, FR-23, FR-24, FR-25
**Dependency note:** All Bucket B. Consumes Epic 4 charting foundation + Data Source and Epic 3 view renderers (embeds wrap them, do not reimplement). View embeds read-oriented in v1 (Open Q6).

### Epic 6: Collaboration & Client Access
Members can discuss records in threaded comments with @mentions and notifications, and admins can invite interface-only collaborators (e.g. external clients) who access only App Builder Pages and never the underlying database (Realizes UJ-3). Closes with the release-blocking security gate.
**FRs covered:** FR-26, FR-27, FR-31
**Dependency note:** Comments/interface-only are Bucket A (gated on clean-room). Interface-only (FR-31) requires App Builder Pages (Epic 5) present. Final story = AR-2 threat model + exhaustive role-combination test matrix + security review covering FR-30/31/33/33B and all data surfaces — a release blocker (§13 step 7).

---

## Epic 1: Trust & Access Foundation

Workspace admins can grant scoped Roles, restrict edit/visibility of individual Fields, keep personal views private, lock shared views, and publish password-protected share links — the load-bearing permission layer that every later surface enforces against. Realizes UJ-4.

### Story 1.1: Establish the clean-room process gate

As a workspace admin / engineering lead,
I want a legally-signed-off clean-room process in place before any premium feature is reimplemented,
So that Bucket A free-tier work proceeds without contaminating it with protected `premium/`/`enterprise/` source.

**Acceptance Criteria:**

**Given** the team has read-access to `premium/` and `enterprise/` dirs,
**When** the clean-room gate is stood up,
**Then** a named owner and legal sign-off are recorded for the process (Open Q7 resolved),
**And** an implementer-isolation mechanism exists — either a walled-off group with enforced no-access to `premium/`/`enterprise/` or external/contracted implementers.

**Given** a behavior spec is authored for a Bucket A feature,
**When** it is reviewed,
**Then** it cites only allowed public sources (public Baserow docs, public upstream SaaS UI, public issues/changelogs),
**And** no `premium/`/`enterprise/` internal symbol name appears as the thing to replicate (free-core MIT symbols are allowed).

**Given** a Bucket A pull request is opened,
**When** it is submitted for merge,
**Then** a provenance record (sources consulted + implementer attestation) is required,
**And** the merge is blocked without it (provenance log = hard merge gate).

### Story 1.2: RBAC role model and migration

As a workspace admin,
I want a granular Role hierarchy above the current ADMIN/MEMBER model,
So that I can later assign Viewer, Commenter, Editor, and Admin tiers to members. Realizes UJ-4. `[A]`

**Acceptance Criteria:**

**Given** the free tier today has only ADMIN/MEMBER (`core/models.py`),
**When** the RBAC layer (`core/rbac/`) is introduced,
**Then** fixed Roles Viewer / Commenter / Editor / Admin are assignable at workspace and database scope,
**And** role checks route through a new PermissionManager registered into the existing `PERMISSION_MANAGERS` chain (never a parallel path).

**Given** existing members with ADMIN or MEMBER,
**When** the migration runs,
**Then** ADMIN maps to Admin and MEMBER maps to Editor (not Viewer/Commenter — no silent write-loss),
**And** the migration is reversible with a documented rollback,
**And** a test asserts every pre-migration member retains equivalent write capability.

**Given** the per-feature test matrix,
**When** this story ships,
**Then** model → handler → serializer/API → frontend-registry → component tests pass and a provenance record is attached (NFR-7, AR-1).

### Story 1.3: Role enforcement for Commenter and Viewer

As a workspace admin,
I want Commenter and Viewer Roles enforced server-side,
So that scoped members can read (and comment) but not restructure data. Realizes UJ-4. `[A]`

**Acceptance Criteria:**

**Given** a member with the Commenter Role,
**When** they attempt to create/edit/delete a Row, Field, or View,
**Then** the operation is denied with 403 on both REST and WebSocket,
**And** they can still read Rows and post Comments.

**Given** a member with the Viewer Role,
**When** they attempt to comment or edit,
**Then** the operation is denied with 403 while read access succeeds.

**Given** enforcement is requested,
**When** any role check runs,
**Then** it resolves through `PERMISSION_MANAGERS`, never a parallel/ad-hoc check (NFR-4).

### Story 1.4: Central field-permission layer with edit restriction

As an admin,
I want to restrict who may edit a specific Field, enforced through one central layer,
So that sensitive Fields (e.g. Salary) are read-only to unauthorized members everywhere. Realizes UJ-4. `[A]`

**Acceptance Criteria:**

**Given** the central enforcement layer (`core/field_permissions/`) is built,
**When** an admin sets a Field to no-edit for a Role/member,
**Then** edits from unauthorized members are rejected server-side with 403,
**And** the Field renders read-only for them,
**And** the rule persists per Field and applies uniformly.

**Given** the layer is the single enforcement path,
**When** a new data surface needs field-permission checks,
**Then** it consumes this layer (one queryset/serializer redactor + one predicate guard), not a per-surface ad-hoc check.

### Story 1.5: Field visibility hiding, inference-oracle guard, and cache invalidation

As an admin,
I want a hidden-by-permission Field to be invisible to unauthorized members across every current data surface, with no inference leak,
So that restricted values cannot be read or deduced. Realizes UJ-4. `[A]`

**Acceptance Criteria:**

**Given** a Field is hidden-by-permission for a principal,
**When** that principal reads via any current surface (all View Types, search, REST, WebSocket payloads),
**Then** the Field value is not returned through any of them.

**Given** the same hidden Field,
**When** the unauthorized principal attempts to filter or sort *on* it,
**Then** the predicate is rejected (inference-oracle guard) because membership/count/order would leak the value.

**Given** a permission change on a Field,
**When** it is applied,
**Then** cached row/field payloads and the Redis model-cache are invalidated and active sessions/WebSocket subscriptions are re-evaluated.

**Given** a WebSocket subscription,
**When** a principal cannot see a Table/Row,
**Then** they cannot open its channel (authorize at subscribe time, not only payload-filter) (NFR-4).

### Story 1.6: Personal Views

As a member,
I want to mark a View as Personal so only I can see it,
So that I can triage without disturbing the team's layout. Realizes UJ-4. `[A]`

**Acceptance Criteria:**

**Given** a member marks a View Personal,
**When** other members list Views,
**Then** the Personal View is filtered out of their list,
**And** a direct fetch-by-id of another member's Personal View returns 403 (no IDOR — not just list-hiding).

**Given** a Personal View,
**When** the owner toggles it back to shared,
**Then** it becomes visible to others again,
**And** Personal behavior works across all View Types (grid, kanban, calendar, etc.).

### Story 1.7: Locked Views

As an editor,
I want to lock a View's configuration so others cannot change it,
So that a shared "Master" layout stays intact. Realizes UJ-4. `[A]`

**Acceptance Criteria:**

**Given** a Locked View,
**When** a non-owner attempts to change its filters/sorts/fields/layout,
**Then** the change is rejected server-side (config read-only),
**And** Data within the View remains editable per the member's Role.

**Given** a Locked View,
**When** an unlock is attempted,
**Then** only an Admin or the lock owner can remove the lock (defined unlock authority).

### Story 1.8: Password-protected share links with least-privilege principal

As a member,
I want to add a password to a public share link that resolves under a least-privilege principal,
So that I can share read-only Data safely without exposing my full permissions. `[B]`

**Acceptance Criteria:**

**Given** a password-protected share link,
**When** a visitor enters the correct password,
**Then** read access is granted under a deny-by-default least-privilege **share principal** (FR-17), never the sharer's permissions,
**And** hidden-by-permission Fields and restricted Rows are not exposed through the link.

**Given** the password store,
**When** a password is set and later verified,
**Then** it is hashed with Argon2id (defined work factor) and compared in constant time,
**And** the share token is high-entropy and unguessable (no sequential/enumerable IDs).

**Given** repeated wrong-password attempts,
**When** they exceed the threshold,
**Then** rate-limiting/lockout applies and the error response is uniform (does not reveal whether a link exists).

**Given** the password is removed,
**When** the link is accessed,
**Then** it reverts to open/closed as configured.

### Story 1.9: Exports honor Field Permissions

As an admin,
I want every export path to respect Field Permissions and row restrictions,
So that hidden Data cannot leak through a download. `[X]`

**Acceptance Criteria:**

**Given** a principal exports via CSV/JSON/XLSX, Map, or any download,
**When** the export is produced,
**Then** hidden-by-permission Fields (FR-30) and restricted Rows are absent from every format,
**And** the export path consumes the central field-permission layer (Story 1.5).

**Given** a public/anonymous or interface-only principal,
**When** they attempt to export,
**Then** they cannot export beyond their granted surface.

---

## Epic 2: Richer Field Types

Editors can capture business data faithfully with five new typed Fields instead of free-text hacks. All Bucket B / license-clean.

### Story 2.1: Currency Field

As an editor,
I want a Currency Field with a configurable symbol and precision,
So that monetary values store and display correctly. `[B]`

**Acceptance Criteria:**

**Given** an editor creates a Currency Field,
**When** they set a currency symbol and decimal precision,
**Then** values store as numbers and render with the configured symbol and decimal places,
**And** the symbol and precision persist as Field config.

**Given** a Currency Field,
**When** the Table is sorted or filtered on it,
**Then** ordering is numeric, not lexical (correct `get_order_by_field_string` + indexing, NFR-2).

### Story 2.2: Percent Field

As an editor,
I want a Percent Field with configurable precision,
So that percentages display with a `%` and sort numerically. `[B]`

**Acceptance Criteria:**

**Given** an editor creates a Percent Field,
**When** a value is entered (whole-number entry convention, Open Q8),
**Then** it renders with a `%` suffix at the configured precision,
**And** underlying numeric storage and sort/filter are correct and consistent.

### Story 2.3: Barcode Field

As an editor,
I want a Barcode Field that renders a value as a scannable code,
So that I can display QR/Code128 codes from stored data. `[B]`

**Acceptance Criteria:**

**Given** an editor creates a Barcode Field with a chosen symbology,
**When** a value is stored,
**Then** the Field renders a scannable code (e.g. QR, Code128) client-side from the value,
**And** the symbology is configurable and persists.

**Given** the Barcode Field,
**When** a user views it,
**Then** only display is supported — camera-based scanning to capture values is out of scope.

### Story 2.4: Autonumber Field

As an editor,
I want an Autonumber Field that assigns a stable auto-incrementing integer to each Row,
So that every Row has a durable sequence number in creation order. `[B]`

**Acceptance Criteria:**

**Given** an Autonumber Field,
**When** a new Row is created,
**Then** it receives the next unused integer automatically and the value is not user-editable.

**Given** existing Rows,
**When** a Row is deleted,
**Then** other Rows are not renumbered (assigned values are stable).

**Given** concurrent inserts and bulk import,
**When** Rows are created,
**Then** the sequence is monotonic per Table and collision-free (Postgres-sequence-backed, not read-then-increment); gaps are acceptable on rollback/delete.

### Story 2.5: Running Count Field

As an editor,
I want a Running Count Field that counts Rows matching a condition,
So that I can see how many Rows satisfy a filter without a formula. `[B]`

**Acceptance Criteria:**

**Given** a Running Count Field with a configured condition (default whole-Table scope, Open Q11),
**When** matching Data changes,
**Then** the Field recomputes the count of Rows satisfying its condition,
**And** existing relational Count behavior is unaffected.

---

## Epic 3: Visualize Data Multiple Ways

Editors can flip one Table between Kanban, Calendar, Timeline, Gantt (dependencies/CPM/milestones), and Map views — visualizing and rescheduling the same data without exporting. Realizes UJ-1, UJ-2, UJ-5. All views honor Epic 1 field permissions.

### Story 3.1: Create and configure a Kanban View

As an editor,
I want to add a Kanban View grouped by a Single-select Field,
So that I can see Rows as a board. Realizes UJ-1. `[A]`

**Acceptance Criteria:**

**Given** any Table,
**When** an editor adds a Kanban View and chooses a Single-select Field,
**Then** columns render one per option plus an "Uncategorized" column for empty values,
**And** existing View filters, sorts, and field visibility apply,
**And** the View persists and reopens with the same configuration.

### Story 3.2: Drag a Kanban card between columns

As an editor,
I want to drag a card to another column,
So that moving a card updates the underlying grouping Field. Realizes UJ-1. `[A]`

**Acceptance Criteria:**

**Given** a Kanban card,
**When** it is dropped in another column,
**Then** the Row's grouping Field is set to the target option (or null for Uncategorized),
**And** the change broadcasts in real time to other connected clients without a refresh (NFR-1).

**Given** the update fails,
**When** the server rejects it,
**Then** the card rolls back to its origin column and an error surfaces (optimistic + rollback, NFR-3).

### Story 3.3: Configure Kanban card appearance

As an editor,
I want to choose which Fields and the cover image show on a card,
So that cards display the right information. `[A]`

**Acceptance Criteria:**

**Given** a Kanban View,
**When** an editor selects card-face Fields and toggles the cover image,
**Then** hidden Fields do not render on cards and the setting persists per View,
**And** cards render without dependency on row coloring (out of scope this release).

### Story 3.4: Create and configure a Calendar View

As an editor,
I want to add a Calendar View positioned by a Date Field,
So that I can see Rows on a month/week calendar. `[A]`

**Acceptance Criteria:**

**Given** a Table with a Date Field,
**When** an editor adds a Calendar View and selects the Date Field,
**Then** Rows with a value appear on their date and Rows without are listed in an "unscheduled" tray,
**And** month and week display modes are available,
**And** if both a start and end Date Field are configured, an entry spans multiple days as a continuous bar; with a single Date Field it renders single-day,
**And** filters/sorts/field-visibility apply.

### Story 3.5: Reschedule a calendar entry by drag

As an editor,
I want to drag a calendar entry to another date,
So that the Date Field updates. `[A]`

**Acceptance Criteria:**

**Given** a calendar entry,
**When** it is dropped on another date,
**Then** the Row's Date Field updates to the target date and broadcasts in real time (NFR-1),
**And** a failed update rolls back and surfaces an error (NFR-3).

### Story 3.6: Create and configure a Timeline View

As an editor,
I want a Timeline View showing Rows as bars over start/end Date Fields,
So that I can see scheduling on a zoomable time axis. `[A]`

**Acceptance Criteria:**

**Given** a Table with start and end Date Fields,
**When** an editor adds a Timeline View and maps them,
**Then** each Row renders as a bar from start to end on the time axis,
**And** day/week/month zoom levels are selectable and persist,
**And** Rows missing start or end are listed separately, not rendered as malformed bars.

### Story 3.7: Reschedule and resize Timeline bars

As an editor,
I want to drag a bar to move it or drag its edge to resize it,
So that I can adjust schedule and duration. `[A]`

**Acceptance Criteria:**

**Given** a Timeline bar,
**When** it is moved,
**Then** both Date Fields update preserving duration,
**And** when an edge is dragged the dragged endpoint updates,
**And** changes broadcast in real time and failures roll back (NFR-1/NFR-3).

### Story 3.8: Render a Gantt View

As an editor,
I want a Gantt View building on the timeline with a dependency layer,
So that I can plan a project on a time axis. Realizes UJ-2. `[B]`

**Acceptance Criteria:**

**Given** a Table with start/end Date Fields,
**When** an editor adds a Gantt View,
**Then** bars render like Timeline (Story 3.6) with a dependency layer overlaid,
**And** zoom and filter/sort behavior match Timeline,
**And** the render uses the Frappe Gantt lazy-loaded renderer (AR-4) drawing bars/connectors only.

### Story 3.9: Define Task Dependencies with cycle prevention

As an editor,
I want to draw dependencies between task Rows,
So that the schedule reflects predecessor/successor ordering. Realizes UJ-2. `[B]`

**Acceptance Criteria:**

**Given** two task Rows,
**When** an editor draws a dependency,
**Then** it is persisted as a directed edge (predecessor → successor), survives reload, and renders as a connector line.

**Given** any mutation path — interactive create, restore-from-trash, or import,
**When** an operation would introduce a cycle,
**Then** it is rejected with a clear error (cycle prevention holds across ALL paths, AR-8).

### Story 3.10: Prompt-first reschedule on dependency

As an editor,
I want to be prompted before dependent tasks shift when I move a predecessor,
So that cascading reschedules are intentional. Realizes UJ-2. `[B]`

**Acceptance Criteria:**

**Given** a finish-to-start dependency,
**When** a predecessor's end moves past a successor's start,
**Then** a confirmation prompt names the successor(s) that would move and the count of cascaded dependents.

**Given** the prompt,
**When** the user confirms,
**Then** successors shift to maintain FS ordering (preserving duration), the shift cascades through the chain, and the whole shift is undoable as a single step.

**Given** the prompt,
**When** the user declines,
**Then** the predecessor move is kept but dependents stay in place and the dependency is flagged as violated (not silently broken),
**And** overlapping cascades cannot interleave (affected Rows are locked, NFR-3).

### Story 3.11: Milestones and Critical Path (CPM)

As an editor,
I want milestones and an automatically-highlighted critical path,
So that I can spot the zero-slack chain and key dates. `[B]`

**Acceptance Criteria:**

**Given** a task,
**When** an editor marks it a Milestone,
**Then** it renders as a zero-duration diamond marker on its date.

**Given** the FS dependency graph,
**When** the system computes scheduling,
**Then** a CPM forward pass (earliest start/finish) and backward pass (latest start/finish) run, tasks with zero slack form the Critical Path and are visually distinguished,
**And** the Critical Path recomputes when any dependency or date changes.

**Given** user-entered dates that violate a dependency,
**When** CPM runs,
**Then** the task is flagged as a scheduling conflict and excluded from a valid Critical Path until resolved; CPM uses the dependency-implied schedule and surfaces the discrepancy,
**And** resource leveling, lag/lead, and SS/FF/SF types are out of scope (FS only).

### Story 3.12: Geocoding infrastructure (provider abstraction + throttled queue)

As a self-hosting operator / cloud user,
I want a configurable geocoding service that caches results and respects rate limits,
So that the Map View can resolve addresses without blocking the UI or violating provider ToS. `[B]`

**Acceptance Criteria:**

**Given** a geocoding request,
**When** it is processed,
**Then** it routes through a provider abstraction selecting Google Geocoding (cloud) or Nominatim-OSM (self-host) via env var (AR-6),
**And** resolved lat/lng is cached in the DB and not re-requested on every load,
**And** geocoding runs through a Celery throttled queue respecting provider rate limits without blocking the UI.

**Given** new env vars (provider selector, API key/billing, tile source),
**When** they are added,
**Then** they follow the `add-django-config-env-var` pattern (base.py + compose + env-remap + docs).

**Given** geocoded lat/lng is derived from an address Field,
**When** it is read,
**Then** the source Field's permission is enforced per-principal at read time (NFR-4).

### Story 3.13: Configure a Map View

As an editor,
I want to add a Map View plotting Rows by an address Field or lat/lng pair,
So that I can see records geographically. Realizes UJ-5. `[B]`

**Acceptance Criteria:**

**Given** a Table with an address Field (or lat/lng pair),
**When** an editor adds a Map View and chooses the location source,
**Then** Rows with a resolvable location render as pins and unresolvable Rows are listed in a "could not locate" tray,
**And** filters/sorts apply to which Rows are plotted,
**And** the map renders via MapLibre GL JS lazy-loaded (AR-5).

### Story 3.14: Geocode and interact with map pins

As a field user,
I want to click a pin to open its Row and see pins cluster by zoom,
So that I can navigate account density. Realizes UJ-5. `[B]`

**Acceptance Criteria:**

**Given** a Map View,
**When** addresses are geocoded (via Story 3.12 infra),
**Then** coordinates are cached and not re-requested on every load,
**And** clicking a pin opens the corresponding Row detail,
**And** pins cluster at low zoom and expand on zoom-in.

---

## Epic 4: Dashboards & Charts

Users can report on data with bar/line/pie/scatter chart Widgets and summary metrics on a Dashboard, sharing it via a least-privilege public link. Realizes UJ-1. Builds the shared charting foundation reused by Epic 5.

### Story 4.1: Charting foundation (shared, lazy-loaded)

As a developer building charts,
I want a single shared ECharts-based charting foundation,
So that Dashboard Widgets and App Builder Elements render charts from one implementation. `[B]`

**Acceptance Criteria:**

**Given** the charting foundation,
**When** it is built,
**Then** it wraps Apache ECharts via vue-echarts (AR-3) supporting bar/line/pie/doughnut/scatter,
**And** it is consumed by both FR-15 (Dashboard) and FR-22 (App Builder) — built once.

**Given** the heavy chart bundle,
**When** a route loads it,
**Then** it is lazy-loaded only on routes that need it and the added bundle stays within the ≤400KB gzip budget measured with the code actually loaded (NFR-2/SM-C3).

### Story 4.2: Grouped-aggregate Data Source

As a user,
I want a Data Source that groups Rows by a Field and aggregates a value per group,
So that charts have category/value data to render. `[B]`

**Acceptance Criteria:**

**Given** a Table,
**When** a user configures a grouped-aggregate Data Source,
**Then** it returns (category, aggregated-value[, series]) tuples with a configurable group-by Field and aggregation (count/sum/avg/min/max),
**And** it is registered in `service_type_registry` (AR-9) and reusable by Dashboard and App Builder.

**Given** the requesting principal,
**When** the Data Source aggregates,
**Then** it honors field-hide and row permissions (Story 1.5) — it does not aggregate over Fields the principal cannot see (no inference leak, NFR-4).

### Story 4.3: Chart Widgets — bar and pie/doughnut (clean-room)

As a user,
I want bar and pie/doughnut chart Widgets on a Dashboard,
So that I can visualize grouped data. Realizes UJ-1. `[A]`

**Acceptance Criteria:**

**Given** a Dashboard and a grouped-aggregate Data Source,
**When** a user adds a bar or pie/doughnut Widget,
**Then** it renders from the Data Source with configurable category/value/series,
**And** it is a clean-room reimplementation (provenance record attached, AR-1),
**And** it interoperates with the existing free `summary` metric Widget on the same Dashboard.

### Story 4.4: Chart Widgets — line and scatter

As a user,
I want line and scatter chart Widgets on a Dashboard,
So that I can visualize trends and distributions. `[B]`

**Acceptance Criteria:**

**Given** a Dashboard and a grouped-aggregate Data Source,
**When** a user adds a line or scatter Widget,
**Then** it renders correctly from the Data Source,
**And** the Widget updates when underlying Data changes via fetch-on-load + WebSocket row-event invalidation (debounced re-aggregate, no polling, AR-15/NFR-1).

**Given** a Dashboard with up to 12 chart/metric Widgets over 100k-row Tables,
**When** it loads,
**Then** charts lazy-load so an off-screen Widget does not block first paint (NFR-2).

### Story 4.5: Metric Widget non-regression

As a user,
I want the existing summary metric Widget to keep working alongside new chart Widgets,
So that adding charts does not break existing dashboards. `[X]`

**Acceptance Criteria:**

**Given** a Dashboard with the existing free summary metric Widget,
**When** chart Widgets are added,
**Then** the metric Widget continues to compute and render correctly (non-regression check only, no new build),
**And** an automated test asserts metric+chart coexistence.

### Story 4.6: Dashboard public share with least-privilege principal

As a user,
I want to share a Dashboard via a public link that resolves under a defined principal,
So that stakeholders see it read-only without exposing restricted Data. `[B]`

**Acceptance Criteria:**

**Given** a Dashboard,
**When** a user creates a public link,
**Then** it renders the Dashboard read-only without authentication,
**And** Data Sources resolve under a deny-by-default least-privilege share principal (Story 1.8), not the sharer's permissions — hidden-by-permission Fields and restricted Rows are not exposed.

**Given** a shared Dashboard link,
**When** the user revokes it,
**Then** access is disabled immediately server-side with no cached bypass.

---

## Epic 5: Build Apps & Embeds

Builders can assemble App Builder Pages with live chart/metric Elements, embedded views, and a record-review walkthrough. Realizes UJ-1, UJ-3. All Bucket B; consumes Epic 4 charting + Epic 3 renderers.

### Story 5.1: Chart Element

As a builder,
I want to place chart Elements on a Page bound to a Data Source,
So that published apps show live visualizations. Realizes UJ-1, UJ-3. `[B]`

**Acceptance Criteria:**

**Given** an App Builder Page,
**When** a builder adds a bar/line/pie/doughnut/scatter chart Element bound to a Data Source,
**Then** it renders on the published Page from its Data Source (reusing the Story 4.1 charting foundation),
**And** it respects Page-level filters/parameters where applicable.

### Story 5.2: Metric Element

As a builder,
I want to place a summary metric Element on a Page,
So that apps show a key aggregated number. `[B]`

**Acceptance Criteria:**

**Given** an App Builder Page,
**When** a builder adds a metric Element,
**Then** it computes and renders its aggregation on the published Page.

### Story 5.3: Kanban / Calendar / Timeline embed Elements

As a builder,
I want to embed Kanban, Calendar, or Timeline displays of a Table on a Page,
So that apps present data in those view layouts. Realizes UJ-3. `[B]`

**Acceptance Criteria:**

**Given** an App Builder Page and a Data Source,
**When** a builder adds a Kanban/Calendar/Timeline embed Element,
**Then** it renders the corresponding View layout on the published Page by wrapping the Epic 3 renderers (does not reimplement them),
**And** read/interaction permissions follow the viewer's Role (embeds read-oriented in v1, Open Q6).

### Story 5.4: Record review layout Element

As a builder,
I want a record-review Element that walks a user through filtered Rows one at a time,
So that reviewers can step through records. `[B]`

**Acceptance Criteria:**

**Given** an App Builder Page and a Data Source,
**When** a builder adds a record-review Element,
**Then** it presents one Row at a time with next/previous navigation over the Data Source,
**And** AI-generated review layouts are out of scope.

---

## Epic 6: Collaboration & Client Access

Members can discuss records in threaded comments with @mentions, and admins can invite interface-only collaborators who never see the database. Realizes UJ-3. Closes with the release-blocking security gate.

### Story 6.1: Row comments with @mentions

As a member with at least Commenter Role,
I want to post threaded comments on a Row and @mention members,
So that we can discuss records in context. Realizes UJ-1, UJ-3. `[A]`

**Acceptance Criteria:**

**Given** a Row the member can see,
**When** they post a Comment,
**Then** it persists per Row, renders in thread order, and broadcasts in real time only to recipients who can see that Row (per Story 1.3/1.5),
**And** a Comment must not embed or leak hidden-by-permission Field values to lower-privileged subscribers.

**Given** an @mention,
**When** the mentioned member lacks Row access,
**Then** the mention is rejected (no notification, no row-link leak),
**And** mentioning a member who has access is allowed.

**Given** a member's own Comment,
**When** they edit or delete it,
**Then** it is supported per Role, and Admins can moderate others' Comments.

### Story 6.2: Comment notifications

As a mentioned or subscribed member,
I want an in-app notification for comment activity I'm authorized to see,
So that I know when I'm needed. `[X]`

**Acceptance Criteria:**

**Given** an @mention or subscription,
**When** relevant Comment activity occurs,
**Then** an in-app notification linking to the Row/Comment is generated only if the recipient can access the Row,
**And** it reuses the existing in-app notification infrastructure (email digest deferred).

### Story 6.3: Interface-only collaborator Role

As an admin,
I want to invite a member who can access only App Builder Pages and never the underlying Data,
So that external clients (e.g. Priya) can use an app without seeing the database. Realizes UJ-3. `[A]`

**Acceptance Criteria:**

**Given** an interface-only collaborator,
**When** they open a granted App Page,
**Then** they see only that Page's Elements; database navigation is hidden.

**Given** the same collaborator,
**When** they attempt any Database/Table/View REST endpoint, App Builder Data Source dispatch, formula evaluation, or WebSocket channel beyond the granted Page,
**Then** access is denied (403/empty) — enforced data-scoped, not just nav-hiding (no back-door via data source or formula),
**And** Data returned through a Page is the minimum its Elements need, not the full row.

### Story 6.4: Security release gate — threat model + role-combination matrix

As an engineering lead,
I want a threat model and exhaustive role-combination test matrix passed before release,
So that the new permission surfaces are verified leak-free. `[Gate — release blocker]`

**Acceptance Criteria:**

**Given** all collaboration and permission FRs are implemented,
**When** the security gate runs (§13 step 7),
**Then** a role-combination matrix enumerates every combination of {Viewer, Commenter, Editor, Admin, interface-only} × {field-permission state} × {personal/locked view} × {public/password share} as resolved cells with a most-restrictive-wins precedence rule,
**And** a threat model + security review covers FR-30/31/33/33B and all data surfaces (charts, embeds, exports, WebSocket, formulas/lookups/rollups, filter/sort predicates, search).

**Given** the gate,
**When** any cell or surface fails,
**Then** the release is blocked until resolved.
