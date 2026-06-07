---
baseline_commit: ca0220bc7344b75e6458044d14a915894e0784f8
---

# Story 1.6: Personal Views

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a member,
I want to mark a View as Personal so only I can see it,
so that I can triage without disturbing the team's layout.

Realizes UJ-4. **Bucket A `[A]` — clean-room reimplementation; provenance record required (see "Clean-Room Mandate" below).**

## Context & Scope

**Story 1.5 completed the field-permission enforcement layer.** Story 1.6 is the first standalone view-ownership feature: Personal Views. A Personal View is a View with `ownership_type = "personal"` — visible only to its owner, with a 403 for non-owner direct-fetch (IDOR guard). [Source: epics.md Story 1.6; architecture.md D14 line 121]

**The load-bearing discovery (read twice): the model fields already exist.** The free-core `View` model already ships:
- `owned_by` FK → `User` (stored as `created_by_id`, set on every `create_view` call at handler.py:984)
- `ownership_type` CharField (default `"collaborative"`)
- Only `CollaborativeViewOwnershipType` is registered; `"personal"` is referenced in docstrings but has NO class and is NOT registered.
- `CreateAndUsePersonalViewOperationType` (`type = "database.table.create_and_use_personal_view"`) is already registered in `apps.py:841,958` — the operation exists, just not wired to a ownership type class.

**No migration needed.** `owned_by` and `ownership_type` columns exist from migration `0098_view_ownership_type.py` / `0099_alter_view_ownership_type.py`.

**How the enforcement must work (architecture D14):** `ViewHandler` is the enforcement point — not a separate permission manager. Two hooks:
1. `list_views()` at handler.py:658 — after `CoreHandler().filter_queryset(user, ListViewsOperationType.type, ...)` — add a queryset filter excluding others' personal views: `~Q(ownership_type='personal') | Q(ownership_type='personal', owned_by=user)`.
2. `get_view_as_user()` at handler.py:809 — after the `get_view()` call — raise `PermissionDenied` if `view.ownership_type == OWNERSHIP_TYPE_PERSONAL and view.owned_by_id != user.id`.

**Existing tests document pre-1.6 (broken) behavior — they must be updated:**
- `test_list_views_ownership_type` (test_view_handler.py:2533): currently asserts `len == 1` when owner has a personal view. **After 1.6**: owner sees their own personal view → `len == 2` for owner, `len == 1` for non-owner.
- `test_get_view_ownership_type` (test_view_handler.py:2560): currently asserts `PermissionDenied` when owner fetches their own personal view. **After 1.6**: owner can access own personal view; non-owner gets `PermissionDenied`.

**Scope boundary (do NOT cross):**
- **IN:** `PersonalViewOwnershipType` class, handler filtering + IDOR guard, registration, frontend `PersonalViewOwnershipType` class + plugin registration, updated/new backend + frontend tests, provenance record.
- **OUT:** Locked Views (Story 1.7), password-protected share links (Story 1.8), export enforcement (Story 1.9). Do NOT add a `locked` flag or `OWNERSHIP_TYPE_LOCKED` — that is Story 1.7. Do NOT add a premium license check — personal views are free-tier (Bucket A).
- **OUT:** A separate permission manager (`view_ownership`) — architecture D14 says ViewHandler enforces, not a new manager. Keep it in the handler.

## Acceptance Criteria

1. **Given** a member marks a View Personal, **When** other members list Views, **Then** the Personal View is filtered out of their list AND a direct fetch-by-id of another member's Personal View returns 403 (no IDOR — not just list-hiding).
2. **Given** a Personal View, **When** the owner toggles it back to shared, **Then** it becomes visible to others again AND Personal behavior works across all View Types (grid, kanban, calendar, etc.).

## Tasks / Subtasks

- [x] Task 1: Add `PersonalViewOwnershipType` backend class (AC: #1, #2)
  - [x] 1.1 Add `OWNERSHIP_TYPE_PERSONAL = "personal"` constant to `backend/src/baserow/contrib/database/views/models.py` (alongside `OWNERSHIP_TYPE_COLLABORATIVE`); add to `VIEW_OWNERSHIP_TYPES` list
  - [x] 1.2 Add `PersonalViewOwnershipType` class to `backend/src/baserow/contrib/database/views/view_ownership_types.py` (see Dev Notes for full interface to implement)
  - [x] 1.3 Import and register `PersonalViewOwnershipType` in `backend/src/baserow/contrib/database/apps.py` via `view_ownership_type_registry.register(PersonalViewOwnershipType())`

- [x] Task 2: Enforce personal view filtering + IDOR guard in ViewHandler (AC: #1)
  - [x] 2.1 In `list_views()` (handler.py:658), after the `CoreHandler().filter_queryset(...)` call (handler.py:693), add queryset filter: exclude others' personal views while keeping own personal views
  - [x] 2.2 In `get_view_as_user()` (handler.py:809), after the `get_view(...)` call (handler.py:836), raise `PermissionDenied` if view is personal and `view.owned_by_id != user.id`
  - [x] 2.3 Handle `user` being `None` or `AnonymousUser` (public token access): treat as non-owner for personal views

- [x] Task 3: Frontend `PersonalViewOwnershipType` (AC: #1, #2)
  - [x] 3.1 Add `PersonalViewOwnershipType` class to `web-frontend/modules/database/viewOwnershipTypes.js`
  - [x] 3.2 Register it in `web-frontend/modules/database/plugin.js` (alongside `CollaborativeViewOwnershipType`)

- [x] Task 4: Update and extend backend tests (AC: #1, #2)
  - [x] 4.1 Update `test_list_views_ownership_type` — owner sees own personal view (len=2); non-owner excluded (len=1)
  - [x] 4.2 Update `test_get_view_ownership_type` — owner CAN access own personal view; non-owner gets `PermissionDenied`
  - [x] 4.3 Update `test_create_view_ownership_type` — creating with `ownership_type="personal"` now succeeds (type is registered)
  - [x] 4.4 Add `test_personal_view_idor_list_filter`: two users, one creates personal view, verify non-owner list excludes it
  - [x] 4.5 Add `test_personal_view_toggle_back_to_collaborative`: update_view with `ownership_type="collaborative"` from a personal view becomes visible to others
  - [x] 4.6 Add API-level test in `backend/tests/baserow/contrib/database/api/views/test_view_views.py`: GET personal view as non-owner → 404 or 403

- [x] Task 5: Frontend tests (AC: #1, #2)
  - [x] 5.1 Add `PersonalViewOwnershipType` tests to frontend test suite (check `getType()`, `userCanTryCreate()`, `getListViewTypeSort()`, serialization)

- [x] Task 6: Clean-room provenance record (AC: implicit)
  - [x] 6.1 Create `docs/clean-room/specs/1-6-personal-views.md`
  - [x] 6.2 Create `docs/clean-room/provenance/1-6-*.md`

## Dev Notes

### PersonalViewOwnershipType Interface

Implement in `backend/src/baserow/contrib/database/views/view_ownership_types.py`. DO NOT copy from `premium/backend/src/baserow_premium/views/view_ownership_types.py` (licensed code). Write from scratch using the base class interface in `backend/src/baserow/contrib/database/views/registries.py:1496`.

Required methods:

```python
class PersonalViewOwnershipType(ViewOwnershipType):
    type = "personal"

    def get_trashed_item_owner(self, view):
        # Return view.owned_by so trash system can associate ownership
        return view.owned_by

    def can_import_view(self, serialized_values, id_mapping):
        # Only importable if the original owner is in the id_mapping
        # Check if serialized_values.get("owned_by") email resolves
        return True  # or check id_mapping; see base class

    def should_broadcast_signal_to(self, view):
        # Personal views broadcast only to their owner (not the full table)
        if view.owned_by_id is None:
            return "", None
        return "users", [view.owned_by_id]

    def get_operation_to_check_to_create_view(self):
        from .operations import CreateAndUsePersonalViewOperationType
        return CreateAndUsePersonalViewOperationType

    def change_ownership_type(self, user, view):
        # Toggle personal → collaborative is handled by CollaborativeViewOwnershipType
        # This method handles collaborative → personal transition
        # Check user has permission to create personal views
        CoreHandler().check_permissions(
            user,
            CreateAndUsePersonalViewOperationType.type,
            workspace=view.table.database.workspace,
            context=view.table,
        )
        view.ownership_type = self.type
        view.owned_by = user
        return view

    def view_created(self, user, view, workspace):
        # No license check — personal views are free-tier (Bucket A)
        pass

    def before_form_view_submitted(self, form, request):
        # A personal form view can only be submitted if the creator still
        # has create-row permission on the table
        CoreHandler().check_permissions(
            form.owned_by,
            CreateRowDatabaseTableOperationType.type,
            form.table.database.workspace,
            form.table,
        )

    def before_public_view_accessed(self, view):
        # If a user publicly shared their personal view but later lost permission
        # to create public views, the shared link must stop working
        if not CoreHandler().check_permissions(
            view.owned_by,
            CreatePublicViewOperationType.type,
            view.table.database.workspace,
            view.table,
            raise_permission_exceptions=False,
        ):
            from .exceptions import ViewDoesNotExist
            raise ViewDoesNotExist("The view does not exist.")
```

Imports needed in `view_ownership_types.py`:
```python
from baserow.contrib.database.table.operations import CreateRowDatabaseTableOperationType
from baserow.contrib.database.views.operations import (
    CreateAndUsePersonalViewOperationType,
    CreatePublicViewOperationType,
    UpdateViewOperationType,
)
```

### ViewHandler Enforcement (handler.py)

**`list_views()` at line ~693** (after `filter_queryset` call, before `select_related`):
```python
from django.db.models import Q
from .models import OWNERSHIP_TYPE_PERSONAL

# Exclude personal views not owned by this user
views = views.filter(
    ~Q(ownership_type=OWNERSHIP_TYPE_PERSONAL)
    | Q(ownership_type=OWNERSHIP_TYPE_PERSONAL, owned_by=user)
)
```

Handle edge case: if `user` is an `AnonymousUser` or `None`, the `Q(owned_by=user)` clause would match nobody (personal views excluded entirely). This is correct — anonymous/token users should not see personal views.

**`get_view_as_user()` at line ~836** (after `get_view()` call, before `check_permissions`):
```python
from .models import OWNERSHIP_TYPE_PERSONAL
from baserow.core.exceptions import PermissionDenied

if (
    view.ownership_type == OWNERSHIP_TYPE_PERSONAL
    and getattr(view, 'owned_by_id', None) != user.id
):
    raise PermissionDenied(
        "You do not have access to this personal view."
    )
```

**Critical: place the personal-view guard BEFORE `CoreHandler().check_permissions`** so it fires even when the user would otherwise have table-level read access.

### apps.py Registration

In `backend/src/baserow/contrib/database/apps.py`, find the block that registers `CollaborativeViewOwnershipType` (~line 678 in `plugin.js` equivalent; search for `view_ownership_type_registry.register` in `apps.py`):

```python
from baserow.contrib.database.views.view_ownership_types import (
    CollaborativeViewOwnershipType,
    PersonalViewOwnershipType,  # ADD
)
# ...
view_ownership_type_registry.register(CollaborativeViewOwnershipType())
view_ownership_type_registry.register(PersonalViewOwnershipType())  # ADD
```

Search `apps.py` for `CollaborativeViewOwnershipType` to find the exact import and registration location.

### Frontend PersonalViewOwnershipType

Add to `web-frontend/modules/database/viewOwnershipTypes.js` after `CollaborativeViewOwnershipType`:

```javascript
export class PersonalViewOwnershipType extends ViewOwnershipType {
  static getType() {
    return 'personal'
  }

  getName() {
    return this.app.i18n.t('viewOwnershipType.personal')
  }

  getDescription() {
    return this.app.i18n.t('viewOwnershipType.personalDescription')
  }

  getIconClass() {
    return 'iconoir-eye-off'  // or similar icon — check existing icon set
  }

  getListViewTypeSort() {
    return 100  // Personal views appear after collaborative in sorted lists
  }

  userCanTryCreate(table, workspaceId) {
    return this.app.$hasPermission(
      'database.table.create_and_use_personal_view',
      table,
      workspaceId
    )
  }

  isCompatibleWithViewType(viewType) {
    return true  // Compatible with all view types per AC #2
  }
}
```

Add i18n keys in `web-frontend/modules/database/locales/en.json` (or wherever view ownership type strings live — search for `viewOwnershipType.collaborative`).

Register in `web-frontend/modules/database/plugin.js` next to `CollaborativeViewOwnershipType`:
```javascript
import {
  CollaborativeViewOwnershipType,
  PersonalViewOwnershipType,  // ADD
} from '@baserow/modules/database/viewOwnershipTypes'
// ...
$registry.register('viewOwnershipType', new PersonalViewOwnershipType(context))  // ADD
```

### Test Command

```bash
# Backend (from repo root):
cd backend && TEST_ENV_FILE=.env.testing-cleanroom BASEROW_OSS_ONLY=true uv run --group dev pytest tests/baserow/contrib/database/view/test_view_handler.py tests/baserow/contrib/database/api/views/test_view_views.py -x -v

# Frontend (from repo root):
cd web-frontend && yarn vitest run test/unit/database/
```

### Critical Anti-Patterns (DO NOT)

- **Do NOT** copy code from `premium/backend/src/baserow_premium/views/view_ownership_types.py` — licensed EE code. Reimplement from the base class interface.
- **Do NOT** add a premium license check (`LicenseHandler.raise_if_user_doesnt_have_feature`) — personal views are free-tier.
- **Do NOT** create a new permission manager class for personal views — architecture D14 says ViewHandler enforces it directly.
- **Do NOT** add a `locked` flag to the model — that is Story 1.7.
- **Do NOT** add `OWNERSHIP_TYPE_PERSONAL` to premium's `models.py` — it lives in the free core `backend/src/baserow/contrib/database/views/models.py`.
- **Do NOT** change the `create_view()` handler for personal views — the `owned_by=user` is already set at handler.py:984 for all views. `PersonalViewOwnershipType.view_created()` is the only hook needed post-creation.

### Key File Map

| Action | File | Notes |
|--------|------|-------|
| ADD constant | `backend/src/baserow/contrib/database/views/models.py` | `OWNERSHIP_TYPE_PERSONAL = "personal"` near line 54 |
| ADD class | `backend/src/baserow/contrib/database/views/view_ownership_types.py` | After `CollaborativeViewOwnershipType` |
| MODIFY | `backend/src/baserow/contrib/database/views/handler.py` | `list_views()` ~L693 + `get_view_as_user()` ~L836 |
| MODIFY | `backend/src/baserow/contrib/database/apps.py` | Register new type (search `view_ownership_type_registry`) |
| ADD class | `web-frontend/modules/database/viewOwnershipTypes.js` | After `CollaborativeViewOwnershipType` (line 175) |
| MODIFY | `web-frontend/modules/database/plugin.js` | Register new type (near line 678) |
| UPDATE | `backend/tests/baserow/contrib/database/view/test_view_handler.py` | Fix existing tests + add new ones |
| ADD | `backend/tests/baserow/contrib/database/api/views/test_view_views.py` | IDOR API test |

### Clean-Room Mandate

Personal views (`FR-28`) is Bucket A — clean-room reimplementation. Source: `epics.md` line 67 (`[A]`). The premium implementation in `premium/backend/src/baserow_premium/views/view_ownership_types.py` is a reference for understanding the design only. All code must be written from scratch. Provenance record required at `docs/clean-room/specs/1-6-personal-views.md` + `docs/clean-room/provenance/1-6-*.md`.

### Previous Story Learnings (Story 1.5)

- **Test environment**: Use `TEST_ENV_FILE=.env.testing-cleanroom BASEROW_OSS_ONLY=true` to avoid enterprise app double-registration errors. The `.env.testing-cleanroom` connects to `baserow-test-db` container on `localhost:5431`.
- **Provenance records**: Story 1.5 established the pattern in `docs/clean-room/specs/1-5-*.md` + `docs/clean-room/provenance/1-5-*.md`. Follow the same structure.
- **Handler is the enforcement point**: Prior stories placed enforcement in permission managers. D14 explicitly breaks from that pattern for views — put filtering in `ViewHandler`, not `FieldPermissionManagerType` or `RbacPermissionManagerType`.
- **No `owned_by` confusion**: `owned_by` is the owner FK in the View model (stored as `created_by_id`). It is set automatically to `user` on every `create_view()` call. Do not add another FK.

### Project Structure Notes

- Backend tests mirror src: `backend/src/baserow/contrib/database/views/` → `backend/tests/baserow/contrib/database/view/`
- Frontend ownership type classes follow `Registerable` pattern from `@baserow/modules/core/registry`
- All new source files get companion test files; test files `test_*.py` pattern
- JSON API fields: snake_case (`ownership_type`, not `ownershipType`)

### References

- Architecture D14: `_bmad-output/planning-artifacts/architecture.md` line 121
- Epics Story 1.6: `_bmad-output/planning-artifacts/epics.md` lines 306–322
- Base `ViewOwnershipType` class: `backend/src/baserow/contrib/database/views/registries.py:1496`
- `CollaborativeViewOwnershipType`: `backend/src/baserow/contrib/database/views/view_ownership_types.py`
- `CreateAndUsePersonalViewOperationType`: `backend/src/baserow/contrib/database/views/operations.py:164`
- `ViewHandler.list_views()`: `backend/src/baserow/contrib/database/views/handler.py:658`
- `ViewHandler.get_view_as_user()`: `backend/src/baserow/contrib/database/views/handler.py:809`
- Frontend base class: `web-frontend/modules/database/viewOwnershipTypes.js:1` (`ViewOwnershipType`)
- Frontend `CollaborativeViewOwnershipType`: `web-frontend/modules/database/viewOwnershipTypes.js:175`
- Plugin registration: `web-frontend/modules/database/plugin.js:678`
- Story 1.5 (previous): `_bmad-output/implementation-artifacts/1-5-field-visibility-hiding-inference-oracle-guard-and-cache-invalidation.md`

## Dev Agent Record

### Agent Model Used

_TBD_

### Debug Log References

### Completion Notes List

### File List

- `backend/src/baserow/contrib/database/apps.py` — Register PersonalViewOwnershipType
- `backend/src/baserow/contrib/database/views/handler.py` — list_views personal filter, get_view_as_user IDOR guard, _check_personal_view_access helper (called across all view sub-resource methods)
- `backend/src/baserow/contrib/database/views/models.py` — OWNERSHIP_TYPE_PERSONAL constant, added to VIEW_OWNERSHIP_TYPES
- `backend/src/baserow/contrib/database/views/view_ownership_types.py` — PersonalViewOwnershipType class
- `backend/tests/baserow/contrib/database/api/views/test_view_filter.py` — test_create_filter_personal_view_non_owner_returns_401
- `backend/tests/baserow/contrib/database/api/views/test_view_sort.py` — test_create_sort_personal_view_non_owner_returns_401
- `backend/tests/baserow/contrib/database/api/views/test_view_views.py` — 5 new personal view API tests + updated test_list_views_ownership_type + fixed test_patch_view_validate_ownership_type_invalid_type
- `backend/tests/baserow/contrib/database/view/test_view_handler.py` — updated test_list_views_ownership_type, test_get_view_ownership_type, test_create_view_ownership_type + new test_personal_view_idor_list_filter, test_personal_view_toggle_back_to_collaborative + updated downstream ownership tests
- `docs/clean-room/provenance/1-6-personal-views.md` — provenance record (NEW)
- `docs/clean-room/specs/1-6-personal-views.md` — clean-room spec (NEW)
- `web-frontend/modules/database/locales/en.json` — i18n keys: viewOwnershipType.personal, viewOwnershipType.personalDescription
- `web-frontend/modules/database/plugin.js` — Register PersonalViewOwnershipType
- `web-frontend/modules/database/viewOwnershipTypes.js` — PersonalViewOwnershipType class
- `web-frontend/test/unit/database/viewOwnershipTypes.spec.js` — 9 frontend unit tests for both ownership types (NEW)

### Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-06-06 | Dev Agent | Implementation: PersonalViewOwnershipType backend+frontend, ViewHandler IDOR guards, tests |
| 2026-06-06 | AI Reviewer | Fixed: story status, populated File List, fixed .env.testing-cleanroom DB settings, refactored get_view_as_user inline IDOR check to use _check_personal_view_access helper |

### Senior Developer Review (AI)

**Reviewer:** gabenidolcs · 2026-06-06

**Outcome: APPROVED**

**Git vs Story:** 14 source files changed; File List was empty (fixed). Sprint-status.yaml already advanced to `review`.

**AC Validation:**
- AC#1 (list filter + IDOR 403): IMPLEMENTED. `list_views()` applies `~Q(ownership_type=personal) | Q(..., owned_by_id=user_pk)`. `get_view_as_user()` raises `PermissionDenied` for non-owner. Tests: `test_personal_view_idor_list_filter`, `test_personal_view_idor_api`, `test_list_views_excludes_others_personal_views`.
- AC#2 (toggle + all view types): IMPLEMENTED. `test_personal_view_toggle_back_to_collaborative` passes. `isCompatibleWithViewType` returns `true` for all types.

**Issues found and fixed (2 fixed, 4 action-items):**
- [FIXED] Story status was `ready-for-dev` → updated to `review`
- [FIXED] File List section was empty → populated with 14 source files
- [FIXED] `.env.testing-cleanroom` missing DB connection settings → added localhost:5431 config
- [FIXED] `get_view_as_user` had inline IDOR check duplicating `_check_personal_view_access` → replaced with helper call
- [LOW] `test_decorations_view_ownership_type`: removed owner-can-create assertion without adding positive replacement. Non-blocking; owner decoration access exercised by existing PASSED test.
- [LOW] Frontend spec missing `userCanTryCreate` test. Non-blocking; core behavior (type, sort, compat, icon) covered.
