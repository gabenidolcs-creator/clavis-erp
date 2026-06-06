# Provenance record — Story 1.3 Role enforcement for Commenter and Viewer

- **PR / branch:** feat(story-1.3) role enforcement for Commenter and Viewer (branch: develop)
- **Story:** 1.3 Role enforcement for Commenter and Viewer
- **Bucket:** A (clean-room reimplement)
- **Implementer:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-06

## Sources Consulted

<!--
All sources below are on the allowed-source list (see ../allowed-sources.md):
public docs, public SaaS UI, public issues, and MIT free-core symbols in this repo.
No excluded paid (PE/EE) source was read, copied, adapted, or recalled.
-->

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | Public Baserow documentation — role-tier capabilities (Viewer read-only, Commenter read+comment) | public docs | https://baserow.io/docs |
| 2 | Public hosted Baserow SaaS UI — observable Viewer/Commenter deny-on-edit behavior | public SaaS UI | https://baserow.io |
| 3 | `BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS` — operation-`type`-string list convention (no class import) | MIT free-core | `backend/src/baserow/core/permission_manager.py` |
| 4 | `PermissionManagerType.check_multiple_permissions` contract (True=grant / exception=deny / absent=defer) | MIT free-core | `backend/src/baserow/core/registries.py` |
| 5 | `CoreHandler.check_permissions` re-raise + deny-by-default semantics | MIT free-core | `backend/src/baserow/core/handler.py` |
| 6 | `PermissionException` / `PermissionDenied` hierarchy | MIT free-core | `backend/src/baserow/core/exceptions.py` |
| 7 | `map_exceptions` / `apply_exception_mapping` / MRO resolution + `api_exception_registry` global merge | MIT free-core | `backend/src/baserow/api/utils.py`, `backend/src/baserow/api/registries.py`, `backend/src/baserow/api/decorators.py` |
| 8 | `ERROR_PERMISSION_DENIED` (401) error tuple shape | MIT free-core | `backend/src/baserow/api/errors.py` |
| 9 | Row / Field / View / Table operation `type` strings | MIT free-core | `backend/src/baserow/contrib/database/{rows,fields,views,table}/operations.py` |
| 10 | WebSocket subscribe path (`CoreConsumer`, `TablePageType.can_add`, `listen_to_all`) | MIT free-core | `backend/src/baserow/ws/consumers.py`, `backend/src/baserow/contrib/database/ws/pages.py` |
| 11 | Frontend permission-manager registry (deferring `hasPermission`) | MIT free-core | `web-frontend/modules/core/permissionManagerTypes.js` |
| 12 | Django / DRF framework documentation | general public knowledge | https://docs.djangoproject.com, https://www.django-rest-framework.org |

## Implementer Attestation

- [x] I affirm that this Bucket A reimplementation was produced **clean-room**: I did
      **not** read, copy, adapt, or rely on memory of any excluded paid (PE/EE) source
      for this feature, and I was not *influenced by* it. Every source I used is listed
      above and is on the allowed-source list.

**Implementer signature / handle:** AI dev-agent (isolation model (a))   **Date:** 2026-06-06

## Reviewer confirmation (filled at review)

- [ ] Reviewer verified implementer eligibility per implementer-isolation.md.
- [ ] Reviewer verified all sources above are on the allowed-source list.

## Notes

- **No migration / no model change.** Story 1.3 is pure enforcement logic layered over
  the Story 1.2 `RoleAssignment` model; nothing to roll back at the data level. Reverting
  the code restores the 1.2 grant-or-defer behavior (every member keeps write access).
- The enterprise role manager (`enterprise/backend/.../role/`) was **not** consulted; its
  DB-driven custom-role/operation-table model is not our fixed-tier design. Only the
  public MIT registry shape (a manager returning an exception to deny) was used.
