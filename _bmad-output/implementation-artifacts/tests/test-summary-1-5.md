# Test Automation Summary — Story 1.5: Field Visibility Hiding, Inference-Oracle Guard, Cache Invalidation

**Date:** 2026-06-06
**Frameworks:** pytest (backend), vitest (frontend)
**Test runner:** `cd backend && TEST_ENV_FILE=.env.testing-oss PYTHONPATH="src:../premium/backend/src:tests:../premium/backend/tests" uv run --group dev pytest {test_paths}`

---

## Gap Tests Added (4 new)

Added to `backend/tests/baserow/contrib/database/api/test_field_visibility_api.py`:

### API / Integration Tests

- [x] `tests/baserow/contrib/database/api/test_field_visibility_api.py::test_grid_view_omits_hidden_field_for_below_threshold` — Grid view endpoint redaction (AC #1 surface parity)
- [x] `tests/baserow/contrib/database/api/test_field_visibility_api.py::test_gallery_view_omits_hidden_field_for_below_threshold` — Gallery view endpoint redaction (AC #1 surface parity)
- [x] `tests/baserow/contrib/database/api/test_field_visibility_api.py::test_member_cannot_update_sort_to_hidden_field` — `update_sort` inference-oracle guard (AC #2 parity with `update_filter`)
- [x] `tests/baserow/contrib/database/api/test_field_visibility_api.py::test_ws_broadcast_excludes_hidden_field_ids` — WS broadcast `_visibility_restricted_field_ids` redaction (AC #3)

---

## Full Coverage

### Backend test_field_visibility_api.py (20 tests — was 16, +4 gaps)

AC #1 REST redaction: row list, row get, include= override, grid view, gallery view
AC #1 Search oracle guard: hidden value no hit, admin sees hit, visible field still hits
AC #2 Inference-oracle guard: create_filter, create_sort, update_filter, update_sort, admin bypass, over-block guard
AC #3 Cache + live-session: cache invalidation, same-session redaction, WS broadcast exclusion
NFR-4 Single path: central redactor, no-rules no-regression

### Backend test_permission_manager.py (18 tests)

Write/edit ops, read ops, filter_queryset, get_permissions_object, N+1 guards

### Backend test_field_permission_model.py (9 tests)

Table, one-to-one, cascade, readable_by_role column, null default, independent round-trip

### Frontend permissionManagerTypes.spec.js (12 tests)

RbacPermissionManagerType (3), FieldPermissionManagerType (9 including 5 Story 1.5-specific)

---

## Coverage

| Surface | Status |
|---------|--------|
| REST rows list (viewless) | ✅ |
| REST rows get (single) | ✅ |
| REST include= override blocked | ✅ |
| Grid view list | ✅ NEW |
| Gallery view list | ✅ NEW |
| Search (no oracle inference) | ✅ |
| ViewHandler.create_filter | ✅ |
| ViewHandler.create_sort | ✅ |
| ViewHandler.update_filter | ✅ |
| ViewHandler.update_sort | ✅ NEW |
| WS broadcast field exclusion | ✅ NEW |
| Cache invalidation on change | ✅ |
| Live-session redaction after change | ✅ |
| Central redactor single path (NFR-4) | ✅ |
| Frontend column hiding | ✅ |

## Results

| Suite | Pass | Fail | Total |
|-------|------|------|-------|
| Backend (story 1.5) | 47 | 0 | 47 |
| Frontend | 12 | 0 | 12 |
| **Total** | **59** | **0** | **59** |

## Test Runner Setup

`.env.testing-oss` updated with local `baserow-test-db` container connection (port 5431).

```bash
cd backend && TEST_ENV_FILE=.env.testing-oss \
  PYTHONPATH="src:../premium/backend/src:tests:../premium/backend/tests" \
  uv run --group dev pytest \
  tests/baserow/contrib/database/api/test_field_visibility_api.py \
  tests/baserow/core/field_permissions/test_permission_manager.py \
  tests/baserow/contrib/database/field/test_field_permission_model.py \
  -v -q
```

Frontend:
```bash
cd web-frontend && node_modules/.bin/vitest run test/unit/core/permissionManagerTypes.spec.js
```
