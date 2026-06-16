---
baseline_commit: 1d44b80719bf94152756a71e54fae62c2f2c2458
---
<!-- Powered by BMAD-CORE™ -->

# Story 3.15: Conditional row coloring (view decorations)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to color rows by a condition (e.g. "Trạng thái = Trễ → red"),
so that I can spot the rows that matter at a glance across my views. `[A]`

## Context & Scope

### 🚨 THIS IS A BUCKET A CLEAN-ROOM STORY — READ FIRST, NON-NEGOTIABLE

Row coloring is a **Bucket A** premium feature. It must be reimplemented in **core** without ever reading, copying, or being "influenced by" any `premium/` or `enterprise/` source. The PE/EE license forbids copying; a provenance record is a **hard CI merge gate**.

- **Do NOT open, read, `grep`, or adapt** anything under `premium/` or `enterprise/` — specifically the concrete decorator/value-provider implementations that already exist there. Reading them = contamination = the PR cannot merge. [Source: architecture.md line 268; memory `clean-room-isolation-porous`; `baserow-open-core-license-constraint`]
  - **OFF-LIMITS (do not open):** `premium/backend/src/baserow_premium/views/decorator_types.py`, `premium/backend/src/baserow_premium/views/decorator_value_provider_types.py`, `premium/web-frontend/modules/baserow_premium/viewDecorators.js`, `premium/web-frontend/modules/baserow_premium/decoratorValueProviders.js`, and all `premium/.../components/views/*ColorViewDecorator.vue` / `*ColorValueProviderForm.vue`.
- All new code lands in **core** (`backend/src/baserow/...`, `web-frontend/modules/database/...`). [Source: architecture.md line 205]
- A provenance record under `docs/clean-room/provenance/3-15-conditional-row-coloring.md` is **mandatory** (final task) and is the CI merge gate. [Source: 1-1-establish-the-clean-room-process-gate.md]
- Premium-precedence: in full open-core builds premium registers the same decorator/provider `type` strings; last-registration-wins. Our core types are the active ones only in **OSS-only** builds (`BASEROW_OSS_ONLY=true`). Run tests OSS-only. [Source: 3-1 Completion Notes; 3-2 Context & Scope]

### 🧭 SINGLE MOST IMPORTANT FACT: the decoration SCAFFOLD already exists in MIT core — build the CONCRETE types, do not rebuild the framework

Core already ships the entire view-decoration framework (MIT/upstream). **Do NOT reinvent it.** Your job is to add the two concrete **decorator types** + the one concrete **value-provider type** on top of the existing registries, then wire rendering into the views that don't yet show decorations.

**What already exists in core (reuse verbatim — cite these):**

Backend:
- `ViewDecoration` model + `ViewDecorationManager`. [Source: backend/src/baserow/contrib/database/views/models.py:425]
- `DecoratorType`, `DecoratorValueProviderType` base classes + `decorator_type_registry`, `decorator_value_provider_type_registry`. [Source: backend/src/baserow/contrib/database/views/registries.py]
- Decoration exceptions (`DecoratorTypeDoesNotExist`, `DecoratorValueProviderTypeNotCompatible`, `ViewDecorationNotSupported`, …). [Source: backend/src/baserow/contrib/database/views/exceptions.py:152–200]
- Value-provider signal hooks that recompute/clean decoration `value_provider_conf` on field/filter changes. [Source: backend/src/baserow/contrib/database/views/signals.py:43–53]
- CRUD handler + API for `ViewDecoration` (create/update/list/delete decorations on a view) is already generic in core. **No new endpoint needed for the decoration record itself.**

Frontend:
- `ViewDecoratorType` base class. [Source: web-frontend/modules/database/viewDecorators.js]
- `DecoratorValueProviderType` base class. [Source: web-frontend/modules/database/decoratorValueProviders.js]
- Render slot: `decorationsByPlace` + the `viewDecoration` mixin already consumed by Grid + Gallery + RowCard. [Source: web-frontend/modules/database/mixins/viewDecoration.js; components/view/grid/GridViewRow.vue, GridViewRows.vue, GridViewSection.vue; components/view/gallery/GalleryView.vue; components/card/RowCard.vue]

> ⚠️ **Anti-pattern (forbidden):** writing a new `ViewDecoration` model/migration, a new decoration registry, a new decoration CRUD endpoint, or a new render mixin. They exist. If you're editing `registries.py` to add a *base* class or writing a decoration migration, **stop — you've left the story.** You add concrete `*Type` subclasses + register them; you add Vue form/decorator components; you extend the render slot to the 3 views that lack it.

### Scope of THIS story (3.15) — decided with PM

**Strategy:** **Conditional color only.** Color is chosen by evaluating view-filter-style conditions per row (matching condition group → its color). *(Single-select-field color is a separate, simpler strategy — explicitly DEFERRED to a follow-up story.)*

**Decorator types (both):**
- `left_border_color` — colored left border on the row/card.
- `background_color` — colored background on the whole row/card.

**Views (all 5):** Grid, Gallery, Kanban, Calendar, Timeline.
- Grid + Gallery + RowCard already consume `decorationsByPlace` (Kanban cards render via `RowCard`). **Verify** these render with the new types.
- Calendar and Timeline render their own row/event components and **do not yet** consume the decoration slot — wiring decoration rendering into them is **net-new frontend work in this story** and the primary effort/risk. [Source: this story; verify against components/view/calendar/* and components/view/timeline/*]

**In scope:**
- Backend: `LeftBorderColorDecoratorType`, `BackgroundColorDecoratorType` (decorator types); `ConditionalColorValueProviderType` (value provider) — reimplemented clean-room in core, registered in `backend/src/baserow/contrib/database/apps.py`.
  - `conditional_color` `value_provider_conf` stores an ordered list of `{ id, color, filters, filter_groups, filter_type }` "color rules". Reuse core's existing **view filter** model/evaluation primitives for matching — do not invent a new predicate engine. [Source: backend/src/baserow/contrib/database/views/ — view filter handler/registry]
  - Signal hygiene: when a field referenced by a rule's filters is deleted or a filter becomes invalid, the rule is cleaned up via the existing `decorator_value_provider_type_registry` signal path (implement `after_field_*` / config-update hooks on the provider type).
- Frontend: register `LeftBorderColorViewDecoratorType`, `BackgroundColorViewDecoratorType`, `ConditionalColorValueProviderType` in `web-frontend/modules/database/plugin.js`; add the decorator render components + the `ConditionalColorValueProviderForm.vue` (color-rule editor reusing the core view-filter form components).
- Frontend: extend decoration rendering to **Calendar** and **Timeline** (and confirm Kanban via RowCard).
- Tests: backend (provider conf validate/persist, condition→color evaluation, field-delete cleanup), frontend unit (decorator types compatible with all 5 views; conditional provider resolves a row's color from rules; form dispatches), E2E (add a rule on a Grid view → matching rows colored → persists on reopen; same on one card-based view).
- Provenance record (final task).

**Explicitly OUT of scope (do NOT build):**
- ❌ **Single-select-field color** value provider (`single_select_color`) — deferred to a follow-up story.
- ❌ Rebuilding any part of the core decoration scaffold (model, registries, CRUD endpoint, render mixin) listed above.
- ❌ Opening/reading/adapting anything under `premium/` or `enterprise/`.
- ❌ Form, Spreadsheet-export, or public-share coloring concerns beyond the 5 listed views (note them as follow-ups if they surface).

## Acceptance Criteria

1. **Given** a Grid view, **When** an editor adds a `background_color` (or `left_border_color`) decoration with a `conditional_color` provider and defines a color rule (e.g. `Trạng thái = "Trễ" → #FF0000`), **Then** every row matching the rule renders with that color and non-matching rows render undecorated.
2. **And** multiple ordered rules are supported: the **first matching** rule wins; a row matching no rule is undecorated. Rule conditions reuse core view-filter semantics (operators, AND/OR groups).
3. **And** both decorator types work: `left_border_color` colors the row/card left border; `background_color` colors the whole row/card background.
4. **And** coloring renders across **all five** views — Grid, Gallery, Kanban (via RowCard), Calendar, Timeline — for the same decoration configuration.
5. **And** the decoration configuration **persists per view** and re-hydrates identically on reopen (export/import round-trips the `value_provider_conf`).
6. **And** when a field referenced by a color rule is deleted (or a rule's filter becomes invalid), the affected rule is cleaned from `value_provider_conf` without breaking the view (no 500, remaining rules still apply).
7. **And** the feature is active in **OSS-only** builds (no premium license required); registered in core; tests run `BASEROW_OSS_ONLY=true`.
8. A **provenance record** exists at `docs/clean-room/provenance/3-15-conditional-row-coloring.md` attesting no premium/enterprise source was read (CI merge gate).

## Tasks / Subtasks

### Task 1 — Verify the existing core decoration scaffold (AC: all) — DO NOT MODIFY THE SCAFFOLD
- [ ] Read (do not modify) `models.py:425` (`ViewDecoration`/manager), `registries.py` (`DecoratorType`, `DecoratorValueProviderType` + both registries), `exceptions.py:152–200`, `signals.py:43–53`. Write findings + exact line cites into Dev Notes. Confirm the decoration CRUD handler/endpoint already exists and needs no change.
- [ ] Read (do not modify) frontend `viewDecorators.js`, `decoratorValueProviders.js`, `mixins/viewDecoration.js`, and confirm which view components already consume `decorationsByPlace` (Grid, Gallery, RowCard) vs which do not (Calendar, Timeline).
- [ ] Confirm the existing core **view filter** model + evaluation primitives that the `conditional_color` provider will reuse for per-row matching (cite handler/registry). Do not build a new predicate engine.

### Task 2 — Backend: concrete decorator + value-provider types in core (AC: 1, 2, 3, 5, 6, 7)
- [ ] Add `backend/src/baserow/contrib/database/views/decorator_types.py` (core): `LeftBorderColorDecoratorType` (`type = "left_border_color"`), `BackgroundColorDecoratorType` (`type = "background_color"`). No premium license gate.
- [ ] Add `backend/src/baserow/contrib/database/views/decorator_value_provider_types.py` (core): `ConditionalColorValueProviderType` (`type = "conditional_color"`), compatible with both decorator types. Implement `value_provider_conf` schema validation (ordered rules: `id`, `color`, `filters`, `filter_groups`, `filter_type`) reusing core view-filter validation.
- [ ] Implement config-cleanup hooks (field deleted / filter invalid) on the provider type via the existing `decorator_value_provider_type_registry` signal path (`signals.py:43–53`).
- [ ] Register all three types in `backend/src/baserow/contrib/database/apps.py` (guard with the `if "baserow_premium" not in INSTALLED_APPS` premium-precedence pattern used by other core view registrations).
- [ ] Ensure export/import serializes/deserializes `value_provider_conf` (round-trip).

### Task 3 — Frontend: concrete types, components, registration (AC: 1, 2, 3, 5)
- [ ] Add core `LeftBorderColorViewDecoratorType`, `BackgroundColorViewDecoratorType` (in `web-frontend/modules/database/viewDecorators.js` or sibling), compatible with Grid/Gallery/Kanban/Calendar/Timeline. No premium feature gate.
- [ ] Add core `ConditionalColorValueProviderType` (in `decoratorValueProviders.js` or sibling) that resolves a row → color by evaluating its rules.
- [ ] Add decorator render components + `ConditionalColorValueProviderForm.vue` (color-rule editor) reusing core view-filter form components for the condition UI.
- [ ] Register the three types in `web-frontend/modules/database/plugin.js`.

### Task 4 — Frontend: render coloring across all 5 views (AC: 4)
- [ ] Confirm Grid + Gallery render the new decorations via the existing slot (no/minimal change).
- [ ] Confirm Kanban cards render via `RowCard` decoration slot.
- [ ] Extend **Calendar** event/row components to consume the decoration slot.
- [ ] Extend **Timeline** bar/row components to consume the decoration slot.

### Task 5 — Tests (AC: all) — run OSS-only
- [ ] Backend: provider conf validates/persists; first-matching-rule → correct color; multiple rules ordered; field-delete cleans the rule; export/import round-trip. (`just b test ... -p no:randomly`, OSS-only env.)
- [ ] Frontend unit: decorator types report compatibility with all 5 views; conditional provider resolves row color from rules; form dispatches decoration update. [Source: skill `write-frontend-unit-test`]
- [ ] E2E: add a rule on a Grid view → matching rows colored, non-matching not, persists on reopen; repeat on one card-based view.

### Task 6 — Provenance record (AC: 8) — MERGE GATE
- [ ] Write `docs/clean-room/provenance/3-15-conditional-row-coloring.md` attesting no `premium/`/`enterprise/` source was opened; list the core files referenced. Mirror an existing provenance record's structure (e.g. `docs/clean-room/provenance/3-3-configure-kanban-card-appearance.md`).

## Dev Notes

- **Epic placement:** Epic 3 (Visualize Data Multiple Ways). New requirement; suggest registering it in `epics.md` as **FR-34 — Conditional Row Coloring** (Bucket A, clean-room). FR-3 (Kanban appearance) previously declared row coloring out of scope for v1 — this story re-scopes it as a deliberate addition. [Source: epics.md:32,171]
- **Two competing strategies exist upstream** (single-select color, conditional color). This story ships **conditional only**; the simpler single-select strategy is a clean follow-up reusing the same decorator types.
- **Biggest risk = Calendar/Timeline render wiring**, not the registry work — those two views do not consume `decorationsByPlace` today. Budget effort there. Grid/Gallery/Kanban are largely free via the existing slot.
- **Clean-room discipline:** the framework is MIT and already in core; only the concrete `*ColorDecoratorType` / `ConditionalColorValueProviderType` semantics must be re-derived from the public registry contracts + AC, never from premium files.

## Change Log

| Date       | Version | Description                  | Author |
|------------|---------|------------------------------|--------|
| 2026-06-15 | 0.1     | Initial draft (PM John)      | John   |
