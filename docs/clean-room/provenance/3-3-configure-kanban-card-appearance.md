# Provenance record — Story 3.3 Configure Kanban card appearance

- **PR / branch:** feat(story-3.3) configure kanban card appearance (branch: develop)
- **Story:** 3.3 Configure Kanban card appearance
- **Bucket:** A (clean-room reimplement)
- **Implementer:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-09

## Sources Consulted

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | Public Airtable/Baserow "Kanban" UX — customizing which fields appear on a card face and choosing a cover image field for the card | public SaaS UI / public docs | https://baserow.io/docs , https://airtable.com |
| 2 | The Story 3.1 free-core Kanban view this story verifies/tests (`KanbanViewType`, `KanbanView` model, `KanbanViewFieldOptions`, `card_cover_image_field`, per-field `hidden`/`order` field options) — authored in 3.1 by mirroring the public free-core Gallery view | this repo (core, MIT free-core, authored in 3.1) | `backend/src/baserow/contrib/database/views/view_types.py` (KanbanViewType), `backend/src/baserow/contrib/database/views/models.py`, `web-frontend/modules/database/components/view/kanban/KanbanView.vue`, `web-frontend/modules/database/components/view/kanban/KanbanViewHeader.vue` |
| 3 | Free-core `GalleryViewType` — the MIT reference whose `card_cover_image_field` validation (`can_represent_files`), `get_hidden_fields` (keep grouping + cover always visible), and export/import round-trip 3.1 mirrored and 3.3 verifies | MIT free-core | `backend/src/baserow/contrib/database/views/view_types.py` (GalleryViewType) |
| 4 | Shared `RowCard.vue` card renderer — `.card__cover` (empty-state icon when no image), `.card__field-name`/`.card__field-value` per visible field, optional `decorationsByPlace` (defaults undefined → no decorations on the Kanban board, AC #3) | MIT free-core | `web-frontend/modules/database/components/card/RowCard.vue` |
| 5 | Shared `ViewFieldsContext.vue` ("Customize cards" body) — `.hidings__item` list with a `SwitchInput` per field toggling `field_options.hidden`, plus cover-image field chooser | MIT free-core | `web-frontend/modules/database/components/view/ViewFieldsContext.vue` |
| 6 | Two shared persistence paths reused unchanged: field face via the generic `PATCH /api/database/views/{id}/field_options/` endpoint, cover image via the generic `PATCH /api/database/views/{id}/` view update | MIT free-core | `backend/src/baserow/contrib/database/api/views/views.py`, `web-frontend/modules/database/utils/view.js` (`filterVisibleFieldsFunction`, `sortFieldsByOrderAndIdFunction`) |
| 7 | Free-core Gallery view unit test + gallery mock-server fixtures — reference shape for the Kanban card-appearance computeds/header-dispatch unit harness | MIT free-core | `web-frontend/test/unit/database/components/view/gallery/`, `web-frontend/test/fixtures/gallery.js` |
| 8 | Baserow test harness for OSS-only view-type registration (`BASEROW_OSS_ONLY=true`, `TEST_ENV_FILE`) so the core Kanban — not the open-core override — is the registered `kanban` type under test | this repo (core) | `backend/src/baserow/config/settings/test.py`, `backend/.env.oss-test` |
| 9 | Playwright locator/assertion API for the authored E2E customize-cards scenario | general public knowledge | https://playwright.dev |

## Implementer Attestation

- [x] I affirm that this Bucket A reimplementation was produced **clean-room**: I did
      **not** read, copy, adapt, or rely on memory of any `premium/` or `enterprise/`
      (PE/EE) source for this feature, and I was not *influenced by* it. Every source I
      used is listed above and is on the allowed-source list.

**Implementer signature / handle:** AI dev-agent (isolation model (a))   **Date:** 2026-06-09

## Reviewer confirmation (filled at review)

- [ ] Reviewer verified implementer eligibility per implementer-isolation.md.
- [ ] Reviewer verified all sources above are on the allowed-source list.

## Notes

- **Verify + close-test-gap + provenance, not a net-new build.** The card-appearance
  feature (per-field `hidden`/`order` field options that drive which fields render on
  the card face, the `card_cover_image_field` cover selection, and the "Customize cards"
  header link) already shipped in Story 3.1, which built the free-core Kanban view by
  mirroring the public MIT `GalleryViewType`. Story 3.3's work was: (1) verify every AC
  against the existing 3.1 code with line cites, (2) add the missing backend + frontend
  unit tests for the cover image field and the card-face field-visibility selection
  (the 3.1 test gap), (3) author the OSS-only E2E customize-cards scenario, and (4) add
  this provenance record. No new endpoint, serializer, view, handler, signal, model
  field, or migration was added; no production code was changed.
- **Two shared persistence paths, no Kanban-specific endpoint.** The card face is
  toggled through the generic `field_options` PATCH (shared by Grid/Gallery/Kanban), and
  the cover image field is set through the generic view PATCH carrying
  `card_cover_image_field`. There is intentionally no Kanban-specific field-options
  endpoint; the backend API test asserts the generic one persists and round-trips.
- **AC #3 — no row-coloring on the Kanban board.** `KanbanView.vue` passes no
  `decorationsByPlace` to `RowCard`, so no decorator components render. Decorations are
  component-driven with no fixed CSS class, so AC #3 is asserted at the unit level
  (RowCard receives no decorations) and only structurally in the E2E spec (the card
  renders its standard `.card__content` with no extra layer).
- **No premium/enterprise contamination.** Premium ships its own Kanban view with its
  own card-appearance implementation; it was **not** opened, read, grepped, or recalled
  at any point. Every source consulted is the free-core 3.1 Kanban, the MIT Gallery it
  mirrors, the shared card/field-options components, or public docs. The free core
  Kanban is the registered `kanban` view type only in OSS-only builds
  (`BASEROW_OSS_ONLY=true`); in a full open-core build premium's Kanban registers later
  and overrides it (last-registration-wins). All Story 3.3 tests therefore run OSS-only.
- **Clean-room test execution.** Backend tests run with `TEST_ENV_FILE=.env.oss-test`
  (22 passed) and frontend unit tests run in the OSS context with i18n mocked as in 3.1
  (33 passed). The E2E customize-cards scenario in
  `e2e-tests/tests/database/kanban_view.spec.ts` is authored to run in the OSS-only CI
  lane and is not run locally (requires the Docker stack).
