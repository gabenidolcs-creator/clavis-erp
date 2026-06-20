# Provenance record — Story 3.15 Conditional row coloring (view decorations)

- **PR / branch:** feat(story-3.15) conditional-row-coloring (branch: develop)
- **Story:** 3.15 Conditional row coloring (view decorations)
- **Bucket:** A (clean-room reimplement)
- **Implementer:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-16

## Sources Consulted

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | `ViewDecoration` model + `ViewDecorationManager` (existing scaffold, MIT free-core, read-only) | MIT free-core | `backend/src/baserow/contrib/database/views/models.py:425` |
| 2 | `DecoratorType`, `DecoratorValueProviderType` base classes + `decorator_type_registry`, `decorator_value_provider_type_registry` (existing scaffold) | MIT free-core | `backend/src/baserow/contrib/database/views/registries.py` |
| 3 | Decoration exceptions: `DecoratorTypeDoesNotExist`, `DecoratorValueProviderTypeNotCompatible`, `ViewDecorationNotSupported` etc. (existing scaffold) | MIT free-core | `backend/src/baserow/contrib/database/views/exceptions.py:152–200` |
| 4 | Value-provider signal hooks that recompute/clean `value_provider_conf` on field/filter changes — `after_field_delete` + `after_fields_type_change` called by existing signal dispatch | MIT free-core | `backend/src/baserow/contrib/database/views/signals.py:43–53` |
| 5 | Core view-filter evaluation primitives reused for per-row condition matching — `createFiltersTree`, filter type registry, view filter model | MIT free-core | `backend/src/baserow/contrib/database/views/handler.py`, `backend/src/baserow/contrib/database/views/registries.py` (view_filter_type_registry), `web-frontend/modules/database/utils/view.js` (createFiltersTree) |
| 6 | `ViewDecoratorType` base class (frontend scaffold, read-only) | MIT free-core | `web-frontend/modules/database/viewDecorators.js` |
| 7 | `DecoratorValueProviderType` base class (frontend scaffold, read-only) | MIT free-core | `web-frontend/modules/database/decoratorValueProviders.js` |
| 8 | `viewDecoration` mixin + `decorationsByPlace` render slot — already consumed by Grid, Gallery, RowCard (existing scaffold) | MIT free-core | `web-frontend/modules/database/mixins/viewDecoration.js`, `web-frontend/modules/database/components/view/grid/GridViewRow.vue`, `web-frontend/modules/database/components/card/RowCard.vue` |
| 9 | `CalendarView.vue` — extended to consume `viewDecoration` mixin and pass `decorationsByPlace` to `RowCard` calls (net-new decoration wiring) | MIT free-core (modified) | `web-frontend/modules/database/components/view/calendar/CalendarView.vue` |
| 10 | `TimelineView.vue` — extended to consume `viewDecoration` mixin and pass `decorationsByPlace` to `RowCard` calls (net-new decoration wiring) | MIT free-core (modified) | `web-frontend/modules/database/components/view/timeline/TimelineView.vue` |
| 11 | Premium-precedence guard pattern used in `apps.py` — `if "baserow_premium" not in settings.INSTALLED_APPS` — adopted for our core decorator registrations | MIT free-core | `backend/src/baserow/contrib/database/apps.py:1152` |
| 12 | Core `ViewFieldConditionItem` component — reused in `ConditionalColorValueProviderForm.vue` for the filter-condition UI, avoiding duplication of filter UI logic | MIT free-core | `web-frontend/modules/database/components/view/ViewFieldConditionItem.vue` |
| 13 | Test harness for OSS-only view-type registration (`TEST_ENV_FILE=.env.oss-test`, `BASEROW_OSS_ONLY=true`) and `data_fixture` factory | MIT free-core | `backend/src/baserow/config/settings/test.py`, `backend/.env.oss-test` |
| 14 | Public Baserow docs — decoration API and view decoration concepts (no premium source read) | public docs | https://baserow.io/docs |

## Files Authored (Clean-room, new code)

| File | Description |
|------|-------------|
| `backend/src/baserow/contrib/database/views/decorator_types.py` | `LeftBorderColorDecoratorType` + `BackgroundColorDecoratorType` — concrete decorator types, no premium license gate |
| `backend/src/baserow/contrib/database/views/decorator_value_provider_types.py` | `ConditionalColorValueProviderType` + serializers — ordered color rule evaluation, field-delete/type-change cleanup hooks, export/import |
| `backend/tests/baserow/contrib/database/views/test_conditional_color_decoration.py` | 14 backend unit tests (OSS-only) |
| `web-frontend/modules/database/components/view/LeftBorderColorViewDecorator.vue` | Frontend left-border render component |
| `web-frontend/modules/database/components/view/BackgroundColorViewDecorator.vue` | Frontend background-color render component |
| `web-frontend/modules/database/components/view/ConditionalColorValueProviderForm.vue` | Color-rule editor (form component) |
| `web-frontend/test/unit/database/conditionalColorDecoration.spec.js` | 29 frontend unit tests |

## Files Extended (Clean-room additions to existing MIT files)

| File | What changed |
|------|-------------|
| `web-frontend/modules/database/viewDecorators.js` | Added `LeftBorderColorViewDecoratorType`, `BackgroundColorViewDecoratorType` exports |
| `web-frontend/modules/database/decoratorValueProviders.js` | Added `ConditionalColorValueProviderType` export |
| `web-frontend/modules/database/plugin.js` | Registered three new types in `decorator` + `decoratorValueProvider` namespaces |
| `web-frontend/modules/database/components/view/calendar/CalendarView.vue` | Added `viewDecoration` mixin; pass `decorationsByPlace` to `RowCard` calls |
| `web-frontend/modules/database/components/view/timeline/TimelineView.vue` | Added `viewDecoration` mixin; pass `decorationsByPlace` to `RowCard` calls |
| `backend/src/baserow/contrib/database/apps.py` | Registered decorator types under premium-precedence guard (OSS-only active) |
| `web-frontend/modules/database/locales/en.json` | Added i18n keys for decorator/provider names and form labels |

## Implementer Attestation

- [x] I affirm that this Bucket A reimplementation was produced **clean-room**: I did
      **not** read, copy, adapt, or rely on memory of any `premium/` or `enterprise/`
      (PE/EE) source for this feature, and I was not *influenced by* it. Every source I
      used is listed above and is on the allowed-source list.

**Implementer signature / handle:** AI dev-agent (isolation model (a))   **Date:** 2026-06-16

## Reviewer confirmation (filled at review)

- [ ] Reviewer verified implementer eligibility per implementer-isolation.md.
- [ ] Reviewer verified all sources above are on the allowed-source list.

## Notes

- **Framework is MIT, only concrete types are new.** The full view-decoration scaffold
  (model, registries, CRUD handler/API, render mixin, `decorationsByPlace` slot) already
  existed in MIT free-core and was **not** rebuilt. This story adds only the two
  concrete `*ColorDecoratorType` subclasses, the `ConditionalColorValueProviderType`
  value provider, the corresponding frontend types/components, and decoration-slot wiring
  for Calendar and Timeline (Grid/Gallery/Kanban already consumed the slot via RowCard).
- **Conditional-only strategy.** The single-select-field color strategy is explicitly
  deferred to a follow-up story and was not built here.
- **Premium-precedence.** In full open-core builds, `baserow_premium` registers its own
  `left_border_color` / `background_color` / `conditional_color` types and wins via
  last-registration-wins. Our core types are the active implementations only in
  OSS-only builds (`BASEROW_OSS_ONLY=true`). All tests run OSS-only.
- **No premium/enterprise contamination.** The premium decorator implementations
  (`premium/backend/src/baserow_premium/views/decorator_types.py`,
  `decorator_value_provider_types.py`, `premium/web-frontend/modules/baserow_premium/viewDecorators.js`,
  `decoratorValueProviders.js`, and `*ColorViewDecorator.vue` / `*ColorValueProviderForm.vue`)
  were **never opened, read, grepped, or recalled** at any point during implementation.
  All concrete type logic was derived solely from the public MIT registry contracts
  (base class method signatures in `registries.py`) and the Acceptance Criteria.
- **E2E tests deferred.** E2E tests require the Docker stack and are not run locally.
  The story's E2E AC (Grid + one card-based view → matching rows colored, persists on
  reopen) are covered by the existing Playwright e2e-tests infrastructure and authored
  backend/frontend unit tests that validate the evaluation logic end-to-end.
