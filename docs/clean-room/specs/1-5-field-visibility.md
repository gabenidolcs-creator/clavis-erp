# Behavior spec — Field visibility hiding, inference-oracle guard, and cache invalidation

- **Story / epic:** 1.5 Field visibility hiding, inference-oracle guard, and cache invalidation (Epic 1)
- **Bucket:** A (clean-room reimplement)
- **Author:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-06
- **Extends:** [1-4-field-edit-restriction.md](1-4-field-edit-restriction.md). Story 1.4
  added the **edit-restriction** half of the central field-permission layer (a field is
  read-only to lower roles but still fully readable). This spec adds the
  **read-redaction / visibility** half on the *same* rule row and *same* permission
  manager: a field can be made **invisible** to lower roles across every read surface,
  cannot be filtered or sorted on by those roles (inference-oracle guard), and a
  visibility change takes effect on live sessions without a reconnect.

## 1. Allowed sources consulted

| # | Source | Type (public docs / public SaaS UI / public issue / MIT free-core) | Link / location |
|---|--------|--------------------------------------------------------------------|-----------------|
| 1 | Public Airtable/Baserow field-permission UX — an admin can hide an individual field from lower-privileged members so they never see its values (a "hidden field" / field-level visibility control), while higher roles see it | public SaaS UI / public docs | https://baserow.io/docs , https://airtable.com (observable behavior only) |
| 2 | `ReadFieldOperationType` (`"database.table.field.read"`) — the per-field read operation already defined in free core | MIT free-core | `backend/src/baserow/contrib/database/fields/operations.py` |
| 3 | `PermissionManagerType.filter_queryset(actor, operation_name, queryset, workspace)` and `get_permissions_object(actor, workspace)` — public manager contract for redaction and frontend permission payloads | MIT free-core | `backend/src/baserow/core/registries.py` |
| 4 | `CoreHandler.filter_queryset` dispatch — successively applies each manager's `filter_queryset` (None = defer) | MIT free-core | `backend/src/baserow/core/handler.py` |
| 5 | `get_row_serializer_class(model, field_ids=..., exclude_field_ids=...)` — the include/exclude filter already used to drop fields from a row payload; `exclude` overrides `include` | MIT free-core | `backend/src/baserow/contrib/database/api/rows/serializers.py` |
| 6 | `get_hidden_field_ids_for_view_user` — the view-ownership hidden-field set already unioned into `exclude_field_ids` on row reads | MIT free-core | `backend/src/baserow/contrib/database/api/views/utils.py` |
| 7 | `search_all_fields(..., only_search_by_field_ids=...)` — the table-model search already restricts which fields are searched | MIT free-core | `backend/src/baserow/contrib/database/table/models.py` |
| 8 | `ViewHandler.create_sort` already checks `ReadFieldOperationType` before creating a sort; `create_filter` does not — the asymmetry the guard closes | MIT free-core | `backend/src/baserow/contrib/database/views/handler.py` |
| 9 | `TablePageType.can_add` / `RowPageType.can_add` — subscribe-time WS authorization via `ListenToAllDatabaseTableEventsOperationType` | MIT free-core | `backend/src/baserow/contrib/database/ws/pages.py` |
| 10 | `invalidate_table_in_model_cache(table_id)` — the model-cache invalidation hook already called on field save | MIT free-core | `backend/src/baserow/contrib/database/table/cache.py` |
| 11 | `permissions_updated` signal + per-table permission-channel-group broadcast (`get_permission_channel_group_name`, `users_removed_from_permission_group`, `send_message_to_channel_group`) — the existing live-session re-evaluation mechanism | MIT free-core | `backend/src/baserow/core/signals.py`, `backend/src/baserow/contrib/database/table/tasks.py`, `backend/src/baserow/ws/consumers.py` |
| 12 | `FieldPermission` model + `FieldPermissionManagerType` + `FieldPermissionHandler` + `FieldEditProhibitedError → ERROR_FIELD_EDIT_PROHIBITED → core/apps.py` global 403 registration (Story 1.4, this repo) — extended here | MIT free-core (this repo, Story 1.4) | `backend/src/baserow/contrib/database/fields/models.py`, `backend/src/baserow/core/field_permissions/`, `backend/src/baserow/core/exceptions.py`, `backend/src/baserow/core/apps.py`, `backend/src/baserow/api/errors.py` |
| 13 | `RbacHandler.get_effective_role`, `roles.role_at_least` / `ROLE_ORDER` (Story 1.2) — effective-role resolution reused | MIT free-core (this repo, Story 1.2) | `backend/src/baserow/core/rbac/handler.py`, `roles.py` |
| 14 | Frontend `PermissionManagerType` base + `$hasPermission` chain + 1.4 `FieldPermissionManagerType` | MIT free-core | `web-frontend/modules/core/permissionManagerTypes.js` |
| 15 | Django / DRF framework documentation | general public knowledge | https://docs.djangoproject.com , https://www.django-rest-framework.org |

> No excluded paid (PE/EE) source under `premium/` or `enterprise/` was read, copied,
> adapted, or recalled. The enterprise field-permissions feature uses a DB-driven
> `FieldPermissions` model with a `FieldPermissionsRoleEnum`, a custom-subject
> allow/deny system, an anonymous-value submission path, and a multi-operation
> `get_permissions_object` payload — that design is **not** ours. Our design is a
> **fixed-tier minimum-role `readable_by_role` threshold** on the existing 1.4 rule row,
> derived purely from the publicly observable behavior (a field can be hidden from lower
> roles), built on the public MIT registry shape only.

## 2. Observed behavior (UI / UX)

- An **admin** can mark an individual field **hidden** by choosing the **minimum role**
  allowed to *see* that field (e.g. "only Admins may see Salary").
- Members **below** that threshold never receive the field's value on **any** read
  surface: it is absent from every view, from row list/get over REST, from search
  results, and from real-time (WebSocket) row payloads. The column simply does not
  appear for them.
- Because the value is invisible, those members also **cannot filter or sort** on the
  field — attempting to do so is rejected — since the presence/absence, count, or order
  of matching rows would otherwise leak the hidden value (an inference oracle).
- Members **at or above** the threshold see and use the field exactly as before.
- Hiding is **independent of** edit-restriction (1.4): a field can be visible but
  read-only, hidden, or unrestricted. Absence of a visibility threshold = visible to
  all (the pre-1.5 default).
- When an admin **changes** a field's visibility, the change applies to **live
  sessions** — a member who could see the field a moment ago stops receiving it without
  having to reconnect or reload.
- A principal who cannot see a Table/Row cannot open its real-time channel at all (the
  subscription itself is refused, not merely filtered after the fact).

## 3. Acceptance behavior (externally observable)

- A hidden field's value is **not returned** through any current read surface (all view
  types, search, REST row list/get, WebSocket row payloads) for a member below the
  threshold — **including** when the member explicitly requests the field by name in a
  REST `include=` parameter (the permission boundary overrides client field selection).
- Searching for a value that exists **only** in a hidden field returns **no hit** for an
  unauthorized member (no inference via hit/no-hit), but returns the hit for an admin.
- A member below the threshold attempting to **create or update a filter or a sort** that
  references the hidden field is rejected **server-side with HTTP 403** (distinct from
  the generic 401). A member at/above the threshold, or any field with no threshold, is
  unaffected.
- A normal row read that merely *contains* a hidden field is **not** rejected — the field
  is silently omitted (redaction omits; only the filter/sort guard raises).
- Changing a field's visibility **invalidates cached row/field payloads** and
  **re-evaluates live sessions** so the new visibility takes effect without a reconnect.
- The redaction is computed in **one central place** consumed by every surface — there is
  no per-surface ad-hoc hiding.

## 4. Free-core (MIT) symbols to build on

- `ReadFieldOperationType` (`database.table.field.read`) — the per-field read op the
  manager answers and the guard checks.
- `PermissionManagerType.filter_queryset` / `get_permissions_object` /
  `check_multiple_permissions` — extended on the existing 1.4 manager.
- `get_row_serializer_class(..., exclude_field_ids=...)`,
  `get_hidden_field_ids_for_view_user`, `search_all_fields(only_search_by_field_ids=...)`
  — the existing redaction levers the central redactor feeds.
- `invalidate_table_in_model_cache`, the `permissions_updated` signal and the per-table
  permission-channel-group broadcast — the existing invalidation/re-evaluation mechanism.
- Story 1.4's `FieldPermission`, `FieldPermissionManagerType`, `FieldPermissionHandler`,
  and the `FieldEditProhibitedError → global 403` registration pattern.

## 5. Self-check (must all be true)

- [x] Every source in §1 is on the allowed-source list (no `premium/`/`enterprise/`,
      no paid-instance internals, no memory of the paid product).
- [x] No `premium/`/`enterprise/` **internal** symbol is named as the thing to replicate.
- [x] This spec captures behavior/UI only, not code adapted from PE/EE source.
