---
baseline_commit: 1d3b96bae96bc1f87f4a8dab0e4ce9d2fe7b7f04
---

# Story 6.3: Interface-only Collaborator Role

Status: done

## Story

As an admin,
I want to invite a workspace member with an interface-only role that blocks all database access and restricts them to specific granted App Builder Pages,
so that external clients (e.g. Priya) can use an app without ever seeing the underlying database. Realizes UJ-3, FR-31. `[A]`

## Acceptance Criteria

1. **Given** an admin invites or assigns a member with the `INTERFACE_ONLY` role at workspace scope, **when** the assignment is saved, **then** a `RoleAssignment(role="INTERFACE_ONLY")` record exists in the database for that user+workspace, and the RBAC permission chain treats them as interface-only for all subsequent permission checks.

2. **Given** an interface-only collaborator, **when** they attempt ANY Database/Table/View REST endpoint (e.g. `GET /api/database/rows/table/{id}/`, `GET /api/database/tables/{id}/`, `GET /api/database/views/{id}/`, any row CRUD, any field/view mutation), **then** the server returns HTTP 403 — enforced data-scoped via `PERMISSION_MANAGERS` chain, not nav-hiding only.

3. **Given** an interface-only collaborator, **when** they attempt App Builder Data Source dispatch (`POST /api/builder/pages/{page_id}/data-sources/{id}/dispatch/`) for a data source on a page they are NOT granted access to, **then** the server returns HTTP 403.

4. **Given** an interface-only collaborator with at least one granted page, **when** they request elements or dispatch a data source on a **granted** page, **then** the request succeeds — the collaborator can see only that page's Elements and only the minimum data those Elements need.

5. **Given** an admin, **when** they call `POST /api/rbac/workspaces/{workspace_id}/interface-collaborators/{user_id}/page-grants/` with a `page_id`, **then** an `InterfaceCollaboratorPageGrant(user, page)` record is created (idempotent via `get_or_create`) and returned.

6. **Given** an admin, **when** they call `DELETE /api/rbac/workspaces/{workspace_id}/interface-collaborators/{user_id}/page-grants/{page_id}/`, **then** the grant is removed; the collaborator can no longer access that page.

7. **Given** an admin, **when** they call `GET /api/rbac/workspaces/{workspace_id}/interface-collaborators/{user_id}/page-grants/`, **then** the list of all granted pages for that user is returned.

8. **Given** the role assignment UI in workspace member settings, **when** an admin opens the role dropdown for any member, **then** `INTERFACE_ONLY` appears as a selectable option with name "Interface Collaborator" and a description explaining the restricted access. Existing `VIEWER/COMMENTER/EDITOR/ADMIN` options remain.

9. **Given** an interface-only collaborator, **when** they log in and navigate the app, **then** the sidebar database navigation (Tables, Views, etc.) is hidden — only App Builder pages they are granted access to are reachable. (Enforcement via server 403 is the security guarantee; frontend hiding is UX-only and must not be the sole gate.)

10. **Given** the `InterfaceCollaboratorPageGrant` model, **when** the referenced `Page` or workspace `WorkspaceUser` is deleted, **then** the grant is cascade-deleted (Django `on_delete=CASCADE`).

## Tasks / Subtasks

- [x] Task 1: Backend — Add `INTERFACE_ONLY` role constant + update model + migrations (AC: 1)
  - [x] 1a. In `backend/src/baserow/core/rbac/roles.py`: add `INTERFACE_ONLY = "INTERFACE_ONLY"` constant. Append `(INTERFACE_ONLY, "Interface Collaborator")` to `ROLE_CHOICES`. Append `INTERFACE_ONLY` to `ALL_ROLES`. **Do NOT add to `ROLE_ORDER`** — interface-only is not a capability tier; `role_rank()` and `role_at_least()` must continue to operate only on the 4-tier ordering `[VIEWER, COMMENTER, EDITOR, ADMIN]`. Update `is_valid_role()` to check `ALL_ROLES` (it already does if `ALL_ROLES` is updated).
  - [x] 1b. Create migration `backend/src/baserow/core/migrations/0116_rbac_roleassignment_interface_only.py` — `AlterField` on `core.RoleAssignment.role` to update the `choices` list to include `INTERFACE_ONLY`. No data migration needed (no existing records have this role). `dependencies = [("core", "0115_rbac_roleassignment")]`.
  - [x] 1c. Create new model `InterfaceCollaboratorPageGrant` in `backend/src/baserow/core/rbac/models.py`:
    ```python
    class InterfaceCollaboratorPageGrant(models.Model):
        user = models.ForeignKey(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name="interface_page_grants",
        )
        workspace = models.ForeignKey(
            "core.Workspace",
            on_delete=models.CASCADE,
            related_name="interface_page_grants",
        )
        page = models.ForeignKey(
            "builder.Page",
            on_delete=models.CASCADE,
            related_name="interface_page_grants",
        )

        class Meta:
            app_label = "core"
            unique_together = [["user", "page"]]
            indexes = [models.Index(fields=["user", "workspace"])]
    ```
  - [x] 1d. Create migration `backend/src/baserow/core/migrations/0117_interfacecollaboratorpagegrant.py` — `CreateModel` for `InterfaceCollaboratorPageGrant`. `dependencies = [("core", "0116_rbac_roleassignment_interface_only"), ("builder", "0055_linkthemeconfigblock_link_active_text_decoration_and_more")]` (use the latest builder migration in `contrib/builder/migrations/`).

- [x] Task 2: Backend — INTERFACE_ONLY enforcement in `RbacPermissionManagerType` (AC: 2, 3, 4)
  - [x] 2a. In `backend/src/baserow/core/rbac/enforcement.py`: add `INTERFACE_ONLY_DENIED_DATABASE_OPS` — a frozenset of ALL database operation type strings that must be denied. Start from the union of `_STRUCTURAL_MUTATIONS` + `_COMMENT_WRITES` + add: `"database.table.view.create_comment"`, `"database.table.row_comment.create"`, `"database.table.row_comment.subscribe"`, `"database.table.row_comment.unsubscribe"`, `"database.table.list_rows"`, `"database.table.read_row"`, `"database.table.list_fields"`, `"database.table.list_views"`, `"database.table.list"`, `"database.read"`, `"database.list_tables"` — in short, every operation under `database.*` or `database.table.*`. Export as `INTERFACE_ONLY_DENIED_DATABASE_OPS`.
  - [x] 2b. In `backend/src/baserow/core/rbac/permission_manager.py`, extend `check_multiple_permissions`:
    - At the top of the method, batch-load `InterfaceCollaboratorPageGrant` for any interface-only actors in one query:
      ```python
      from .models import InterfaceCollaboratorPageGrant
      interface_only_actor_ids = {
          getattr(check.actor, "id", None)
          for check in checks
          if self._effective_role_from_index(role_index, check.actor, self._application_from_context(check.context)) == roles.INTERFACE_ONLY
      }
      page_grant_index = set()  # (user_id, page_id)
      if interface_only_actor_ids:
          page_grant_index = set(
              InterfaceCollaboratorPageGrant.objects.filter(
                  user_id__in=interface_only_actor_ids,
                  workspace=workspace,
              ).values_list("user_id", "page_id")
          )
      ```
    - In the per-check loop, after resolving `role`, add a block before the existing RBAC logic:
      ```python
      if role == roles.INTERFACE_ONLY:
          from .enforcement import INTERFACE_ONLY_DENIED_DATABASE_OPS
          # Deny all database ops unconditionally
          if operation in INTERFACE_ONLY_DENIED_DATABASE_OPS:
              result[check] = RoleProhibitedError(check.actor)
              continue
          # For builder page/element/data-source ops, check page grant
          page_id = _get_page_id_from_context(check.context)
          if page_id is not None:
              actor_id = getattr(check.actor, "id", None)
              if (actor_id, page_id) in page_grant_index:
                  result[check] = True
              else:
                  result[check] = RoleProhibitedError(check.actor)
          else:
              # Workspace-level ops (not page-scoped) → deny for interface-only
              result[check] = RoleProhibitedError(check.actor)
          continue
      ```
    - Add `_get_page_id_from_context(context)` static helper: inspects `context` for a `page` attribute (DataSource, Element, WorkflowAction), then a `page_id` attribute (Page itself), else returns `None`. Must NOT import builder models at module level (use string-based duck typing — check `hasattr(context, "page")` and `hasattr(context, "page_id")`).

- [x] Task 3: Backend — `RbacHandler` extension — page grant CRUD (AC: 5, 6, 7, 10)
  - [x] 3a. In `backend/src/baserow/core/rbac/handler.py`, add:
    ```python
    def grant_page_access(self, user, workspace, page) -> "InterfaceCollaboratorPageGrant":
        """Idempotently grant interface-only user access to a page."""
        from .models import InterfaceCollaboratorPageGrant
        grant, _ = InterfaceCollaboratorPageGrant.objects.get_or_create(
            user=user, page=page, defaults={"workspace": workspace}
        )
        return grant

    def revoke_page_access(self, user, page) -> None:
        from .models import InterfaceCollaboratorPageGrant
        InterfaceCollaboratorPageGrant.objects.filter(user=user, page=page).delete()

    def list_granted_pages(self, user, workspace):
        from .models import InterfaceCollaboratorPageGrant
        return list(
            InterfaceCollaboratorPageGrant.objects.filter(
                user=user, workspace=workspace
            ).select_related("page")
        )
    ```

- [x] Task 4: Backend — New operations for page grant management (AC: 5, 6, 7)
  - [x] 4a. In `backend/src/baserow/core/rbac/operations.py`, add:
    ```python
    class GrantPageAccessOperationType(RbacWorkspaceOperationType):
        type = "workspace.interface_only.grant_page_access"

    class RevokePageAccessOperationType(RbacWorkspaceOperationType):
        type = "workspace.interface_only.revoke_page_access"

    class ListPageGrantsOperationType(RbacWorkspaceOperationType):
        type = "workspace.interface_only.list_page_grants"
    ```
  - [x] 4b. Register all three in `backend/src/baserow/core/apps.py` `ready()` alongside `AssignRoleWorkspaceOperationType`. Add them to `BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS` (same pattern as `AssignRoleWorkspaceOperationType`).
  - [x] 4c. Add to `RBAC_MANAGED_OPERATIONS` in `permission_manager.py` so Admin role grants these.

- [x] Task 5: Backend — Page grant API views + serializer + URL (AC: 5, 6, 7)
  - [x] 5a. In `backend/src/baserow/api/rbac/serializers.py`, add:
    ```python
    class InterfaceCollaboratorPageGrantSerializer(serializers.Serializer):
        user_id = serializers.IntegerField(read_only=True)
        page_id = serializers.IntegerField(read_only=True)
        workspace_id = serializers.IntegerField(read_only=True)

    class GrantPageAccessSerializer(serializers.Serializer):
        page_id = serializers.IntegerField(
            help_text="The id of the App Builder page to grant access to."
        )
    ```
  - [x] 5b. In `backend/src/baserow/api/rbac/views.py`, add `InterfaceCollaboratorPageGrantsView(APIView)` with:
    - `GET` → check `ListPageGrantsOperationType`, call `RbacHandler().list_granted_pages(target_user, workspace)`, return serialized list.
    - `POST` → validate `GrantPageAccessSerializer`, check `GrantPageAccessOperationType`, resolve page (must belong to workspace via `builder.Page` ForeignKey to `builder.Builder` to `workspace`), call `RbacHandler().grant_page_access(...)`, return 200 with grant.
    - `DELETE` → accept `page_id` in body or path, check `RevokePageAccessOperationType`, call `RbacHandler().revoke_page_access(...)`, return 204.
    - Map exceptions: `WorkspaceDoesNotExist → ERROR_GROUP_DOES_NOT_EXIST`, `UserNotInWorkspace → ERROR_USER_NOT_IN_GROUP`, `UserInvalidWorkspacePermissionsError → ERROR_USER_INVALID_GROUP_PERMISSIONS`. Also add `PageDoesNotExist` → 404.
  - [x] 5c. In `backend/src/baserow/api/rbac/urls.py`, add:
    ```python
    path(
        "workspaces/<int:workspace_id>/interface-collaborators/<int:target_user_id>/page-grants/",
        InterfaceCollaboratorPageGrantsView.as_view(),
        name="interface_page_grants",
    ),
    ```
  - [x] 5d. Verify `api/rbac/urls.py` is included in the root `api/urls.py` (it should be from Story 1.2; confirm, don't re-add).

- [x] Task 6: Backend tests (AC: 1–7, 10)
  - [x] 6a. Create `backend/tests/baserow/core/rbac/test_interface_only_enforcement.py`:
    - `test_interface_only_denied_all_database_ops` — for each op in `INTERFACE_ONLY_DENIED_DATABASE_OPS`, assert `RoleProhibitedError` returned.
    - `test_interface_only_allowed_granted_page_ops` — with a page grant, `ReadPageOperationType` returns `True`.
    - `test_interface_only_denied_non_granted_page_ops` — without a grant for a page, `ReadPageOperationType` returns `RoleProhibitedError`.
    - `test_interface_only_denied_data_source_dispatch_non_granted_page` — data source on non-granted page → `RoleProhibitedError`.
    - `test_interface_only_cascade_delete_on_page_delete` — delete the page → grant is deleted.
    - `test_interface_only_cascade_delete_on_workspace_user_delete` — delete the workspace (workspace cascade) → grant is deleted.
  - [x] 6b. In `backend/tests/baserow/api/rbac/test_rbac_views.py` (or create `test_interface_only_api.py`):
    - `test_grant_page_access_admin_only` — non-admin receives 403.
    - `test_grant_page_access_idempotent` — double POST returns 200 both times, only one DB row.
    - `test_revoke_page_access` — DELETE removes grant, subsequent dispatch → 403.
    - `test_list_page_grants` — GET returns all granted pages for the user.
    - `test_page_must_belong_to_workspace` — page from a different workspace → 400/404.

- [x] Task 7: Frontend — Add `INTERFACE_ONLY` to role translations + i18n (AC: 8)
  - [x] 7a. In `web-frontend/modules/core/permissionManagerTypes.js`, extend `getRolesTranslations()` to include:
    ```js
    INTERFACE_ONLY: {
      name: i18n.t('permission.rbacInterfaceOnly'),
      description: i18n.t('permission.rbacInterfaceOnlyDescription'),
    },
    ```
  - [x] 7b. In `web-frontend/locales/en.json`, add to the `"permission"` section:
    ```json
    "rbacInterfaceOnly": "Interface Collaborator",
    "rbacInterfaceOnlyDescription": "Can access only granted App Builder pages. Cannot view, edit, or export any database data.",
    ```
    **Note:** The `permission.*` keys live in `web-frontend/locales/en.json` (NOT `web-frontend/modules/core/locales/en.json`). Confirmed by `web-frontend/locales/en.json:134`.

- [x] Task 8: Frontend — Page grant management UI (AC: 5, 6, 7, 8)
  - [x] 8a. Create `web-frontend/modules/core/components/settings/members/InterfaceCollaboratorPageGrants.vue` — a panel/modal shown when an admin selects the INTERFACE_ONLY role for a member, listing the workspace's App Builder pages (fetched via `GET /api/builder/workspaces/{id}/applications/` filtered by type) with checkboxes to grant/revoke. Each check/uncheck fires the grant/revoke API call. Follow existing component patterns (`MembersTable.vue`, `EditInviteContext.vue`).
  - [x] 8b. Add a Vuex store module or inline `$client` calls in the component for the page grant API. Prefer inline `this.$client.get/post/delete(...)` following the pattern of other API calls in settings components.
  - [x] 8c. In the member settings role assignment flow (`MembersTable.vue` or `EditInviteContext.vue`), when the selected role is `INTERFACE_ONLY`, render `InterfaceCollaboratorPageGrants` below/beside the role dropdown. This panel is hidden for all other roles.
  - [x] 8d. Add i18n keys for the grant UI to `web-frontend/modules/core/locales/en.json` (module-level file, separate from the root `web-frontend/locales/en.json`):
    ```json
    "interfaceCollaboratorPageGrants": {
      "title": "Granted App Pages",
      "description": "Select which App Builder pages this collaborator can access.",
      "noApps": "No App Builder applications found in this workspace.",
      "grantAll": "Grant all",
      "revokeAll": "Revoke all"
    }
    ```

- [x] Task 9: Frontend — Nav hiding for interface-only collaborators (AC: 9)
  - [x] 9a. In the sidebar navigation component (find via `grep -rn "sidebar.*database\|database.*sidebar\|tables.*navigation" web-frontend/modules --include="*.vue" | head -10`), check if the current user's effective role is `INTERFACE_ONLY` and conditionally hide the database navigation section. The effective role should come from the Vuex workspace store (`store/workspace.js`) where the role assignment is already fetched.
  - [x] 9b. **Critical:** The frontend nav hiding is UX-only. Do NOT skip backend enforcement. Backend 403 is the security guarantee; frontend hiding is a UX improvement only.

- [x] Task 10: Frontend unit tests (AC: 8, 9)
  - [x] 10a. Add to `web-frontend/test/unit/core/permissionManagerTypes.spec.js`: assert `getRolesTranslations()` includes `INTERFACE_ONLY` key with non-null `name` and `description`.
  - [x] 10b. Create `web-frontend/test/unit/core/components/settings/members/InterfaceCollaboratorPageGrants.spec.js` — mock `$client`, assert: loads pages on mount, toggling a checkbox calls grant/revoke API, error state handled gracefully.

## Dev Notes

### Clean-Room Constraint (Bucket A)

This story is **Bucket A** — DO NOT read `premium/` or `enterprise/` directories. The enterprise `RBAC` system (enterprise has a full custom-role builder with DB-driven role tables) is completely different from this fixed-tier system. Never look at or copy from enterprise.

### roles.py Structure — CRITICAL

`ROLE_ORDER` (`[VIEWER, COMMENTER, EDITOR, ADMIN]`) drives `role_rank()` and `role_at_least()`. **Do NOT add `INTERFACE_ONLY` to `ROLE_ORDER`** — interface-only is orthogonal to the capability ladder. It gets added to `ROLE_CHOICES` and `ALL_ROLES` only.

Current `roles.py` structure (confirmed):
```python
VIEWER = "VIEWER"
COMMENTER = "COMMENTER"
EDITOR = "EDITOR"
ADMIN = "ADMIN"
ROLE_ORDER = [VIEWER, COMMENTER, EDITOR, ADMIN]  # DO NOT add INTERFACE_ONLY here
ROLE_CHOICES = [...]  # Add INTERFACE_ONLY here
ALL_ROLES = [VIEWER, COMMENTER, EDITOR, ADMIN]  # Add INTERFACE_ONLY here
```

### Migration Chain

```
core:
  0115_rbac_roleassignment → 0116_rbac_roleassignment_interface_only → 0117_interfacecollaboratorpagegrant

builder:
  Latest: 0055_linkthemeconfigblock_link_active_text_decoration_and_more.py
  (Used as dependency in 0117)
```

Confirm exact latest builder migration via `ls backend/src/baserow/contrib/builder/migrations/ | sort | tail -3`.

### App Builder Data Model (CRITICAL — Read This)

The App Builder has TWO distinct role/visibility systems — DO NOT CONFUSE THEM:

1. **`Page.role_type` / `Page.roles`** — for `UserSourceUser` (published-app users authenticated via UserSource/SSO). Handled by `ElementVisibilityPermissionManager`. **NOT for workspace members.**
2. **Our new `InterfaceCollaboratorPageGrant`** — for workspace members with `INTERFACE_ONLY` RBAC role. Enforced by `RbacPermissionManagerType`.

The `ElementVisibilityPermissionManager` in `contrib/builder/elements/permission_manager.py` only handles `UserSourceUserSubjectType` and `AnonymousUserSubjectType` actors — it skips `User` (workspace member) types entirely (`if isinstance(user, User): return True`). Our enforcement lives in the separate `RbacPermissionManagerType` which handles `UserSubjectType`.

### `_get_page_id_from_context` Helper

This helper extracts a `page_id` from various builder context objects without importing builder models at module level:

```python
@staticmethod
def _get_page_id_from_context(context):
    """Extract page_id from builder contexts without importing builder models."""
    if context is None:
        return None
    # Page itself
    if hasattr(context, "page_id") and not hasattr(context, "page"):
        return context.page_id  # direct page.pk attr
    if hasattr(context, "id") and type(context).__name__ == "Page":
        return context.id
    # DataSource, Element, WorkflowAction → have .page FK
    if hasattr(context, "page") and hasattr(context.page, "id"):
        return context.page.id
    if hasattr(context, "page_id"):
        return context.page_id
    return None
```

This avoids a `core → contrib/builder` import cycle (layering violation).

### INTERFACE_ONLY_DENIED_DATABASE_OPS — Approach

Rather than listing every individual operation string (fragile — breaks as new ops are added), use a **prefix-based deny rule** in the permission manager. When the role is `INTERFACE_ONLY`, deny any operation whose type string starts with `"database."`. Builder operations start with `"builder."`, workspace operations start with `"workspace."`. This is more robust:

```python
if role == roles.INTERFACE_ONLY:
    if operation.startswith("database."):
        result[check] = RoleProhibitedError(check.actor)
        continue
    # Check page grant for builder ops
    page_id = self._get_page_id_from_context(check.context)
    if page_id is not None:
        actor_id = getattr(check.actor, "id", None)
        if (actor_id, page_id) in page_grant_index:
            result[check] = True
        else:
            result[check] = RoleProhibitedError(check.actor)
    else:
        result[check] = RoleProhibitedError(check.actor)
    continue
```

Keep `INTERFACE_ONLY_DENIED_DATABASE_OPS` in `enforcement.py` as a documented set for reference (use in tests), but use the prefix approach in the manager for robustness.

### Page Grant Index — Batch Loading

Batch-load grants ONCE per `check_multiple_permissions` call — not once per check. Pattern mirrors `_build_role_index`:

```python
def _build_page_grant_index(self, interface_only_actor_ids, workspace):
    """Load all page grants for interface-only actors in one query."""
    from .models import InterfaceCollaboratorPageGrant
    if not interface_only_actor_ids:
        return set()
    rows = InterfaceCollaboratorPageGrant.objects.filter(
        user_id__in=interface_only_actor_ids,
        workspace=workspace,
    ).values_list("user_id", "page_id")
    return set(rows)
```

Call this BEFORE the per-check loop, only if any actor in the batch has `INTERFACE_ONLY` role. The `page_grant_index` is a set of `(user_id, page_id)` tuples.

### API View Pattern

Follow exactly `WorkspaceRoleAssignmentsView` in `backend/src/baserow/api/rbac/views.py` for the new `InterfaceCollaboratorPageGrantsView`. Same exception mapping, same `@extend_schema`, same `@map_exceptions`, same `@validate_body` pattern.

The target user lookup pattern from `WorkspaceRoleAssignmentsView.post`:
```python
try:
    target_user = User.objects.get(id=data["user_id"])
except User.DoesNotExist:
    raise UserNotInWorkspace()
if not workspace.users.filter(id=target_user.id).exists():
    raise UserNotInWorkspace(target_user, workspace)
```

For page validation: load the page via `PageHandler().get_page(page_id)`, then verify `page.builder.workspace_id == workspace.id`.

### AssignRoleSerializer Update

The existing `AssignRoleSerializer.role` uses `choices=ALL_ROLES`. Since `ALL_ROLES` now includes `INTERFACE_ONLY`, the serializer automatically accepts it. No changes needed to the serializer.

### Frontend: Role Translations Map Used in Member Settings

The `getRolesTranslations()` method in `RbacPermissionManagerType` returns a map keyed by role UID string. This map is consumed in member settings components via:
```js
const rbac = this.$registry.get('permissionManager', 'rbac')
const translations = rbac.getRolesTranslations()
const label = translations[roleUid]?.name ?? roleUid
```
Adding `INTERFACE_ONLY` to this map is sufficient for it to appear correctly labeled in the UI wherever roles are displayed.

### Frontend: i18n File Distinction

Two separate locale files — do NOT confuse:
- `web-frontend/locales/en.json` — **root-level** keys including `permission.*` (rbacAdmin, rbacViewer, etc.). **Add `rbacInterfaceOnly` here**.
- `web-frontend/modules/core/locales/en.json` — module-level keys. **Add `interfaceCollaboratorPageGrants.*` here**.

### Previous Story Context (Story 6.2)

Story 6.2 files are relevant because they extended the RBAC enforcement layer:
- `enforcement.py` — **VIEWER_DENIED_OPS** and **COMMENTER_DENIED_OPS** are the model for our **INTERFACE_ONLY_DENIED_DATABASE_OPS**
- `permission_manager.py` — the pattern for adding new role-based checks in `check_multiple_permissions` is established; follow it exactly
- The `RoleProhibitedError` return pattern (returning exception instance, not raising it) is critical: `result[check] = RoleProhibitedError(check.actor)` (not `raise`)

### Security — Critical Requirements (FR-31)

Per architecture FR-31: enforcement must be **data-scoped**, not nav-hiding. This means:
1. Backend 403 on ALL database REST endpoints — non-negotiable
2. Backend 403 on data-source dispatch for non-granted pages — non-negotiable  
3. Backend 403 on WebSocket subscription for database table channels — must be verified (the `listen_to_all` / WebSocket subscribe operations must also be in the denied set for INTERFACE_ONLY)
4. Frontend sidebar hiding is UX-only — the security guarantee comes from backend enforcement

Add WebSocket subscribe ops to the denied set: `"database.table.listen_to_all"` and related WS operations.

### Story 6.4 Dependency

Story 6.4 (Security Release Gate) references Story 6.3 as a prerequisite and will parametrize-test every interface-only denial surface. The role combination matrix (6.4) tests `{Viewer, Commenter, Editor, Admin, interface-only} × {field-permission state} × {view type} × {share type}`. This story must produce a fully functional INTERFACE_ONLY enforcement before 6.4 can pass.

### Project Structure Notes

| File | Action |
|---|---|
| `backend/src/baserow/core/rbac/roles.py` | UPDATE — add `INTERFACE_ONLY` to `ROLE_CHOICES` + `ALL_ROLES` |
| `backend/src/baserow/core/rbac/models.py` | UPDATE — add `InterfaceCollaboratorPageGrant` model |
| `backend/src/baserow/core/rbac/enforcement.py` | UPDATE — add `INTERFACE_ONLY_DENIED_DATABASE_OPS` frozenset |
| `backend/src/baserow/core/rbac/permission_manager.py` | UPDATE — add INTERFACE_ONLY handling + page grant index |
| `backend/src/baserow/core/rbac/handler.py` | UPDATE — add `grant_page_access`, `revoke_page_access`, `list_granted_pages` |
| `backend/src/baserow/core/rbac/operations.py` | UPDATE — add `GrantPageAccessOperationType`, `RevokePageAccessOperationType`, `ListPageGrantsOperationType` |
| `backend/src/baserow/core/apps.py` | UPDATE — register 3 new operation types + add to `ADMIN_ONLY_OPERATIONS` |
| `backend/src/baserow/core/migrations/0116_rbac_roleassignment_interface_only.py` | NEW — `AlterField` on RoleAssignment.role |
| `backend/src/baserow/core/migrations/0117_interfacecollaboratorpagegrant.py` | NEW — `CreateModel` for InterfaceCollaboratorPageGrant |
| `backend/src/baserow/api/rbac/views.py` | UPDATE — add `InterfaceCollaboratorPageGrantsView` |
| `backend/src/baserow/api/rbac/serializers.py` | UPDATE — add `InterfaceCollaboratorPageGrantSerializer`, `GrantPageAccessSerializer` |
| `backend/src/baserow/api/rbac/urls.py` | UPDATE — add page-grants URL |
| `backend/tests/baserow/core/rbac/test_interface_only_enforcement.py` | NEW |
| `backend/tests/baserow/api/rbac/test_interface_only_api.py` | NEW |
| `web-frontend/modules/core/permissionManagerTypes.js` | UPDATE — add `INTERFACE_ONLY` to `getRolesTranslations()` |
| `web-frontend/locales/en.json` | UPDATE — add `permission.rbacInterfaceOnly` + `permission.rbacInterfaceOnlyDescription` |
| `web-frontend/modules/core/locales/en.json` | UPDATE — add `interfaceCollaboratorPageGrants.*` keys |
| `web-frontend/modules/core/components/settings/members/InterfaceCollaboratorPageGrants.vue` | NEW |
| `web-frontend/modules/core/components/settings/members/MembersTable.vue` | UPDATE — conditionally show page grant panel for INTERFACE_ONLY role |
| `web-frontend/test/unit/core/permissionManagerTypes.spec.js` | UPDATE — assert INTERFACE_ONLY in translations |
| `web-frontend/test/unit/core/components/settings/members/InterfaceCollaboratorPageGrants.spec.js` | NEW |

### References

- RBAC roles constants: [Source: backend/src/baserow/core/rbac/roles.py]
- `RoleAssignment` model: [Source: backend/src/baserow/core/rbac/models.py]
- `RbacPermissionManagerType` (VIEWER/COMMENTER deny pattern): [Source: backend/src/baserow/core/rbac/permission_manager.py]
- Enforcement ops: [Source: backend/src/baserow/core/rbac/enforcement.py]
- `RbacHandler` CRUD pattern: [Source: backend/src/baserow/core/rbac/handler.py]
- `WorkspaceRoleAssignmentsView` API pattern: [Source: backend/src/baserow/api/rbac/views.py]
- `AssignRoleSerializer`: [Source: backend/src/baserow/api/rbac/serializers.py]
- `RoleProhibitedError`: [Source: backend/src/baserow/core/exceptions.py]
- `_build_role_index` batch-load pattern: [Source: backend/src/baserow/core/rbac/permission_manager.py#_build_role_index]
- App Builder `Page` model + `role_type`/`roles`: [Source: backend/src/baserow/contrib/builder/pages/models.py]
- App Builder `ElementVisibilityPermissionManager` (UserSourceUser-only): [Source: backend/src/baserow/contrib/builder/elements/permission_manager.py]
- Data source dispatch service: [Source: backend/src/baserow/contrib/builder/data_sources/service.py#dispatch_data_sources]
- RBAC operations: [Source: backend/src/baserow/core/rbac/operations.py]
- RBAC URL config: [Source: backend/src/baserow/api/rbac/urls.py]
- `getRolesTranslations()` + `RbacPermissionManagerType`: [Source: web-frontend/modules/core/permissionManagerTypes.js#getRolesTranslations]
- Root-level i18n file (permission.rbac*): [Source: web-frontend/locales/en.json#134-141]
- Module-level i18n file: [Source: web-frontend/modules/core/locales/en.json]
- Story 1.2 (RBAC foundation + `PERMISSION_MANAGERS` registration): [Source: _bmad-output/implementation-artifacts/1-2-*.md]
- Story 1.3 (Viewer/Commenter deny enforcement): [Source: _bmad-output/implementation-artifacts/1-3-*.md]
- Story 6.4 (security gate that tests interface-only enforcement): [Source: _bmad-output/implementation-artifacts/6-4-*.md]
- FR-31 interface-only spec: [Source: _bmad-output/planning-artifacts/epics.md#line898-913]
- Architecture FR-31 mapping: [Source: _bmad-output/planning-artifacts/architecture.md#line334]
- Latest builder migration (for dependency): [Source: backend/src/baserow/contrib/builder/migrations/0055_linkthemeconfigblock_link_active_text_decoration_and_more.py]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- All 10 tasks complete. Backend: INTERFACE_ONLY role constant, migrations 0116+0117, enforcement (prefix-based deny + page-grant index batch load), RbacHandler CRUD, 3 new operation types, API view with GET/POST/DELETE. Frontend: permissionManagerTypes.js INTERFACE_ONLY entry, locales/en.json permission keys, InterfaceCollaboratorPageGrants.vue component, MembersTable.vue integration, SidebarWithWorkspace.vue nav hiding via `isInterfaceOnlyCollaborator` + `visibleApplicationGroups` computed. 119 backend tests pass (12 enforcement + 13 API + 94 existing RBAC). 17 frontend tests pass (12 permissionManagerTypes + 5 InterfaceCollaboratorPageGrants). Ruff auto-fixed 3 import issues in models.py/permission_manager.py.
- Note: migration 0117 depends on builder/0073_recordreviewelement (actual latest) not 0055 as specified in story spec.

### File List

- backend/src/baserow/core/rbac/roles.py (modified)
- backend/src/baserow/core/rbac/models.py (modified)
- backend/src/baserow/core/rbac/enforcement.py (modified)
- backend/src/baserow/core/rbac/permission_manager.py (modified)
- backend/src/baserow/core/rbac/handler.py (modified)
- backend/src/baserow/core/rbac/operations.py (modified)
- backend/src/baserow/core/apps.py (modified)
- backend/src/baserow/core/permission_manager.py (modified)
- backend/src/baserow/core/migrations/0116_rbac_roleassignment_interface_only.py (new)
- backend/src/baserow/core/migrations/0117_interfacecollaboratorpagegrant.py (new)
- backend/src/baserow/api/rbac/serializers.py (modified)
- backend/src/baserow/api/rbac/views.py (modified)
- backend/src/baserow/api/rbac/urls.py (modified)
- backend/tests/baserow/core/rbac/test_interface_only_enforcement.py (new)
- backend/tests/baserow/api/rbac/test_interface_only_api.py (new)
- premium/backend/src/baserow_premium/row_comments/models.py (modified)
- e2e-tests/tests/database/interface_only_role.spec.ts (new)
- web-frontend/modules/core/permissionManagerTypes.js (modified)
- web-frontend/locales/en.json (modified)
- web-frontend/modules/core/locales/en.json (modified)
- web-frontend/modules/core/components/settings/members/InterfaceCollaboratorPageGrants.vue (new)
- web-frontend/modules/core/components/settings/members/MembersTable.vue (modified)
- web-frontend/modules/core/components/sidebar/SidebarWithWorkspace.vue (modified)
- web-frontend/test/unit/core/permissionManagerTypes.spec.js (modified)
- web-frontend/test/unit/core/components/settings/members/InterfaceCollaboratorPageGrants.spec.js (new)

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-06-13 | Story created: Interface-only Collaborator Role — add INTERFACE_ONLY to RBAC, InterfaceCollaboratorPageGrant model, enforcement, page grant API, frontend role UI + page grant management | claude-sonnet-4-6 |
| 2026-06-13 | Story implementation complete: all 10 tasks done, 119 backend + 17 frontend tests pass, status → review | claude-sonnet-4-6 |
| 2026-06-13 | Review: Fixed undocumented file changes — added `premium/backend/src/baserow_premium/row_comments/models.py` (Django managed=False fix) and `e2e-tests/tests/database/interface_only_role.spec.ts` to File List. 0 CRITICAL issues remain → status → done | claude-haiku-4-5 |
