# Test Automation Summary — Story 1.9: Exports Honor Field Permissions

## Generated Tests

### Backend API / Integration Tests
- [x] `backend/tests/baserow/contrib/database/api/export/test_export_views.py::test_export_table_hides_permission_restricted_field` — MEMBER user table export omits ADMIN-restricted field (AC #1)
- [x] `backend/tests/baserow/contrib/database/api/export/test_export_views.py::test_export_view_hides_permission_restricted_field` — MEMBER user view export omits ADMIN-restricted field (AC #1)
- [x] `backend/tests/baserow/contrib/database/api/export/test_export_views.py::test_export_no_field_permissions_exports_all_fields` — No FieldPermission rows → all fields present (regression guard, AC #1)
- [x] `backend/tests/baserow/contrib/database/api/export/test_export_views.py::test_export_anonymous_public_view_hides_restricted_field` — Anonymous export job (user=None) omits ADMIN-restricted field (AC #2)

## Coverage
- Backend export field-permission path: 4/4 tests, all passing
- AC #1 (table export): covered by tests 1, 2, 3
- AC #2 (anonymous/public export): covered by test 4
- Regression guard (no permissions = all fields): covered by test 3

## Bugs Found and Fixed

### Bug 1: `FieldPermissionManagerType.supported_actor_types` missing `"anonymous"`
**File:** `backend/src/baserow/core/field_permissions/permission_manager.py`
**Impact:** `AnonymousUser` actors bypassed `FieldPermissionManagerType.filter_queryset` entirely — `get_hidden_field_ids(AnonymousUser(), table)` always returned empty set, so anonymous public exports leaked all field data regardless of `FieldPermission` rules.
**Fix:** Added `AnonymousUserSubjectType.type` to `supported_actor_types`.

### Bug 2: `premium/apps.py` double-registered `PersonalViewOwnershipType`
**File:** `premium/backend/src/baserow_premium/apps.py`
**Impact:** Story 1.6 moved `PersonalViewOwnershipType` to the free backend but premium still registered it, causing `InstanceTypeAlreadyRegistered` on startup and blocking all local test runs.
**Fix:** Removed the premium registration; backend registers it once.

### Bug 3: `enterprise/apps.py` double-registered `AssignRoleWorkspaceOperationType`
**File:** `enterprise/backend/src/baserow_enterprise/apps.py`
**Impact:** RBAC story moved `AssignRoleWorkspaceOperationType` to free backend but enterprise still registered it, causing `OperationTypeAlreadyRegistered` on startup.
**Fix:** Removed the enterprise registration; backend registers it once.

### Bug 4: Tests read `exported_file_name` from POST response (always `null`)
**File:** `backend/tests/baserow/contrib/database/api/export/test_export_views.py`
**Impact:** Tests 3.1–3.3 read `filename = response.json()["exported_file_name"]` from the initial POST response, which is always `null`. They should GET the job after `django_capture_on_commit_callbacks` completes.
**Fix:** Added `api_client.get(reverse("api:database:export:get", kwargs={"job_id": ...}))` after callbacks to retrieve the completed filename.

## Test Results
```
14 passed, 353 warnings in 8.53s
```
All 14 export tests pass (10 pre-existing + 4 new story 1.9 tests).

## Next Steps
- Run full test suite in CI to validate no broader regressions from the 3 double-registration fixes
