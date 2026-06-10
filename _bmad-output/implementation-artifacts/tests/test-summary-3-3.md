# Test Automation Summary — Story 3.3: Configure Kanban Card Appearance

**Workflow:** `bmad-qa-generate-e2e-tests` (QA automation, gap analysis + auto-apply)
**Date:** 2026-06-10
**Story:** `_bmad-output/implementation-artifacts/3-3-configure-kanban-card-appearance.md`
**Framework:** Playwright (E2E), Vitest (frontend unit), pytest (backend) — all pre-existing.

## Context

Story 3.3 is a **verify + close-test-gap + provenance** story; the card-appearance
feature (per-field card-face visibility + `card_cover_image_field`) already shipped in
Story 3.1 by mirroring the public MIT Gallery view. dev-story already authored the
backend (22), frontend unit (33), and an E2E customize-cards scenario. This QA pass did
**gap analysis on the E2E coverage** against AC #1–#4 and auto-applied the gaps found.

## Gaps Discovered & Applied (E2E)

`e2e-tests/tests/database/kanban_view.spec.ts`

1. **AC #1 — cover-image picker UI surface not asserted.** The existing customize-cards
   test sets the cover field via the generic view PATCH (API) only; it never confirmed the
   "Customize cards" context actually exposes the cover picker. **Added** an assertion that
   `.hidings__cover` (the `allow-cover-image-field=true` FormGroup from the shared
   `ViewFieldsContext`) renders when the context opens.
2. **AC #4 — no E2E guard for grouping-field data dependency.** Backend tests pin
   `get_hidden_fields` keeping the single-select + cover fields visible, but no E2E proved
   the board still buckets correctly when the grouping field's option is `hidden`. **Added**
   a new test: with the grouping single-select field's `field_options.hidden = true`, cards
   must still bucket into their matching option columns after reload (a regressed guard would
   dump every card into the trailing "Uncategorized" column).

## Generated / Extended Tests

### E2E (`e2e-tests/tests/database/kanban_view.spec.ts`)
- [x] `customizing card appearance hides a field, sets a cover image, and both persist on reload (AC #1, #2, #3)` — pre-existing (dev) + cover-picker UI-surface assertion added this pass.
- [x] `keeps the grouping single-select field data-available when its field option is hidden, so cards still bucket correctly (AC #4)` — **new this pass.**

### Frontend unit (`web-frontend/test/unit/database/components/view/kanban/kanbanView.spec.js`)
- [x] `cardFields` / `hiddenFields` / `coverImageField` computeds + `KanbanViewHeader` dispatch — pre-existing (dev). Re-run this pass: **33 passed.**

### Backend (`backend/tests/.../view/test_kanban_view_type.py`, `.../api/views/kanban/test_kanban_view_views.py`)
- [x] cover-image set/persist/reject/null-on-delete, `get_hidden_fields` guard, field_options PATCH — pre-existing (dev). Documented **22 passed (OSS-only, `TEST_ENV_FILE=.env.oss-test`)**; not re-run this pass (requires Docker Postgres).

## Coverage vs Acceptance Criteria

| AC | Covered by | Status |
|----|-----------|--------|
| #1 field-face select + cover renders | E2E (toggle + cover, + new picker-surface assertion); FE unit `cardFields`/`coverImageField`; BE cover-set | ✅ |
| #2 persists per view + reopens | E2E reload (hidden + cover); BE PATCH persistence (field_options + view) | ✅ |
| #3 no row-coloring dependency | E2E `.card__content` present / no decoration layer; FE unit RowCard no decorations | ✅ |
| #4 grouping + cover always visible | BE `get_hidden_fields` guard test; **E2E bucketing guard (new this pass)** | ✅ |

## Validation

- **Frontend unit:** `yarn vitest run … kanbanView.spec.js` → **33 passed** ✅
- **Backend:** documented 22 passed (OSS-only); not re-run (Docker Postgres required).
- **E2E:** author-only. `e2e-tests/` has no installed `node_modules` and targets the
  OSS-only Docker CI lane (`BASEROW_OSS_ONLY=true`) — per story constraint, NOT run locally.
  New/edited cases structurally validated against existing fixtures (`updateFieldOptions`,
  `setupKanban` returns, `createRow`) and core DOM locators (`.kanban-view__column`,
  `.kanban-view__card`, `.hidings__cover` confirmed in `ViewFieldsContext.vue`).

## Checklist (`.agents/skills/bmad-qa-generate-e2e-tests/checklist.md`)

- [x] API tests generated (backend pytest — pre-existing, documented green)
- [x] E2E tests generated (UI exists — extended + new case)
- [x] Tests use standard framework APIs (Playwright / Vitest / pytest)
- [x] Happy path covered; [x] critical error/guard cases covered (reject non-file cover; AC #4 guard)
- [x] Frontend unit run successfully (33 passed); backend documented green; E2E author-only (CI lane)
- [x] Semantic/accessible + stable locators; clear descriptions; no hardcoded sleeps; tests independent
- [x] Summary created with coverage metrics

## Next Steps

- Run the E2E spec in the OSS-only CI lane (Docker stack, `BASEROW_OSS_ONLY=true`).
- No further gaps; AC #1–#4 fully covered across backend + frontend unit + E2E.
