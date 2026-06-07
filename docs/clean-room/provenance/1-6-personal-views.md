# Provenance record — Story 1.6 Personal Views

- **PR / branch:** feat(story-1.6) personal views (branch: develop)
- **Story:** 1.6 Personal Views
- **Bucket:** A (clean-room reimplement)
- **Implementer:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-06

## Sources Consulted

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | Public Airtable/Baserow "Personal View" UX — a user marks a view private so only they see it | public SaaS UI / public docs | https://baserow.io/docs , https://airtable.com |
| 2 | `OWNERSHIP_TYPE_COLLABORATIVE`, `owned_by` FK, `ownership_type` CharField on `View` model | MIT free-core | `backend/src/baserow/contrib/database/views/models.py` |
| 3 | `ViewOwnershipType` base class interface + `ViewOwnershipTypeRegistry` | MIT free-core | `backend/src/baserow/contrib/database/views/registries.py` |
| 4 | `CollaborativeViewOwnershipType` — reference for implementation pattern | MIT free-core | `backend/src/baserow/contrib/database/views/view_ownership_types.py` |
| 5 | `CreateAndUsePersonalViewOperationType` (`database.table.create_and_use_personal_view`) | MIT free-core | `backend/src/baserow/contrib/database/views/operations.py` |
| 6 | `ViewHandler.list_views` + `get_view_as_user` — handler methods extended | MIT free-core | `backend/src/baserow/contrib/database/views/handler.py` |
| 7 | `CoreHandler.check_permissions` / `PermissionDenied` from `baserow.core.exceptions` | MIT free-core | `backend/src/baserow/core/handler.py`, `backend/src/baserow/core/exceptions.py` |
| 8 | Django ORM Q-filter pattern | general public knowledge | https://docs.djangoproject.com |
| 9 | Frontend `ViewOwnershipType` base class + `CollaborativeViewOwnershipType` | MIT free-core | `web-frontend/modules/database/viewOwnershipTypes.js` |
| 10 | Frontend plugin.js registration pattern | MIT free-core | `web-frontend/modules/database/plugin.js` |

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

- **No migration needed.** `owned_by` FK and `ownership_type` CharField already exist
  from migrations `0098_view_ownership_type.py` / `0099_alter_view_ownership_type.py`.
- **No new permission manager.** Architecture D14 specifies ViewHandler as the
  enforcement point. The personal-view list-filter and IDOR guard are implemented
  directly in `ViewHandler.list_views()` and `get_view_as_user()`.
- **`OWNERSHIP_TYPE_PERSONAL = "personal"` moved to free-core** `views/models.py`
  (alongside `OWNERSHIP_TYPE_COLLABORATIVE`) so it is available without the premium
  module.
- **`VIEW_OWNERSHIP_TYPES` list updated** to include `"personal"`.
- **`PersonalViewOwnershipType`** class added to `view_ownership_types.py` and
  registered in `apps.py` — no license gate (personal views are free-tier, Bucket A).
- **IDOR guard raises `PermissionDenied`** → maps to HTTP 401 via the global
  `PermissionException → ERROR_PERMISSION_DENIED` catch in `api/decorators.py`.
