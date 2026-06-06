---
baseline_commit: 3719a093f
---

# Story 1.3: Role enforcement for Commenter and Viewer

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a workspace admin,
I want Commenter and Viewer Roles enforced server-side,
so that scoped members can read (and, for Commenter, comment) but cannot create, edit, or delete data.

Realizes UJ-4. **Bucket A `[A]` — clean-room reimplementation; provenance record required (see "Clean-Room Mandate" below).**

## Context & Scope

**Story 1.2 built the RBAC *foundation*: the four fixed-tier roles (`Viewer/Commenter/Editor/Admin`), the `RoleAssignment` model layered above legacy `ADMIN/MEMBER`, and `RbacPermissionManagerType` wired into `PERMISSION_MANAGERS` in a strict "grant-or-defer, never deny" mode that preserved every existing member's capabilities.** This story flips on the **deny** side for the two read-only tiers — making `RbacPermissionManagerType` return a permission-denied result when a **Commenter** or **Viewer** attempts a mutating operation (Row/Field/View create/update/delete), while leaving read (and, for Commenter, comment-create) intact.

**Why now:** Per architecture §"Implementation sequence", D6 RBAC enforcement is the load-bearing security primitive every later surface depends on (NFR-4: "server-side enforcement via `PERMISSION_MANAGERS`"). Story 1.4 (field-permission edit restriction) and Story 1.5 (field visibility) build on a manager that can actually *deny*. [Source: architecture.md lines 35, 126, 156-157, 166; epics.md lines 64, 81]

**The central design fact (read this twice):** In 1.2 the manager only ever returned `True` (grant) or omitted the check (defer). Deferring is **not** denial — the legacy `basic` manager grants any workspace member write access. So a Viewer/Commenter who maps from a former `MEMBER` (→ Editor by migration, but explicitly assigned Viewer/Commenter via `RoleAssignment`) would still be granted writes **unless this manager actively returns a denial**. Therefore 1.3's core change is: for Viewer/Commenter, on a mutating operation, return a `PermissionException` (deny) — do **not** defer. [Source: core/rbac/permission_manager.py `check_multiple_permissions`; core/permission_manager.py `BasicPermissionManagerType`]

**Scope boundary (do NOT cross):**
- **IN:** Deny `Row/Field/View` create/update/delete for **Viewer** and **Commenter** via `RbacPermissionManagerType` (the existing chain entry — never a parallel path); allow reads for both; allow **comment-create** for Commenter and deny it for Viewer (against the already-registered comment operation-type stubs); a dedicated `RoleProhibitedError` mapped to **HTTP 403**; the model→handler→permission-manager→serializer/API→frontend-registry→component test matrix; an updated provenance record.
- **OUT:** Field-level edit restriction (Story 1.4) and field visibility/inference guard (Story 1.5); the actual row-comments subsystem (Epic 6 / Story 6.1 — only the operation-type *stubs* exist in free core today); interface-only collaborator (FR-31); the exhaustive role-combination security gate (AR-2 / Story 6.4); Editor/Admin behavior (unchanged from 1.2).
- **Preserve, don't over-block:** Viewer/Commenter must retain **read** access (REST list/read **and** WebSocket subscribe). Deny only the enumerated mutating operations — do NOT switch the manager to deny-by-default for these roles, or you will break legitimate reads (listing databases, reading rows, subscribing to table pages). [Source: epics.md lines 251-262]

## Clean-Room Mandate (Bucket A)

This capability exists under the PE/EE license in `enterprise/backend/src/baserow_enterprise/role/`. That source **must not be copied, adapted, or recalled from memory.** [Source: architecture.md lines 205-206, 240-242, 256, 260; memory baserow-open-core-license-constraint]

- Reference `premium/`/`enterprise/` only for **registration shape via public MIT symbols** (e.g. *that* a `PermissionManagerType` returns a `PermissionException` to deny) — never to replicate role→operation mapping logic. Our model is **fixed code-defined tiers**, not the enterprise custom-role/operation-table system. Do not import the enterprise model.
- Story 1.2's behavior spec (`docs/clean-room/specs/1-2-rbac-role-model.md`) and provenance record already exist; **extend** them (or add a `1-3-*` spec) from allowed public sources only (public Baserow docs, public upstream SaaS UI, public issues/changelogs). No `premium/`/`enterprise/` internal symbol name as the thing to replicate (free-core MIT symbols are allowed). [Source: docs/clean-room/allowed-sources.md; Story 1.1]
- **Attach/extend a provenance record** under `docs/clean-room/provenance/` using the template. No provenance → the merge gate (`docs/clean-room/scripts/check_provenance.py` + `.github/workflows/clean-room-provenance-gate.yml`) blocks merge. Flag the PR Bucket A via the `bucket-a` label or PR-template checkbox. [Source: Story 1.1; architecture.md lines 240-242]
- **Legal gate (Open Q7):** Story 1.2 confirmed owner/legal sign-off is recorded in `docs/clean-room/owner-and-sign-off.md` (commit `0dc79c4da`). Re-confirm it is still filled before writing code; if reverted to `_TODO_`, HALT and surface as blocker. [Source: Story 1.2 Clean-Room Mandate; git log]

## Acceptance Criteria

1. **Commenter: read + comment, deny all structural mutations (REST + WebSocket).** Given a member with the **Commenter** Role, when they attempt to **create/edit/delete a Row, Field, or View**, then the operation is denied with **HTTP 403** on both REST and WebSocket-originated paths, **and** they can still **read Rows** (REST + WebSocket subscribe) **and post Comments** (the `database.table.view.create_comment` operation resolves to *allowed* through the chain). [Source: epics.md lines 251-255; architecture.md lines 35, 189]

2. **Viewer: read only, deny comment and all mutations.** Given a member with the **Viewer** Role, when they attempt to **comment or to create/edit/delete a Row/Field/View**, then the operation is denied with **HTTP 403** while **read access succeeds** (REST list/read + WebSocket subscribe). [Source: epics.md lines 256-260]

3. **Single enforcement path — no parallel/ad-hoc check.** Given enforcement is requested, when any role check runs, then it resolves **through the `PERMISSION_MANAGERS` chain** (specifically the existing `RbacPermissionManagerType` — extended, not duplicated), never a parallel or per-view ad-hoc check (NFR-4). Full Bucket A DoD: model→handler→permission-manager→serializer/API→frontend-registry→component tests pass and a provenance record is attached. [Source: epics.md lines 261-264; architecture.md lines 35, 234-237, 254-255]

## Tasks / Subtasks

- [x] **Task 1 — Re-confirm clean-room gate + extend provenance (AC: #3, Clean-Room)** — do this FIRST
  - [x] Confirm `docs/clean-room/owner-and-sign-off.md` still has owner + legal sign-off filled (not `_TODO_`). If reverted, HALT and surface as blocker.
  - [x] Extend the 1.2 behavior spec (or add `docs/clean-room/specs/1-3-role-enforcement.md`) describing the deny policy (which ops each tier may/may not perform), citing only allowed public sources.
  - [x] Start/extend the provenance record under `docs/clean-room/provenance/`; keep it updated through implementation.

- [x] **Task 2 — Define the role→denied-operation policy as type-string sets (AC: #1, #2)**
  - [x] Add a policy module (e.g. `backend/src/baserow/core/rbac/enforcement.py`) defining the **mutating operation `type` strings** denied to Viewer/Commenter, **as plain strings** (mirror the `BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS` convention of listing type strings, NOT importing the operation classes — `core` importing `contrib.database` operation classes risks an import cycle and a layering violation). [Source: core/permission_manager.py `ADMIN_ONLY_OPERATIONS`]
  - [x] **Denied to BOTH Viewer and Commenter** (structural writes) — enumerate, confirming each exact string against the source files:
    - Rows: `database.table.create_row` (`CreateRowDatabaseTableOperationType`, `contrib/database/table/operations.py:42`), `database.table.update_row`, `database.table.delete_row` (`contrib/database/rows/operations.py`); and view-scoped (`contrib/database/views/operations.py`): `database.table.view.create_row`, `database.table.view.update_row`, `database.table.view.delete_row`. *(Mutations route through `_check_permissions_with_view_fallback`, which issues BOTH a table-scoped and a view-scoped check — denying either is sufficient, but list both so neither variant slips through.)*
    - Fields (`contrib/database/fields/operations.py`): `database.table.create_field`, `database.table.field.update`, `database.table.field.delete`.
    - Views (`contrib/database/views/operations.py`): `database.table.create_view`, `database.table.view.update`, `database.table.view.delete`.
  - [x] **Comment policy** (operation-type stubs already registered in free core at `contrib/database/views/operations.py:63-82`): `database.table.view.create_comment` → **allowed for Commenter, denied for Viewer**; `database.table.view.update_comment` / `delete_comment` → denied for both (own-comment edit is an Epic 6 policy decision — keep 1.3 minimal). `database.table.view.list_comments` → allowed for both (read).
  - [x] **Do NOT deny** read/subscribe ops: `database.table.read_row`, `database.table.view.list_rows`, `database.table.view.read_row`, `database.table.list_fields`, `database.table.list_views`, and critically `database.table.listen_to_all` (`ListenToAllDatabaseTableEventsOperationType` — the WebSocket subscribe op; Viewer/Commenter must keep read access). Leave these to **defer**.

- [x] **Task 3 — Add deny semantics to `RbacPermissionManagerType` (AC: #1, #2, #3)**
  - [x] In `backend/src/baserow/core/rbac/permission_manager.py` `check_multiple_permissions`, after resolving the effective `role` for each check:
    - If `role == roles.VIEWER` and `operation in VIEWER_DENIED_OPS` → `result[check] = RoleProhibitedError(check.actor)`.
    - If `role == roles.COMMENTER` and `operation in COMMENTER_DENIED_OPS` → `result[check] = RoleProhibitedError(check.actor)`.
    - Otherwise keep the existing 1.2 logic (Admin grants admin-only ops; everything else **defers**). **Editor and Admin behavior is unchanged.**
  - [x] **Return the exception instance in the result dict** (the contract: a `PermissionException` value = deny; `True` = grant; absent = defer). Returning the exception lets the handler re-raise it so the API maps it to a status code. [Source: registries.py:747-760 `check_multiple_permissions` contract; handler.py:283-293 default-deny]
  - [x] **Defer, don't deny, for unlisted ops** so reads/subscribe and unrelated workspace ops still resolve through the chain (preserves read access — do not flip to deny-by-default for these roles).
  - [x] Context/scope note: 1.2's `_application_from_context` only resolves database scope when `context` is an `Application`. For Row/Field/View contexts (`Table`/`Field`/`View`), the effective role falls back to the **workspace-scoped** `RoleAssignment` — which is the primary 1.3 case. If an AC test requires database-scoped Viewer/Commenter to be enforced on a Table/View/Row context, optionally extend `_application_from_context` to walk `Table → Database`; otherwise leave the 1.2 behavior and document it. [Source: core/rbac/permission_manager.py:50-66; Story 1.2 Senior Review "Notes"]
  - [x] Keep the single batched `_build_role_index` query — do NOT reintroduce a per-check `get_effective_role` call (that was the N+1 fixed in 1.2 review, regression-tested). [Source: Story 1.2 Senior Review H1]

- [x] **Task 4 — `RoleProhibitedError` → HTTP 403, registered globally (AC: #1, #2)**
  - [x] Define `RoleProhibitedError(PermissionException)` in `backend/src/baserow/core/exceptions.py` (sits beside `PermissionDenied`). [Source: core/exceptions.py:4,48]
  - [x] **Why a dedicated exception:** the generic `PermissionException` is globally mapped to `ERROR_PERMISSION_DENIED` = **HTTP 401** (`api/errors.py:43-47`, injected into every `@map_exceptions` view at `api/decorators.py:98-99`). The AC + architecture (line 189: "403 for permission denial") require **403**. A subclass works because `apply_exception_mapping` walks the raised exception's **MRO most-specific-first** (`api/utils.py` `_search_up_class_hierarchy_for_mapping`) — `RoleProhibitedError` is matched before the `PermissionException` catch-all.
  - [x] Register it **globally** so all endpoints get 403 with **zero per-view edits**: in `core/apps.py` `ready()`, `api_exception_registry.register(RegisteredException(exception_class=RoleProhibitedError, exception_error=("ERROR_ROLE_PROHIBITED", HTTP_403_FORBIDDEN, "...")))`. The registry's entries are merged into every view's mapping by `map_exceptions`. [Source: api/registries.py:7-26; api/utils.py map_exceptions registry merge; api/decorators.py:98-99]
  - [x] Verify in a test that a denied Row/Field/View mutation returns status **403** with error code `ROLE_PROHIBITED` (not 401), and that an *unrelated* permission denial (e.g. non-member) still returns the legacy 401 (no regression of the catch-all).

- [x] **Task 5 — WebSocket parity (AC: #1, #2)**
  - [x] **No new WS code expected.** Confirm and document that the WebSocket layer is **read/subscribe + broadcast only** — `CoreConsumer` (`ws/consumers.py:156-244`) handles only `page` (subscribe) / `remove_page`; there is **no mutating command over WS**. All writes go through REST handlers → the same `CoreHandler.check_permissions` → `PERMISSION_MANAGERS` chain, so "403 on WebSocket" for mutations is satisfied structurally (there is no separate WS write path to bypass enforcement). Do NOT invent a WS deny path. [Source: ws/consumers.py:156-244; ws/tasks.py broadcast-permission filtering]
  - [x] Confirm subscribe-time auth (`TablePageType.can_add` → `CoreHandler().check_permissions(..., ListenToAllDatabaseTableEventsOperationType.type, ...)` at `contrib/database/ws/pages.py:21-52`) still **succeeds** for Viewer/Commenter (read), because `listen_to_all` is NOT in the deny sets. Add a test asserting a Viewer `can_add` returns truthy (read/subscribe preserved). [Source: ws/registries.py PageType.can_add; contrib/database/ws/pages.py]

- [x] **Task 6 — Frontend registry parity (AC: #3)**
  - [x] The frontend `RbacPermissionManagerType` (added in 1.2 in `web-frontend/modules/core/permissionManagerTypes.js`) currently **defers** (`hasPermission` returns `null`). For 1.3, decide: keep deferring (server is the source of truth; client shows optimistic UI then snaps to the 403) **or** mirror the deny so Viewer/Commenter UI disables mutating controls. **Recommended: keep the client deferring** (avoid a second source of truth; the architecture mandates server-side enforcement as authoritative) and only add UI gating in a later UX-focused story. Whatever is chosen, update `permissionManagerTypes.spec.js` accordingly and keep the registry registration intact. [Source: architecture.md lines 35, 196-199, 234; web-frontend/modules/core/permissionManagerTypes.js; Story 1.2 frontend manager]
  - [x] Add any new i18n strings (e.g. a `permission.roleProhibited` message) to `en.json` + locales if the frontend surfaces the 403. [Source: architecture.md line 248]

- [x] **Task 7 — Test matrix (AC: #1, #2, #3)** — mirror paths under `backend/tests/baserow/...` (NOT co-located)
  - [x] **permission-manager unit** (`backend/tests/baserow/core/rbac/test_permission_manager.py`, extend): for each denied op string, assert `check_multiple_permissions` returns a `RoleProhibitedError` for a Viewer and a Commenter; assert it returns **absent/defer** (not deny) for read/subscribe ops; assert **Commenter is granted-through** for `create_comment` while **Viewer is denied**; assert Editor/Admin results are unchanged from 1.2. Reuse the `@override_settings(PERMISSION_MANAGERS=[...])` + `data_fixture` pattern. [Source: test_basic_permissions.py:177-261; Story 1.2 tests]
  - [x] **handler/integration** — via `CoreHandler().check_permissions(user, op, workspace=ws, context=...)`: Viewer/Commenter raise `RoleProhibitedError` on a real Row/Field/View mutation op; reads return `True`/pass.
  - [x] **API (REST) — the 403 assertion (AC #1/#2):** hit a real endpoint (e.g. create field, update row, create view) as a Viewer and as a Commenter; assert HTTP **403** + `error == "ROLE_PROHIBITED"`. Assert the same endpoints succeed (or are not role-denied) for Editor/Admin. Assert a **read** endpoint (list rows / read row) returns 200 for Viewer/Commenter. [Source: architecture.md line 189; existing API test patterns under backend/tests/baserow/contrib/database/api/]
  - [x] **comment policy** — at the permission/handler level assert Commenter is allowed and Viewer denied for `database.table.view.create_comment` (no comment *endpoint* exists in free core — that is Epic 6; test the policy resolution, not an HTTP comment route). Document this limitation. [Source: Explore: row comments are premium-only; epics.md Story 6.1]
  - [x] **WebSocket** — assert `TablePageType.can_add` is truthy for a Viewer/Commenter (read/subscribe preserved). [Source: contrib/database/ws/pages.py]
  - [x] **no-regression** — Editor (former MEMBER) and Admin (former ADMIN) retain all current capabilities (re-run/extend the 1.2 equivalence assertions); non-member denials still return the legacy 401.
  - [x] **frontend** — update `web-frontend/test/unit/core/permissionManagerTypes.spec.js` for whatever Task 6 decision is made; `just f yarn test:core <path>`.

- [x] **Task 8 — Finalize provenance + DoD**
  - [x] Complete the provenance record (sources consulted + implementer attestation); flag PR Bucket A (`bucket-a` label or PR-template checkbox); confirm the provenance gate passes. [Source: Story 1.1; architecture.md lines 240-242]

## Dev Notes

### Architecture patterns & constraints (MUST follow)
- **One enforcement path:** extend the existing `RbacPermissionManagerType` in the `PERMISSION_MANAGERS` chain — NEVER add a parallel/ad-hoc role check in a view or handler. This is NFR-4 and the load-bearing security invariant. [Source: architecture.md lines 35, 234-237, 254-255; epics.md line 81]
- **Deny = return a `PermissionException` from the manager**; grant = `True`; defer = omit the check. The chain default-denies only *undetermined* checks at the very end; within the chain, a manager that wants to *deny* must return the exception (don't rely on default-deny, which yields the generic 401). [Source: registries.py:747-760; handler.py:283-293]
- **403 not 401:** the codebase's generic permission-denied is **401** (`ERROR_PERMISSION_DENIED`, `api/errors.py:43-47`). The AC + architecture demand **403** for these role denials. Use the dedicated `RoleProhibitedError` + global `api_exception_registry` registration (Task 4) — MRO precedence guarantees 403 without touching individual views. [Source: api/errors.py:43-47; api/decorators.py:98-99; api/utils.py `_search_up_class_hierarchy_for_mapping`; architecture.md line 189]
- **Type strings, not class imports:** define deny sets as operation `type` strings to avoid `core → contrib.database` import cycles/layering breaks (this is exactly why `ADMIN_ONLY_OPERATIONS` uses strings). [Source: core/permission_manager.py]
- **Preserve reads & the batched query:** deny only the enumerated mutating ops; keep the 1.2 single-query `_build_role_index` (no per-check `get_effective_role`). [Source: Story 1.2 Senior Review H1]
- **Naming/format:** `snake_case` files/columns, `PascalCase` classes (`RoleProhibitedError`), Ruff 88-col, Python 3.14, `snake_case` JSON. [Source: architecture.md lines 180-217]
- **Bucket A placement:** code in `backend/src` / `web-frontend` only — NEVER `premium/`/`enterprise/`. Tests under `backend/tests/baserow/...` mirroring `src`. [Source: architecture.md lines 204-210, 256, 260]

### Source tree components to touch
- `backend/src/baserow/core/rbac/permission_manager.py` `[X]` — add Viewer/Commenter deny branch.
- `backend/src/baserow/core/rbac/enforcement.py` `[A]` NEW (or constants in `permission_manager.py`) — denied-operation type-string sets per role.
- `backend/src/baserow/core/exceptions.py` `[X]` — add `RoleProhibitedError`.
- `backend/src/baserow/core/apps.py` `[X]` — register `RoleProhibitedError` in `api_exception_registry` (in `ready()`).
- `web-frontend/modules/core/permissionManagerTypes.js` `[X]` — frontend parity (likely no behavior change; see Task 6).
- Tests: `backend/tests/baserow/core/rbac/test_permission_manager.py` (extend), new API + WS tests under `backend/tests/baserow/contrib/database/...`, `web-frontend/test/unit/core/permissionManagerTypes.spec.js`.

### Files to READ before coding (current state — preserve behavior)
- `backend/src/baserow/core/rbac/permission_manager.py` (the whole file — 1.2's grant-or-defer logic you are extending; note `RBAC_MANAGED_OPERATIONS`, `_build_role_index`, `_effective_role_from_index`, `_application_from_context`).
- `backend/src/baserow/core/rbac/roles.py` (`VIEWER/COMMENTER/EDITOR/ADMIN`, `role_at_least`).
- `backend/src/baserow/core/permission_manager.py:286-359` (`BasicPermissionManagerType` — `ADMIN_ONLY_OPERATIONS` string-list convention; the literal `== "ADMIN"` check you must not disturb).
- `backend/src/baserow/core/registries.py:669-760` (`PermissionManagerType.check_multiple_permissions` contract — True/exception/absent semantics).
- `backend/src/baserow/core/handler.py:283-293, 327-395` (`check_permissions`: returns/re-raises the manager's `PermissionException`; default-deny block).
- `backend/src/baserow/core/exceptions.py:1-55` (`PermissionException`, `PermissionDenied`).
- `backend/src/baserow/api/errors.py:43-47` (`ERROR_PERMISSION_DENIED` = 401 — the thing you are overriding for roles).
- `backend/src/baserow/api/decorators.py:90-120` (global `PermissionException → ERROR_PERMISSION_DENIED` injection).
- `backend/src/baserow/api/utils.py` (`map_exceptions`, `apply_exception_mapping`, `_search_up_class_hierarchy_for_mapping` — MRO precedence proof) and `backend/src/baserow/api/registries.py:1-26` (`api_exception_registry`, `RegisteredException`).
- `backend/src/baserow/contrib/database/rows/operations.py`, `fields/operations.py`, `views/operations.py` (exact mutating + comment-stub op `type` strings — confirm `create_row`'s string).
- `backend/src/baserow/ws/consumers.py:156-244` and `backend/src/baserow/contrib/database/ws/pages.py:21-129` (WS subscribe path; `listen_to_all` op; confirm read/broadcast-only).
- `backend/tests/baserow/core/test_basic_permissions.py:177-261` (permission-manager test shape).

### Clean-room reference-shape ONLY (do not copy behavior)
- `enterprise/backend/src/baserow_enterprise/role/permission_manager.py` — look only at *that* a manager returns a denial in `check_multiple_permissions` (public registry shape); the enterprise role→operation mapping is custom-role/teams/license-gated and is NOT our design. [Source: architecture.md lines 256, 260]

### Key design decisions / hazards
- **HAZARD — defer ≠ deny.** The #1 way this story fails: leaving Viewer/Commenter mutating ops to "defer", expecting some downstream manager to deny. It won't — `basic` grants members. The manager must **return `RoleProhibitedError`** for those ops. [Source: core/permission_manager.py; epics.md 251-262]
- **HAZARD — 401 vs 403.** Default permission denial is 401 in this codebase; the AC says 403. Without the dedicated exception + registry registration you will silently ship 401 and fail AC #1/#2. The fix is global and zero-per-view (Task 4). [Source: api/errors.py:43-47; architecture.md line 189]
- **HAZARD — over-blocking reads.** Do NOT deny-by-default for Viewer/Commenter. `listen_to_all` (WS subscribe), `list_rows`, `read_row`, `list_fields`, `list_views` must remain deferrable, or you break the "read still succeeds" half of both ACs.
- **Comments are stubs only.** Free core has the comment *operation types* (registered) but no model/handler/endpoint — that's Epic 6 / Story 6.1. Encode the Commenter-allow / Viewer-deny **policy** now (testable at the manager/handler level); the end-to-end HTTP comment test lands with 6.1. [Source: Explore findings; epics.md Story 6.1]
- **Scope resolution.** Workspace-scoped roles cover the primary AC cases. Database-scoped enforcement on Table/View/Row contexts requires a `Table → Database` walk in `_application_from_context` — optional for 1.3, document if deferred. [Source: Story 1.2 Senior Review "Notes"]
- **Chain position unchanged:** `"rbac"` stays after `"member"`, before `"basic"`. Do not reorder. [Source: config/settings/base.py:1270-1289; Story 1.2]

### Testing standards
- Backend: `just b test backend/tests/baserow/core/rbac/` and the new API/WS tests (pytest + pytest-django). OSS-only env: migrations/makemigrations need `BASEROW_OSS_ONLY=true` + dev settings; tests use `backend/.env.testing-oss` (`TEST_ENV_FILE`) against the local `clavis_postgres` container (`DATABASE_HOST=172.22.0.12`, user `clavis`), `BASEROW_TESTS_SETUP_DB_FIXTURE=off`. Frontend: `just f yarn test:core <path>` (Vitest). **Vitest gotcha (from 1.2):** the project is yarn-classic (v1); corepack may resolve yarn 4 — if `just f` misbehaves, invoke vitest directly via `node_modules/.bin`. Do NOT let `yarn.lock`/`package.json`/`.yarnrc.yml` drift into the diff (1.2 had to revert exactly that). [Source: Story 1.2 Debug Log + Senior Review H2]
- Full Bucket A matrix model→handler→permission-manager→serializer/API→frontend-registry→component is the DoD. [Source: architecture.md lines 247-248; epics.md line 263]

### Previous story intelligence (Story 1.2)
- `RbacPermissionManagerType` is **grant-or-defer only** today; `RoleAssignment` is layered above `WorkspaceUser.permissions` (never rewrites it); migration derives Admin/Editor assignments (ADMIN→Admin, MEMBER→Editor). [Source: Story 1.2 Completion Notes / File List]
- 1.2 review fixed an **N+1** in the manager (batch `_build_role_index`) with a regression test asserting one query for 20 checks — preserve it. It also fixed `RBAC_CHAIN` test order (`member → token → rbac → basic`) and added a handler cross-workspace guard. [Source: Story 1.2 Senior Review H1/M1/M2]
- The `PostToolUse` Edit hook fails because `python` isn't on PATH — use `python3` for any scripts (e.g. the provenance gate). [Source: Story 1.2 session obs 2852-2853]
- 1.2 backend file list to build on: `core/rbac/{roles,operations,permission_manager,handler,models}.py`, `api/rbac/*`, `core/apps.py`, `config/settings/base.py`, tests under `backend/tests/baserow/core/rbac/` + `backend/tests/baserow/api/rbac/`. [Source: Story 1.2 File List]

### Git intelligence
- Branch from `develop`. Baseline `3719a093f` (Story 1.2 merge: "feat(story-1.2): RBAC role model and migration"). Conventional Commit prefix `feat(story-1.3): ...`. Recent perf commit `b8559a56c` touched the permissions endpoint — the batched-query design (1.2) keeps it safe; do not regress it. [Source: git log; Story 1.2]

### Project Structure Notes
- No new env var expected. No new model/migration expected (1.3 is pure enforcement logic over the 1.2 model). If a feature flag is introduced, follow the `add-django-config-env-var` skill.
- New backend code stays in `core/rbac/`; the new exception in `core/exceptions.py`; registration in `core/apps.py`. Tests mirror `src` under `backend/tests/`. No `premium/`/`enterprise/` edits. [Source: architecture.md lines 204-210, 271-275]

### References
- [Source: epics.md#Epic 1 → Story 1.3 (lines 243-264)] — the three ACs (Commenter deny mutations / Viewer read-only / single `PERMISSION_MANAGERS` path).
- [Source: epics.md lines 64 (FR-29), 81 (NFR-4)] — RBAC foundation + server-side every-surface enforcement.
- [Source: architecture.md lines 35 (every-surface enforcement), 126 (D6 RBAC, PermissionManager not a parallel path), 156-157/166 (sequence + prerequisite), 189 (403 for permission denial), 204-210/254-260 (Bucket A placement + anti-patterns), 234-237 (PERMISSION_MANAGERS mandatory routing)].
- [Source: backend code map] — rbac/permission_manager.py, rbac/roles.py; core/permission_manager.py:286-359; registries.py:669-760; handler.py:283-293,327-395; exceptions.py:4,48; api/errors.py:43-47; api/decorators.py:98-99; api/utils.py (map_exceptions/MRO); api/registries.py:1-26; contrib/database/{rows,fields,views}/operations.py; ws/consumers.py:156-244; contrib/database/ws/pages.py:21-129.
- [Source: Story 1.2 (`1-2-rbac-role-model-and-migration.md`)] — foundation, grant-or-defer manager, N+1 fix, chain order, OSS test env.
- [Source: docs/clean-room/ (Story 1.1)] — allowed-sources.md, provenance template, check_provenance.py, owner-and-sign-off.md.
- [Source: memory baserow-open-core-license-constraint] — paid features need clean-room reimplement; PE/EE license forbids copying.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Code, BMAD create-story workflow).

### Debug Log References

- Backend tests required the OSS-only + local-DB env (no default `db` host in this dev box). Working invocation:
  `BASEROW_OSS_ONLY=true TEST_ENV_FILE=.env.testing-oss DATABASE_HOST=172.22.0.12 DATABASE_USER=clavis DATABASE_PASSWORD=clavis_secret DATABASE_NAME=baserow DATABASE_PORT=5432 BASEROW_TESTS_SETUP_DB_FIXTURE=off just b test <paths> --reuse-db`. Without the DB env, every test errors at setup with `psycopg2 ... host=db user=baserow` connection refused.
- `just` is not on PATH; it lives at `backend/.venv/bin/just` — `export PATH="$PWD/backend/.venv/bin:$PATH"`.
- Frontend Vitest: corepack resolves yarn 4 ("This package doesn't seem to be present in your lockfile"), so `just f yarn test:core` fails. Ran vitest directly: `cd web-frontend && node_modules/.bin/vitest run test/unit/core/permissionManagerTypes.spec.js`. No `yarn.lock`/`package.json`/`.yarnrc.yml` drift in the diff (verified).
- Pre-existing OSS-env failures (NOT caused by this story, confirmed by stashing the src changes and re-running): `test_basic_permissions.py::test_get_permissions` and `::test_allow_if_template_permission_manager*` fail because `user_source_type_registry` is empty under `BASEROW_OSS_ONLY` (`user_source.py:14 IndexError`). Unrelated to RBAC enforcement.

### Completion Notes List

- **Deny side implemented as a return-the-exception branch in the existing manager** (`RbacPermissionManagerType.check_multiple_permissions`) — no parallel/ad-hoc check (AC #3). Viewer/Commenter mutating ops resolve to `RoleProhibitedError`; reads/subscribe and unrelated ops still defer; Editor/Admin unchanged from 1.2.
- **403, not 401:** added `RoleProhibitedError(PermissionException)` (`core/exceptions.py`), mapped to `ERROR_ROLE_PROHIBITED` = HTTP 403 (`api/errors.py`), registered globally in `core/apps.py:ready()` via `api_exception_registry` (guarded against double-registration). MRO most-specific-first in `apply_exception_mapping` guarantees the 403 subclass wins over the `PermissionException`→401 catch-all; proven in `test_exception_mapping_role_prohibited_wins_over_catch_all` and via live REST 403 assertions.
- **Deny sets are type-string sets** in `core/rbac/enforcement.py` (mirrors `ADMIN_ONLY_OPERATIONS` string convention) to avoid a `core → contrib.database` import cycle. Both table- and view-scoped row mutation variants are listed so neither slips through `_check_permissions_with_view_fallback`.
- **Comment policy** encoded at the manager/handler level (no comment endpoint in free core — Epic 6): `create_comment` allowed for Commenter, denied for Viewer; `update/delete_comment` denied to both.
- **WebSocket parity is structural** — no mutating WS command exists (`CoreConsumer` = subscribe/remove_page only). Confirmed `TablePageType.can_add` (→ `listen_to_all`, not in deny sets) stays truthy for Viewer/Commenter so read/subscribe is preserved.
- **Frontend keeps deferring** (`hasPermission` → `null`) — server is the single source of truth (no second deny mirror). Spec updated to assert a mutating op still resolves to `null` on the client. No new i18n surfaced (no client-side deny mirror).
- **Scope:** workspace-scoped `RoleAssignment` covers the AC cases; database-scoped enforcement on Table/View/Row contexts (the optional `Table → Database` walk in `_application_from_context`) was NOT added — documented as deferred per Task 3 / Story 1.2 review note.
- **Tests:** 68 backend pass (`test_permission_manager.py` 47, `test_enforcement_handler.py` 13, `test_role_enforcement_api.py` 6, `test_role_enforcement_ws.py` 2); 3 frontend pass. Ruff check + format clean; ESLint clean. Provenance record validates and the gate logic passes (Bucket A flag set at PR time via `bucket-a` label/checkbox).

### File List

**New**
- `backend/src/baserow/core/rbac/enforcement.py` — Viewer/Commenter denied-operation type-string sets + `CREATE_COMMENT_OPERATION`.
- `backend/tests/baserow/core/rbac/test_enforcement_handler.py` — handler-level enforcement with real Row/Field/View contexts.
- `backend/tests/baserow/contrib/database/api/test_role_enforcement_api.py` — REST 403 (`ERROR_ROLE_PROHIBITED`) + MRO precedence assertions.
- `backend/tests/baserow/contrib/database/ws/test_role_enforcement_ws.py` — WS subscribe (`can_add`) preserved for Viewer/Commenter.
- `docs/clean-room/specs/1-3-role-enforcement.md` — behavior spec / deny policy.
- `docs/clean-room/provenance/1-3-role-enforcement-for-commenter-and-viewer.md` — Bucket A provenance record.

**Modified**
- `backend/src/baserow/core/rbac/permission_manager.py` — Viewer/Commenter deny branch; docstring + imports.
- `backend/src/baserow/core/exceptions.py` — added `RoleProhibitedError`.
- `backend/src/baserow/api/errors.py` — added `ERROR_ROLE_PROHIBITED` (403).
- `backend/src/baserow/core/apps.py` — global `RoleProhibitedError → ERROR_ROLE_PROHIBITED` registration in `ready()`.
- `backend/tests/baserow/core/rbac/test_permission_manager.py` — Story 1.3 manager-level deny/defer tests.
- `web-frontend/modules/core/permissionManagerTypes.js` — comment updated (keep deferring; server authoritative).
- `web-frontend/test/unit/core/permissionManagerTypes.spec.js` — defer test extended to a mutating op.

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-06-06 | 1.0 | Implemented Viewer/Commenter server-side deny enforcement: `RoleProhibitedError`→HTTP 403 (global), deny-op type-string sets, manager deny branch, full test matrix (68 backend + 3 frontend pass). Status → review. | claude-opus-4-8 (Claude Code, BMAD dev-story) |
| 2026-06-06 | 1.1 | Senior Developer Review (AI): adversarial review — all 3 ACs + 8 tasks verified against code + green tests (80 backend + 3 frontend re-run); op-type strings, MRO/registry/handler 403 wiring, provenance gate + sign-off all confirmed. Fixed 1 LOW test-gap: added REST 403 tests for delete_row + field update/delete + view update/delete (API suite 16→28 pass). 0 CRITICAL. Status → done. | claude-opus-4-8 (Claude Code, BMAD story-automator-review) |
