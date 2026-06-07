# Test Automation Summary — Story 1.6: Personal Views

**Date:** 2026-06-06
**Frameworks:** pytest (backend), vitest (frontend)
**Test runner:** `cd backend && TEST_ENV_FILE=.env.testing-oss PYTHONPATH="src:../premium/backend/src:tests:../premium/backend/tests" uv run --group dev pytest {test_paths}`

---

## Gap Tests Added (6 new)

### API / Integration Tests

Added to `backend/tests/baserow/contrib/database/api/views/test_view_views.py`:

- [x] `test_list_views_excludes_others_personal_views` — Non-owner list for a table excludes personal views owned by a different user; collaborative views still appear
- [x] `test_patch_personal_view_non_owner_returns_401` — Non-owner PATCH of a personal view returns 401; owner PATCH succeeds and renames view
- [x] `test_delete_personal_view_non_owner_returns_401` — Non-owner DELETE of a personal view returns 401; owner DELETE returns 204
- [x] `test_create_personal_view_via_post` — POST with `ownership_type=personal` creates a personal view owned by the caller

Added to `backend/tests/baserow/contrib/database/api/views/test_view_filter.py`:

- [x] `test_create_filter_personal_view_non_owner_returns_401` — Non-owner POST filter on a personal view returns 401; owner POST filter succeeds

Added to `backend/tests/baserow/contrib/database/api/views/test_view_sort.py`:

- [x] `test_create_sort_personal_view_non_owner_returns_401` — Non-owner POST sort on a personal view returns 401; owner POST sort succeeds

---

## Full Coverage

### Previously existing tests (passing before this session)

**Handler tests** (`test_view_handler.py`) — 16 ownership tests:
- `test_list_views_ownership_type`, `test_get_view_ownership_type`, `test_create_view_ownership_type`
- `test_personal_view_idor_list_filter`, `test_personal_view_toggle_back_to_collaborative`
- `test_update_view_ownership_type_non_existing`, `test_duplicate_view_ownership_type`
- `test_delete_view_ownership_type`, `test_field_options_view_ownership_type`
- `test_filters_view_ownership_type`, `test_sorts_view_ownership_type`
- `test_decorations_view_ownership_type`, `test_aggregations_view_ownership_type`
- `test_update_view_slug_ownership_type`, `test_get_public_view_ownership_type`
- `test_order_views_ownership_type`

**API tests** (`test_view_views.py`) — 3 existing ownership tests:
- `test_list_views_ownership_type` — owner sees own personal view in list
- `test_personal_view_idor_api` — non-owner GET returns 401, owner GET returns 200 with `ownership_type=personal`
- `test_patch_view_validate_ownership_type_invalid_type` — invalid ownership type string returns 400

**Frontend unit tests** (`viewOwnershipTypes.spec.js`) — 9 tests:
- `PersonalViewOwnershipType` class: `isOwner`, `getOwnershipBadgeTitle`, `canCreateNewType`, `canChangeType`, `getFeatureName`, `canImportView`, `getPublicViewAuthToken`, `updateContext`, `getListenToAllProperties`

---

## Coverage Map

| Surface | Guard tested | Status |
|---------|-------------|--------|
| `GET /views/{id}/` as non-owner | IDOR block | ✅ existing |
| `GET /views/?table_id=` as non-owner | Excludes personal views | ✅ **NEW** |
| `POST /views/table/{id}/` with `ownership_type=personal` | Creates personal view | ✅ **NEW** |
| `PATCH /views/{id}/` as non-owner | 401 | ✅ **NEW** |
| `DELETE /views/{id}/` as non-owner | 401 | ✅ **NEW** |
| `POST /views/{id}/filters/` as non-owner | 401 | ✅ **NEW** |
| `POST /views/{id}/sortings/` as non-owner | 401 | ✅ **NEW** |
| Handler `list_views()` filter | Queryset excludes others' personal | ✅ existing (handler) |
| Handler `_check_personal_view_access()` | 15+ methods guarded | ✅ existing (handler) |
| Frontend `PersonalViewOwnershipType` | All interface methods | ✅ existing (vitest) |

---

## Results

| Suite | File | New tests | Pass |
|-------|------|-----------|------|
| API | `test_view_views.py` | 4 | ✅ 4/4 |
| API | `test_view_filter.py` | 1 | ✅ 1/1 |
| API | `test_view_sort.py` | 1 | ✅ 1/1 |
| **Total new** | | **6** | ✅ 6/6 |

---

## Test Runner Commands

```bash
# All 6 new gap tests
cd backend && TEST_ENV_FILE=.env.testing-oss \
  PYTHONPATH="src:../premium/backend/src:tests:../premium/backend/tests" \
  uv run --group dev pytest \
  tests/baserow/contrib/database/api/views/test_view_views.py::test_list_views_excludes_others_personal_views \
  tests/baserow/contrib/database/api/views/test_view_views.py::test_patch_personal_view_non_owner_returns_401 \
  tests/baserow/contrib/database/api/views/test_view_views.py::test_delete_personal_view_non_owner_returns_401 \
  tests/baserow/contrib/database/api/views/test_view_views.py::test_create_personal_view_via_post \
  tests/baserow/contrib/database/api/views/test_view_filter.py::test_create_filter_personal_view_non_owner_returns_401 \
  tests/baserow/contrib/database/api/views/test_view_sort.py::test_create_sort_personal_view_non_owner_returns_401 \
  -v
```
