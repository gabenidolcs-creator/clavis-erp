# Behavior spec — Role enforcement for Commenter and Viewer (deny side)

- **Story / epic:** 1.3 Role enforcement for Commenter and Viewer (Epic 1)
- **Bucket:** A (clean-room reimplement)
- **Author:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-06
- **Extends:** [1-2-rbac-role-model.md](1-2-rbac-role-model.md) (the role *model*; this
  spec adds the *enforcement* / deny policy).

## 1. Allowed sources consulted

| # | Source | Type (public docs / public SaaS UI / public issue / MIT free-core) | Link / location |
|---|--------|--------------------------------------------------------------------|-----------------|
| 1 | Public Baserow documentation — what each role tier may/may not do (Viewer read-only, Commenter read+comment) | public docs | https://baserow.io/docs |
| 2 | Observable role behavior in the public hosted Baserow SaaS (a Viewer cannot edit; a Commenter can comment but not edit) | public SaaS UI | https://baserow.io |
| 3 | `BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS` — the *string-list of operation types* convention (deny/grant decisions keyed on `operation.type` strings, no class import) | MIT free-core | `backend/src/baserow/core/permission_manager.py` |
| 4 | `PermissionManagerType.check_multiple_permissions` contract — `True` = grant, a `PermissionException` value = deny, absent = defer | MIT free-core | `backend/src/baserow/core/registries.py` |
| 5 | `CoreHandler.check_permissions` / `check_multiple_permissions` — re-raises the manager's returned `PermissionException`; deny-by-default for undetermined checks | MIT free-core | `backend/src/baserow/core/handler.py` |
| 6 | `PermissionException` / `PermissionDenied` hierarchy | MIT free-core | `backend/src/baserow/core/exceptions.py` |
| 7 | `map_exceptions` / `apply_exception_mapping` / `_search_up_class_hierarchy_for_mapping` — MRO most-specific-first resolution; `api_exception_registry` global merge | MIT free-core | `backend/src/baserow/api/utils.py`, `backend/src/baserow/api/registries.py`, `backend/src/baserow/api/decorators.py` |
| 8 | Row / Field / View operation `type` strings (the exact mutating + comment-stub op names) | MIT free-core | `backend/src/baserow/contrib/database/{rows,fields,views,table}/operations.py` |
| 9 | WebSocket subscribe path — `CoreConsumer` handles only `page` / `remove_page`; `ListenToAllDatabaseTableEventsOperationType` (`database.table.listen_to_all`) gates subscribe; no mutating WS command exists | MIT free-core | `backend/src/baserow/ws/consumers.py`, `backend/src/baserow/contrib/database/ws/pages.py` |
| 10 | Django / DRF framework documentation | general public knowledge | https://docs.djangoproject.com, https://www.django-rest-framework.org |

> No excluded paid (PE/EE) source under `premium/` or `enterprise/` was read, copied,
> adapted, or recalled. The enterprise role manager uses a DB-driven custom-role /
> operation-table model that is **not** our design; only the *public registry shape*
> (that a manager returns an exception to deny) is shared and is observable from the MIT
> free-core base class.

## 2. Observed behavior (UI / UX)

In the public product the two read-scoped tiers behave as:

- **Viewer** — read-only. Can list/open databases, tables, views and read rows. Cannot
  create/edit/delete rows, fields or views. Cannot post comments.
- **Commenter** — read + comment. Same read access as Viewer, **plus** may post
  comments on rows. Still cannot create/edit/delete rows, fields or views.

Editor and Admin are unchanged from Story 1.2 (Editor = today's "member" write
capability; Admin = today's full management).

## 3. Enforcement policy (server-side, authoritative)

Enforcement runs through the **single** existing `PERMISSION_MANAGERS` chain entry
`RbacPermissionManagerType` (extended, never duplicated; no parallel/per-view check).

For each permission check the manager resolves the effective role (1.2 logic, batched),
then applies the deny policy below by **operation `type` string**:

### Denied to BOTH Viewer and Commenter (structural mutations → deny)

| Surface | Operation type strings |
|---|---|
| Rows (table-scoped) | `database.table.create_row`, `database.table.update_row`, `database.table.delete_row` |
| Rows (view-scoped) | `database.table.view.create_row`, `database.table.view.update_row`, `database.table.view.delete_row` |
| Fields | `database.table.create_field`, `database.table.field.update`, `database.table.field.delete` |
| Views | `database.table.create_view`, `database.table.view.update`, `database.table.view.delete` |

### Comments

| Operation type string | Viewer | Commenter |
|---|---|---|
| `database.table.view.create_comment` | deny | **allow (grant-through)** |
| `database.table.view.update_comment` | deny | deny |
| `database.table.view.delete_comment` | deny | deny |
| `database.table.view.list_comments` | allow (defer/read) | allow (defer/read) |

> Comment *operation types* are registered in free core but there is no comment
> model/handler/endpoint yet (Epic 6 / Story 6.1). The policy is therefore enforced and
> tested at the permission-manager / handler level only; the end-to-end HTTP comment
> route lands with 6.1.

### Deferred (NOT denied) — read / subscribe must keep working

`database.table.read_row`, `database.table.view.list_rows`,
`database.table.view.read_row`, `database.table.list_fields`,
`database.table.list_views`, and critically `database.table.listen_to_all`
(the WebSocket subscribe op). The manager **defers** (omits the check) for these so the
legacy chain still grants read access to Viewer/Commenter. The manager is **not**
deny-by-default for these roles.

## 4. Error contract

A denied role mutation raises `RoleProhibitedError(PermissionException)`, mapped
**globally** (via `api_exception_registry`) to **HTTP 403** with error code
`ERROR_ROLE_PROHIBITED`. The generic `PermissionException` remains mapped to **HTTP 401**
(`PERMISSION_DENIED`) for non-role denials (e.g. non-member) — MRO most-specific-first
resolution guarantees the subclass 403 wins for role denials while the catch-all 401 is
unchanged. No per-view edits are required.

## 5. WebSocket parity

There is no mutating command over WebSocket — `CoreConsumer` handles only subscribe
(`page`) / `remove_page`; all writes go through REST → the same
`CoreHandler.check_permissions` → chain. So "403 on WebSocket mutation" is satisfied
structurally (there is no WS write path to bypass). Subscribe-time auth
(`TablePageType.can_add` → `listen_to_all`) is **not** in the deny sets, so Viewer/
Commenter retain read/subscribe.

## 6. Out of scope (later stories)

Field-level edit restriction (1.4), field visibility/inference guard (1.5), the
row-comments subsystem itself (Epic 6 / 6.1), interface-only collaborator (FR-31), the
exhaustive role-combination security gate (AR-2 / 6.4), and any client-side UI gating
(the frontend manager keeps deferring; server is the authoritative source of truth).
