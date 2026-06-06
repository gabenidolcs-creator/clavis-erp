---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-clavis-erp-2026-06-06/prd.md
  - _bmad-output/planning-artifacts/prds/prd-clavis-erp-2026-06-06/addendum.md
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2026-06-06'
project_name: 'clavis-erp'
user_name: 'Tinsu'
date: '2026-06-06'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
34 FRs (FR-1–FR-33B) in 5 batches. Each maps to an existing Baserow registry extension point:
- Batch 1 Views (FR-1–13): new `ViewType` subclasses — Kanban/Calendar/Timeline (Bucket A clean-room), Gantt + Map (Bucket B). Gantt adds a new `TaskDependency` model + CPM critical-path engine.
- Batch 2 Dashboard (FR-14–17): chart `WidgetType`s (bar/pie Bucket A, line/scatter Bucket B) + a new grouped-aggregate Data Source; dashboard module + metric widget already free (non-regression only).
- Batch 3 Field Types (FR-18–21B): Currency/Percent (extend `NumberFieldType`), Barcode (wrap `TextField`), Autonumber (DB-sequence-backed), Running Count — all Bucket B.
- Batch 4 App Builder (FR-22–25): new `ElementType`s — chart/metric (reuse charting foundation), Kanban/Calendar/Timeline embeds (wrap Batch-1 renderers), record review.
- Batch 5 Collaboration (FR-26–33B): RBAC foundation (FR-29, load-bearing prerequisite), comments + @mentions, personal/locked views, field permissions, interface-only collaborator, password share links, export enforcement — mostly Bucket A, security-critical.

**Non-Functional Requirements:**
- Real-time WebSocket broadcast on all mutating views/collab; p95 latency ≤ baseline (SM-C1).
- Perf: virtual-scroll/lazy-row at 100k rows; correct `get_order_by_field_string` + field indexing for new sortable fields; map clustering; ≤400KB gzip added bundle, lazy-loaded.
- Optimistic UX with rollback; defined concurrent-edit semantics (LWW per field + snap-to-authoritative); Gantt cascade row-locking.
- Security every-surface: server-side enforcement via `PERMISSION_MANAGERS`, WebSocket subscribe-time auth, inference-oracle guards, deny-by-default share principal, KDF + rate-limit for password shares, cache invalidation (row/field + aggregate + Redis model-cache) on permission change.
- a11y (WCAG 2.1 AA target), i18n (all new strings in catalogs), full test matrix per feature (model→handler→serializer/API→frontend registry→component).

**Scale & Complexity:**
- Primary domain: full-stack web (Django/DRF/Celery/Postgres/Redis + Nuxt3/Vue3/Vuex).
- Complexity level: high.
- Estimated architectural components (new/extended): ~5 ViewTypes, 5 FieldTypes, chart WidgetTypes + Data Source, ~4 ElementTypes, RBAC role layer, comment subsystem, field-permission enforcement layer, geocoding service, CPM/dependency engine, charting foundation.

### Technical Constraints & Dependencies

- **Legal clean-room (binding, §8):** Bucket A features built only from public sources by an isolated implementer population; provenance log = merge gate; blocks all Bucket A until owner + legal sign-off (Open Q7). Repo-access contamination unresolved.
- **Brownfield registry patterns mandatory:** singleton registries populated in Django `ready()`; thin API views over Handlers; frontend `$registry.register`. New types must not require core rewrites.
- **Platform:** web only; Vue 3 / Nuxt 3 (repo authoritative); JSX in `.jsx`/`.tsx`.
- **Geocoding provider split:** Google (cloud) / Nominatim-OSM (self-host) via env var, driven by Google ToS caching constraint.
- **Preserve differentiators:** unlimited records, WebSocket realtime, self-hosting, two-way Postgres sync, push webhooks, MCP server.

### Cross-Cutting Concerns Identified

- **Permission enforcement** — spans every data surface (REST, WebSocket, Data Source dispatch, formulas/lookups/rollups, chart aggregation, filter/sort predicates, search, exports); release-gated by threat model + exhaustive role-combination matrix with most-restrictive-wins precedence.
- **Charting foundation** — shared by Dashboard widgets and App Builder elements; build once.
- **View renderers** — Batch-1 views reused by App Builder embeds.
- **Real-time/WebSocket** — every new mutating feature; subscribe-time authorization + per-recipient filtering.
- **Clean-room provenance** — process gate across all Bucket A work.
- **Caching & invalidation** — permission changes must invalidate row/field, aggregate/chart, and Redis model caches and re-evaluate live sessions.
- **i18n / a11y / test matrix** — uniform across all features.

## Starter Template Evaluation

### Primary Technology Domain
Full-stack web — **brownfield extension** of the existing Baserow open-core monorepo. No starter template applies; the existing repository is the architectural foundation.

### Starter Options Considered
None. This is not a greenfield project. Evaluating starter templates (Next.js, T3, etc.) would be a category error — clavis-erp builds *inside* an established Django + Nuxt monorepo whose conventions, registries, and build tooling are fixed and authoritative. All 34 FRs slot into existing extension points.

### Selected Foundation: Existing clavis-erp / Baserow monorepo

**Rationale:** Every feature is a registry extension (ViewType / FieldType / WidgetType / ElementType / service-type / application-type) or a new model + handler + API view within the current layout. Introducing a starter would break the patterns the PRD/addendum mandate ("new types slot in without core rewrites").

**Initialization Command:** N/A — `just init` (existing) installs deps + creates `.env.local`; `just dev up` runs the stack. No project scaffolding step.

**Architectural Decisions Provided by Existing Foundation (pinned versions):**

**Language & Runtime:** Python 3.14 (backend), Vue 3.5 / Nuxt 3.21 (frontend), TypeScript/JS via Vite-compatible Nuxt build; JSX in `.jsx`/`.tsx`.

**Backend stack:** Django 5.2.14, DRF 3.16.1, Celery 5.6.2 (redis broker), PostgreSQL, Redis 6 (django-redis) + django-cachalot 2.8 model cache, WebSocket realtime layer.

**Styling:** SCSS, BEM naming (existing `web-frontend/modules` convention).

**Build Tooling:** `just` orchestration wrapping `uv` (backend) and `yarn` (frontend); Vite via Nuxt 3.

**Testing:** pytest + pytest-django (backend), Vitest 4 (frontend), Storybook (stories), e2e in `e2e-tests/`.

**Code Organization:** monorepo — `backend/src`, `web-frontend/modules`, paid mirrors in `premium/` `enterprise/` (clean-room-walled for Bucket A), `docs/`, `deploy/`.

**Development Experience:** `just dev up` local stack; `just dc-dev up -d` Docker; hot reload via Nuxt; pre-commit lint hooks; Ruff (Python, 88-col) + ESLint/Stylelint/Prettier (frontend).

**Note:** No initialization story needed — foundation exists. First implementation story is the §13 step-0 clean-room process gate, then license-clean foundations.

## Core Architectural Decisions

### Decision Priority Analysis

**Fixed by brownfield foundation (not re-decided — repo is authoritative):**
PostgreSQL + dynamic-model generation; JWT auth (djangorestframework-simplejwt); DRF REST with thin API views over Handler classes; Vuex 4 state; existing WebSocket realtime layer; Redis 6 + django-cachalot 2.8 model cache; Celery 5.6 async; Docker/`just` deploy; registry pattern (`field_type_registry`, `view_type_registry`, `element_type_registry`, `service_type_registry`, `application_type_registry`) for all new types; `PERMISSION_MANAGERS` chain for authorization.

**Critical Decisions (block implementation):** D1 charting, D6 RBAC model, D7 field-permission enforcement layer, D8 TaskDependency+CPM, D9 grouped-aggregate Data Source, D12 password KDF.

**Important Decisions (shape architecture):** D2 Gantt lib, D3 map render, D4 geocoding, D5 barcode, D10 autonumber, D11 chart refresh, D13 geocode cache/throttle, D14 personal/locked view model.

**Deferred / defaulted (PRD Open Qs):** FR-24 embeds default read-only v1 (Open Q6); Running Count default whole-table scope (Open Q11).

### Library Decisions (new dependencies — versions verified June 2026)

| ID | Decision | Choice | License | Version | Rationale / tradeoff |
|---|---|---|---|---|---|
| D1 | Charting (shared: Dashboard widgets + App Builder elements) | Apache ECharts via vue-echarts | Apache-2.0 | echarts 6.0, vue-echarts 8.0.1 | bar/line/pie/scatter native; strong large-dataset perf; canvas+svg renderers. Heavier than ApexCharts → must lazy-load to honor ≤400KB gzip budget (SM-C3). Build once, consumed by FR-15 + FR-22. |
| D2 | Gantt render layer | Frappe Gantt | MIT | 1.2.2 | ~zero-dep, ~50kB, render-only. Dependencies/CPM/cascade computed in **our backend** (D8); lib draws bars/connectors only. DHTMLX rejected (GPLv2, incompatible with MIT free tier). |
| D3 | Map rendering | MapLibre GL JS | BSD-3 | 5.24 | works for both cloud + self-host; tile source chosen by provider abstraction. Google-Maps-JS-only rejected (ToS couples tiles+geocode, blocks self-host cache model — PRD §4.5). |
| D4 | Geocoding | Provider abstraction: Google Geocoding (cloud) / Nominatim-OSM (self-host) | proprietary / ODbL | — | env-var selected per PRD §8. Google ToS forbids long-term cache → self-host path uses Nominatim (cacheable). |
| D5 | Barcode (display only) | qrcode.vue + Code128 renderer (jsbarcode-class lib) | MIT | latest | client-side render from stored value; symbology configurable. Camera scanning deferred (FR-20). |

### Data Architecture

- **D8 — TaskDependency + CPM (FR-9–11):** new `TaskDependency` model holding a directed edge (predecessor→successor) with dependency-type (default FS). **Cycle detection runs on every mutation path** — interactive create, restore-from-trash, import — rejecting any edge that closes a cycle (FR-9). **CPM computed synchronously in a backend handler** (forward/backward pass over the FS graph) on any dependency/date change; graph is bounded per-view so sync keeps Critical Path fresh (FR-11). Cascade reschedule (FR-10) acquires/locks affected Rows so overlapping cascades cannot interleave (§10).
- **D9 — Grouped-aggregate Data Source (FR-14):** new **service-type** registered in `service_type_registry`, returning (category, aggregated-value[, series]) via SQL `GROUP BY` with configurable group-by field + aggregation (count/sum/avg/min/max). Honors requesting principal's field-hide + row permissions (no aggregation over hidden fields). Reused by Dashboard charts (FR-15) and App Builder chart elements (FR-22).
- **D10 — Autonumber (FR-21):** backed by a **Postgres sequence** (`nextval`), not read-then-increment — collision-free under concurrent inserts and bulk import; monotonic per Table; gaps acceptable on delete/rollback.
- **D14 — Personal/Locked Views (FR-28/32):** add `owner` FK + `locked` flag to the free-core `View` model (+ migration). `ViewHandler` enforces: personal views filtered from others' list **and** direct fetch-by-id by a non-owner returns 403 (no IDOR); locked-view config read-only to non-owner/non-admin, data still editable per Role.
- **Field types (D-fields):** Currency/Percent extend `NumberFieldType` with formatting metadata (`currency_symbol`, precision, `number_type`); Barcode wraps `TextField` with `barcode_type`; Running Count computes count-of-matching-rows (default whole-table filter). New field metadata only — migration on field-metadata model, not user tables (dynamic-model pattern).

### Authentication & Security

- **D6 — RBAC model (FR-29):** clean-room role layer with fixed tiers (Viewer / Commenter / Editor / Admin) + interface-only collaborator, assignable at workspace/database scope. Enforced via a **new PermissionManager registered into the existing `PERMISSION_MANAGERS` chain** — never a parallel check path. Migration maps existing `ADMIN`→Admin, `MEMBER`→Editor (no silent write-loss), reversible + test-verified. Behavior-only spec; no enterprise-source copy (§8).
- **D7 — Field-permission enforcement (FR-30):** a **single central enforcement layer** — one queryset/serializer-field redactor + one predicate guard — consumed by every data surface (REST, WebSocket, Data Source dispatch, formulas/lookups/rollups, chart aggregation, filter/sort predicates, search, exports). One code path so no surface is missed. Inference-oracle guard (reject filter/sort *on* a hidden field) lives here. Permission change invalidates row/field + aggregate/chart + Redis model caches and re-evaluates live sessions/subscriptions.
- **D12 — Password share KDF (FR-33):** **Argon2id** (Django Argon2 hasher), constant-time compare, rate-limit + lockout, high-entropy unguessable share tokens, uniform error (no link-existence oracle). Shares resolve under a deny-by-default least-privilege **share principal** (FR-17).
- **WebSocket:** authorize at **subscribe** time, not only payload-filter — a principal who cannot see a Table/Row cannot open its channel (§10).
- **Interface-only (FR-31):** data-scoped, not nav-hiding — deny DB/Table/View endpoints + Data Source dispatch + formula eval + WebSocket channels beyond the granted Page. Mandatory security review + exhaustive role-combination matrix before ship.

### API & Communication Patterns

- All new endpoints follow existing **thin-API-view-over-Handler** pattern; REST + WebSocket + CLI share the handler.
- **D11 — Chart data refresh (FR-15):** fetch-on-load + **WebSocket row-event invalidation** for the bound table (debounced re-aggregate). No polling (preserves SM-C1). Resolves §9 open assumption.
- **D13 — Geocode cache + throttle (FR-13):** lat/lng cached in DB; geocoding runs through a **Celery throttled queue** respecting provider rate limits without blocking UI; geocoded lat/lng is derived data, enforced under the source address field's permission at **read** time.
- Errors/serialization/pagination follow existing DRF conventions; no new API paradigm (no GraphQL).

### Frontend Architecture

- New View renderers, Widgets, and Elements register via `$registry.register(...)` mirroring backend — slot in without core rewrites.
- Vuex grid patterns reused: sparse arrays, lazy row loading, virtual scrolling, optimistic update + rollback. Concurrent-edit = last-write-wins per field + snap-to-authoritative on supersede (§10).
- **Bundle discipline:** ECharts (D1), MapLibre (D3), Frappe Gantt (D2) lazy-loaded only on routes that need them; budget validated with the heavy code actually loaded (SM-C3), not deferred off the landing route.
- SCSS + BEM; JSX in `.jsx`/`.tsx`; Vue 3 render semantics (`h` from `vue`).

### Infrastructure & Deployment

- No infra change — existing Docker/`just` stack, Postgres, Redis, Celery workers.
- New env vars: geocoding provider selector + API key/billing (Google cloud), tile source config (§8). Follow `add-django-config-env-var` skill (base.py + compose + env-remap + docs).
- Monitoring/logging: existing OpenTelemetry Django/Celery instrumentation; no new pipeline.

### Decision Impact Analysis

**Implementation sequence (mirrors PRD §13):**
0. Clean-room process gate (blocks all Bucket A).
1. Foundations: license-clean fields (D10 + Currency/Percent/Barcode/Running-Count), charting foundation (D1), geocoding infra (D4/D13), **RBAC foundation (D6)**.
2. Permission enforcement layer (D7) + personal/locked views (D14) + WebSocket subscribe-auth + export enforcement + share principal/KDF (D12).
3. View layer: Kanban/Calendar/Timeline (Bucket A), Gantt+CPM (D8, D2), Map (D3) — all honor step-2 permissions.
4. Dashboard charts: grouped-aggregate Data Source (D9) + chart Widgets (D1, D11).
5. App Builder Elements: chart/metric (D1) + view embeds (wrap step-3 renderers) + record review.
6. Remaining collaboration: comments + @mentions + notifications, interface-only (FR-31).
7. Security gate (release blocker): threat model + role-combination matrix.

**Cross-component dependencies:**
- D1 charting → consumed by FR-15 (Dashboard) AND FR-22 (App Builder) — build once.
- D6 RBAC → prerequisite for D7 field perms, Commenter, interface-only.
- D7 enforcement layer → every new data surface (D8/D9/views/charts/embeds/exports) must wire into it as it lands; completeness confirmed at step-7 gate.
- D8 backend CPM → D2 Frappe Gantt is render-only over it.
- D9 Data Source → consumed by D1 charts in both Dashboard + App Builder.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Governing rule:** clavis-erp is a brownfield extension. Every new file MUST match the conventions of the nearest existing equivalent. Agents do NOT introduce new naming/structure/format styles — they replicate the established ones below. When in doubt, copy the shape of the closest existing core (MIT) file.

### Naming Patterns

**Database (Postgres / Django models):**
- Tables: Django default (`app_modelname`, lowercase) — never override `db_table` unless the surrounding app does.
- Columns / fields: `snake_case` (`grouping_field_id`, `predecessor_id`).
- Foreign keys: `<entity>` with `_id` implied by Django (`owner = models.ForeignKey(...)`).
- New models register migrations in the owning app's `migrations/` (field-metadata model only — never per-user-table).

**API (DRF REST):**
- Endpoint paths: existing Baserow style (`/api/database/views/...`), plural resource segments, trailing patterns matching neighbors.
- JSON fields: `snake_case` (DRF default in this repo — do NOT camelCase API payloads).
- Route params: DRF `<int:pk>` / `<str:...>` style.
- Status codes: existing convention — 403 for permission denial (every security FR), 400 with structured error code for validation.

**Backend code (Python):**
- `snake_case` files (`view_types.py`, `task_dependency.py`), `PascalCase` classes (`GanttViewType`, `TaskDependency`), `snake_case` functions.
- Ruff format, 88-col, Python 3.14.

**Frontend code (Vue 3 / Nuxt 3):**
- `.vue` components `PascalCase` or existing module convention; registry files `camelCase` (`viewTypes.js`, `fieldTypes.js`).
- `h` imported from `vue`; JSX only in `.jsx`/`.tsx`.
- SCSS BEM matching `web-frontend/modules`.

### Structure Patterns

**Backend:**
- Free-tier code in `backend/src/baserow/...`; type implementations in the owning contrib app (`contrib/database/views/`, `contrib/database/fields/`, `contrib/dashboard/widgets/`, App Builder elements, etc.).
- Tests in `backend/tests/baserow/...` mirroring the `src` path (NOT co-located).
- **Bucket A free reimplementations go in core `backend/src` — NEVER in `premium/` or `enterprise/`.** Reference premium/enterprise only for the registration *shape* (public MIT symbols), never to copy behavior (§8).

**Frontend:**
- Module code in `web-frontend/modules/<module>/`; registry registration in the module's `viewTypes.js`/`fieldTypes.js`/`elementTypes.js`/plugin.
- Tests in `web-frontend/test/` (and premium/enterprise mirrors), `*.spec.js`.

### Format Patterns

- API responses: existing Baserow shape — direct serialized object (no custom `{data,error}` wrapper); errors via existing DRF exception → `{error: "ERROR_CODE", detail: ...}` convention used in repo.
- Dates: ISO 8601 strings in JSON.
- Booleans: JSON `true`/`false`.
- Null: explicit `null`, not omitted, where the field exists.

### Communication Patterns

**Registry registration (the central pattern — every new type):**
- Backend: subclass the base type (`ViewType`, `FieldType`, `WidgetType`, `ElementType`, service-type), register in the app's `ready()` via the singleton registry.
- Frontend: mirror with `$registry.register(...)` in the module plugin.
- WebSocket broadcast + Redis model-cache invalidation come free **only if** the handler patterns are followed — new mutations go through Handler classes, not direct ORM in views.

**Events / realtime:**
- Reuse existing WebSocket signal/broadcast layer; event names follow existing Baserow conventions. New mutating features MUST broadcast (no polling — SM-C1).
- **Authorize at subscribe time**, then per-recipient payload filter.

**State (Vuex 4):**
- Reuse grid store patterns: sparse arrays, lazy row loading, optimistic update + rollback, virtual scrolling. Immutable-style commits via mutations; concurrent edit = last-write-wins per field + snap-to-authoritative.

### Process Patterns

**Permission enforcement (MANDATORY — security-critical):**
- ALL authorization routes through the existing `PERMISSION_MANAGERS` chain — NEVER a parallel/ad-hoc check.
- Every new data surface wires into the single central field-permission enforcement layer (D7). New endpoints/data-sources/formulas/exports are NOT considered done until they re-verify against it.
- Deny-by-default for share principals; 403 (not 404 leak, not silent empty unless spec'd) on unauthorized.

**Clean-room provenance (MANDATORY for Bucket A):**
- Every Bucket A PR carries a provenance record (allowed sources consulted + implementer attestation) — no provenance, no merge.
- Premium/enterprise internal symbol names MUST NOT appear in specs/tickets/code as the thing to replicate. Describe behavior, not their code.

**Error handling / loading:**
- Reuse existing frontend error + loading-state patterns (per-component loading flags, global notification for errors); optimistic ops roll back + surface error on failure.

**Testing (per-feature matrix, MANDATORY):**
- Each feature ships: model → handler → serializer/API → frontend registry → component tests. Backend pytest (`just b test backend/tests/...`), frontend Vitest (`just f yarn test:core <path>`). i18n strings added to `en.json` + locales.

### Enforcement Guidelines

**All AI agents MUST:**
- Match the nearest existing core file's conventions; never introduce a new style.
- Route every new type through the appropriate registry; never bypass Handlers for mutations.
- Route every authorization through `PERMISSION_MANAGERS`; wire every data surface into the D7 enforcement layer.
- Place Bucket A reimplementations in `backend/src`/`web-frontend` core, never copy from `premium/`/`enterprise/`, and attach a provenance record.
- Ship the full test matrix + translations per feature.

**Anti-patterns (forbidden):**
- camelCase JSON API payloads; co-located backend tests; direct ORM mutation in API views (skips broadcast/cache-invalidation); parallel permission checks; per-surface ad-hoc field hiding instead of the central layer; copying/adapting premium/enterprise source; new charting/Gantt/map lib loaded eagerly on the landing route.

## Project Structure & Boundaries

### Component-to-Location Map (new/extended code in the existing monorepo)

This is a brownfield extension — no new project root. The tree below shows ONLY where this release's code lands. `[A]` = Bucket A clean-room (core dir, never copied from premium/enterprise); `[B]` = Bucket B greenfield; `[X]` = extend existing.

```
backend/src/baserow/
├── core/
│   ├── models.py                         [X] FR-29 extend: role assignment (above ADMIN/MEMBER)
│   ├── permission_manager.py             [X] FR-29/30/31 register new PermissionManager into PERMISSION_MANAGERS
│   ├── rbac/                             [A] FR-29 NEW clean-room role layer (Viewer/Commenter/Editor/Admin + interface-only)
│   │   ├── models.py, handler.py, roles.py, operations.py
│   │   └── migrations/                       FR-29 ADMIN→Admin, MEMBER→Editor (reversible, test-verified)
│   ├── field_permissions/               [A] FR-30 central enforcement layer (queryset/serializer redactor + predicate guard + cache invalidation)
│   └── notifications/                    [X] FR-27 comment @mention notifications (existing infra)
├── contrib/database/
│   ├── views/
│   │   ├── view_types.py                 [A/B] FR-1/4/6/8/12 register Kanban[A],Calendar[A],Timeline[A],Gantt[B],Map[B]
│   │   ├── models.py                     [X] FR-28/32 add owner FK + locked flag; FR-1.. view configs
│   │   ├── handler.py                    [X] FR-28 personal-view list-filter + fetch-by-id 403 (IDOR guard); FR-32 lock auth
│   │   ├── gantt/                        [B] FR-8-11 TaskDependency model, CPM engine (fwd/back pass), cycle detection, cascade
│   │   └── map/                          [B] FR-12-13 MapViewType, lat/lng configs
│   ├── fields/
│   │   ├── field_types.py                [B] FR-18-21B Currency,Percent,Barcode,Autonumber,RunningCount
│   │   └── models.py                     [B] field metadata (currency_symbol, precision, barcode_type, sequence)
│   ├── row_comments/                     [A] FR-26 NEW clean-room comment model+API+@mention (row-access-scoped broadcast)
│   └── export/                           [X] FR-33B exports wire into field_permissions layer
├── contrib/dashboard/
│   ├── widgets/                          [A/B] FR-15 chart widget types (bar/pie[A], line/scatter[B])
│   └── data_sources/                     [B] FR-14 grouped-aggregate Data Source (service-type)
├── contrib/builder/
│   └── elements/                         [B] FR-22-25 chart/metric elements, KCT view-embeds (wrap Batch-1 renderers), record-review
├── core/services/ (service_type_registry) [B] FR-14 grouped-aggregate service consumed by dashboard + builder
└── api/ (per app)                         [X] thin DRF views over handlers; share principal + Argon2id KDF (FR-17/33)

geocoding/  (new service module, core)    [B] FR-4/13 provider abstraction: Google(cloud)/Nominatim(self-host) + Celery throttled queue

web-frontend/modules/
├── core/                                 [X] FR-29 role UI; $registry plumbing; lazy-load wiring
├── database/
│   ├── viewTypes.js                      [A/B] register Kanban/Calendar/Timeline/Gantt/Map view types
│   ├── components/view/{kanban,calendar,timeline,gantt,map}/  [A/B] Vue 3 renderers (ECharts/MapLibre/FrappeGantt lazy)
│   ├── fieldTypes.js                     [B] Currency/Percent/Barcode/Autonumber/RunningCount
│   └── components/row/RowComments*.vue   [A] FR-26 comment thread UI
├── dashboard/                            [A/B] chart widget components (vue-echarts)
└── builder/                              [B] chart/metric/embed/record-review element components

enterprise/  premium/                     REFERENCE SHAPE ONLY (public MIT symbols) — NO copy of behavior (§8)
```

### Architectural Boundaries

**API boundaries:** all new endpoints are thin DRF views under each app's `api/` over Handler classes; REST + WebSocket + CLI share the handler. Public/share endpoints resolve under a deny-by-default share principal.

**Permission boundary (the load-bearing one):** every data surface (REST, WebSocket subscribe + payload, dashboard/builder Data Source dispatch, formulas/lookups/rollups, chart aggregation, filter/sort predicates, search, exports) passes through `core/field_permissions/` + the `PERMISSION_MANAGERS` chain. No surface bypasses it. Interface-only (FR-31) denies all DB/Table/View + data-source/formula/WS access beyond the granted Page.

**Component boundaries:** new ViewTypes/FieldTypes/WidgetTypes/ElementTypes register via singleton registries (backend `ready()`) mirrored by frontend `$registry.register`. App Builder view-embeds wrap Batch-1 view renderers — they do not reimplement them.

**Data boundaries:** new models (TaskDependency, role assignment, comments, field-permission rules) add migrations to their owning app; field types add metadata to the field-metadata model only (dynamic-model pattern — no per-user-table migration). Geocoded lat/lng cached in DB, treated as derived data under source-field permission.

### Requirements → Structure Mapping

| Batch / FRs | Primary location |
|---|---|
| FR-1–13 Views | `contrib/database/views/` (+ `gantt/`, `map/`) + `web-frontend/modules/database` |
| FR-14–17 Dashboard | `contrib/dashboard/{widgets,data_sources}` + `web-frontend/modules/dashboard` |
| FR-18–21B Fields | `contrib/database/fields/` + `web-frontend/modules/database` fieldTypes |
| FR-22–25 App Builder | `contrib/builder/elements/` + `web-frontend/modules/builder` |
| FR-26–27 Comments | `contrib/database/row_comments/` + `core/notifications` |
| FR-28/32 Personal/Locked views | `contrib/database/views/{models,handler}.py` |
| FR-29 RBAC | `core/rbac/` + `core/models.py` + `core/permission_manager.py` |
| FR-30/33B Field perms + export | `core/field_permissions/` + `contrib/database/export/` |
| FR-31 Interface-only | `core/rbac/` + builder data-source dispatch guards |
| FR-17/33 Share principal + password | per-app `api/` + `core/` share-token + Argon2id |
| FR-4/13 Geocoding | new `geocoding/` service module + Celery |

### Integration Points

- **Internal:** Handler classes are the integration spine — API/WS/CLI all call them; broadcast + cache invalidation fire from handlers.
- **External:** geocoding providers (Google/Nominatim) via provider abstraction + env vars; map tiles via MapLibre.
- **Data flow:** mutation → Handler → model + permission check → Postgres → WebSocket broadcast (subscribe-authorized, per-recipient filtered) + Redis model-cache invalidation → frontend store (optimistic, snap-to-authoritative).

### Development Workflow Integration

- Dev: `just dev up` (local) / `just dc-dev up -d` (Docker); hot reload via Nuxt.
- Build: `just`/`uv`/`yarn`; new heavy libs (ECharts/MapLibre/FrappeGantt) lazy-loaded per route (SM-C3 budget).
- Tests: `just b test backend/tests/baserow/...` (mirror path), `just f yarn test:core <path>`; e2e in `e2e-tests/`.
- Config: new env vars via `add-django-config-env-var` skill (base.py + compose + env-remap + docs).

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:** All version choices interoperate — echarts 6.0 / vue-echarts 8.0.1 (peer vue ^3.3, repo on 3.5.25 ✓), Nuxt 3.21, Django 5.2.14, DRF 3.16.1, Python 3.14. New libs are license-compatible with the MIT free tier (ECharts Apache-2.0, Frappe Gantt MIT, MapLibre BSD-3, qrcode.vue MIT); DHTMLX (GPLv2) and Google-Maps-only correctly rejected. No contradictory decisions.

**Pattern Consistency:** Implementation patterns reinforce the decisions — registry registration (D-all), `PERMISSION_MANAGERS` routing (D6/D7), handler-spine for broadcast+cache (D11), lazy-load for bundle budget (D1/D2/D3). Naming/structure/format rules inherit existing Baserow conventions, removing agent ambiguity.

**Structure Alignment:** Every decision has a concrete home in the existing tree; the central `core/field_permissions/` enforcement boundary (D7) makes "every-surface security" structurally enforceable rather than aspirational. Bucket A code is confined to core dirs with reference-only access to premium/enterprise.

### Requirements Coverage Validation ✅

**Functional Requirements Coverage:** All 34 FRs (FR-1–FR-33B) mapped to specific files/dirs in the §"Requirements → Structure Mapping" table. Shared foundations (charting D1, grouped-aggregate Data Source D9, view renderers) built once and consumed by multiple FRs as the PRD requires.

**Non-Functional Requirements Coverage:**
- Real-time (SM-C1): handler-driven WebSocket broadcast, subscribe-time auth, no polling.
- Perf (SM-C3): virtual-scroll reuse, lazy-loaded heavy libs, field indexing + `get_order_by_field_string`, map clustering. Concrete budget numbers remain §10 placeholders to ratify against measured baselines.
- Security: single central enforcement layer + `PERMISSION_MANAGERS`, inference-oracle guard, deny-by-default share principal, Argon2id, cache invalidation — release-gated by threat model + role-combination matrix (§13 step 7).
- a11y / i18n / test matrix: covered in patterns.

### Implementation Readiness Validation ✅

**Decision Completeness:** All critical decisions documented with verified versions and rationale; defaults applied for open PRD questions and flagged.

**Structure Completeness:** Directory map is file-specific (not placeholder); component boundaries + integration points + data flow defined.

**Pattern Completeness:** Naming, structure, format, communication, and process (permission, clean-room provenance, error/loading, testing) patterns all specified with anti-patterns.

### Gap Analysis Results

- **CRITICAL (external / non-architectural):** Open Q7 — clean-room process owner + legal sign-off unassigned. Blocks all Bucket A implementation (§13 step 0). The architecture is ready; Bucket A *execution* is legally gated and cannot start until resolved. This is a PRD/process blocker, not an architecture deficiency.
- **Minor (defaulted PRD open questions):** FR-24 embed interactivity (Q6 → read-only v1); Running Count scope (Q11 → whole-table); parity target/owner (Q1/Q9 → 80%); percent entry convention (Q8 → whole-number). All defaulted with rationale; confirmable without architectural change.
- **Minor (ratify during build):** concrete perf budget numbers (§10); chart live-push debounce interval (D11).

### Validation Issues Addressed

No architectural contradictions to resolve. The single Critical gap (Q7) is organizational/legal and is explicitly carried forward to §13 step 0 as a hard prerequisite for Bucket A. Minor gaps are resolved by documented defaults.

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed (budgets parameterized as placeholders to ratify)

**Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY WITH MINOR GAPS — the architecture document itself is complete and coherent (all 16 checklist items satisfied). One CRITICAL *external* blocker (clean-room owner/legal sign-off, Open Q7) gates Bucket A *execution* but not the architecture; Bucket B work (Gantt, Map, fields, line/scatter charts, password share, chart/metric elements) can begin immediately.

**Confidence Level:** high — brownfield foundation is proven, decisions are verified, and the load-bearing risks (permissions, clean-room, scheduling) have concrete architectural answers.

**Key Strengths:**
- Brownfield registry model means low structural risk — new types slot in without core rewrites.
- Security enforcement is centralized (D7) and structurally hard to bypass.
- Shared foundations (charting, Data Source, view renderers) prevent duplication.
- Clean-room provenance is wired into the merge process, not left to discipline.

**Areas for Future Enhancement:**
- Ratify concrete perf budgets against measured baselines.
- Custom-role builder, interactive embeds, email digests, automations/Button field — deferred waves.

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions (D1–D14 + fixed brownfield foundation) exactly.
- Use the inherited Baserow patterns; never introduce new styles.
- Route all authorization through `PERMISSION_MANAGERS` + the `core/field_permissions/` layer.
- No Bucket A code until Open Q7 (clean-room gate) is resolved; attach a provenance record to every Bucket A PR.

**First Implementation Priority:**
§13 step 0 — stand up the clean-room process gate (legal sign-off, implementer isolation, provenance-log merge gate). In parallel, begin Bucket B foundations: license-clean field types (D10 + Currency/Percent/Barcode/Running-Count), charting foundation (D1), geocoding infra (D4/D13), and the RBAC foundation spec (D6, Bucket A — code blocked until Q7).
