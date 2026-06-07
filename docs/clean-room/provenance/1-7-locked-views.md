# Provenance record — Story 1.7 Locked Views

- **PR / branch:** feat(story-1.7) locked views (branch: develop)
- **Story:** 1.7 Locked Views
- **Bucket:** A (clean-room reimplement)
- **Implementer:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-06

## Sources Consulted

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | Public UX concept — locking a view configuration to protect a shared "Master" layout | general public knowledge / product design | https://support.google.com/docs |
| 2 | `owned_by` FK (existing `created_by_id` column), `ownership_type` CharField on `View` model | MIT free-core | `backend/src/baserow/contrib/database/views/models.py` |
| 3 | `_check_personal_view_access` helper pattern (Story 1.6) | MIT free-core (this repo) | `backend/src/baserow/contrib/database/views/handler.py` |
| 4 | `BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS` — string-literal extension pattern | MIT free-core (this repo) | `backend/src/baserow/core/permission_manager.py` |
| 5 | `CoreHandler.check_permissions`, `PermissionDenied` from `baserow.core.exceptions` | MIT free-core | `backend/src/baserow/core/handler.py`, `backend/src/baserow/core/exceptions.py` |
| 6 | `ViewOperationType` base class | MIT free-core | `backend/src/baserow/contrib/database/views/operations.py` |
| 7 | `ViewSerializer` + `UpdateViewSerializer` — field extension pattern | MIT free-core | `backend/src/baserow/contrib/database/api/views/serializers.py` |
| 8 | `errors.py` error-constant pattern + `map_exceptions` decorator | MIT free-core | `backend/src/baserow/contrib/database/api/views/errors.py`, `views.py` |
| 9 | Django `BooleanField(default=False)` + `AddField` migration pattern | general public knowledge | https://docs.djangoproject.com |
| 10 | Lock icon (`iconoir-lock`) in `ViewsContextItem.vue` | MIT free-core | `web-frontend/modules/database/components/view/ViewsContextItem.vue` |
| 11 | `$store.getters['auth/getUserId']` + `$hasPermission(...)` Vue patterns | MIT free-core | `web-frontend/modules/core/store/auth.js` |

## Implementer Attestation

- [x] I affirm that this Bucket A reimplementation was produced **clean-room**: I did
      **not** read, copy, adapt, or rely on memory of any `premium/` or `enterprise/`
      (PE/EE) source for this feature, and I was not *influenced by* it. Every source I
      used is listed above and is on the allowed-source list.

**Implementer signature / handle:** AI dev-agent (isolation model (a))   **Date:** 2026-06-06

## Reviewer confirmation (filled at review)

- [ ] Reviewer verified implementer eligibility per implementer-isolation.md.
- [ ] Reviewer verified all sources above are on the allowed-source list.

## Notes

- **Migration:** `0214_view_locked.py` — simple `AddField` on `database_view`, `locked
  BooleanField(default=False)`. No data migration needed.
- **No new permission manager.** `_check_locked_view_config_access` is a `ViewHandler`
  helper (same pattern as `_check_personal_view_access` from Story 1.6), not a new
  manager class. Keeps the architecture simple per D14.
- **Admin bypass via `ADMIN_ONLY_OPERATIONS`.** String literal
  `"database.table.view.update_locked_config"` added to `BasicPermissionManagerType`
  so workspace admins pass the `CoreHandler.check_permissions` check inside the helper.
- **Lock owner = existing `owned_by` FK.** No new FK needed — `create_view()` already
  sets `owned_by = user`; lock acquisition overwrites it to the locking user.
- **Row mutations unguarded by design.** `create_row`, `update_row`, `delete_row` live
  in `rows/handler.py` and are entirely separate from view config. AC1 explicitly
  states data remains editable per Role.
- **`delete_view()` unguarded by design.** Locking is a config concept, not a
  lifecycle concept. Existing `DeleteViewOperationType` check is sufficient.
- **Error maps to HTTP 400** (`ERROR_VIEW_IS_LOCKED`) to be consistent with other
  view-layer validation errors in Baserow (personal view uses 401 via `PermissionDenied`;
  locked view raises a custom `ViewIsLockedException` to distinguish the two concepts).
