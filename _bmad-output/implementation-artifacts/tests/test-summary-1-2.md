# Test Automation Summary — Story 1.2 (RBAC Role Model and Migration)

**Workflow:** bmad-qa-generate-e2e-tests
**Date:** 2026-06-06
**Engineer:** Tinsu (QA automation)
**Scope:** Automated API + E2E coverage for the RBAC role-assignment feature shipped in Story 1.2.

> Output written to a story-scoped file (`test-summary-1-2.md`) rather than the shared
> `test-summary.md` to avoid clobbering Story 1.1's summary.

## Test Framework

- **API/backend:** pytest + pytest-django (existing project framework).
- **E2E:** Playwright (`e2e-tests/`) — existing project framework.
- **Frontend unit:** Vitest (registry/component coverage already in story matrix; not re-generated here).

## Generated / Extended Tests

### API Tests — `backend/tests/baserow/api/rbac/test_rbac_views.py`

Endpoint under test: `POST|GET /api/workspaces/{workspace_id}/role-assignments/`
(`WorkspaceRoleAssignmentsView`).

Existing (8 cases, baseline): auth-required GET, admin list, non-admin list 400,
admin assign 200, non-admin assign 400, target-not-member 400, invalid-role 400,
unknown-workspace 404.

**Auto-applied gap coverage (+10 cases):**

| Test | Gap closed |
|---|---|
| `test_assign_role_requires_auth` | POST 401 (only GET 401 was covered) |
| `test_admin_assigns_each_role_tier[VIEWER/COMMENTER/EDITOR/ADMIN]` | All four fixed tiers accepted (was only VIEWER/EDITOR) — AC #1 |
| `test_admin_assigns_database_scoped_role` | Database/application-scoped assignment via `application_id` — AC #1 "workspace **and** database scope" |
| `test_workspace_and_database_scope_coexist` | Both scopes persist; most-specific (database) wins — handler `get_effective_role` |
| `test_reassign_role_updates_existing_assignment` | Upsert: re-assign at same scope updates in place, no duplicate row |
| `test_assign_role_unknown_application` | 404 `ERROR_APPLICATION_DOES_NOT_EXIST` |
| `test_assign_role_application_in_other_workspace` | Cross-workspace application rejected 404; no row written |

### E2E Tests — none generated (no UI surface)

Story 1.2 is a foundation story. Its frontend change (`permissionManagerTypes.js` +
`plugin.js`) registers an `RbacPermissionManagerType` whose `hasPermission` **returns
`null` (defers)** to preserve pre-1.2 behavior. There is **no user-facing role-assignment
UI** in this story (role-management UI is downstream — Story 1.3+). A Playwright E2E test
would have no clickable workflow to assert against. Frontend behavior is covered by the
existing Vitest registry/defer/component spec
(`web-frontend/test/unit/core/permissionManagerTypes.spec.js`).

**Recommendation:** generate E2E flows when the role-assignment UI lands (Story 1.3+).

## Coverage

- **RBAC API endpoint:** 1/1 view, both methods (GET list + POST assign), all mapped
  status codes exercised — 200, 400 (×3 error codes), 401, 404 (×2 error codes).
- **Role tiers:** 4/4 (VIEWER, COMMENTER, EDITOR, ADMIN).
- **Scopes:** workspace + database, coexistence, most-specific-wins.
- **UI features:** 0/0 — no UI surface in this story (defer-only frontend).

## Validation

```
uv run pytest tests/baserow/api/rbac/test_rbac_views.py
→ 18 passed (8 baseline + 10 new) in 121.66s
ruff check + ruff format --check → clean
```

Run command (OSS-only env, local clavis_postgres):
```
cd backend && TEST_ENV_FILE=.env.testing-oss BASEROW_OSS_ONLY=true \
DJANGO_SETTINGS_MODULE=baserow.config.settings.test \
DATABASE_HOST=172.22.0.12 DATABASE_USER=clavis DATABASE_PASSWORD=clavis_secret \
DATABASE_NAME=clavis_postgres BASEROW_TESTS_SETUP_DB_FIXTURE=off \
uv run pytest tests/baserow/api/rbac/test_rbac_views.py
```

All generated tests pass ✅ — checklist (`./checklist.md`) satisfied for the
applicable items (E2E item N/A: no UI exists).

## Next Steps

- Run in CI alongside the Story 1.2 backend matrix.
- Add Playwright E2E for role assignment when the management UI ships (Story 1.3+).
- Extend API coverage for the GET endpoint's `application` scope filter once the
  list view exposes a query param (not present in 1.2).
