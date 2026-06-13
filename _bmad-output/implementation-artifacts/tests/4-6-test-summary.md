# Test Summary: Story 4.6 — Dashboard Public Share with Least-Privilege Principal

## Coverage

| Layer | File | Tests | Status |
|---|---|---|---|
| Backend API | `backend/tests/baserow/contrib/dashboard/api/test_dashboard_share.py` | 8 | ✅ All pass |
| E2E (API-level) | `e2e-tests/tests/dashboard/dashboard_share.spec.ts` | 7 | Requires Docker e2e stack |

## Acceptance Criteria Coverage

| AC | Description | Backend test | E2E test |
|---|---|---|---|
| AC #1 | Public link with share principal enforcement | `test_enable_sharing_sets_public_true`, `test_public_dashboard_returns_dashboard_info` | "Enable sharing returns public=true and slug; anonymous GET returns dashboard info" |
| AC #2 | Immediate revocation via public=False | `test_disable_sharing_sets_public_false` | "Disable sharing causes public GET to return 401" |
| AC #3 | Slug rotation invalidates old link | `test_rotate_slug_invalidates_old_slug` | "Rotate slug invalidates old link; new link returns 200" |
| AC #4 | Public dispatch runs as AnonymousUser | `test_public_dispatch_unconfigured_returns_400` (400 not 401 = AnonymousUser accepted), `test_public_dispatch_requires_public_true` | "Public dispatch endpoint reachable without auth", "Public dispatch on non-public dashboard returns 401" |
| AC #5 | Widgets render read-only (widgets in response) | `test_public_dashboard_returns_dashboard_info` | "Public dashboard response includes widgets and data_sources arrays" |
| AC #6 | Share UI gated by update permission | `test_enable_sharing_requires_update_permission` | "Enable sharing requires authentication — unauthenticated POST returns 401" |

## Gaps Discovered and Applied

### Gap 1: Missing dispatch endpoint backend tests
**Before:** No tests for `GET /public/{slug}/dispatch/{data_source_id}/`

**Added:**
- `test_public_dispatch_requires_public_true` — dispatch on non-public dashboard returns 401 (no existence oracle)
- `test_public_dispatch_unconfigured_returns_400` — dispatch without auth returns 400 not 401, proving AnonymousUser principal accepted

### Gap 2: No E2E tests for story 4.6
**Before:** `e2e-tests/tests/dashboard/` had no share-related spec

**Added:** `e2e-tests/tests/dashboard/dashboard_share.spec.ts` with 7 API-level E2E tests covering all 6 ACs plus existence-oracle protection.

## Test Commands

```bash
# Backend (from /backend directory)
DATABASE_URL=postgresql://baserow:baserow@localhost:5431/baserow \
PYTHONPATH="tests:../premium/backend/tests:../enterprise/backend/tests:src:../premium/backend/src:../enterprise/backend/src" \
uv run --active pytest tests/baserow/contrib/dashboard/api/test_dashboard_share.py -v

# E2E (requires Docker stack)
cd e2e-tests && yarn playwright test tests/dashboard/dashboard_share.spec.ts
```
