# PRD Addendum — Clavis ERP Airtable Parity Release

Depth that belongs downstream (architecture, eng-process, UX), preserved here so the PRD stays capability-focused. Sourced from `technical-airtable-vs-baserow-oss-feature-gap-research-2026-06-05.md`. **Validate library licenses + bundle impact before committing (SM-C3).**

## Clean-room process (for Bucket A reimplements) — BINDING
> ⚠️ This team already has repo read-access to `premium/` and `enterprise/`. A naive "haven't read the source" rule is unenforceable here. The process below must be set up and legally signed off BEFORE any Bucket A work (§13 step 0). Owner unassigned — Open Q7.
- **Implementer isolation:** Bucket A free-tier code is written by either (a) a walled-off group with enforced no-access to `premium/`/`enterprise/` dirs, or (b) external/contracted implementers. Anyone who has read the protected source cannot write the corresponding free implementation.
- **Allowed sources only:** behavior specs derive from an explicit allowed-source list — public Baserow docs, the public upstream Baserow SaaS UI, public issues/changelogs. NOT the team's `premium/`/`enterprise/` source and NOT paid-instance internals. "Influenced by" protected source counts as contamination.
- **Provenance log = merge gate:** every Bucket A PR carries a provenance record (sources consulted, implementer attestation); no provenance → no merge.
- **Symbol hygiene:** internal premium/enterprise symbol names (class/method/module identifiers from protected code) MUST NOT appear in specs, tickets, or the free implementation as the thing to replicate — describe *behavior*, not their code. (Free-core MIT symbols — `ViewType`, `FieldType`, `NumberFieldType`, `PERMISSION_MANAGERS`, `ElementType`, etc. — are fine to reference.)
- Legal sign-off on the whole process before Bucket A work begins (Open Q7).
- Links project memory: `baserow-open-core-license-constraint`.

## Architecture patterns (universal)
- Registry-based: backend singleton registries populated in Django `ready()` (`field_type_registry`, `view_type_registry`, `element_type_registry`, `service_type_registry`, `application_type_registry`). API views are thin shells over Handler classes; REST + WebSocket + CLI share the handler.
- Frontend mirrors backend: `$registry.register(...)`. New types slot in without core rewrites. WebSocket broadcast + Redis model-cache invalidation come free if the patterns are followed.
- Dynamic model generation: new field type = `get_model_field()` + `get_serializer_field()` + migration on field-metadata model only (not every user table).
- **Stack:** Vue 3 / Nuxt 3 (repo authoritative; research "Vue 2" note is stale). Vuex grid patterns = sparse arrays, lazy row loading, optimistic updates + rollback, virtual scrolling.

## Candidate libraries (per feature — evaluate, not mandated)
| Area | Candidate | License | Notes |
|---|---|---|---|
| Gantt | Frappe Gantt | MIT | ~50kB, framework-agnostic, critical path + milestones. Alt: DHTMLX (GPLv2, heavier). |
| Map rendering | Google Maps JS (cloud) / MapLibre GL JS + OSM tiles (self-host) | proprietary / BSD | PRD §4.5: Google default on cloud, configurable for self-host. |
| Geocoding | Google Geocoding (cloud) / Nominatim-OSM (self-host) | proprietary / ODbL | **Google ToS couples geocoding + tiles and forbids long-term result caching → the cache-and-self-host path uses Nominatim (1 req/sec, cache, self-host).** Provider configurable via env var. Matches PRD §4.5/§8. |
| Charts | Apache ECharts via vue-echarts | Apache 2.0 | 20+ types, large datasets. Alt: ApexCharts (MIT). |
| Barcode | vue-barcode / qrcode.vue | MIT | Client-side render. |

## Per-feature implementation notes
- **Kanban/Calendar/Timeline (Bucket A):** `ViewType` subclass; rebuild Vue rendering clean-room. Each ~1–2 wks, reimplementing the View first.
- **Gantt (B):** `ViewType` + new `TaskDependency` model (edge predecessor→successor) + endpoints + migration. Cycle detection on dependency create. ~2–3 wks, medium risk.
- **Map (B):** new `MapViewType` (free-core `ViewType`) storing lat/lng Field configs; geocode server-side, cache where ToS allows. ~1–2 wks.
- **Dashboard (CORRECTED):** the dashboard module + `SummaryWidgetType` (metric) are **already in free core** (`backend/src/baserow/contrib/dashboard`) — do NOT rebuild them. Gap = chart Widget types (bar/pie are Bucket A clean-room; line/scatter are Bucket B greenfield) + a grouped-aggregate Data Source (the free chart-data path is missing) + embedding charts in App Builder. Describe chart behavior from public sources; do not lift premium chart-widget code.
- **Currency/Percent (B):** extend `NumberFieldType`; formatting metadata (`currency_symbol`, `number_type`). 1–2 days each, low risk — top quick wins.
- **Barcode (B):** wrap `TextField`, `barcode_type` config. 2–3 days. Camera scanning deferred (native app).
- **Chart/Metric Elements (B):** `ChartElementType` + `MetricElementType`; ECharts; data via service registry. ~1 wk each, low risk.
- **View embeds (FR-24):** thin `ElementType` wrappers over Batch-1 View renderers (must exist first).
- **Personal Views (A):** `owner` FK on free-core `View` + migration; filter by current user in listing AND deny direct fetch-by-id of others' personal Views (no IDOR); check in `ViewHandler`. 3–4 days.
- **RBAC foundation + Commenter (A, CORRECTED — was wildly under-estimated):** free tier has ONLY `ADMIN`/`MEMBER` (`core/models.py`); there is no Viewer/Editor/Commenter hierarchy to slot into. This is a clean-room reimplement of an RBAC role layer (fixed tiers Viewer/Commenter/Editor/Admin), routed through `PERMISSION_MANAGERS`, with a migration mapping existing ADMIN/MEMBER. Foundation for field perms + interface-only. **Weeks, not ~1 wk — largest single item.** Behavior-only spec; do not lift enterprise role code.
- **Row comments (A):** reimplement comment model + API + @mention notification from public behavior; broadcasts and @mentions must respect Row access (no leak to users without Row access). ~1–2 wks.
- **Interface-only collaborator (A-dependent, NOT pure B):** builds on the RBAC foundation. Enforce **data-scoped**, not just nav-hiding — deny DB/Table/View endpoints AND App Builder data-source dispatch / formula eval / websocket channels beyond the granted Page. 1–2 wks on top of RBAC, **security review required**, exhaustive role-combination tests.
- **Field permissions (A):** clean-room — restrict edit + visibility per Role/member, enforced at every data surface (REST, websocket, charts/aggregation, formulas/lookups/rollups, exports, embeds). Free-core `FieldType` already exposes capability hooks to build on; describe enterprise *behavior* from public sources, and do not copy enterprise modules.

## Cross-cutting technical concerns
- Realtime WebSocket + push webhooks are differentiators — preserve, don't regress (SM-C1).
- New filterable fields: implement `get_order_by_field_string()` correctly; use 2025 field indexing.
- Hook permission features into `PERMISSION_MANAGERS`, never bypass.
- Test matrix: `just b test backend/tests/...`, `just b test-builder`, `just b test-automation`, `just b test --reuse-db`, `just f yarn test:core <path>`. Per-feature: model→handler→serializer/API→frontend registry→Vue components→backend+frontend tests→translations.

## Deferred-but-adjacent (not this release)
- Button field → needs `BUTTON_CLICKED` automation trigger (automation wave).
- Run Script → JS sandboxing: Deno subprocess recommended (strict `--allow-*` + cgroup limits); QuickJS-WASM alt; **vm2/Node subprocess = do NOT use** (escape vulns); CodeMirror 6 editor. Security audit mandatory.
- PDF/Page Designer → WeasyPrint + django-weasyprint (CSS-only, no JS) / Playwright fallback.
- AI field/formula generator (Bucket A), sync connectors (mixed A/B), SSO + audit log + **custom-role builder** (Enterprise A). NOTE: fixed-tier RBAC IS in scope this release (FR-29); only the custom-role builder is deferred.

## Free-tier advantages to preserve (design constraints)
Unlimited records (vs Airtable 500k cap), self-hosting, push webhooks, WebSocket realtime, MCP server, custom-domain publishing, two-way PostgreSQL sync.
