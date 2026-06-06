---
title: Clavis ERP — Airtable Parity Release (Views, Dashboard, Fields, App Builder, Collaboration)
status: final
created: 2026-06-06
updated: 2026-06-06
---

# PRD: Clavis ERP — Airtable Parity Release
*Working title — confirm.*

## 0. Document Purpose

This PRD is for the Clavis ERP product and engineering leads, the architects who will sequence the build, and the downstream BMad workflows (architecture, epics/stories, UX). It defines a single combined release ("the next version") that closes the largest Airtable feature gaps in the free/OSS tier across five batches: Views, Dashboard, Field Types, App Builder, and Collaboration. It is grounded in `_bmad-output/planning-artifacts/research/technical-airtable-vs-baserow-oss-feature-gap-research-2026-06-05.md` — that research is the authority for gap analysis and is not duplicated here; this PRD references it. Vocabulary is Glossary-anchored (§3); features are grouped with globally-numbered FRs nested (§4); assumptions are tagged inline `[ASSUMPTION]` and indexed (§9). Technology choices (charting library, map/geocoding stack, Gantt library, etc.) are deliberately kept out of the FRs — they live in `addendum.md` as input to the architecture phase.

## 1. Vision

Clavis ERP is built on the Baserow open-core codebase, where the free/MIT tier reaches only ~50–55% of Airtable's capability and the most-wanted features (Kanban, Calendar, Timeline, Dashboards, comments, personal views, field permissions) sit behind premium/enterprise license keys. This release closes that gap in the **free tier** by clean-room reimplementing the paywalled features and building the genuinely missing ones (Gantt with dependencies, Map view, currency/percent/barcode fields, in-page charts, interface-only collaborators).

The outcome is a free, self-hostable Airtable alternative that a team can actually run their business on: visualize the same data as a board, a calendar, a project timeline with task dependencies, or a map; build dashboards and client-facing apps with live charts; capture richer data types; and collaborate with comments, personal views, and scoped permissions — without hitting a paywall or Airtable's record caps.

It matters because the feature gap is the single biggest reason teams evaluating Clavis/Baserow against Airtable bounce. Closing it — while preserving the differentiators Airtable can't match (real-time WebSocket sync, unlimited records, self-hosting, two-way Postgres sync) — turns "almost Airtable, but missing X" into a credible switch.

## 2. Target User

### 2.1 Jobs To Be Done

- **Visualize the same dataset multiple ways** — flip a table between grid, board, calendar, timeline, Gantt, and map without exporting or duplicating data.
- **Plan and track projects** — see tasks on a timeline, define dependencies between them, spot the critical path and milestones.
- **Build internal tools and client apps** — assemble pages with live charts, metrics, and embedded views, then share them with people who should never see the underlying database.
- **Report on data** — build a dashboard of charts and summary metrics for a team or stakeholder.
- **Capture business data faithfully** — store currency, percentages, and barcodes as first-class typed values, not free-text hacks.
- **Collaborate safely** — discuss records in comment threads, keep a personal view without disturbing teammates, and grant scoped access (comment-only, field-restricted, app-only) instead of all-or-nothing.
- **Stay off the paywall and the record cap** — get all of the above in the free/self-hosted tier with unlimited records.

### 2.2 Non-Users (v1)

- **Mobile-native users needing offline/camera capture** — barcode *display* ships; camera *scanning* needs a native app that does not exist (deferred).
- **Teams needing AI authoring** (AI field, formula generator, AI-generated app pages) — out of scope this release.
- **Teams needing scripting/automation depth** (Run Script, new automation triggers/actions) — out of scope; this gates the deferred Button field.
- **Enterprises requiring SSO/SAML, granular custom RBAC, or a formal audit log as blockers** — partial collaboration scope only; full enterprise IAM is a later wave.

### 2.3 Key User Journeys

- **UJ-1. Maya turns one table into a board, then a dashboard.**
  - **Persona + context:** Maya, ops manager at a 20-person agency, runs the client pipeline in a single Clavis table. She's authenticated, on web.
  - **Entry state:** Looking at the grid view of "Clients."
  - **Path:** Adds a Kanban view grouped by the "Stage" single-select → drags two cards from *Proposal* to *Won* → opens a new Dashboard → drops a bar chart of deals-by-stage and a "Total won this month" metric.
  - **Climax:** The board reflects her drag instantly for every teammate (real-time), and the dashboard metric updates as cards move.
  - **Resolution:** She bookmarks the dashboard and shares its public link with the partner. Realizes UJ via FR-1, FR-2, FR-15, FR-16, FR-17.

- **UJ-2. Diego schedules a launch with dependencies.**
  - **Persona + context:** Diego, project lead, planning a product launch across a "Tasks" table with start/end dates.
  - **Entry state:** Authenticated, viewing "Tasks" grid.
  - **Path:** Creates a Gantt view → drags task bars to reschedule → draws a finish-to-start dependency from "Design" to "Build" → marks "Launch" as a milestone.
  - **Climax:** Moving "Design" later automatically shifts "Build," and the critical path highlights; the milestone diamond shows on the launch date.
  - **Resolution:** He spots the launch will slip and rebalances. Realizes UJ via FR-8, FR-9, FR-10, FR-11.

- **UJ-3. Priya, a client, comments without ever seeing the database.**
  - **Persona + context:** Priya, an external client, invited only to review deliverables.
  - **Entry state:** Receives an app link; logs in as an interface-only collaborator.
  - **Path:** Opens the shared App Builder page → sees a filtered gallery of her deliverables and a status chart → opens a record → leaves a comment "@Maya please revise the hero image."
  - **Climax:** Maya is @-mentioned and notified; Priya never sees a table, other clients' rows, or any database navigation.
  - **Resolution:** Maya replies in-thread. Realizes UJ via FR-31, FR-22, FR-26, FR-27.

- **UJ-4. Sam locks down a shared base.**
  - **Persona + context:** Sam, workspace admin, sharing a base with contractors.
  - **Entry state:** Authenticated, base open.
  - **Path:** Makes the "Master" grid a locked view → grants a contractor the Commenter role → sets the "Salary" field to no-edit for non-admins → creates his own personal view to triage without disturbing the team's layout.
  - **Climax:** Contractors can comment but not restructure; the salary field is read-only for them; Sam's personal view is invisible to others.
  - **Resolution:** Sam shares the base confidently. Realizes UJ via FR-32, FR-29, FR-30, FR-28.

- **UJ-5. Rosa maps her field accounts.**
  - **Persona + context:** Rosa, field sales, with an "Accounts" table holding addresses.
  - **Path:** Adds a Map view → Clavis geocodes the address field → pins cluster by region → she clicks a pin to open the account record.
  - **Climax:** She sees account density by territory on one screen.
  - **Resolution:** Plans her route. Realizes UJ via FR-12, FR-13.

## 3. Glossary

- **Clavis** — the product (Baserow-derived open-core ERP/database platform). Free/OSS tier is the target of this release.
- **Workspace** — top-level container owning Databases, Applications, and members.
- **Database** — a Clavis application type containing Tables.
- **Table** — a collection of Rows with a defined set of Fields.
- **Row** — a single record in a Table.
- **Field** — a typed column on a Table (e.g., Number, Single-select, Date). Governed by a **Field Type**.
- **Field Type** — the class defining a Field's storage, validation, serialization, and rendering (registry-backed).
- **Autonumber** — a Field Type assigning each Row a stable, auto-incrementing integer in creation order (not user-editable).
- **Running Count** — a Field Type computing the number of Rows matching a configured condition (distinct from the existing relational Count).
- **View** — a saved, filtered/sorted/grouped presentation of a Table's Rows. Governed by a **View Type**. Grid, Gallery, Form exist today; this release adds Kanban, Calendar, Timeline, Gantt, Map.
- **View Type** — the class defining how a View renders and behaves (registry-backed).
- **Personal View** — a View owned by and visible only to one Workspace member.
- **Locked View** — a View whose configuration (filters/sorts/fields/layout) cannot be edited by others.
- **Task Dependency** — a directed relationship between two Rows (tasks) in a Gantt View; default semantics finish-to-start.
- **Milestone** — a Gantt task marked as a zero-duration significant date.
- **Dashboard** — a standalone Clavis application type presenting Widgets (charts, metrics) over Table data.
- **Widget** — a chart or metric block placed on a Dashboard.
- **Application Builder (App Builder)** — the Clavis application type for building multi-page apps from **Elements**.
- **Element** — a building block placed on an App Builder Page (e.g., Table, Chart, Heading), registry-backed.
- **Page** — a routable screen in an App Builder application.
- **Data Source** — a query (service-registry-backed) that feeds Rows to a Widget or Element.
- **Comment** — a threaded message attached to a Row, supporting **@mentions**.
- **@mention** — a reference to a Workspace member inside a Comment that notifies them.
- **Role** — a member's permission tier within a Workspace/Database. The free tier today has only `ADMIN`/`MEMBER`; this release introduces a clean-room **RBAC** layer with fixed tiers (Viewer, Commenter, Editor, Admin) plus **Interface-only collaborator**.
- **RBAC** — the role-based access-control layer (FR-29) that the free tier lacks; prerequisite for Commenter, interface-only, and Field Permissions.
- **Commenter** — a Role that can view and comment on Rows but not edit data or structure.
- **Interface-only collaborator** — a Role that can access only App Builder Pages, never the underlying Databases (data-scoped, not just navigation-hidden).
- **Share principal** — the least-privilege identity under which a public/password share link resolves Data; never the sharer's full permissions.
- **Critical Path** — the zero-slack chain through the FS dependency graph, computed by CPM forward/backward passes, that determines the earliest possible schedule completion.
- **Field Permission** — a per-Field rule restricting who may edit (or see) that Field's values.
- **Parity %** — share of Airtable's tracked feature set available in the Clavis free tier (research baseline ~50–55%).
- **Bucket A** — a feature whose code exists in Clavis premium/enterprise dirs under a license that forbids copying; must be **clean-room reimplemented** for the free tier.
- **Bucket B** — a feature absent from every tier; greenfield.
- **Clean-room reimplementation** — building a fresh free-tier implementation from public behavior/UI only, by engineers who have not read the licensed premium/enterprise source.

## 4. Features

> Cross-batch dependency note: several features share foundations (charting, the view layer, the permission/role system). The recommended build order is in §13 Build Sequencing — it does not change scope, only sequence.

### Batch 1 — Views

#### 4.1 Kanban View
**Description:** A board View that groups Rows into columns by a Single-select (or Link/collaborator) Field, with drag-to-move cards that update the underlying Field. Clean-room reimplementation of the Bucket A premium Kanban (do not reuse premium components). Card faces show a configurable subset of Fields and the row's cover image if set. Realizes UJ-1. `[ASSUMPTION: grouping is by a single chosen Single-select field in v1; grouping by other field types is a follow-on.]`

**Functional Requirements:**

##### FR-1: Create and configure a Kanban View
An editor can add a Kanban View to any Table and choose the Single-select Field that defines columns. Realizes UJ-1.
**Consequences (testable):**
- Columns render one per option of the chosen Field, plus an "Uncategorized" column for empty values.
- Existing View filters, sorts, and field visibility apply to the board.
- View is persisted and reopens with the same configuration.

##### FR-2: Drag a card between columns
An editor can drag a card to another column; the grouping Field value updates on the Row.
**Consequences (testable):**
- Dropping a card sets the Row's grouping Field to the target column's option (or null for Uncategorized).
- The change broadcasts in real time to other connected clients (WebSocket) without a refresh.
- A failed update rolls the card back to its origin column and surfaces an error.

##### FR-3: Configure card appearance
An editor can choose which Fields appear on the card face and whether a cover image shows.
**Consequences (testable):**
- Hidden Fields do not render on cards; the setting persists per View.
- `[ASSUMPTION]` Row coloring/decoration is itself a Bucket A premium feature NOT in this release's scope — cards do not depend on it. If a clean-room row-coloring reimplement is later added, cards should honor it then; v1 cards render without it.

#### 4.2 Calendar View
**Description:** A View that places Rows on a monthly/weekly calendar by a Date Field, with drag-to-reschedule. Clean-room reimplementation of Bucket A premium Calendar. Serves scheduling jobs adjacent to UJ-1.

**Functional Requirements:**

##### FR-4: Create and configure a Calendar View
An editor can add a Calendar View and select the Date Field that positions Rows.
**Consequences (testable):**
- Rows with a value in the chosen Date Field appear on their date; rows without are listed in an "unscheduled" tray.
- Month and week display modes are available.
- `[ASSUMPTION]` If both a start and end Date Field are configured, an entry spans multiple days as a continuous bar; with a single Date Field it renders as a single-day entry.
- Filters/sorts/field-visibility apply.

##### FR-5: Reschedule by drag
An editor can drag a calendar entry to another date to update the Date Field.
**Consequences (testable):**
- Dropping updates the Row's Date Field to the target date and broadcasts in real time.
- Failed updates roll back and surface an error.

#### 4.3 Timeline View
**Description:** A horizontal time-axis View showing Rows as bars spanning a start and end Date Field, zoomable by day/week/month. Clean-room reimplementation of Bucket A premium Timeline. Timeline shows scheduling only; dependencies/critical path/milestones are the Gantt View's job (FR-9–FR-11).

**Functional Requirements:**

##### FR-6: Create and configure a Timeline View
An editor can add a Timeline View and map start and end Date Fields.
**Consequences (testable):**
- Each Row renders as a bar from start to end on the time axis.
- Zoom levels day/week/month are selectable and persist.
- Rows missing start or end are listed separately, not rendered as malformed bars.

##### FR-7: Reschedule and resize bars
An editor can drag a bar to move it or drag its edge to change duration.
**Consequences (testable):**
- Moving updates both Date Fields preserving duration; resizing updates the dragged endpoint.
- Changes broadcast in real time; failures roll back.

#### 4.4 Gantt View with Dependencies
**Description:** A project-planning View building on the timeline with first-class **Task Dependencies**, **Critical Path** highlighting, and **Milestones**. Greenfield (Bucket B) — Task Dependency is a new model relating two Rows. Realizes UJ-2. `[ASSUMPTION: dependency semantics default to finish-to-start; other types (SS/FF/SF) are configurable but FS is the v1 default and the only one guaranteed in the auto-reschedule rule below.]`

**Functional Requirements:**

##### FR-8: Render a Gantt View
An editor can add a Gantt View mapping start/end Date Fields, showing task bars on a time axis. Realizes UJ-2.
**Consequences (testable):**
- Bars render like Timeline (FR-6) with a dependency layer overlaid.
- Zoom and filter/sort behavior matches Timeline.

##### FR-9: Define Task Dependencies
An editor can draw a dependency between two task Rows. Realizes UJ-2.
**Consequences (testable):**
- A dependency is persisted as a directed edge (predecessor → successor) and survives reload.
- Dependencies render as connector lines between bars.
- Cycle prevention holds across **all** mutation paths — create, restore-from-trash, and import — not just interactive create; any operation that would introduce a cycle is rejected with a clear error.

##### FR-10: Reschedule on dependency (prompt-first)
When a predecessor task moves such that a finish-to-start dependency is violated, the system prompts the user before shifting dependent tasks. Realizes UJ-2.
**Consequences (testable):**
- Moving a predecessor's end past a successor's start triggers a confirmation prompt naming the successor(s) that would move and the count of cascaded dependents.
- On confirm, successors shift to maintain FS ordering (preserving their duration) and the shift cascades through the dependency chain.
- On decline, the predecessor move is kept but dependents are left in place (dependency shown as violated/flagged, not silently broken).
- The whole confirmed shift is undoable as a single step.

##### FR-11: Milestones and Critical Path
An editor can mark a task as a Milestone; the system computes and highlights the Critical Path via the Critical Path Method (CPM).
**Consequences (testable):**
- A Milestone renders as a zero-duration diamond marker on its date.
- **Algorithm:** the system runs a CPM forward pass (earliest start/finish from dependency-free roots) and backward pass (latest start/finish from terminal tasks) over the FS dependency graph; tasks with zero slack (earliest = latest) form the Critical Path and are visually distinguished.
- Critical Path recomputes when any dependency or date changes.
- **Contradiction rule:** when user-entered dates violate a dependency (a successor starts before its predecessor finishes), the task is flagged as a scheduling conflict and excluded from a valid Critical Path until resolved; CPM uses the dependency-implied schedule, not the contradictory manual date, and surfaces the discrepancy. `[ASSUMPTION: CPM operates on FS dependencies only in v1, matching FR-10's guarantee.]`
- **Out of Scope:** resource leveling, lag/lead times, and SS/FF/SF dependency types in the CPM computation (FS only).

#### 4.5 Map View
**Description:** A View that plots Rows as pins on a map using a location Field (address geocoded to lat/lng, or explicit lat/lng Fields). Greenfield (Bucket B). Realizes UJ-5. Geocoding/map provider is **Google Maps Platform by default on Clavis cloud, with a configurable provider (OSM/Nominatim) for self-hosted installs** — because Google's ToS forbids long-term caching of results and use without Google's map tiles, which conflicts with the self-host + cache model. `[ASSUMPTION: configurable-provider split confirmed; if Google is forced everywhere, self-hosters must supply their own API key + billing and accept the caching restriction — see §8.]`

**Functional Requirements:**

##### FR-12: Configure a Map View
An editor can add a Map View and choose the address Field (or lat/lng pair) to plot.
**Consequences (testable):**
- Rows with a resolvable location render as pins; unresolvable rows are listed in a "could not locate" tray.
- Filters/sorts apply to which Rows are plotted.

##### FR-13: Geocode and interact with pins
The system geocodes address values; a user can click a pin to open the Row. Realizes UJ-5.
**Consequences (testable):**
- Geocoded coordinates are cached and not re-requested on every load.
- Clicking a pin opens the corresponding Row detail.
- Pins cluster at low zoom and expand on zoom-in.
- Geocoding respects provider rate limits without blocking the UI (queued/throttled).

### Batch 2 — Dashboard

#### 4.6 Dashboard
**Description:** The Dashboard application type and the **summary metric Widget already ship in the free core** (`backend/src/baserow/contrib/dashboard`, `SummaryWidgetType`) — these are **out of scope** here except as a baseline that must not regress. The real gap is **chart Widgets**: bar and pie/doughnut exist only in premium (`premium/.../dashboard/widgets`: `ChartWidgetType`, `PieChartWidgetType`) and must be clean-room reimplemented (Bucket A); line and scatter are absent everywhere (Bucket B). Charts also depend on a **grouped-aggregate Data Source** that the premium chart path provides and the free path lacks — that must be built too. Charts share the charting foundation with App Builder chart Elements (§4.8) — built once, consumed by both. Realizes UJ-1.

**Functional Requirements:**

##### FR-14: Grouped-aggregate Data Source for charts
A user can configure a Data Source that groups Rows by a Field and aggregates a value per group, feeding a chart Widget.
**Consequences (testable):**
- Data Source returns (category, aggregated-value[, series]) tuples from a Table with a configurable group-by Field and aggregation (count/sum/avg/min/max).
- Honors field-hide and row permissions of the requesting principal (see §10) — does **not** aggregate over fields the principal cannot see.
- This is the prerequisite for FR-15; it is its own deliverable, not folded into the chart widget.

##### FR-15: Chart Widgets (bar, line, pie/doughnut, scatter)
A user can add bar, line, pie/doughnut, and scatter chart Widgets to the existing free Dashboard, bound to a grouped-aggregate Data Source (FR-14).
**Consequences (testable):**
- Bar and pie/doughnut are clean-room reimplemented (Bucket A) and render from the Data Source with configurable category/value/series.
- Line and scatter (Bucket B) render correctly.
- Charts update when underlying Data changes. `[ASSUMPTION: refresh on load + real-time row events for the bound table; confirm live-push interval/strategy in architecture.]`
- A new chart Widget interoperates with the existing free `summary` metric Widget on the same Dashboard.

##### FR-16: Metric Widget — baseline (already free)
The existing free summary metric Widget continues to work alongside new chart Widgets.
**Consequences (testable):**
- `[NON-GOAL — already implemented]` No new build; this FR exists only as a non-regression acceptance check: adding chart Widgets must not break existing metric Widgets.

##### FR-17: Dashboard public share with defined principal
A user can share a Dashboard via public link, and the link resolves data under an explicit, least-privilege share principal.
**Consequences (testable):**
- A public link renders the Dashboard read-only without authentication.
- The link resolves Data Sources under a defined **share principal** (an anonymous/least-privilege identity), not the sharer's full permissions — hidden-by-permission fields and restricted rows are NOT exposed through the public link (see §10, FR-30, FR-33 for password option).
- Revoking the link disables access immediately (server-side, no cached bypass).

**Feature-specific NFRs:**
- A Dashboard with up to [ASSUMPTION: 12] chart/metric Widgets over tables of 100k rows renders initial paint within the §10 budget; charts must lazy-load so an off-screen Widget does not block first paint.

### Batch 3 — Field Types

#### 4.7 Field Types: Currency, Percent, Barcode, Autonumber, Running Count
**Description:** Five new Field Types, all Bucket B (license-clean), added via the field-type registry. Currency and Percent extend numeric behavior with formatting; Barcode renders a scannable/visual code from a value; **Autonumber** assigns a stable auto-incrementing sequence per Row; **Running Count** computes how many Rows match a condition. (Both count-style fields requested — they serve different jobs.) The **Button field is explicitly deferred** (it requires a new automation trigger — see §5/§11).

**Functional Requirements:**

##### FR-18: Currency Field
An editor can create a Currency Field with a configurable currency symbol and precision.
**Consequences (testable):**
- Values store as numbers and render with the configured symbol and decimal places.
- Sorting/filtering behave numerically, not lexically.
- Currency symbol and precision persist as Field config.

##### FR-19: Percent Field
An editor can create a Percent Field with configurable precision.
**Consequences (testable):**
- Values render with a `%` suffix at the configured precision.
- Underlying storage and numeric sort/filter are correct (e.g., 0.5 vs 50% representation defined and consistent). `[ASSUMPTION: input/display convention (whole-number percent vs fraction) follows Airtable's whole-number entry; confirm.]`

##### FR-20: Barcode Field
An editor can create a Barcode Field rendering a value as a barcode/QR code of a chosen symbology.
**Consequences (testable):**
- The Field renders a scannable code (e.g., QR, Code128) client-side from the stored value.
- Symbology is configurable and persists.
- **Out of Scope:** camera-based scanning to capture values (needs native app) — display only.

##### FR-21: Autonumber Field
An editor can create an Autonumber Field that auto-assigns the next integer to each Row in creation order.
**Consequences (testable):**
- Each new Row receives the next unused integer automatically; the value is not user-editable.
- Deleting a Row does not renumber other Rows (assigned values are stable).
- Sequence is monotonic per Table and collision-free under concurrent inserts (DB-sequence-backed, not read-then-increment) and under bulk import. `[ASSUMPTION: gaps are acceptable on rollback/delete — uniqueness and monotonicity guaranteed, contiguity is not.]`

##### FR-21B: Running Count Field
An editor can create a Running Count Field that counts Rows matching a configured condition.
**Consequences (testable):**
- The Field computes the count of Rows satisfying its filter condition and recomputes when matching Data changes.
- Existing relational Count behavior is unaffected.
- `[ASSUMPTION: condition scope (whole Table vs. a grouping) confirmed with UX — default = whole Table filter.]`

### Batch 4 — App Builder

#### 4.8 App Builder Elements: Charts, Metrics, View Embeds
**Description:** New App Builder Elements so builders can put live data visualizations and database Views directly on App Pages — closing the gap that charts/metrics live only in the (paid) Dashboards module and that Kanban/Calendar/Timeline can't be embedded. Chart/Metric Elements are Bucket B and reuse the shared charting foundation (§4.6). View-embed Elements (Kanban/Calendar/Timeline) depend on the reimplemented Views from Batch 1. Realizes UJ-3.

**Functional Requirements:**

##### FR-22: Chart Element
A builder can place bar/line/pie/doughnut/scatter chart Elements on a Page bound to a Data Source. Realizes UJ-1, UJ-3.
**Consequences (testable):**
- Chart Element renders on the published Page from its Data Source.
- Respects Page-level filters/parameters where applicable.

##### FR-23: Metric Element
A builder can place a summary metric Element on a Page.
**Consequences (testable):**
- Metric computes and renders its aggregation on the published Page.

##### FR-24: Kanban / Calendar / Timeline embed Elements
A builder can embed a Kanban, Calendar, or Timeline display of a Table on a Page.
**Consequences (testable):**
- The embed renders the corresponding View layout from a Data Source on the published Page.
- Read/interaction permissions follow the viewer's Role (see §4.9). `[ASSUMPTION: embeds are read-oriented in v1; whether app viewers can drag-edit via an embed is confirmed with UX/permissions.]`
- **Dependency:** requires the Batch 1 reimplemented View renderers (these embeds wrap them).

##### FR-25: Record review layout
A builder can place a record-review Element that walks a user through filtered Rows one at a time.
**Consequences (testable):**
- Element presents one Row at a time with next/previous navigation over the Data Source.
- `[NON-GOAL for MVP]` AI-generated review layouts.

### Batch 5 — Collaboration

#### 4.9 Collaboration: RBAC, Comments, Personal & Locked Views, Field Permissions
**Description:** The free tier today has only two workspace permission levels — `ADMIN` and `MEMBER` (`core/models.py`); the granular Role hierarchy (Viewer/Editor/Commenter/custom) lives in **enterprise** (Bucket A). So the **RBAC role foundation (FR-29) is the load-bearing prerequisite** for the Commenter role, interface-only collaborator, and Field Permissions — it must be clean-room reimplemented **first** (see §13). On that foundation this batch adds: row comments + @mentions (Bucket A), personal views (Bucket A), field-level permissions (Bucket A — enterprise), locked views (Bucket A), interface-only collaborator (builds on RBAC — Bucket A-dependent, not greenfield), and password-protected share links (Bucket B). The permission system is load-bearing and security-sensitive — every FR here enforces **server-side at every surface** (REST, WebSocket, exports, App Builder embeds, charts, formulas/lookups/rollups). See §10 NFRs, §11 Risk, and the role-interaction matrix in §11.

**Functional Requirements:**

##### FR-29: RBAC role foundation + Commenter Role
An admin can assign granular Roles (at minimum Viewer, Commenter, Editor, plus the existing Admin) to members at workspace/database scope. Realizes UJ-4. **Clean-room reimplementation** of the enterprise RBAC layer — must not copy enterprise source (§8).
**Consequences (testable):**
- A new Role hierarchy is introduced above the current ADMIN/MEMBER model. **Migration mapping (no loss of access):** existing `ADMIN` → Admin; existing `MEMBER` (today a full read-write member) → **Editor** (NOT Viewer/Commenter — mapping down would silently strip write access from all non-admins). The migration is reversible (documented rollback) and verified by a test asserting every pre-migration member retains equivalent write capability.
- **Commenter** can read Rows and post Comments but cannot create/edit/delete Rows, Fields, or Views (enforced server-side, 403; enforced on REST and WebSocket).
- **Viewer** can read but not comment or edit.
- Role checks route through the existing `PERMISSION_MANAGERS` system, not a parallel check path.
- **Out of Scope:** fully custom user-defined roles with arbitrary operation grids (enterprise-grade RBAC admin UI) — v1 ships the fixed Viewer/Commenter/Editor/Admin tiers. `[ASSUMPTION: fixed tiers acceptable for v1; custom-role builder deferred.]`

##### FR-26: Row comments with @mentions
A member with at least Commenter Role can post threaded Comments on a Row and @mention members. Realizes UJ-1, UJ-3.
**Consequences (testable):**
- Comments persist per Row, render in thread order, and broadcast in real time **only to recipients who can see that Row** (per FR-29/FR-30).
- A Comment must not embed or leak hidden-by-permission Field values to lower-privileged subscribers.
- An @mention is only allowed for members who already have access to the Row; mentioning a member without Row access is rejected (no notification, no row link leak).
- Editing/deleting one's own Comment is supported per Role; admins can moderate others' Comments.

##### FR-27: Comment notifications
A mentioned or subscribed member receives an in-app notification for relevant Comment activity they are authorized to see.
**Consequences (testable):**
- @mention generates a notification linking to the Row/Comment, only if the recipient can access the Row.
- `[ASSUMPTION: in-app notification only in v1; email digest deferred.]`

##### FR-28: Personal Views
A member can mark a View as Personal so only they can see it. Realizes UJ-4.
**Consequences (testable):**
- A Personal View is filtered out of the View list of all other members **and** any direct fetch of another member's Personal View by ID returns 403 (not just list-hiding — no IDOR).
- Owner can toggle it back to shared.
- Personal Views work across all View Types (grid, kanban, calendar, etc.).

##### FR-30: Field Permissions
An admin can restrict both editing and visibility of a Field by Role/member, enforced at every data surface. Realizes UJ-4.
**Consequences (testable):**
- A restricted Field rejects edits from unauthorized members server-side (403) and renders read-only for them.
- A hidden-by-permission Field is **not returned by the API to unauthorized members through ANY path**: grid/all View Types, App Builder embeds, chart/metric Data Sources (no aggregation, sum/min/max/labels), formulas/lookups/rollups that reference it, search/filter results, exports (FR-33B), and WebSocket broadcasts.
- Aggregations and formulas that transitively read a hidden Field are blocked or null-redacted for unauthorized principals (no value inference via aggregate). A **visible** formula/lookup/rollup whose inputs include a hidden Field (including cross-table) is also blocked/redacted for that principal — derivation is a leak path.
- **Inference-oracle guard:** an unauthorized principal cannot filter or sort *on* a hidden Field — predicate use is rejected, because result membership/count/order leaks the value even when the Field itself is not returned.
- Permission rules persist per Field and apply uniformly; a permission change invalidates cached row/field payloads **and** aggregate/chart caches and the Redis model-cache, and re-evaluates active sessions/WebSocket subscriptions.

##### FR-31: Interface-only collaborator Role
An admin can invite a member who can access only App Builder Pages, never the underlying Data — enforced data-scoped, not just by hiding navigation. Realizes UJ-3. Builds on FR-29.
**Consequences (testable):**
- The member can open shared App Pages they're granted; database navigation is hidden.
- All Database/Table/View REST endpoints, **App Builder Data Source dispatch, formula evaluation, and WebSocket channels** deny direct Data access beyond what the granted Page's elements expose (403/empty), so there is no back-door to the DB via a data source or formula.
- Data returned through a Page is the minimum the Page's Elements need — not the full row.
- **Mandatory security review and an exhaustive role-combination test matrix before ship** (see §11).

##### FR-32: Locked Views
An editor can lock a View so its configuration cannot be changed by others. Realizes UJ-4.
**Consequences (testable):**
- A Locked View's filters/sorts/fields/layout are read-only to non-owners (server-enforced).
- Data within the View is still editable per the member's Role.
- Lock can be removed only by an Admin or the lock owner (defined unlock authority).

##### FR-33: Password-protected share links
A member can add a password to a public share link (View, Dashboard, or App Page), implemented to a defined security bar.
**Consequences (testable):**
- Accessing the link prompts for the password; correct password grants read access under a least-privilege **share principal** (FR-17) — never the sharer's permissions.
- Password stored with a modern KDF (e.g. Argon2id/bcrypt, defined work factor), compared in constant time; the share token is high-entropy and unguessable (no sequential/enumerable IDs).
- Rate-limiting and lockout on repeated wrong passwords; uniform error response that does not reveal whether a link exists.
- Removing the password reverts to open/closed as configured.

##### FR-33B: Exports honor Field Permissions
All export paths (CSV/JSON/XLSX, Map, and any download) return only Data the requesting principal is permitted to see.
**Consequences (testable):**
- Hidden-by-permission Fields (FR-30) and restricted Rows are absent from every export format.
- Public/anonymous and interface-only principals cannot export beyond their granted surface.

## 5. Non-Goals (Explicit)

- **Not building automations this release** — no new triggers/actions, no Run Script. This is why the **Button field is deferred** (it needs a `BUTTON_CLICKED` trigger).
- **Not building AI features** — no AI field, no formula/AI generator, no AI-generated app pages.
- **Not shipping native mobile / offline** — barcode is display-only (no camera scanning).
- **Not delivering full enterprise IAM** — no SSO/SAML/OIDC, no formal audit-log product, and **no custom user-defined role builder** in this wave. The RBAC foundation (FR-29) ships fixed tiers (Viewer/Commenter/Editor/Admin); arbitrary custom roles with per-operation grids are deferred. Commenter, interface-only, and field permissions are the scoped subset built on that foundation.
- **Not building new sync connectors** (GitHub/Jira/Salesforce/etc.) — separate wave.
- **Not adding conditional/role-based element visibility in App Builder** this release (research flags it as a gap) — App Builder Elements render unconditionally for principals with Page access; data-level scoping is handled by Field Permissions (FR-30) + interface-only (FR-31), not per-Element show/hide rules. Revisit in a later App Builder wave. `[NOTE FOR PM]`
- **Not un-gating premium code** — all Bucket A features are *clean-room reimplemented*, never copied. This is a hard legal constraint (§8).
- **Not changing Clavis's free-tier differentiators** — unlimited records, real-time WebSocket, self-hosting, two-way Postgres sync must be preserved, not regressed.

## 6. MVP Scope

### 6.1 In Scope
- **RBAC foundation** (fixed tiers Viewer/Commenter/Editor/Admin) — the permission prerequisite, built first.
- Views: Kanban, Calendar, Timeline, Gantt (dependencies, CPM critical path, milestones), Map — all in the free tier.
- Dashboard **chart Widgets** (bar/pie clean-room + line/scatter new) + grouped-aggregate Data Source + dashboard public share. *(Dashboard module + metric Widget already free — non-regression only.)*
- Field types: Currency, Percent, Barcode (display), Autonumber, Running Count.
- App Builder: Chart, Metric, Kanban/Calendar/Timeline embed, and record-review Elements.
- Collaboration: row comments + @mentions + notifications, personal views, field permissions (edit + hide), interface-only collaborator, locked views, password-protected share links — all with every-surface server-side enforcement + a release-gating security review.

### 6.2 Out of Scope for MVP
- Button field and its automation trigger — *deferred to the automation wave* (load-bearing for power users; revisit when automations are scheduled). `[NOTE FOR PM]`
- **Custom user-defined role builder** — v1 ships fixed RBAC tiers only.
- Dashboard module/metric Widget rebuild — already free; not rebuilt.
- Email/digest comment notifications — in-app only in v1.
- AI elements, Run Script, native mobile/barcode scanning, SSO/audit-log, new sync connectors — separate waves.
- Grouping Kanban by non-single-select fields; non-FS dependency auto-reschedule guarantees.

## 7. Success Metrics

*Measurement note: most usage metrics can only be collected on Clavis **cloud** — self-hosted installs send no telemetry by default. Targets below are measured on cloud; self-host signal is opt-in (anonymous, if the operator enables it) and treated as directional, not authoritative.*

**Primary**
- **SM-1: Airtable parity %** — move free-tier parity from the research baseline ~50–55% to ≥80% on the same tracked feature set. Validates the release as a whole (FR-1 through FR-33B). Measurement: re-score the corrected research feature matrix after release by a named reviewer against a fixed checklist (not self-graded ad hoc). `[ASSUMPTION: 80% target — confirm exact threshold and who owns the re-score.]`

**Secondary** (cloud-measured)
- **SM-2: New-view adoption** — % of active free-tier cloud bases that create at least one new View type (Kanban/Calendar/Timeline/Gantt/Map) within 60 days. Validates FR-1–FR-13. Target: `[ASSUMPTION: ≥30%]`.
- **SM-3: Collaboration activation** — % of multi-member cloud workspaces using comments or a scoped Role (Commenter/interface-only) within 60 days. Validates FR-26–FR-33B.
- **SM-4: Data-viz usage** — # of cloud dashboards/app pages created with a chart/metric Widget/Element. Validates FR-14–FR-25.

**Counter-metrics (do not optimize)**
- **SM-C1: Real-time latency must not regress** — p95 WebSocket broadcast latency for row/board updates stays at or below current baseline **under the same row-count and concurrent-client load as the baseline run** (so adding per-recipient permission filtering and bigger payloads can't hide a regression behind a lighter test). Counterbalances all view/collaboration FRs.
- **SM-C2: Free-tier record limits stay unlimited** — no feature introduces a row cap. Counterbalances SM-1 (don't reach parity by Airtable-style gating).
- **SM-C3: Frontend bundle/perf budget** — initial app load and grid render budgets do not regress beyond an agreed threshold, **measured with the new charting/map/Gantt code actually loaded on a representative page** (not just lazy-deferred off the landing route, which would mask the cost). Counterbalances SM-2/SM-4.

## 8. Constraints and Guardrails

### Licensing (load-bearing)
- Every Bucket A feature (Kanban, Calendar, Timeline, **Dashboard chart widgets (bar/pie)**, comments, personal views, **RBAC roles incl. Commenter**, field permissions, locked views, **interface-only collaborator** which builds on RBAC) MUST be **clean-room reimplemented**: built from public docs/UI behavior only. Copying, adapting, or sublicensing the licensed source into the free build is prohibited by the PE/EE license.
- **Repo-access contamination is the central risk.** This team already has read access to `premium/` and `enterprise/` in this repo, so "engineers who have not read premium source" may be a population that does not exist. The clean-room process MUST resolve this — options: (a) a walled-off implementer group with enforced no-access to those dirs, (b) external/contracted implementers, (c) per-feature legal review of provenance. Reconstructing from memory of the paid product is NOT clean-room. **Owner + legal sign-off required before any Bucket A work (step 0 of §13).**
- **Process gates (binding, not advisory):** (1) reader/writer population separation; (2) behavior specs authored ONLY from allowed public sources — an explicit allowed-source list (public docs, public UI of the *upstream Baserow SaaS*, public issues), excluding the team's own `premium/`/`enterprise/` source and paid-instance internals; (3) a per-feature provenance log that is a **merge gate** — no Bucket A PR merges without it; (4) "influenced by" counts as contamination, not just verbatim copy.
- Bucket B features (Gantt, Map, Currency/Percent/Barcode/Autonumber/Running-Count, line/scatter charts, chart/metric App elements, password share) carry no license entanglement and are safe to start first. **Note:** interface-only collaborator and the Commenter role are NOT pure Bucket B — they depend on the RBAC reimplement (Bucket A).
- **Trademark:** "Airtable parity / alternative" framing is for internal/PRD use only; it must not leak into product UI or marketing copy without trademark review.

### Privacy / Cost (geocoding)
- Map geocoding sends address data to a third-party provider. Default = **Google Maps Platform** (cloud); self-host uses a configurable provider (OSM/Nominatim default). Google ToS: results may **not** be cached long-term and the map may **not** be shown without Google tiles — so the cache-and-self-host path requires a non-Google provider. Provider configurable via env var; rate limits respected; document data-egress for self-hosters; Google needs API key + billing.

### Platform
- Web only (Nuxt 3 / Vue 3 — repo is authoritative over the research doc's stale "Vue 2" note). Vue 3 render semantics; JSX in `.jsx`/`.tsx`.

## 9. Assumptions Index

- §4.1 — Kanban grouping by a single Single-select field in v1.
- §4.4 — Dependency default finish-to-start; auto-reschedule guaranteed for FS only.
- §4.4 FR-10 — RESOLVED: prompt-first reschedule.
- §4.5 — Geocoding: Google Maps default (cloud), configurable provider for self-host; if forced Google everywhere, self-host needs own key + accepts caching limits.
- §4.6 — Dashboard module + metric Widget already free (verified in repo); scope = chart Widgets (bar/pie Bucket A, line/scatter Bucket B) + grouped-aggregate Data Source + app embed.
- §4.6 FR-15 — Chart refresh on load + real-time row events (strategy confirmed in architecture).
- §4.6 NFR — 12-widget/100k-row render budget figure.
- §4.9 FR-29 — Fixed RBAC tiers (Viewer/Commenter/Editor/Admin) acceptable for v1; custom-role builder deferred.
- §4.7 FR-19 — Percent uses whole-number entry convention.
- §4.7 FR-21/21B — RESOLVED: ship both Autonumber and Running Count. Running Count condition scope (whole table vs grouping) pending UX.
- §4.8 FR-24 — View embeds are read-oriented in v1.
- §4.9 FR-27 — In-app notifications only (no email) in v1.
- §7 SM-1 — 80% parity target threshold.
- §7 SM-2 — 30% new-view adoption target.

## 10. Cross-Cutting NFRs

- **Real-time:** all new mutating views/collaboration features broadcast over the existing WebSocket layer; no feature introduces polling where realtime is expected. p95 broadcast latency ≤ current baseline (SM-C1).
- **Performance (concrete budgets, to ratify in architecture):** Kanban/Calendar/Timeline/Gantt must use the existing virtual-scroll/lazy-row patterns for large tables; new filterable/sortable Fields implement correct ordering (`get_order_by_field_string`) and use field indexing. Map clusters server- or client-side to avoid plotting all rows at once. Initial budget targets: `[ASSUMPTION]` a new View first-meaningful-paint ≤ 2s on a 100k-row Table (broadband, mid-tier laptop); scroll/drag interaction ≥ 50fps; a 12-Widget Dashboard initial paint ≤ 3s; added frontend bundle from charting+map+Gantt ≤ 400KB gzip on routes that load them (SM-C3). Numbers are placeholders for the architect to confirm/replace with measured baselines.
- **Optimistic UX + concurrent edits:** drag operations (cards, calendar entries, Gantt bars) apply optimistically with rollback on failure. **Concurrent-edit semantics defined:** when two users move the same Row/card simultaneously, last-write-wins per field with a real-time broadcast that reconciles both clients; a client whose optimistic update is superseded snaps to the authoritative state (no silent divergence). Gantt cascade reschedules (FR-10) acquire the affected Rows so two overlapping cascades cannot interleave into an inconsistent schedule.
- **Security (every-surface enforcement):** all role/permission FRs enforced **server-side** (never UI-only); 403 on unauthorized; route through the existing `PERMISSION_MANAGERS` system, never a parallel path. Enforcement must hold at EVERY data surface — REST, **WebSocket (authorize at *subscribe* time, not only payload-filter — a principal who can't see a Table/Row cannot open its channel)**, App Builder Data Source dispatch, formulas/lookups/rollups, chart/metric aggregation, **filter/sort predicates** (no inference oracle), search, and exports. Public/password share links resolve under a least-privilege share principal that is **deny-by-default** (a Field is exposed through a share only if explicitly visible to the share principal; password vs no-password links resolve under the same principal model). Passwords use a modern KDF + constant-time compare + rate-limit; share tokens are high-entropy/unguessable (FR-33). Geocoded lat/lng is derived data — enforce the source address Field's permission per-principal at **read** time, not just at cache-write. Permission changes invalidate row/field, aggregate/chart, and Redis model caches and re-evaluate live sessions/subscriptions.
- **Accessibility:** new views and elements meet the project's existing a11y bar (keyboard navigation for board/calendar/gantt interactions where feasible). `[ASSUMPTION: WCAG 2.1 AA target consistent with existing components — confirm.]`
- **i18n:** all new UI strings added to translation catalogs (`en.json` + existing locales).
- **Testing:** each feature ships model→handler→serializer/API→frontend-registry→component tests per the project test matrix (backend pytest, frontend vitest).

## 11. Risk and Mitigations

- **Clean-room contamination (legal, CRITICAL).** Team already has `premium/`+`enterprise/` repo access, so a clean implementer population may not exist; an engineer reuses or is *influenced by* premium source. *Mitigation:* §8 binding gates — walled-off/external implementers, allowed-source list, provenance log as merge gate, legal sign-off as §13 step 0. Blocks ALL Bucket A work until resolved. Owner unassigned (Open Q7) — must be assigned before Bucket A starts.
- **Permission system regression (security, CRITICAL).** RBAC is being introduced where only ADMIN/MEMBER existed; field-hiding must hold across many NEW data surfaces (charts/aggregation, embeds, formulas/lookups/rollups, exports, WebSocket). A gap at any one surface leaks data. *Mitigation:* every-surface server-side enforcement (§10); **role-interaction matrix enumerated and tested** — every combination of {Viewer, Commenter, Editor, Admin, interface-only} × {field-permission state} × {personal/locked view} × {public/password share}, written out as a resolved-cell table with an explicit **most-restrictive-wins** precedence rule (when two grants conflict, the narrower access applies); mandatory security review + threat model as §13 step 7 release gate (esp. FR-30/31/33/33B). Build the permission layer (§13 steps 1–2) BEFORE the features that must honor it.
- **Aggregation/formula inference leak (security, high).** Charts, metrics, and formulas can reveal a hidden Field's values via sum/min/max/labels even when the raw Field is hidden. *Mitigation:* FR-30 blocks/null-redacts transitive reads for unauthorized principals; test inference paths explicitly.
- **Geocoding rate limits / privacy (medium).** Provider throttles or leaks addresses; geocoded PII inherits Field permissions. *Mitigation:* caching where ToS permits, throttled queue, configurable/self-hostable provider, documented egress, geocoded lat/lng treated as derived data under the source Field's permissions.
- **Bundle size / perf regression (medium).** Charting + map + Gantt libraries bloat the frontend. *Mitigation:* validate library licenses and bundle impact before commit (SM-C3), lazy-load heavy view/chart code.
- **Gantt scheduling complexity (medium).** Cycle detection, cascade reschedule, critical path correctness. *Mitigation:* constrain v1 to FS dependencies for auto-reschedule; thorough algorithm tests.
- **Scope (planning, HIGH).** Single combined release across 5 batches is large, and the RBAC reimplement (FR-29) is now known to be a multi-week foundation that gates much of the release — not the small item first assumed. *Mitigation:* dependency-ordered build sequence (§13) front-loads RBAC + permissions and license-clean foundations; release gate is feature-complete, not phased-ship; revisit whether RBAC scope warrants its own milestone if timeline pressure appears. `[NOTE FOR PM]`

## 12. Integration and Dependencies

- **Charting foundation** — shared by Dashboard Widgets (§4.6) and App Builder chart/metric Elements (§4.8). Build once.
- **View renderers** — App Builder Kanban/Calendar/Timeline embeds (FR-24) depend on the Batch 1 reimplemented Views.
- **Permission/role system (foundation, not add-on)** — the free tier has only ADMIN/MEMBER; a clean-room RBAC layer (FR-29) is built first, then Commenter, interface-only, field permissions, and locked views extend it via the existing `PERMISSION_MANAGERS`; personal views add ownership to the View model. Charts/embeds/exports/WebSocket all consume this layer for enforcement.
- **Automation system (deferred dependency)** — Button field (out of scope) needs a `BUTTON_CLICKED` trigger; flagged so the automation wave can pick it up.
- **Notification system** — comment @mentions use the existing in-app notification infrastructure.
- **Data Source / service registry** — all charts/metrics/embeds query through the existing service-type registry.

## 13. Build Sequencing (dependency-ordered, single release)

*All batches ship together as the next version; this is implementation order, not separate releases. Derived from cross-batch dependencies — confirm/refine in the architecture phase (`bmad-create-architecture`).*

**Critical sequencing correction (from review):** the RBAC/permission foundation is a **prerequisite**, not a finale. Field Permissions (FR-30), interface-only (FR-31), and the permission enforcement that charts/embeds/exports rely on all depend on it. It moves to step 1, before the features that must honor it.

0. **Clean-room process gate (blocks all Bucket A work):** assign owner, legal sign-off, behavior-spec template, provenance-log gate, repo-access barrier (§8). No Bucket A code (Kanban, Calendar, Timeline, Dashboard charts, comments, personal views, RBAC, field perms, locked views) starts until this is in place.
1. **Foundations (parallelizable):**
   - License-clean fields (Currency/Percent/Barcode/Autonumber/Running-Count, FR-18–21B); charting foundation; geocoding infrastructure.
   - **RBAC role foundation (FR-29)** — the permission prerequisite for everything below. Clean-room.
2. **Permission enforcement layer:** Field Permissions (FR-30), personal-view ownership + IDOR guard (FR-28), WebSocket subscribe-time auth + per-recipient filtering, export enforcement (FR-33B), share principal + password hardening (FR-17/FR-33). *Built here as the enforcement framework; each NEW data surface added in steps 3–5 (views, charts, embeds) must wire into and re-verify this framework as it lands — "every-surface" is completed incrementally and confirmed at the step 7 gate, not fully testable at step 2 alone.*
3. **View layer (Bucket A clean-room + B):** Kanban (FR-1–3), Calendar (FR-4–5), Timeline (FR-6–7); Gantt + Task Dependency + CPM critical path/milestones (FR-8–11); Map (FR-12–13). All honor step 2 permissions.
4. **Dashboard charts:** grouped-aggregate Data Source (FR-14) + chart Widgets (FR-15) consuming the charting foundation; non-regression of free metric Widget (FR-16); dashboard share (FR-17).
5. **App Builder Elements:** Chart/Metric (FR-22–23, consume charting) + Kanban/Calendar/Timeline embeds (FR-24, consume step 3 views) + record review (FR-25).
6. **Remaining collaboration:** row comments + @mentions + notifications (FR-26–27), locked views (FR-32), interface-only collaborator (FR-31, data-scoped, **security-reviewed before ship**).
7. **Security gate (blocks release):** threat model + role-combination test matrix + security review covering FR-30/31/33/33B and all data surfaces (charts, embeds, exports, WebSocket) — see §11.

**Market-weight tiebreaker (if scope must be cut — but goal is ship-all):** research ranks Kanban as the single biggest free-tier gap, followed by row comments and personal views. If timeline forces a trim, protect those first; Map and App Builder embeds are the most deferrable. `[NOTE FOR PM]`

## 14. Open Questions

1. Confirm exact parity target (SM-1) and the feature matrix used to re-score.
2. ~~Gantt FR-10 interaction model~~ — RESOLVED: prompt-first reschedule.
3. ~~Standalone Count semantics~~ — RESOLVED: ship both Autonumber (FR-21) + Running Count (FR-21B).
4. ~~Field permissions hide-by-permission~~ — RESOLVED: v1 includes edit-restriction + hide-by-permission (FR-30).
5. ~~Geocoding provider~~ — RESOLVED: Google Maps default (cloud) + configurable for self-host. Confirm whether forced-Google-everywhere is acceptable instead.
6. App Builder view embeds (FR-24): read-only or interactive drag-edit in v1? **Now security-load-bearing** — interactive embeds are a privilege-escalation surface (must honor FR-30/Role).
7. **[CRITICAL — assign before Bucket A starts]** Clean-room process owner + legal sign-off + resolution of repo-access contamination (walled-off vs external implementers). See §8.
8. Percent entry/display convention (FR-19) — match Airtable whole-number entry?
9. SM-1 parity re-score: who owns it, and is ≥80% the agreed bar?
10. Confirm fixed RBAC tiers (Viewer/Commenter/Editor/Admin) are enough for v1, or is a custom-role builder needed sooner?
11. Running Count (FR-21B) condition scope: whole-table filter vs per-grouping?
