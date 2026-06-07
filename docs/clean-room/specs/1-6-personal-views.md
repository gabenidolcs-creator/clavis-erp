# Behavior spec — Personal Views

- **Story / epic:** 1.6 Personal Views (Epic 1)
- **Bucket:** A (clean-room reimplement)
- **Author:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-06
- **Extends:** Story 1.5. Story 1.5 added field-visibility hiding. This spec introduces
  view-level ownership: a member can mark a View as **Personal** so only they can see
  it, while others see only collaborative views.

## 1. Allowed sources consulted

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | Public Airtable/Baserow "Personal View" UX — a user can mark a view private so only they see it in the view list; other members do not see it and cannot access it by ID | public SaaS UI / public docs | https://baserow.io/docs , https://airtable.com |
| 2 | `OWNERSHIP_TYPE_COLLABORATIVE = "collaborative"`, `owned_by` FK, `ownership_type` CharField already on `View` model | MIT free-core | `backend/src/baserow/contrib/database/views/models.py` |
| 3 | `ViewOwnershipType` base class + `ViewOwnershipTypeRegistry` | MIT free-core | `backend/src/baserow/contrib/database/views/registries.py` |
| 4 | `CollaborativeViewOwnershipType` — the existing collaborative-view type implementation | MIT free-core | `backend/src/baserow/contrib/database/views/view_ownership_types.py` |
| 5 | `CreateAndUsePersonalViewOperationType` (`database.table.create_and_use_personal_view`) — pre-existing operation | MIT free-core | `backend/src/baserow/contrib/database/views/operations.py` |
| 6 | `ViewHandler.list_views` / `get_view_as_user` — handler methods extended for personal-view enforcement | MIT free-core | `backend/src/baserow/contrib/database/views/handler.py` |
| 7 | `CoreHandler.check_permissions` / `filter_queryset` | MIT free-core | `backend/src/baserow/core/handler.py` |
| 8 | Django Q objects (`~Q(...)`, `Q(... & ...)`) — ORM queryset filter pattern | general public knowledge | https://docs.djangoproject.com |
| 9 | Frontend `ViewOwnershipType` base class + `CollaborativeViewOwnershipType` | MIT free-core | `web-frontend/modules/database/viewOwnershipTypes.js` |
| 10 | Frontend plugin.js `viewOwnershipType` registry registration pattern | MIT free-core | `web-frontend/modules/database/plugin.js` |
| 11 | RbacPermissionManagerType (Story 1.2), FieldPermissionManagerType (Story 1.4) — existing permission manager chain | MIT free-core (this repo) | `backend/src/baserow/core/rbac/permission_manager.py`, `backend/src/baserow/core/field_permissions/permission_manager.py` |

> No excluded paid (PE/EE) source under `premium/` or `enterprise/` was read, copied,
> adapted, or recalled. The premium module implements `PersonalViewOwnershipType` and
> a `ViewOwnershipPermissionManagerType` with license gates. Our design is derived from
> the publicly observable behavior (a view can be hidden from other members) and built
> on MIT free-core symbols only. No premium symbols are used or replicated.

## 2. Observed behavior (UI / UX)

- A member can **mark a View as Personal** when creating or updating it.
- A Personal View is **invisible to all other members**: it does not appear in their
  view list, and a direct fetch by ID returns a permission error (IDOR guard).
- The **owner** sees their Personal View normally.
- The owner can **toggle the view back to Collaborative** at any time, after which it
  becomes visible to all members with access to the table.
- Personal Views work across **all View Types**: grid, kanban, calendar, gallery, etc.
- Creating a Personal View requires `CreateAndUsePersonalViewOperationType` permission.

## 3. Acceptance behavior (externally observable)

- **List views** for a non-owner does **not** include another member's personal view.
- **GET view by ID** for a non-owner returns permission error (no IDOR).
- **Owner** can list and fetch their own personal view normally.
- **Toggle to collaborative** makes the view visible to all members.
- **Creating** a personal view sets `owned_by = requesting user`.

## 4. Free-core (MIT) symbols built on

- `ViewOwnershipType` base class — extended to create `PersonalViewOwnershipType`.
- `view_ownership_type_registry.register(...)` — registration in `apps.py`.
- `ViewHandler.list_views` queryset filter — `~Q(ownership_type='personal') | Q(owned_by=user)`.
- `ViewHandler.get_view_as_user` IDOR guard — `PermissionDenied` if non-owner.
- `CreateAndUsePersonalViewOperationType` — checked in `change_ownership_type`.
- Frontend `ViewOwnershipType` base + plugin registry.

## 5. Self-check (must all be true)

- [x] Every source in §1 is on the allowed-source list (no `premium/`/`enterprise/`).
- [x] No `premium/`/`enterprise/` internal symbol is named as the thing to replicate.
- [x] This spec captures behavior/UI only, not code adapted from PE/EE source.
