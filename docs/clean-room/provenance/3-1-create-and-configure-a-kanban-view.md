# Provenance record — Story 3.1 Create and Configure a Kanban View

- **PR / branch:** feat(story-3.1) create and configure a kanban view (branch: develop)
- **Story:** 3.1 Create and Configure a Kanban View
- **Bucket:** A (clean-room reimplement)
- **Implementer:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-09

## Sources Consulted

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | Public Airtable/Baserow "Kanban" UX — cards grouped into columns by a single-select field, with an "Uncategorized" column for rows that have no value | public SaaS UI / public docs | https://baserow.io/docs , https://airtable.com |
| 2 | `GalleryView` model (`card_cover_image_field` FK, buffered-row view shape) — reference for the analogous Kanban model | MIT free-core | `backend/src/baserow/contrib/database/views/models.py` |
| 3 | `GalleryViewType` — registration shape, `field_options`, `after_field_delete`, allowed view operations | MIT free-core | `backend/src/baserow/contrib/database/views/view_types.py` |
| 4 | `SingleSelectField` / `SingleSelectFieldType` + `SelectOption` model (the grouping field and its options) | MIT free-core | `backend/src/baserow/contrib/database/fields/models.py`, `fields/field_types.py` |
| 5 | `ViewType` base class + `view_type_registry` registration pattern | MIT free-core | `backend/src/baserow/contrib/database/views/registries.py`, `apps.py` |
| 6 | `BASEROW_OSS_ONLY` / `INSTALLED_APPS` gating — used to keep the free Kanban active only when the premium plugin is absent | MIT free-core | `backend/src/baserow/config/settings/base.py` |
| 7 | Frontend `GalleryView.vue`, `GalleryViewHeader.vue`, gallery store/service (`store/view/gallery.js`, `services/view/gallery.js`) — reference for the buffered-row board components and Vuex module | MIT free-core | `web-frontend/modules/database/components/view/gallery/`, `store/view/gallery.js`, `services/view/gallery.js` |
| 8 | Frontend `GalleryViewType` (viewTypes.js), `plugin.js` / `plugin/store.js` registration (last-registration-wins) | MIT free-core | `web-frontend/modules/database/viewTypes.js`, `plugin.js`, `plugin/store.js` |
| 9 | `ChooseSingleSelectField`, `ViewFieldsContext`, `ViewSearch`, `RowCard`, `RowEditModal` shared components | MIT free-core | `web-frontend/modules/database/components/` |
| 10 | `bufferedRows` Vuex helper + `bufferedRowService` | MIT free-core | `web-frontend/modules/database/store/view/bufferedRows.js`, `services/view/bufferedRows.js` |
| 11 | Django ORM `update()` / FK `SET_NULL` soft-delete (trash) behavior — basis for explicitly nulling the grouping FK in `after_field_delete` | general public knowledge | https://docs.djangoproject.com |

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

- **Built from the public MIT Gallery template.** Kanban = Gallery + a `single_select_field`
  grouping FK. The premium Kanban view under `premium/` was **not** read, opened, or
  recalled at any point. The grouping/column model was derived from the public
  Airtable/Baserow Kanban UX and the free-core Gallery view shape only.
- **Premium-precedence guard (no premium files touched).** The core Kanban registers
  in both backend (`view_type_registry`, gated by
  `if "baserow_premium" not in settings.INSTALLED_APPS`) and frontend (last-registration-
  wins). In an open-core build that ships premium, premium's Kanban overrides core; the
  free core Kanban is the active view type only in OSS-only builds
  (`BASEROW_OSS_ONLY=true`). No `premium/` or `enterprise/` file was modified.
- **Soft-delete handling.** Field deletion is a trash (soft delete), so the
  `single_select_field` FK `SET_NULL` does not fire automatically; `after_field_delete`
  explicitly nulls `single_select_field_id` (and `card_cover_image_field_id`).
- **Clean-room test execution.** Backend and frontend tests run in OSS-only mode
  (`TEST_ENV_FILE=.env.testing-cleanroom`, `BASEROW_OSS_ONLY=true`) so the free core
  Kanban is the registered view type under test. The E2E spec
  (`e2e-tests/tests/database/kanban_view.spec.ts`) is authored to run in the OSS-only
  CI lane and is not run locally.
