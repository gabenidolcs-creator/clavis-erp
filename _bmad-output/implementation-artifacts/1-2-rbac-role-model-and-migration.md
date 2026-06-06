---
baseline_commit: 17753c562c4bc14d2f12b290eedef37003d388df
---

# Story 1.2: RBAC role model and migration

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a workspace admin,
I want a granular Role hierarchy above the current ADMIN/MEMBER model,
so that I can later assign Viewer, Commenter, Editor, and Admin tiers to members at workspace and database scope.

Realizes UJ-4. **Bucket A `[A]` — clean-room reimplementation; provenance record required (see "Clean-Room Mandate" below).**

## Context & Scope

**This story builds the RBAC *foundation* — the role model, assignability, the new PermissionManager wired into the chain, and the reversible migration. It does NOT implement Commenter/Viewer 403 enforcement (Story 1.3) or field permissions (Stories 1.4/1.5).** Keep the blast radius tight: stand up the layer and migrate without changing what any existing member can do today.

**Why now:** Per architecture §"Implementation sequence" step 1, the RBAC foundation (D6) is a load-bearing prerequisite. Story 1.3 (Commenter/Viewer enforcement), 1.4 (field-permission edit restriction), and FR-31 (interface-only) all build on the role layer this story creates. [Source: architecture.md lines 157, 167; epics.md lines 64, 105]

**Scope boundary (do NOT cross):**
- IN: `core/rbac/` role layer (fixed tiers Viewer/Commenter/Editor/Admin), assignable at workspace **and** database scope; a new `RbacPermissionManagerType` registered into `PERMISSION_MANAGERS`; reversible data migration ADMIN→Admin / MEMBER→Editor; the model→handler→serializer/API→frontend-registry→component test matrix; a provenance record.
- OUT: Commenter/Viewer deny-with-403 semantics (Story 1.3); field edit/visibility permissions (1.4/1.5); custom-role builder (explicitly out of scope per FR-29); interface-only collaborator (FR-31).
- The new manager must **preserve current behavior** — a member who can write today must still write after migration. Enforcement *tightening* for Commenter/Viewer comes in 1.3. [Source: epics.md lines 243-264]

## Clean-Room Mandate (Bucket A)

This feature exists under the PE/EE license in `enterprise/backend/src/baserow_enterprise/role/`. That source **must not be copied, adapted, or recalled from memory.** [Source: architecture.md lines 205-206, 240-242, 256, 260; memory baserow-open-core-license-constraint]

- Reference `premium/`/`enterprise/` only for **registration shape via public MIT symbols** (e.g. *that* a `PermissionManagerType` subclass is registered via `permission_manager_type_registry.register(...)` in `apps.ready()`) — never to replicate behavior logic.
- **Our scope diverges from enterprise by design:** enterprise RBAC is a *custom-role* system (DB-driven operation→role mappings, teams). Ours is **fixed tiers** — simpler, code-defined roles, no operation-set tables. Do not import the enterprise model.
- Author a behavior spec from allowed public sources only (public Baserow docs, public upstream SaaS UI, public issues/changelogs); no `premium/`/`enterprise/` internal symbol name as the thing to replicate (free-core MIT symbols are allowed). [Source: docs/clean-room/allowed-sources.md; Story 1.1]
- **Attach a provenance record** under `docs/clean-room/provenance/` using `docs/clean-room/templates/provenance-record-template.md`. No provenance → the merge gate (`docs/clean-room/scripts/check_provenance.py` + `.github/workflows/clean-room-provenance-gate.yml`) blocks merge. Flag the PR Bucket A via the `bucket-a` label or the PR-template checkbox. [Source: Story 1.1 Dev Agent Record; architecture.md lines 240-242]
- **Legal gate (Open Q7):** Story 1.1 stood up the gate but left owner/legal sign-off as `_TODO_`; the gate treats unfilled rows as "not signed off". Bucket A *execution* is legally blocked until `docs/clean-room/owner-and-sign-off.md` is filled by real humans. Confirm this is resolved before writing code, or surface it as a blocker. [Source: architecture.md lines 382, 438; Story 1.1 Completion Notes]

## Acceptance Criteria

1. **Role layer introduced; tiers assignable at workspace + database scope; routed through `PERMISSION_MANAGERS`.** Given the free tier today has only ADMIN/MEMBER (`backend/src/baserow/core/models.py`), when the RBAC layer (`backend/src/baserow/core/rbac/`) is introduced, then fixed Roles **Viewer / Commenter / Editor / Admin** are assignable at workspace **and** database scope, **and** role checks resolve through a **new `PermissionManagerType` registered into the existing `PERMISSION_MANAGERS` chain** in `config/settings/base.py` — never a parallel/ad-hoc path. [Source: epics.md lines 226-232; architecture.md lines 127, 236, 255]

2. **Reversible migration with no silent write-loss; equivalence test.** Given existing members with `ADMIN` or `MEMBER`, when the migration runs, then **ADMIN maps to Admin and MEMBER maps to Editor** (not Viewer/Commenter — no silent write-loss), **and** the migration is reversible with a documented rollback (`RunPython(forward, reverse)`), **and** a test asserts **every pre-migration member retains equivalent write capability** after migration. [Source: epics.md lines 234-240; architecture.md line 127]

3. **Full Bucket A definition-of-done.** Given the per-feature test matrix, when this story ships, then **model → handler → serializer/API → frontend-registry → component** tests pass **and a provenance record is attached** (NFR-7, AR-1). [Source: epics.md lines 242-244; architecture.md lines 247-248, 257]

## Tasks / Subtasks

- [x] **Task 1 — Author behavior spec + create provenance record (AC: #3, Clean-Room)** — do this FIRST, before code
  - [x] Confirm Open Q7 legal sign-off is recorded in `docs/clean-room/owner-and-sign-off.md`; if still `_TODO_`, HALT and surface as blocker.
  - [x] Write a behavior spec (fixed-tier role hierarchy + scope assignment + migration mapping) citing only allowed public sources. Use `docs/clean-room/templates/behavior-spec-template.md`.
  - [x] Start a provenance record from `docs/clean-room/templates/provenance-record-template.md` under `docs/clean-room/provenance/`; keep it updated through implementation.
- [x] **Task 2 — Create the `core/rbac/` clean-room role layer (AC: #1)**
  - [x] `backend/src/baserow/core/rbac/__init__.py`, `roles.py` — define the four fixed roles as code constants (Viewer / Commenter / Editor / Admin) with a documented capability ordering (Admin > Editor > Commenter > Viewer). No DB-driven operation→role table (fixed tiers, not custom roles). [Source: epics.md line 226; FR-29 "Custom-role builder out of scope"]
  - [x] `backend/src/baserow/core/rbac/models.py` — `RoleAssignment` model: (subject/user, role, scope) where scope is **workspace or database**. Layer this **above** the existing `WorkspaceUser.permissions` (ADMIN/MEMBER) — do not replace that field. [Source: architecture.md line 271 "role assignment (above ADMIN/MEMBER)"; models.py:321-356]
  - [x] `backend/src/baserow/core/rbac/handler.py` — `RbacHandler`: assign/get a member's effective role at a given workspace/database scope (most-specific scope wins). Mutations go through the handler, not direct ORM in views. [Source: architecture.md lines 222-224, 236-237]
  - [x] `backend/src/baserow/core/rbac/operations.py` — operation type(s) for managing role assignments (register via `operation_type_registry` in `core/apps.py` `ready()`). [Source: core/operations.py; core/apps.py:247-270]
- [x] **Task 3 — Add `RbacPermissionManagerType` and register it into the chain (AC: #1)**
  - [x] `backend/src/baserow/core/rbac/permission_manager.py` — subclass `PermissionManagerType` (mirror the *shape* of `BasicPermissionManagerType`, not enterprise behavior). `type = "rbac"`, `supported_actor_types = [UserSubjectType.type]`. Implement `check_multiple_permissions` (the abstract method). [Source: registries.py:669-829; permission_manager.py:286-359]
  - [x] **Preserve current behavior (critical):** in this story the manager must NOT deny anything a member can do today. Map Admin→(today's ADMIN capability) and Editor→(today's MEMBER capability). Return `None`/omit for checks it does not own so the chain (basic/member managers) still decides. Commenter/Viewer *restriction* is Story 1.3 — do not implement deny-403 here. [Source: epics.md lines 243-264]
  - [x] **Avoid the BasicPermissionManager regression:** `BasicPermissionManagerType` checks `permissions == "ADMIN"` literally (permission_manager.py:~330). Do **not** mutate `WorkspaceUser.permissions` string values to "Admin"/"Editor" — that would silently break admin-only ops. Keep ADMIN/MEMBER intact and layer roles via `RoleAssignment`. If any approach changes the stored values, the basic manager must be updated in lockstep and covered by tests. [Source: permission_manager.py:286-359; AC #2 "no silent write-loss"]
  - [x] Register the manager: instantiate + `permission_manager_type_registry.register(...)` in `core/apps.py` `ready()`, and add `"rbac"` to `PERMISSION_MANAGERS` in `config/settings/base.py` (place after `"member"`, before `"basic"`; do not collide with the enterprise `"role"` entry). [Source: base.py:1270-1289; apps.py:247-270]
- [x] **Task 4 — Reversible data migration ADMIN→Admin / MEMBER→Editor (AC: #2)**
  - [x] Schema migration creates the `RoleAssignment` model. *(Lands in `core/migrations/0115_rbac_roleassignment.py` — the model is registered on the `core` app config per the "follow the owning app convention" guidance, so no separate `core/rbac/migrations/` package is created.)*
  - [x] Data migration `RunPython(forward, reverse)`: forward derives a `RoleAssignment` (Admin / Editor) from each existing `WorkspaceUser.permissions` (ADMIN→Admin, MEMBER→Editor). Reverse removes the derived assignments (documented rollback). Use `apps.get_model(...)` (no direct imports). *(`WorkspaceInvitation` rows have no user subject, so no RoleAssignment is derivable until acceptance — handled in a later story; their legacy `permissions` field is left intact.)* [Source: core/migrations/0010_fix_trash_constraint.py; models.py:72-73, 321-356, 382]
  - [x] Document the rollback steps in the provenance record / migration docstring.
- [x] **Task 5 — Serializer/API for role assignment (AC: #1, #3)**
  - [x] Thin DRF view(s) over `RbacHandler` under the owning app's `api/` to assign/read a role at workspace and database scope. `snake_case` JSON, 403 on unauthorized, existing DRF error convention. [Source: architecture.md lines 186-190, 214, 296, 315]
- [x] **Task 6 — Frontend registry plumbing (AC: #1, #3)**
  - [x] Register the rbac permission manager type in `web-frontend/modules/core/permissionManagerTypes.js` (mirror backend) via `$registry.register(...)` in `plugin.js`. The frontend manager defers (`hasPermission` returns `null`) so client behavior is preserved. [Source: architecture.md lines 142, 196-199, 221-224, 301; web-frontend/modules/core/permissionManagerTypes.js]
- [x] **Task 7 — Test matrix (AC: #2, #3)**
  - [x] **model** — `RoleAssignment` creation/uniqueness/scope (workspace vs database). Backend pytest, mirror path `backend/tests/baserow/core/rbac/`.
  - [x] **handler** — assign/get effective role; most-specific-scope-wins.
  - [x] **permission manager** — mirror `test_basic_permissions.py`; assert Admin/Editor retain current capabilities and the manager defers (returns `None`) where not owned. [Source: test_basic_permissions.py:177-261]
  - [x] **migration** — the AC #2 equivalence test: build pre-migration ADMIN/MEMBER members, run forward, assert each retains equivalent **write** capability; run reverse, assert restoration.
  - [x] **serializer/API** — assign/read role endpoints (200 happy path, 403 unauthorized).
  - [x] **frontend registry + component** — registry registers; component test for the registered type. `just f yarn test:core <path>`. [Source: architecture.md lines 247-248; write-frontend-unit-test skill]
  - [x] Add any new i18n strings to `en.json` + locales. [Source: architecture.md line 248]
- [x] **Task 8 — Finalize provenance + DoD**
  - [x] Complete the provenance record (sources consulted + implementer attestation); flag PR Bucket A (`bucket-a` label or PR-template checkbox); confirm the provenance gate passes. [Source: Story 1.1; architecture.md lines 240-242]

## Dev Notes

### Architecture patterns & constraints (MUST follow)
- **Registry pattern, no core rewrites:** new `PermissionManagerType` subclass registered via the singleton `permission_manager_type_registry` in `apps.ready()`; frontend mirrors with `$registry.register`. [Source: architecture.md lines 47, 99, 221-224]
- **Handler spine:** all mutations route through `RbacHandler` (REST/WS/CLI share it); never direct ORM in API views (skips broadcast + cache invalidation). [Source: architecture.md lines 135, 224, 260]
- **Permission routing (security-critical):** ALL authorization through the `PERMISSION_MANAGERS` chain — never a parallel/ad-hoc check. [Source: architecture.md lines 236, 255; NFR-4 epics.md line 81]
- **Naming/format:** `snake_case` files/columns, `PascalCase` classes (`RoleAssignment`, `RbacPermissionManagerType`), Ruff 88-col, Python 3.14. `snake_case` JSON payloads (do NOT camelCase). 403 for permission denial. ISO-8601 dates. [Source: architecture.md lines 180-217]
- **Bucket A placement:** code lands in core `backend/src` / `web-frontend` — NEVER in `premium/`/`enterprise/`. Tests in `backend/tests/baserow/...` mirroring `src` (not co-located). [Source: architecture.md lines 204-210, 256, 260]

### Source tree components to touch
- `core/models.py` `[X]` — role assignment layered above ADMIN/MEMBER (do not replace the `permissions` field). [Source: architecture.md line 271]
- `core/permission_manager.py` / `config/settings/base.py` `[X]` — register the new manager into `PERMISSION_MANAGERS`. [Source: architecture.md line 272; base.py:1270-1289]
- `core/rbac/` `[A]` NEW — `models.py, handler.py, roles.py, operations.py, permission_manager.py, migrations/`. [Source: architecture.md lines 273-275]
- `web-frontend/modules/core/` `[X]` — role UI / `$registry` plumbing / permission manager type. [Source: architecture.md line 301]

### Files to READ before coding (current state — preserve behavior)
- `backend/src/baserow/core/models.py:72-73` (`WORKSPACE_USER_PERMISSION_ADMIN/MEMBER`), `:321-356` (`WorkspaceUser.permissions` CharField, default MEMBER), `:382` (`WorkspaceInvitation.permissions`).
- `backend/src/baserow/core/permission_manager.py:286-359` (`BasicPermissionManagerType` — the literal `== "ADMIN"` check is the regression hazard) and `:157-285` (`WorkspaceMemberOnlyPermissionManagerType`).
- `backend/src/baserow/core/registries.py:669-829` (`PermissionManagerType` base + `check_multiple_permissions` contract), `:1409` (`permission_manager_type_registry`).
- `backend/src/baserow/core/handler.py:219-280` (chain iteration — managers return per-check result or `None` to defer).
- `backend/src/baserow/core/types.py:33-44` (`PermissionCheck`).
- `backend/src/baserow/config/settings/base.py:1270-1289` (`PERMISSION_MANAGERS` order; enterprise `"role"` only when installed).
- `backend/src/baserow/core/migrations/0010_fix_trash_constraint.py` (reversible `RunPython(forward, reverse)` pattern).
- `backend/tests/baserow/core/test_basic_permissions.py:177-261` (permission manager test shape; `@override_settings(PERMISSION_MANAGERS=[...])`).
- `web-frontend/modules/core/permissionManagerTypes.js` (frontend manager registry).

### Clean-room reference-shape ONLY (do not copy behavior)
- `enterprise/backend/src/baserow_enterprise/role/` (`permission_manager.py`, `models.py`, `handler.py`, `default_roles.py`), registered in `enterprise/backend/src/baserow_enterprise/apps.py:156-162`; frontend `enterprise/web-frontend/modules/baserow_enterprise/{roleTypes.js,utils/roles.js,services/roleAssignments.js}`. Look only at *that registration happens and where*; the enterprise model is custom-role/teams/license-gated and is NOT our design. [Source: agent code map; architecture.md lines 256, 260, 310]

### Key design decisions / hazards
- **`RoleAssignment` layered above ADMIN/MEMBER** (architecture.md:271) is the recommended approach — it avoids mutating `permissions` strings and the consequent `BasicPermissionManagerType` regression. Migration *derives* assignments; it does not rewrite the legacy field. This directly satisfies AC #2 "no silent write-loss".
- **Chain position:** add `"rbac"` after `"member"`, before `"basic"`. Verify with the equivalence test that admin-only operations still resolve correctly post-migration.
- **Defer, don't deny:** in 1.2 the manager grants/defers to preserve today's behavior; it does not introduce new denials. The Commenter/Viewer 403 tightening is Story 1.3's job. [Source: epics.md lines 243-264]

### Testing standards
- Backend: `just b test backend/tests/baserow/core/rbac/` (pytest + pytest-django). Frontend: `just f yarn test:core <path>` (Vitest). Full matrix model→handler→serializer/API→frontend-registry→component is the Bucket A DoD. [Source: architecture.md lines 247-248; AGENTS.md Testing]

### Previous story intelligence (Story 1.1)
- The clean-room gate is live: provenance template + `check_provenance.py` + `.github/workflows/clean-room-provenance-gate.yml` + PR-template Bucket A checkbox. **This is the first downstream Bucket A consumer** — it must attach a provenance record or the gate blocks merge. [Source: Story 1.1 Dev Agent Record / File List]
- The gate strips HTML comments before its excluded-source scan; do not put `premium/`/`enterprise/` paths in the visible `## Sources Consulted` block. [Source: Story 1.1 Senior Developer Review]
- Open Q7 owner/legal sign-off is still `_TODO_` in `docs/clean-room/owner-and-sign-off.md` — confirm filled before Bucket A code (Task 1).

### Git intelligence
- Branch from `develop`. Baseline `17753c562` (Story 1.1 merge). Recent perf commit `b8559a56c "Improve permissions endpoint query performance"` touches the permissions endpoint — re-check it isn't disturbed by the new manager's `get_permissions_object`. Conventional Commit prefix `feat(story-1.2): ...`. [Source: git log]

### Project Structure Notes
- New backend code in `backend/src/baserow/core/rbac/`; tests mirror at `backend/tests/baserow/core/rbac/` (NOT co-located). Migrations in `core/rbac/migrations/` (or `core/migrations/` if the model lives on a core app config — follow the owning app convention). Frontend in `web-frontend/modules/core/`. No `premium/`/`enterprise/` edits. [Source: architecture.md lines 204-210, 273-275, 301]
- No new env var expected for this story. If a feature flag is introduced, follow the `add-django-config-env-var` skill.

### References
- [Source: epics.md#Epic 1 → Story 1.2: RBAC role model and migration (lines 220-244)] — the three ACs.
- [Source: epics.md lines 64 (FR-29), 81 (NFR-4), 105 (AR-12), 150] — RBAC foundation, server-side every-surface enforcement, clean-room role layer.
- [Source: architecture.md lines 127 (D6 RBAC), 157/167 (sequence + prerequisite), 204-210/255-260 (Bucket A placement + anti-patterns), 221-224/236-237 (registry + handler + PERMISSION_MANAGERS), 271-275/301/333 (structure map), 382/438 (Open Q7)].
- [Source: backend code map] — models.py:72-73,321-356,382; permission_manager.py:286-359; registries.py:669-829,1409; handler.py:219-280; types.py:33-44; base.py:1270-1289; migrations/0010_fix_trash_constraint.py; test_basic_permissions.py:177-261.
- [Source: docs/clean-room/ (Story 1.1)] — allowed-sources.md, templates/{behavior-spec,provenance-record}-template.md, scripts/check_provenance.py, owner-and-sign-off.md.
- [Source: memory baserow-open-core-license-constraint] — paid features need clean-room reimplement; PE/EE license forbids copying.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Code, BMAD dev-story workflow).

### Debug Log References

- `makemigrations` requires `BASEROW_OSS_ONLY=true` + `DJANGO_SETTINGS_MODULE=baserow.config.settings.dev` (premium/enterprise not installed in this env).
- Test settings (`baserow.config.settings.test`) patch `os.getenv` to block all real env vars except the `DATABASE_*` prefix, so `BASEROW_OSS_ONLY` must be passed via a `TEST_ENV_FILE` (created `backend/.env.testing-oss`).
- Backend tests run against the local `clavis_postgres` container (`DATABASE_HOST=172.22.0.12`, user `clavis`) with `BASEROW_TESTS_SETUP_DB_FIXTURE=off` so real migrations run (needed by the `migrator` fixture).
- Migration tests carry the `once_per_day_in_ci` marker → run with `--run-once-per-day-in-ci`. They are not transactional, so rows persist between them; fixed-PK / shared-username collisions were resolved by using unique names and dropping explicit PKs.

### Completion Notes List

- **Clean-room compliance:** No `premium/`/`enterprise/` source was opened, grepped, or recalled. Implementation is from the public behavior spec (`docs/clean-room/specs/1-2-rbac-role-model.md`) and free-core MIT symbols only. Provenance gate verified PASS.
- **Design — layer, don't replace:** `RoleAssignment` is layered above the legacy `WorkspaceUser.permissions` (ADMIN/MEMBER) field; the migration *derives* assignments and never rewrites the legacy field, satisfying AC #2 "no silent write-loss". The model lives on the existing `core` app (`app_label="core"`, migration `core/migrations/0115`) to avoid INSTALLED_APPS/AppConfig churn; string FK refs avoid a circular import and it is registered at the bottom of `core/models.py`.
- **Defer, don't deny:** `RbacPermissionManagerType` only ever *grants* (Admin → admin-only ops) or *defers*; it never denies, preserving today's behavior. The new role-management ops are added to `BasicPermissionManagerType.ADMIN_ONLY_OPERATIONS` in lockstep so legacy admins with no `RoleAssignment` remain authorized. Commenter/Viewer 403 tightening is deferred to Story 1.3.
- **Chain position:** `"rbac"` inserted after `"member"`, before `"basic"` in `PERMISSION_MANAGERS`.
- **Tests:** backend 30 passed (model 5, handler 8, permission_manager 7, migration 2 [once-per-day], API 8); frontend 3 passed (registry + roles + defer). Ruff check + format clean on all touched backend files.
- **AC coverage:** AC #1 — role layer + 4 tiers at workspace/database scope routed through the chain (`test_permission_manager.py`, `test_handler.py`). AC #2 — reversible `RunPython(forward, reverse)` + equivalence test (`test_rbac_migration.py`). AC #3 — full model→handler→serializer/API→frontend-registry→component matrix + provenance record attached.

### File List

**New — backend (`core/rbac/` clean-room layer):**
- `backend/src/baserow/core/rbac/__init__.py`
- `backend/src/baserow/core/rbac/roles.py`
- `backend/src/baserow/core/rbac/models.py`
- `backend/src/baserow/core/rbac/handler.py`
- `backend/src/baserow/core/rbac/operations.py`
- `backend/src/baserow/core/rbac/permission_manager.py`
- `backend/src/baserow/core/migrations/0115_rbac_roleassignment.py`

**New — backend API:**
- `backend/src/baserow/api/rbac/__init__.py`
- `backend/src/baserow/api/rbac/serializers.py`
- `backend/src/baserow/api/rbac/views.py`
- `backend/src/baserow/api/rbac/urls.py`

**Modified — backend:**
- `backend/src/baserow/core/models.py` (import `RoleAssignment` to register it on the core app)
- `backend/src/baserow/core/apps.py` (register `RbacPermissionManagerType` + the two operation types)
- `backend/src/baserow/core/permission_manager.py` (add the two RBAC ops to `ADMIN_ONLY_OPERATIONS`)
- `backend/src/baserow/config/settings/base.py` (add `"rbac"` to `PERMISSION_MANAGERS`)
- `backend/src/baserow/api/urls.py` (include `rbac` urls)

**New — backend tests:**
- `backend/tests/baserow/core/rbac/test_models.py`
- `backend/tests/baserow/core/rbac/test_handler.py`
- `backend/tests/baserow/core/rbac/test_permission_manager.py`
- `backend/tests/baserow/core/migrations/test_rbac_migration.py`
- `backend/tests/baserow/api/rbac/test_rbac_views.py`
- `backend/.env.testing-oss` (OSS-only test env helper)

**New/Modified — frontend:**
- `web-frontend/modules/core/permissionManagerTypes.js` (add `RbacPermissionManagerType`)
- `web-frontend/modules/core/plugin.js` (register the rbac permission manager type)
- `web-frontend/locales/en.json` (add `permission.rbac*` i18n strings)
- `web-frontend/test/unit/core/permissionManagerTypes.spec.js` (registry + component test)

**New — docs (clean-room):**
- `docs/clean-room/specs/1-2-rbac-role-model.md` (behavior spec)
- `docs/clean-room/provenance/1-2-rbac-role-model-and-migration.md` (provenance record)

### Change Log

| Date | Change |
|---|---|
| 2026-06-06 | Implemented Story 1.2: fixed-tier RBAC role layer (`core/rbac/`), `RoleAssignment` model layered above ADMIN/MEMBER, `RbacPermissionManagerType` registered into `PERMISSION_MANAGERS` (grant-or-defer, no new denials), reversible ADMIN→Admin / MEMBER→Editor data migration, thin DRF role-assignment API, frontend registry plumbing + i18n, and the full backend+frontend test matrix. Clean-room behavior spec + provenance record attached (gate PASS). Status → review. |
| 2026-06-06 | Senior Developer Review (AI): 0 Critical. Fixed H1 (N+1 in permission chain → batch-load), H2 (reverted unrelated yarn env pollution), M1 (test chain fidelity), M2 (handler cross-workspace guard). +2 regression tests. Backend 40 + frontend 3 green, ruff clean, provenance PASS. Status → done. |

## Senior Developer Review (AI)

**Reviewer:** Tinsu (adversarial AI review) · **Date:** 2026-06-06 · **Outcome:** ✅ Approved (status → done)

### Summary
All 3 ACs are genuinely implemented and every task marked `[x]` is backed by real code + tests. Clean-room compliance holds: no `premium/`/`enterprise/` leakage in the visible spec/provenance, owner+legal sign-off recorded, provenance gate validates (PASS when the PR is flagged `bucket-a`). Verified live: **backend 40 tests pass** (model 5, handler 9, permission-manager 8, migration 2 once-per-day, API 16), **frontend 3 pass**, ruff check+format clean. Four issues found and auto-fixed; no Critical findings remain.

### Findings & fixes (all auto-applied)
- **[HIGH · perf/security-chain] N+1 in `RbacPermissionManagerType.check_multiple_permissions`.** Called `get_effective_role` (1–2 queries) **per check**, regressing the permission chain that perf commit `b8559a56c` had just optimized. → Rewrote to batch-load all actor assignments in **one** query (`_build_role_index` / `_effective_role_from_index`); added `test_manager_batch_loads_assignments_no_n_plus_1` asserting a single query for 20 checks.
- **[HIGH · supply-chain/hygiene] Undocumented yarn env pollution.** `yarn.lock` (+20k/-14k, converted v1→v4), `package.json` dropped the `vuejs3-datepicker/**/minimatch ^3.1.3` security `resolutions` pin, plus untracked `.yarnrc.yml` (`npmMinimalAgeGate: 0`, `enableScripts: true`, `approvedGitRepositories: ["**"]`) and a `.yarn/install-state.gz` cache blob — none in the File List, none related to RBAC (drift from the automate session). → Reverted `package.json`+`yarn.lock` to develop, removed the untracked `.yarn/` and `.yarnrc.yml`. Develop is yarn-classic (v1); the v4 conversion was the injected artifact.
- **[MEDIUM · test fidelity] `RBAC_CHAIN` didn't mirror production order** (placed `rbac` before `token`). → Reordered to `member → token → rbac → basic` matching `PERMISSION_MANAGERS`, documented the OSS-absent enterprise managers.
- **[MEDIUM · handler spine] `RbacHandler.assign_role` didn't validate `application` belongs to `workspace`.** The API guarded it but the handler is the shared REST/WS/CLI spine. → Added a defense-in-depth `ValueError` guard + `test_assign_role_rejects_application_in_other_workspace`.

### Notes (no action required)
- Database-scoped role resolution only matches when the op context *is* an Application/Database; Table/View/Row contexts fall back to workspace scope. Documented and intentional for the 1.2 foundation — finer context resolution lands with Commenter/Viewer enforcement (Story 1.3).
- PR-time action: apply the `bucket-a` label (or PR-template checkbox) so the clean-room gate enforces (record already validates).
