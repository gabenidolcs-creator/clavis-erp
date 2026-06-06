# Test Automation Summary — Story 1.3 (Role enforcement for Commenter and Viewer)

**Workflow:** bmad-qa-generate-e2e-tests
**Date:** 2026-06-06
**Engineer:** QA automation (Claude Code) for Tinsu
**Story:** `_bmad-output/implementation-artifacts/1-3-role-enforcement-for-commenter-and-viewer.md` (status: review)

## Framework Detected

- **Backend:** pytest + pytest-django (existing). Run env: `BASEROW_OSS_ONLY=true`, `TEST_ENV_FILE=.env.testing-oss`, local `clavis_postgres` (`DATABASE_HOST=172.22.0.12`, user `clavis`), `BASEROW_TESTS_SETUP_DB_FIXTURE=off`.
- **Frontend:** Vitest (yarn-classic v1). Run directly via `node_modules/.bin/vitest` — corepack/yarn-4 avoided per repo guardrail (no `yarn.lock`/`package.json`/`.yarnrc.yml` drift).

## Feature Under Test

Server-side RBAC deny enforcement: Viewer/Commenter denied Row/Field/View create/update/delete (HTTP **403**, `ERROR_ROLE_PROHIBITED`); reads + WS subscribe preserved; Commenter may create comments, Viewer may not. Single `PERMISSION_MANAGERS` chain path (no parallel check).

## Generated / Audited Tests

### API Tests (REST)
- [x] `backend/tests/baserow/contrib/database/api/test_role_enforcement_api.py` — **18 tests** (6 pre-existing + **12 added** this run)
  - create_field 403 (V/C), create_field 200 (Editor), list_fields 200 (V/C), MRO mapping unit *(existing)*
  - **added:** create_row 403 (V/C), update_row 403 (V/C), create_view 403 (V/C), list_rows 200 (V/C), read single row 200 (V/C), create_view 200 (Editor), create_row 200 (Editor)

### Handler / Integration Tests
- [x] `backend/tests/baserow/core/rbac/test_enforcement_handler.py` — 13 tests (real Row/Field/View contexts; reads pass; comment policy; Editor/Admin unaffected)

### Permission-Manager Unit Tests
- [x] `backend/tests/baserow/core/rbac/test_permission_manager.py` — 47 tests; parametrized over **every** `VIEWER_DENIED_OPS` / `COMMENTER_DENIED_OPS` string + read/subscribe defer ops (incl. `listen_to_all`, `read_row`, `list_rows`)

### WebSocket Tests
- [x] `backend/tests/baserow/contrib/database/ws/test_role_enforcement_ws.py` — 2 tests (`TablePageType.can_add` truthy for V/C — subscribe preserved)

### Frontend Tests
- [x] `web-frontend/test/unit/core/permissionManagerTypes.spec.js` — 3 tests (client defers; server authoritative)

### E2E (Playwright) — DEFERRED
No user-facing UI in Story 1.3. Scope is server-side enforcement over `PERMISSION_MANAGERS`; the frontend manager intentionally defers (`hasPermission → null`, no client deny mirror — Task 6 decision). Browser e2e would only re-assert the REST 403 already covered by the API tier. Playwright deferred (no browser install) until a UX-gating story surfaces the 403 in the UI (e.g. disabling mutating controls).

## Gaps Discovered & Auto-Applied

Manager/handler/WS/frontend coverage was already complete. The **REST API tier** under-covered Task 7's named surfaces — only `create_field` (mutation) and `list_fields` (read). Added:

| Gap | Test added |
|---|---|
| update_row → 403 (Task 7 names "update row") | `test_update_row_denied_403_for_read_scoped_roles` |
| create_view → 403 (Task 7 names "create view") | `test_create_view_denied_403_for_read_scoped_roles` |
| create_row → 403 (row mutation surface) | `test_create_row_denied_403_for_read_scoped_roles` |
| read Rows REST 200 (AC#1/#2 "read Rows") | `test_list_rows_read_succeeds_for_read_scoped_roles`, `test_read_single_row_succeeds_for_read_scoped_roles` |
| Editor parity on view/row endpoints | `test_create_view_allowed_for_editor`, `test_create_row_allowed_for_editor` |

> Non-member live-401 was **not** added: membership-checked endpoints raise `ERROR_USER_NOT_IN_GROUP` (400), not the 401 catch-all — making a live 401 assertion fragile. The catch-all 401-vs-403 MRO precedence is already proven by `test_exception_mapping_role_prohibited_wins_over_catch_all`.

## Results

| Suite | Result |
|---|---|
| API (`test_role_enforcement_api.py`) | **18 passed** (2m05s) |
| Manager + handler + WS | **62 passed** (2m40s) |
| Frontend (`permissionManagerTypes.spec.js`) | **3 passed** |
| Ruff check + format | clean |

**Backend total: 80 (was 68; +12). Frontend: 3.** All green.

## Coverage

- AC#1 (Commenter read+comment, deny mutations REST+WS): covered — manager, handler, API, WS, comment policy.
- AC#2 (Viewer read-only, deny comment+mutations): covered — same tiers.
- AC#3 (single `PERMISSION_MANAGERS` path): covered — all tests route through `CoreHandler().check_permissions` / live REST chain; no parallel check.
- REST endpoints exercised: fields (create/list), rows (create/update/list/read), views (create/list).

## Next Steps

- Run in CI under the OSS-only test env.
- Playwright e2e to land with the UX story that surfaces the 403 client-side.
- End-to-end HTTP comment test lands with Epic 6 / Story 6.1 (no comment endpoint in free core today).
