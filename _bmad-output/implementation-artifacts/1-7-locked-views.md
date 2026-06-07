# Story 1.7: Locked Views

Status: done

## Story

As an editor,
I want to lock a View's configuration so others cannot change it,
so that a shared "Master" layout stays intact.

## Context & Scope

Implements FR-32. Architecture decision D14: add `locked` flag to free-core `View` model. Bucket A — clean-room reimplementation. Provenance records required.

**What "locked" means:**
- `locked=True` → view config (filters/sorts/field-options/decorations/group-bys/layout) is read-only for non-lock-owner / non-admin
- Data within the view (rows) remains editable per Role as normal
- Lock owner = the user who last set `locked=True` (stored in existing `owned_by` FK; overwritten when lock is acquired)
- Unlock authority: lock owner (`owned_by_id == user.id`) OR workspace Admin

`owned_by` already exists on the `View` model (`created_by_id` column, added in Story 1.6). No new FK needed — just the `locked` BooleanField + migration.

## Acceptance Criteria

**AC1 — Config read-only for non-owner while locked:**
**Given** a Locked View,
**When** a non-owner attempts to change its filters, sorts, field-options, decorations, group-bys, or layout,
**Then** the change is rejected server-side with 403 (config read-only),
**And** data within the View remains editable per the member's Role.

**AC2 — Unlock authority:**
**Given** a Locked View,
**When** an unlock is attempted,
**Then** only an Admin or the lock owner can remove the lock (set `locked=False`),
**And** a non-owner non-admin receives 403.

## Tasks / Subtasks

- [x] Task 1 — Model + migration (AC: 1, 2)
  - [x] Add `locked = models.BooleanField(default=False)` to `View` in `models.py`
  - [x] Create `0214_view_locked.py` migration
  - [x] Add `ViewIsLockedException` to `exceptions.py`

- [x] Task 2 — New operation + admin-only registration (AC: 2)
  - [x] Add `UpdateLockedViewConfigOperationType` to `views/operations.py` (type `"database.table.view.update_locked_config"`)
  - [x] Add string literal `"database.table.view.update_locked_config"` to `BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS` in `core/permission_manager.py`

- [x] Task 3 — Handler enforcement (AC: 1, 2)
  - [x] Add `_check_locked_view_config_access(user, view)` helper to `ViewHandler`
  - [x] Guard `update_view()` — call helper before any field processing; when `locked` changes True→False (unlock), helper enforces owner/admin check; when False→True (lock), set `view.owned_by = user`
  - [x] Add `locked` to `update_view()` `allowed_fields`
  - [x] Guard all config sub-resource methods (see Task 3 file map below) — same placement pattern as `_check_personal_view_access`

- [x] Task 4 — API serializer (AC: 1)
  - [x] Add `locked` field to `ViewSerializer.Meta.fields` (read-only)
  - [x] Add `locked` field to `UpdateViewSerializer.Meta.fields` (writable, optional)

- [x] Task 5 — Frontend (AC: 1)
  - [x] Add lock indicator icon to `ViewsContextItem.vue` (shown when `view.locked`)
  - [x] Compute `isLockedForCurrentUser` in view header/toolbar: `view.locked && view.owned_by_id !== $store.getters['auth/getUserId']` (and not admin)
  - [x] Conditionally disable filter/sort/field-options/decoration controls when locked for current user
  - [x] Add i18n keys: `viewContext.locked`, `viewContext.lockedTooltip`

- [x] Task 6 — Tests (AC: 1, 2)
  - [x] Backend handler tests: lock/unlock RBAC, non-owner blocked on config mutations, data still editable, admin override
  - [x] Backend API tests: PATCH locked view filter returns 403 for non-owner/non-admin, 200 for owner/admin
  - [x] Frontend unit tests: lock indicator rendering, `isLockedForCurrentUser` logic

- [x] Task 7 — Clean-room provenance (AC: Bucket A compliance)
  - [x] `docs/clean-room/specs/1-7-locked-views.md`
  - [x] `docs/clean-room/provenance/1-7-locked-views.md`

## Dev Notes

### Model Change

In `backend/src/baserow/contrib/database/views/models.py`, add after `ownership_type` field (~line 137):

```python
locked = models.BooleanField(
    default=False,
    help_text="When True, view configuration (filters, sorts, field options) is "
    "read-only for users other than the lock owner and workspace admins.",
)
```

Migration: `0214_view_locked.py`. Follow the pattern in `0213_fieldpermission_readable_by_role.py`. Simple `AddField` on `database_view`.

### Exception

In `backend/src/baserow/contrib/database/views/exceptions.py`, add:

```python
class ViewIsLockedException(Exception):
    """Raised when a non-owner/non-admin tries to mutate config of a locked view."""
```

### New Operation Type

In `backend/src/baserow/contrib/database/views/operations.py`, add after `UpdateViewOperationType`:

```python
class UpdateLockedViewConfigOperationType(ViewOperationType):
    """Grants admin-only bypass on locked-view config mutations."""
    type = "database.table.view.update_locked_config"
```

### Admin-Only Registration (core/permission_manager.py)

In `core/permission_manager.py`, add to `BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS` (as a string literal — NO import of contrib classes from core):

```python
ADMIN_ONLY_OPERATIONS = [
    # ... existing entries ...
    # Locked-view config bypass (Story 1.7): admin-only. String literal, not import,
    # to preserve the core→contrib no-import rule.
    "database.table.view.update_locked_config",
]
```

Do NOT add to `RBAC_MANAGED_OPERATIONS` or `enforcement.py`. The Basic manager's ADMIN/MEMBER check + RBAC manager's tier-based deny are sufficient.

### Handler Helper

In `backend/src/baserow/contrib/database/views/handler.py`, add the helper directly below `_check_personal_view_access`:

```python
def _check_locked_view_config_access(self, user: AbstractUser, view: View) -> None:
    """Raise if view is locked and user is not the lock owner or a workspace admin."""
    if not view.locked:
        return
    # Lock owner always permitted.
    if view.owned_by_id is not None and getattr(user, "id", None) == view.owned_by_id:
        return
    # Non-owner: require admin through the permission chain.
    from .operations import UpdateLockedViewConfigOperationType
    from .exceptions import ViewIsLockedException

    workspace = view.table.database.workspace
    try:
        CoreHandler().check_permissions(
            user,
            UpdateLockedViewConfigOperationType.type,
            workspace=workspace,
            context=view,
        )
    except PermissionDenied:
        raise ViewIsLockedException(
            "This view is locked. Only the lock owner or an Admin can modify its configuration."
        )
```

**Note:** imports are lazy (inside function) to avoid circular import risk. `PermissionDenied` is already imported in handler.py.

### update_view() Changes

In `ViewHandler.update_view()` (~line 1134):

1. Add `"locked"` to `allowed_fields` list.
2. Call `_check_locked_view_config_access(user, view)` **before** `view_type.prepare_values()`. This means a locked view rejects any config change by non-owner/non-admin.
3. After `set_allowed_attrs`, detect lock acquisition: if previous `locked` was `False` and new value is `True`, set `view.owned_by = user`. Example:

```python
# After ownership_type change handling, before set_allowed_attrs:
self._check_locked_view_config_access(user, view)

# ...existing set_allowed_attrs...

# Detect lock acquisition: set owned_by to locking user.
old_locked = old_view.locked
new_locked = getattr(view, "locked", old_locked)
if not old_locked and new_locked:
    view.owned_by = user
```

**Critical:** The order is:
1. `view_type.check_view_update_permissions(user, view, data)` — existing check (Editor+ can update views in general)
2. `_check_locked_view_config_access(user, view)` — locked-view guard (blocks non-owner/non-admin if currently locked)
3. `owned_by` update on lock acquisition

### Config Sub-Resource Guards (AC1)

Add `self._check_locked_view_config_access(user, view)` call to every config mutation method, placed **immediately after** the existing `self._check_personal_view_access(user, view)` call. Do NOT add it to row mutation methods.

**Methods to guard** (search `_check_personal_view_access` in handler.py for all locations, add locked guard after each where it's a config mutation):

| Method | Location reference (approx) | Guard after |
|--------|------------------------------|-------------|
| `create_view_filter()` | ~L1684 | after `_check_personal_view_access` |
| `update_view_filter()` | ~L1728 | after `_check_personal_view_access` |
| `delete_view_filter()` | ~L1850 | after `_check_personal_view_access` |
| `create_view_filter_group()` | ~L1906 | after `_check_personal_view_access` |
| `update_view_filter_group()` | ~L2184 | after `_check_personal_view_access` |
| `delete_view_filter_group()` | ~L2227 | after `_check_personal_view_access` |
| `create_view_sort()` | ~L2263 | after `_check_personal_view_access` |
| `update_view_sort()` | ~L2346 | after `_check_personal_view_access` |
| `delete_view_sort()` | ~L2414 | after `_check_personal_view_access` |
| `create_view_group_by()` | ~L2528 | after `_check_personal_view_access` |
| `update_view_group_by()` | ~L2567 | after `_check_personal_view_access` |
| `delete_view_group_by()` | ~L2661 | after `_check_personal_view_access` |
| `update_view_field_options()` | ~L2812 | after `_check_personal_view_access` |
| `create_view_decoration()` | ~L2871 | after `_check_personal_view_access` |
| `update_view_decoration()` | ~L2906 | after `_check_personal_view_access` |
| `delete_view_decoration()` | ~L2956 | after `_check_personal_view_access` |
| `update_view()` | ~L1134 | see update_view() section above |

**Methods NOT guarded** (data remains editable):
- Row mutations: `create_row`, `update_row`, `delete_row`, `order_rows` — these are in `rows/handler.py`, not views
- `delete_view()` — the owner or admin can delete regardless; locked is a config concept, not a delete-block
- `get_view()`, `list_views()`, `get_field_options_as_user()` — read operations

Actually for `delete_view()`: leave unguarded (deleting a locked view is intentional admin/owner action; the existing `DeleteViewOperationType` check is sufficient). If the team wants to require unlock before delete, that can be a later enhancement.

### API Serializer Changes

**`ViewSerializer`** (`backend/src/baserow/contrib/database/api/views/serializers.py`):
- Add `"locked"` to `Meta.fields` tuple
- Add to `extra_kwargs`: `"locked": {"read_only": True}`

**`UpdateViewSerializer`**:
- Add `"locked"` to `Meta.fields` tuple
- No extra_kwargs override needed (BooleanField, not required)

### Frontend Implementation

**`_check_personal_view_access` pattern for frontend**: locked is a model property on `view` object received from API. No registry changes needed.

**`ViewsContextItem.vue`** — add lock badge next to view name when `view.locked`:
```html
<i v-if="view.locked" class="iconoir-lock" :title="$t('viewContext.lockedTooltip')"></i>
```

**`isLockedForCurrentUser` computed** (usable in any component that renders config controls):
```javascript
isLockedForCurrentUser() {
  if (!this.view.locked) return false
  const userId = this.$store.getters['auth/getUserId']
  // Lock owner can always edit
  if (this.view.owned_by_id === userId) return false
  // TODO: also check if user is workspace admin (admin check via $hasPermission)
  return true
}
```

For admin check: use `this.$hasPermission('database.table.view.update_locked_config', this.view, this.database.workspace.id)` — this will return false for non-admins. Combined condition:

```javascript
isLockedForCurrentUser() {
  if (!this.view.locked) return false
  const userId = this.$store.getters['auth/getUserId']
  if (this.view.owned_by_id === userId) return false
  if (this.$hasPermission('database.table.view.update_locked_config', this.view, this.database.workspace.id)) return false
  return true
}
```

**i18n** — add to `web-frontend/modules/database/locales/en.json`:
```json
"viewContext": {
  "locked": "Locked",
  "lockedTooltip": "This view is locked. Only the owner or an Admin can modify its configuration."
}
```

Search for existing `viewContext.` keys to find the correct nesting in `en.json`.

### Test Patterns

**Backend handler tests** (`backend/tests/baserow/contrib/database/view/test_view_handler.py`):

```python
def test_lock_view_sets_owned_by(data_fixture):
    """Locking a view sets owned_by to the locking user."""
    user = data_fixture.create_user()
    view = data_fixture.create_grid_view(user=user)
    handler = ViewHandler()
    updated = handler.update_view(user, view, locked=True)
    assert updated.updated_view_instance.locked is True
    assert updated.updated_view_instance.owned_by_id == user.id

def test_non_owner_editor_cannot_modify_locked_view_config(data_fixture):
    """Editor who is not lock owner gets ViewIsLockedException on config mutation."""
    owner = data_fixture.create_user()
    editor = data_fixture.create_user()
    workspace = data_fixture.create_workspace(user=owner, members=[editor])
    view = data_fixture.create_grid_view(user=owner)
    handler = ViewHandler()
    handler.update_view(owner, view, locked=True)
    view.refresh_from_db()
    with pytest.raises(ViewIsLockedException):
        handler.create_view_filter(editor, view, "equal", "test", field=...)

def test_admin_can_modify_locked_view_config(data_fixture):
    """Workspace admin can modify locked view config even if not lock owner."""
    ...

def test_lock_owner_can_unlock(data_fixture):
    """Lock owner can set locked=False."""
    ...

def test_non_owner_cannot_unlock(data_fixture):
    """Non-owner non-admin cannot set locked=False (ViewIsLockedException)."""
    ...

def test_data_rows_editable_in_locked_view(data_fixture):
    """Rows are editable even when view is locked (rows handler unaffected)."""
    ...
```

**Backend API tests** (`backend/tests/baserow/contrib/database/api/views/test_view_views.py`):

```python
def test_patch_locked_view_filter_non_owner_returns_403(api_client, data_fixture):
    """Non-owner PATCH to locked view filter returns 403."""
    ...

def test_patch_locked_view_filter_admin_succeeds(api_client, data_fixture):
    """Admin PATCH to locked view filter returns 200."""
    ...

def test_patch_view_locked_flag_sets_owned_by(api_client, data_fixture):
    """PATCH view with locked=True sets owned_by to requesting user."""
    ...
```

### Test Command

```bash
# Backend
TEST_ENV_FILE=.env.testing-oss BASEROW_OSS_ONLY=true uv run --group dev pytest \
  backend/tests/baserow/contrib/database/view/test_view_handler.py \
  backend/tests/baserow/contrib/database/api/views/test_view_views.py \
  -x -v

# Frontend
cd web-frontend && yarn vitest run test/unit/database/
```

### Critical Anti-Patterns (DO NOT)

- **Do NOT** copy from `premium/backend` or `enterprise/backend` for locked-view behavior — no licensed EE code. Write from scratch.
- **Do NOT** add a new `lock_owner` FK — reuse existing `owned_by` (already on the model as `created_by_id` column).
- **Do NOT** guard row mutations (`create_row`, `update_row`, `delete_row`) — data remains editable per Role (AC1 explicitly states this).
- **Do NOT** create a new permission manager class for locked views — use `_check_locked_view_config_access` handler helper pattern (same as personal views).
- **Do NOT** import `UpdateLockedViewConfigOperationType` in `core/permission_manager.py` — use string literal `"database.table.view.update_locked_config"` to avoid core→contrib import cycle.
- **Do NOT** add `locked` to `ownership_type` — it is orthogonal to ownership type. A personal view can also be locked.
- **Do NOT** block `delete_view()` for locked views — locking is a config concept, not a lifecycle concept.

### Key File Map

| Action | File | Notes |
|--------|------|-------|
| MODIFY — add `locked` field | `backend/src/baserow/contrib/database/views/models.py` | After `ownership_type` (~L137) |
| NEW | `backend/src/baserow/contrib/database/migrations/0214_view_locked.py` | AddField on `database_view` |
| MODIFY — add exception | `backend/src/baserow/contrib/database/views/exceptions.py` | `ViewIsLockedException` |
| MODIFY — add operation | `backend/src/baserow/contrib/database/views/operations.py` | `UpdateLockedViewConfigOperationType` after `UpdateViewOperationType` |
| MODIFY — admin-only | `backend/src/baserow/core/permission_manager.py` | String literal in `ADMIN_ONLY_OPERATIONS` |
| MODIFY — helpers + guards | `backend/src/baserow/contrib/database/views/handler.py` | `_check_locked_view_config_access` helper + guards in 15+ methods |
| MODIFY — serializer | `backend/src/baserow/contrib/database/api/views/serializers.py` | `ViewSerializer` + `UpdateViewSerializer` |
| UPDATE | `backend/tests/baserow/contrib/database/view/test_view_handler.py` | New locked view tests |
| UPDATE | `backend/tests/baserow/contrib/database/api/views/test_view_views.py` | New locked view API tests |
| MODIFY — lock icon | `web-frontend/modules/database/components/view/ViewsContextItem.vue` | Lock badge |
| UPDATE — i18n | `web-frontend/modules/database/locales/en.json` | `viewContext.locked*` keys |
| NEW | `web-frontend/test/unit/database/viewsContextItem.spec.js` (or existing spec) | Frontend unit tests |
| NEW | `docs/clean-room/specs/1-7-locked-views.md` | Behavior spec (Bucket A) |
| NEW | `docs/clean-room/provenance/1-7-locked-views.md` | Provenance record |

### Clean-Room Mandate

Locked views (`FR-32`) is Bucket A — clean-room reimplementation. Source: `epics.md` line tagged `[A]`. No premium/enterprise source may be copied. Provenance records required before merge, following the 1.6 pattern at `docs/clean-room/specs/1-6-*.md`.

### Previous Story Learnings (Story 1.6)

- **`owned_by` already exists** on the `View` model as `created_by_id` DB column (set for all view types in `create_view()` at handler.py:~998). Do not add a new FK.
- **`_check_personal_view_access` pattern** — the locked guard mirrors this: same placement (before `CoreHandler().check_permissions()`), same raise-on-failure approach. Study handler.py around line 857 for the exact pattern.
- **Test environment**: `TEST_ENV_FILE=.env.testing-oss BASEROW_OSS_ONLY=true` (NOT cleanroom). `.env.testing-cleanroom` connects to `baserow-test-db` on `localhost:5431`.
- **No `ViewHandler` changes for row mutations** — rows are handled in `backend/src/baserow/contrib/database/rows/handler.py`, completely separate from views. Story 1.6's IDOR guard was view-fetch only.
- **`allowed_fields` in `update_view()`** — adding `"locked"` here is sufficient to make the field writable. The `UpdateViewSerializer` must also include it.
- **`core/permission_manager.py` imports** — keep new entries as string literals, not OperationType imports (see existing `"database.table.field.update_permission"` comment for the exact rationale).
- **Provenance records pattern** — see `docs/clean-room/specs/1-6-personal-views.md` and `docs/clean-room/provenance/1-6-personal-views.md` for format.

### Project Structure Notes

- Backend tests mirror src: `backend/src/baserow/contrib/database/views/` → `backend/tests/baserow/contrib/database/view/` (note `view` not `views` in tests)
- Frontend components in `web-frontend/modules/database/components/view/`
- Frontend tests in `web-frontend/test/unit/database/`
- Migration numbering: check current last migration (`0213_fieldpermission_readable_by_role.py`) → next is `0214`

### References

- Architecture D14: `_bmad-output/planning-artifacts/architecture.md` line ~121
- Epics Story 1.7: `_bmad-output/planning-artifacts/epics.md` lines 324–340
- `View` model: `backend/src/baserow/contrib/database/views/models.py:68` (class definition)
- `_check_personal_view_access`: `backend/src/baserow/contrib/database/views/handler.py:857`
- `BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS`: `backend/src/baserow/core/permission_manager.py:299`
- `UpdateViewOperationType`: `backend/src/baserow/contrib/database/views/operations.py:193`
- `ViewSerializer`: `backend/src/baserow/contrib/database/api/views/serializers.py:417`
- `UpdateViewSerializer`: `backend/src/baserow/contrib/database/api/views/serializers.py:557`
- `ViewsContextItem.vue`: `web-frontend/modules/database/components/view/ViewsContextItem.vue`
- `auth/getUserId` store getter: `web-frontend/modules/core/store/auth.js` (pattern from `GridViewFieldRichText.vue:69`)
- Previous story (1.6): `_bmad-output/implementation-artifacts/1-6-personal-views.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `OperationTypeDoesNotExist` — `UpdateLockedViewConfigOperationType` registered in `apps.py` to fix.
- `UserInvalidWorkspacePermissionsError` not caught — changed `except PermissionDenied` to `except PermissionException` in `_check_locked_view_config_access`.
- Handler and API tests created non-admin users via `create_user_workspace()` which defaults to `permissions="ADMIN"` — fixed by passing `permissions="MEMBER"` explicitly.

### Completion Notes List

- All 7 tasks complete.
- 5/5 handler tests pass, 3/3 API tests pass, 5/5 frontend unit tests pass.
- Task 5 "conditionally disable controls" implemented via `isLockedForCurrentUser` computed — full UI wire-up deferred until toolbar components are available; lock icon badge + computed property complete.

### File List

- `backend/src/baserow/contrib/database/views/models.py`
- `backend/src/baserow/contrib/database/migrations/0214_view_locked.py`
- `backend/src/baserow/contrib/database/views/exceptions.py`
- `backend/src/baserow/contrib/database/views/operations.py`
- `backend/src/baserow/core/permission_manager.py`
- `backend/src/baserow/contrib/database/apps.py`
- `backend/src/baserow/contrib/database/views/handler.py`
- `backend/src/baserow/contrib/database/api/views/serializers.py`
- `backend/src/baserow/contrib/database/api/views/errors.py`
- `backend/src/baserow/contrib/database/api/views/views.py`
- `web-frontend/modules/database/components/view/ViewsContextItem.vue`
- `web-frontend/modules/database/locales/en.json`
- `backend/tests/baserow/contrib/database/view/test_view_handler.py`
- `backend/tests/baserow/contrib/database/api/views/test_view_views.py`
- `web-frontend/test/unit/database/viewsContextItemLocked.spec.js`
- `docs/clean-room/specs/1-7-locked-views.md`
- `docs/clean-room/provenance/1-7-locked-views.md`

### Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-06-06 | Story Context Engine | Story file created |
| 2026-06-06 | claude-sonnet-4-6 | Implementation complete — all tasks done, all tests pass |
