# Behavior spec — Locked Views

- **Story / epic:** 1.7 Locked Views (Epic 1)
- **Bucket:** A (clean-room reimplement)
- **Author:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-06
- **Extends:** Story 1.6. Story 1.6 added personal views. This spec introduces
  view-level locking: an editor can lock a View's configuration so others cannot
  change filters, sorts, field options, decorations, or group-bys.

## 1. Allowed sources consulted

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | Public UX concept — "locking" a view config so shared "Master" layouts stay intact; similar to Google Sheets protected sheets | general public knowledge / product design | https://support.google.com/docs , baserow.io |
| 2 | `owned_by` FK + `ownership_type` CharField on `View` model | MIT free-core | `backend/src/baserow/contrib/database/views/models.py` |
| 3 | `_check_personal_view_access` helper pattern in `ViewHandler` | MIT free-core (this repo, Story 1.6) | `backend/src/baserow/contrib/database/views/handler.py` |
| 4 | `BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS` string-literal list | MIT free-core (this repo) | `backend/src/baserow/core/permission_manager.py` |
| 5 | `CoreHandler.check_permissions` | MIT free-core | `backend/src/baserow/core/handler.py` |
| 6 | `ViewOperationType` base class | MIT free-core | `backend/src/baserow/contrib/database/views/operations.py` |
| 7 | `UpdateViewSerializer` / `ViewSerializer` in DRF | MIT free-core | `backend/src/baserow/contrib/database/api/views/serializers.py` |
| 8 | Django `BooleanField(default=False)` | general public knowledge | https://docs.djangoproject.com |
| 9 | `map_exceptions` decorator pattern + `errors.py` error constant pattern | MIT free-core | `backend/src/baserow/contrib/database/api/views/errors.py`, `views.py` |
| 10 | Existing lock icon `iconoir-lock` in `ViewsContextItem.vue` | MIT free-core | `web-frontend/modules/database/components/view/ViewsContextItem.vue` |
| 11 | `$store.getters['auth/getUserId']` and `$hasPermission(...)` patterns in Vue components | MIT free-core | `web-frontend/modules/core/store/auth.js` |

> No excluded paid (PE/EE) source under `premium/` or `enterprise/` was read, copied,
> adapted, or recalled. This design is derived from first principles (a BooleanField +
> handler guard pattern mirroring the existing personal-view guard) and MIT free-core
> symbols only.

## 2. Observed behavior (UI / UX)

- An editor can **lock a View** by setting `locked=True`. They become the lock owner.
- While locked, only the **lock owner** or a **workspace Admin** can modify
  the view's configuration (filters, sorts, field options, decorations, group-bys).
- **Data within the view** (rows) remains editable per each member's Role.
- The lock owner or an Admin can **unlock** the view by setting `locked=False`.
- A **lock badge** (lock icon) appears next to the view name when it is locked.
- Non-owner/non-admin attempts to mutate config return an error.

## 3. Acceptance behavior (externally observable)

- **Lock acquisition:** PATCH view with `locked=True` → `owned_by` set to requesting
  user; response includes `locked: true`.
- **Config blocked for non-owner:** creating/updating/deleting filters, sorts, field
  options, decorations, or group-bys on a locked view by a non-owner non-admin
  returns `ERROR_VIEW_IS_LOCKED` (HTTP 400).
- **Owner unblocked:** lock owner and workspace admin can perform all config mutations.
- **Unlock:** PATCH with `locked=False` by owner or admin succeeds.
- **Row mutations unaffected:** rows remain editable per Role regardless of lock state.
- **UI:** lock icon visible when `view.locked === true`.

## 4. Free-core (MIT) symbols built on

- `View` model — new `locked = BooleanField(default=False)` field.
- `owned_by` FK (existing `created_by_id` column) — reused to store lock owner.
- `_check_personal_view_access` pattern — mirrored as `_check_locked_view_config_access`.
- `UpdateLockedViewConfigOperationType` — new operation type, type string
  `"database.table.view.update_locked_config"`.
- `BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS` — string literal added.
- `ViewIsLockedException` — new exception in `exceptions.py`.
- `ViewSerializer.locked` (read-only), `UpdateViewSerializer.locked` (writable).
- `ViewsContextItem.vue` — lock badge icon + `isLockedForCurrentUser` computed.

## 5. Self-check (must all be true)

- [x] Every source in §1 is on the allowed-source list (no `premium/`/`enterprise/`).
- [x] No `premium/`/`enterprise/` internal symbol is named as the thing to replicate.
- [x] This spec captures behavior/UI only, not code adapted from PE/EE source.
