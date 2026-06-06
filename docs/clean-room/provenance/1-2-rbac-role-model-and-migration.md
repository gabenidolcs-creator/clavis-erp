# Provenance record — Story 1.2 RBAC role model and migration

- **PR / branch:** feat(story-1.2) RBAC role model and migration (branch: develop)
- **Story:** 1.2 RBAC role model and migration
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
| 1 | Public Baserow documentation — workspace/database roles and permission tiers | public docs | https://baserow.io/docs |
| 2 | Public hosted Baserow SaaS UI — observable Viewer/Commenter/Editor/Admin tiers | public SaaS UI | https://baserow.io |
| 3 | `PermissionManagerType` base + `permission_manager_type_registry` (registration shape) | MIT free-core | `backend/src/baserow/core/registries.py` |
| 4 | `BasicPermissionManagerType` / `WorkspaceMemberOnlyPermissionManagerType` (chain shape, admin-only set) | MIT free-core | `backend/src/baserow/core/permission_manager.py` |
| 5 | `WorkspaceUser` / `WorkspaceInvitation` permissions field (ADMIN/MEMBER) | MIT free-core | `backend/src/baserow/core/models.py` |
| 6 | `CoreHandler.check_multiple_permissions` chain algorithm (deny-by-default, defer with None) | MIT free-core | `backend/src/baserow/core/handler.py` |
| 7 | Reversible `RunPython(forward, reverse)` data-migration pattern | MIT free-core | `backend/src/baserow/core/migrations/0010_fix_trash_constraint.py` |
| 8 | Frontend permission-manager registry + `$registry.register('permissionManager', ...)` | MIT free-core | `web-frontend/modules/core/permissionManagerTypes.js`, `web-frontend/modules/core/plugin.js` |
| 9 | Django / DRF / Vue framework documentation | general public knowledge | https://docs.djangoproject.com |

## Implementer Attestation

- [x] I affirm that this Bucket A reimplementation was produced **clean-room**: I did
      **not** read, copy, adapt, or rely on memory of any excluded paid (PE/EE) source
      for this feature, and I was not *influenced by* it. Every source I used is listed
      above and is on the allowed-source list.

**Implementer signature / handle:** AI dev-agent (isolation model (a))   **Date:** 2026-06-06

## Reviewer confirmation (filled at review)

- [ ] Reviewer verified implementer eligibility per implementer-isolation.md.
- [ ] Reviewer verified all sources above are on the allowed-source list.

## Rollback (migration reversal)

The data migration `core/migrations/0115_rbac_roleassignment.py` is reversible:

- **Forward:** creates the `RoleAssignment` table, then derives one workspace-scoped
  `RoleAssignment` per existing `WorkspaceUser` — `ADMIN → Admin`, `MEMBER → Editor`.
  The legacy `WorkspaceUser.permissions` / `WorkspaceInvitation.permissions` fields are
  left untouched (invitations carry no user subject, so no assignment is derivable until
  acceptance — handled in a later story).
- **Reverse:** deletes all derived `RoleAssignment` rows, then drops the table. After
  reversal the system returns to the pre-1.2 ADMIN/MEMBER-only state with no data loss
  (the legacy permissions field was never modified).
- **Command:** `just b run python src/baserow/manage.py migrate core 0114` rolls back to
  the pre-1.2 state.
