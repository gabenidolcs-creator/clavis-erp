# Test Automation Summary — Story 1.4 (Central field-permission layer with edit restriction)

**Workflow:** `bmad-qa-generate-e2e-tests` · **Date:** 2026-06-06 · **Engineer:** Tinsu (QA automation)
**Story status:** review · **Baseline commit:** `179f0ff93`

## Scope

Story 1.4 is already implemented (status `review`) with 21 backend + 8 frontend tests. This
run **audited** existing coverage against the Task 7 matrix + the two ACs, found gaps, and
**auto-applied** them. No new feature code — tests only.

## Framework Detected

- **Backend:** `pytest` + `pytest-django` (OSS-only env). Run via
  `BASEROW_OSS_ONLY=true TEST_ENV_FILE=.env.testing-oss DATABASE_HOST=172.22.0.12
  DATABASE_USER=clavis DATABASE_PASSWORD=clavis_secret DATABASE_NAME=baserow
  DATABASE_PORT=5432 BASEROW_TESTS_SETUP_DB_FIXTURE=off just b test <paths> --reuse-db`.
- **Frontend:** `vitest`. Run via `web-frontend/node_modules/.bin/vitest run <spec>`
  directly (corepack/`yarn install` deliberately avoided — yarn-classic v1 repo; no
  lockfile drift introduced).

## Coverage Audit (existing vs Task 7 matrix)

| Area | Task 7 item | Pre-run | After gap-fill |
|---|---|---|---|
| Model | table/columns, default-unrestricted, round-trip, 1:1, cascade | OK 5 | OK 5 |
| Permission-manager unit | deny below-threshold (write+config), defer at/above, defer unrestricted, defer read, admin `update_permission` op, no-N+1 | OK 6 | OK 6 |
| **AC #2 single-path / data-source parity** | LocalBaserow data source governed by the same manager, single chain entry | MISSING | **+1** |
| **`get_permissions_object` backend payload** (read-only render contract) | restricted ids for below-threshold, `None` for admin/empty | MISSING | **+3** |
| API (REST) 403 | row-write 403, row-write unrestricted 200, row read 200, admin 200, field-config 403, no-rule no-regression, set-rule non-admin 403 / admin persist+reload / null clears | OK 10 | OK 10 |
| **401 catch-all no-regression** (MRO precedence) | generic `PermissionException` stays 401; `FieldEditProhibitedError` -> 403 | MISSING | **+1** |
| **Handler-layer enforcement** | `RowHandler.update_rows` + `FieldHandler.update_field` direct | REST-only | **+2** |
| Frontend manager | registered, restricted->false (both ops), unrestricted->null, non-governed->null, no-payload->null | OK 8 | OK 8 |

## Gaps Discovered & Auto-Applied

### Backend — `tests/baserow/core/field_permissions/test_permission_manager.py` (+4)
- `test_single_path_governs_data_source_write_surface` — **AC #2**: the op the
  Application-Builder LocalBaserow data source emits (`service_types.py:2069`) is the same
  `database.table.field.write_values` the row handler emits, `"field_permissions"` is a
  **single** entry in `PERMISSION_MANAGERS`, and a data-source-shaped check on a restricted
  field is denied — proving one enforcement path, zero surface-specific code.
- `test_get_permissions_object_lists_restricted_fields_for_below_threshold` — backend half
  of AC #1's read-only render: below-threshold actor -> `{"restricted_field_ids": [id]}`.
- `test_get_permissions_object_none_for_actor_at_or_above_threshold` — Admin -> `None`.
- `test_get_permissions_object_none_when_no_rules` — zero rules -> `None` (no regression).

### Backend — `tests/baserow/contrib/database/api/test_field_permission_api.py` (+3)
- `test_exception_mapping_field_edit_prohibited_wins_over_catch_all` — MRO precedence:
  `FieldEditProhibitedError` -> 403 while the legacy generic `PermissionException` catch-all
  stays **401** (the new global mapping did not hijack it). Mirrors Story 1.3's proof.
- `test_handler_row_update_restricted_field_raises` — `RowHandler.update_rows` raises
  `FieldEditProhibitedError` for a restricted field; a non-restricted field in the same row
  still updates.
- `test_handler_update_field_restricted_config_raises` — `FieldHandler.update_field` raises
  for an Editor, succeeds for an Admin.

## Results

- **Backend:** `28 passed` (5 model + 10 manager + 13 API) — was 21, **+7**.
- **Frontend:** `8 passed` (`permissionManagerTypes.spec.js`).
- **Lint:** `ruff check` + `ruff format --check` clean on both edited test files.
- **No lockfile drift** (`yarn.lock` / `package.json` / `.yarnrc` untouched).

## Coverage

- **Acceptance Criteria:** AC #1 (403 + read-only + persists + readable) and AC #2 (single
  enforcement path / data-source parity) — both now have direct assertions.
- **Task 7 matrix:** model -> manager -> handler -> API -> frontend-registry — all rows covered.
- API endpoints exercised: `PATCH /api/database/rows/table/<id>/<row>/`,
  `PATCH /api/database/fields/<id>/`, `PATCH /api/database/fields/<id>/permission/` (+ GET).

## Playwright E2E — Deferred (with rationale)

No browser-driven E2E added. Justification:

1. **No standalone UI surface for this story.** Story 1.4's only frontend behavior is the
   existing, already-wired `canWriteFieldValues -> $hasPermission('...write_values')` gate that
   flips a grid cell read-only (`GridViewRow.vue:114`). 1.4 supplies *data*
   (`restricted_field_ids`), not a new component or page flow.
2. **The gate is unit-covered at the source of truth** — the frontend
   `FieldPermissionManagerType` returns `false`/`null` correctly (8 specs), and the backend
   `get_permissions_object` payload that feeds it is now backend-tested (+3). A Playwright
   run would re-assert the same boolean through a full app stack.
3. **Cost/benefit + environment.** A live E2E needs the full Nuxt + Django + Postgres stack
   running and an authenticated multi-role session; the skill's guidance ("manager-level
   assertion is sufficient if an end-to-end test is heavy") applies. Recommend a single
   grid-cell read-only Playwright scenario be added in `e2e-tests/` when the Epic-1 RBAC E2E
   harness lands (track with Story 1.5's visibility work, which adds real read-path UI).

## Next Steps

- Run the three test paths in CI under the OSS-only env profile.
- When the `e2e-tests/` RBAC harness exists, add one grid-cell read-only scenario (deferred
  above) to close the browser-level loop alongside Story 1.5.
