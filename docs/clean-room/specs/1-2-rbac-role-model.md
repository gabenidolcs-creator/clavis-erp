# Behavior spec — RBAC fixed-tier role model (workspace + database scope)

- **Story / epic:** 1.2 RBAC role model and migration (Epic 1)
- **Bucket:** A (clean-room reimplement)
- **Author:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-06

## 1. Allowed sources consulted

| # | Source | Type (public docs / public SaaS UI / public issue / MIT free-core) | Link / location |
|---|--------|--------------------------------------------------------------------|-----------------|
| 1 | Public Baserow documentation on workspace/database roles and permission tiers | public docs | https://baserow.io/docs |
| 2 | Observable role tiers in the public hosted Baserow SaaS (Viewer / Commenter / Editor / Admin) | public SaaS UI | https://baserow.io |
| 3 | `PermissionManagerType` base class + `permission_manager_type_registry` (registration shape, abstract `check_multiple_permissions`) | MIT free-core | `backend/src/baserow/core/registries.py` |
| 4 | `BasicPermissionManagerType` / `WorkspaceMemberOnlyPermissionManagerType` (chain shape, `ADMIN_ONLY_OPERATIONS`, `permissions == "ADMIN"` model) | MIT free-core | `backend/src/baserow/core/permission_manager.py` |
| 5 | `WorkspaceUser` / `WorkspaceInvitation` `permissions` CharField (ADMIN/MEMBER) and `WORKSPACE_USER_PERMISSION_*` constants | MIT free-core | `backend/src/baserow/core/models.py` |
| 6 | `CoreHandler.check_multiple_permissions` chain algorithm (deny-by-default, defer with `None`) | MIT free-core | `backend/src/baserow/core/handler.py` |
| 7 | Reversible data-migration pattern `RunPython(forward, reverse)` with `apps.get_model(...)` | MIT free-core | `backend/src/baserow/core/migrations/0010_fix_trash_constraint.py` |
| 8 | Frontend `permissionManagerTypes.js` registry + `$registry.register('permissionManager', ...)` | MIT free-core | `web-frontend/modules/core/permissionManagerTypes.js`, `web-frontend/modules/core/plugin.js` |
| 9 | Django / DRF / Vue framework documentation | general public knowledge | https://docs.djangoproject.com, https://www.django-rest-framework.org |

## 2. Observed behavior (UI / UX)

A workspace member can hold one of four ordered role tiers, observable in the public
product:

- **Viewer** — read-only access.
- **Commenter** — read + comment.
- **Editor** — read + write content (the today's "member" capability).
- **Admin** — full workspace management (the today's "ADMIN" capability).

Capability ordering: **Admin > Editor > Commenter > Viewer**. A role is assignable at
**workspace** scope and at the more specific **database** scope; the most specific
assignment wins (a database-level role overrides the workspace-level role for that
database). The fixed tiers are not user-editable (no custom-role builder).

Story 1.2 establishes only the *model and assignability*; it does NOT yet tighten
enforcement (Commenter/Viewer 403 denial is Story 1.3). Today, a workspace has only
ADMIN/MEMBER; after migration every existing member keeps the exact write capability
they had.

## 3. Acceptance behavior

- Four fixed roles (Viewer / Commenter / Editor / Admin) exist as code constants with a
  documented capability ordering Admin > Editor > Commenter > Viewer.
- A role is assignable to a member at **workspace** scope and at **database** scope; the
  most specific scope wins.
- Role authorization resolves through a new permission manager registered into the
  existing permission-manager chain — never via an ad-hoc/parallel path.
- Migration maps existing **ADMIN → Admin** and **MEMBER → Editor** (never to
  Viewer/Commenter — no silent write loss); the legacy ADMIN/MEMBER field is preserved,
  not rewritten.
- The migration is reversible (`RunPython(forward, reverse)`) with a documented rollback.
- Every pre-migration member retains equivalent **write** capability after migration.
- Role-assignment management is restricted to workspace admins; unauthorized callers get
  403.

## 4. Free-core (MIT) symbols to build on

- `PermissionManagerType` (abstract base), `permission_manager_type_registry`,
  `operation_type_registry` — `backend/src/baserow/core/registries.py`.
- `BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS` (reused to preserve current
  admin-only behavior) — `backend/src/baserow/core/permission_manager.py`.
- `UserSubjectType` — `backend/src/baserow/core/subjects.py`.
- `CreatedAndUpdatedOnMixin` — `backend/src/baserow/core/mixins.py`.
- Frontend `PermissionManagerType` (Registerable) — `web-frontend/modules/core/permissionManagerTypes.js`.

## 5. Self-check (must all be true)

- [x] Every source in §1 is on the allowed-source list (no excluded paid source, no
      paid-instance internals, no memory of the paid product).
- [x] No excluded internal symbol is named as the thing to replicate (only public
      behavior + free-core MIT symbols).
- [x] This spec captures behavior/UI only, not code adapted from excluded source.
