# Role-Combination Matrix — Story 6.4 Security Gate

**Generated:** 2026-06-12  
**Gate classification:** AR-2 release blocker (all cells must be GREEN before shipping)

---

## Most-Restrictive-Wins Precedence Rule

When a principal has multiple overlapping grants, the **narrower access governs**. The
resolution chain is:

1. **Scope precedence** — database-scoped assignment overrides workspace-scoped via
   `RbacHandler.get_effective_role` (`core/rbac/handler.py` L63–80).
   - `application_id`-specific assignment → wins over workspace-level fallback.
   - Example: workspace-level EDITOR + database-level VIEWER → effective role **VIEWER**
     (database scope wins).

2. **Field-permission override** — `FieldPermissionManagerType.check_multiple_permissions`
   (`core/field_permissions/permission_manager.py` L124–260) applies ON TOP of the
   effective role:
   - `editable_by_role` threshold: role below threshold → `FieldEditProhibitedError` (403
     on write attempts). Read is unaffected.
   - `readable_by_role` threshold: role below threshold → `FieldVisibilityProhibitedError`
     on explicit filter/sort (403); silent redaction on row reads via `filter_queryset`.

3. **Chain resolution order** — `PERMISSION_MANAGERS` in `config/settings/base.py` L1289:
   ```
   view_ownership → core → setting_operation → staff → allow_if_template →
   allow_public_builder → element_visibility → member → token →
   [write_field_values (EE)] → [role (EE)] → field_permissions → rbac → basic
   ```
   `field_permissions` precedes `rbac` and `basic`; a denial at this layer propagates
   immediately (returning an exception instance, not False).

4. **Anonymous principal (share)** — `FieldPermissionManagerType._hidden_field_ids`
   (`permission_manager.py` L262–278) treats `AnonymousUser` as having no role → all
   fields with a `readable_by_role` rule are deny-by-default (redacted from response).

---

## Legend

| Symbol | Meaning |
|--------|---------|
| **ALLOW** | Field returned in row response; write operations permitted at this role tier |
| **DENY-EDIT** | Field readable (returned in row response); write operations rejected (HTTP 403 `ERROR_FIELD_EDIT_PROHIBITED`). Enforced by `FieldPermissionManagerType` at `check_multiple_permissions` for `WRITE_FIELD_VALUES` and `UPDATE_FIELD` ops. |
| **REDACT** | Field absent from row response; filter/sort on this field returns HTTP 403 `ERROR_FIELD_VISIBILITY_PROHIBITED`. Enforced by `FieldPermissionManagerType.filter_queryset` via `get_hidden_field_ids`. |
| **DEFERRED** | Requires a prerequisite story not yet implemented; this cell cannot be tested until that story ships. |

---

## Field-Permission State Definitions

| State | `FieldPermission` row | Effect |
|-------|----------------------|--------|
| **unrestricted** | No row (`FieldPermission.objects.filter(field=...)` returns nothing) | No restriction; pre-1.4 behavior |
| **edit-restricted** | `editable_by_role=ADMIN`, `readable_by_role=NULL` | Field visible to all; only ADMIN can edit |
| **hidden** | `readable_by_role=ADMIN` (editable_by_role may also be set) | Field absent from row responses for VIEWER/COMMENTER/EDITOR; ADMIN sees and can edit |

---

## Matrix: 135 Cells (5 roles × 3 field-perm states × 3 view types × 3 share types)

### Share Type: `authenticated` (standard JWT login, no public share link)

| Role | Field State | regular view | personal view | locked view |
|------|------------|-------------|---------------|-------------|
| VIEWER | unrestricted | **ALLOW** [V-U-rg-a] | **ALLOW** [V-U-pv-a] | **ALLOW** [V-U-lk-a] |
| VIEWER | edit-restricted | **DENY-EDIT** [V-E-rg-a] | **DENY-EDIT** [V-E-pv-a] | **DENY-EDIT** [V-E-lk-a] |
| VIEWER | hidden | **REDACT** [V-H-rg-a] | **REDACT** [V-H-pv-a] | **REDACT** [V-H-lk-a] |
| COMMENTER | unrestricted | **ALLOW** [C-U-rg-a] | **ALLOW** [C-U-pv-a] | **ALLOW** [C-U-lk-a] |
| COMMENTER | edit-restricted | **DENY-EDIT** [C-E-rg-a] | **DENY-EDIT** [C-E-pv-a] | **DENY-EDIT** [C-E-lk-a] |
| COMMENTER | hidden | **REDACT** [C-H-rg-a] | **REDACT** [C-H-pv-a] | **REDACT** [C-H-lk-a] |
| EDITOR | unrestricted | **ALLOW** [Ed-U-rg-a] | **ALLOW** [Ed-U-pv-a] | **ALLOW** [Ed-U-lk-a] |
| EDITOR | edit-restricted | **DENY-EDIT** [Ed-E-rg-a] | **DENY-EDIT** [Ed-E-pv-a] | **DENY-EDIT** [Ed-E-lk-a] |
| EDITOR | hidden | **REDACT** [Ed-H-rg-a] | **REDACT** [Ed-H-pv-a] | **REDACT** [Ed-H-lk-a] |
| ADMIN | unrestricted | **ALLOW** [A-U-rg-a] | **ALLOW** [A-U-pv-a] | **ALLOW** [A-U-lk-a] |
| ADMIN | edit-restricted | **ALLOW** [A-E-rg-a] | **ALLOW** [A-E-pv-a] | **ALLOW** [A-E-lk-a] |
| ADMIN | hidden | **ALLOW** [A-H-rg-a] | **ALLOW** [A-H-pv-a] | **ALLOW** [A-H-lk-a] |
| interface-only | unrestricted | **DEFERRED** — Story 6.3 | **DEFERRED** | **DEFERRED** |
| interface-only | edit-restricted | **DEFERRED** — Story 6.3 | **DEFERRED** | **DEFERRED** |
| interface-only | hidden | **DEFERRED** — Story 6.3 | **DEFERRED** | **DEFERRED** |

### Share Type: `public` (public share link, anonymous user — `AnonymousUser`)

| Role | Field State | regular view | personal view | locked view |
|------|------------|-------------|---------------|-------------|
| anonymous | unrestricted | **ALLOW** [Anon-U-rg-pub] | **ALLOW** [Anon-U-pv-pub] | **ALLOW** [Anon-U-lk-pub] |
| anonymous | edit-restricted | **ALLOW** [Anon-E-rg-pub] ¹ | **ALLOW** [Anon-E-pv-pub] ¹ | **ALLOW** [Anon-E-lk-pub] ¹ |
| anonymous | hidden | **REDACT** [Anon-H-rg-pub] | **REDACT** [Anon-H-pv-pub] | **REDACT** [Anon-H-lk-pub] |

¹ Public share principals have no write path (read-only). ALLOW = field visible in read response.

### Share Type: `password` (password-protected share link, anonymous user after auth)

| Role | Field State | regular view | personal view | locked view |
|------|------------|-------------|---------------|-------------|
| anonymous (post-auth) | unrestricted | **ALLOW** [Anon-U-rg-pw] | **ALLOW** [Anon-U-pv-pw] | **ALLOW** [Anon-U-lk-pw] |
| anonymous (post-auth) | edit-restricted | **ALLOW** [Anon-E-rg-pw] ¹ | **ALLOW** [Anon-E-pv-pw] ¹ | **ALLOW** [Anon-E-lk-pw] ¹ |
| anonymous (post-auth) | hidden | **REDACT** [Anon-H-rg-pw] | **REDACT** [Anon-H-pv-pw] | **REDACT** [Anon-H-lk-pw] |

---

## Enforcing Code Path per Cell Type

| Outcome | Enforcing path |
|---------|---------------|
| **ALLOW** (authenticated) | `FieldPermissionManagerType` defers (no threshold or role ≥ threshold); `basic` or `rbac` grants |
| **DENY-EDIT** (authenticated) | `FieldPermissionManagerType.check_multiple_permissions` L186–243: `FieldEditProhibitedError` on `WRITE_FIELD_VALUES` / `UPDATE_FIELD` ops |
| **REDACT** (authenticated) | `FieldPermissionManagerType.filter_queryset` L268–284 excludes field id; `FieldPermissionHandler.get_hidden_field_ids` L44–70 is the single central call; explicit filter/sort → `FieldVisibilityProhibitedError` |
| **ALLOW** (public share) | Field has no `readable_by_role` rule; `_hidden_field_ids` anon path returns empty set |
| **REDACT** (public/password share) | `_hidden_field_ids` L262–278: `AnonymousUser` → deny-by-default for any `readable_by_role` rule |

---

## Most-Restrictive-Wins: 10 Conflict Scenarios

| # | Scenario | Expected outcome | Enforcing code path |
|---|----------|-----------------|---------------------|
| 1 | workspace EDITOR + database-scoped VIEWER | Effective role = VIEWER (database scope wins) | `RbacHandler.get_effective_role` L63–80 prefers `application_id`-specific assignment |
| 2 | database-scoped ADMIN + field `readable_by_role=EDITOR` | Field visible (ADMIN ≥ EDITOR) | `FieldPermissionManagerType._effective_role` + `roles.role_at_least` |
| 3 | workspace EDITOR + field `readable_by_role=ADMIN` | REDACT (EDITOR < ADMIN) | `FieldPermissionManagerType.filter_queryset` |
| 4 | database-scoped ADMIN + field `editable_by_role=ADMIN` | ALLOW edit (ADMIN ≥ ADMIN) | `check_multiple_permissions` L186–243: `role_at_least` → defers |
| 5 | database-scoped EDITOR + field `editable_by_role=ADMIN` | DENY-EDIT (EDITOR < ADMIN), read still allowed | `check_multiple_permissions` → `FieldEditProhibitedError`; read op not governed |
| 6 | workspace ADMIN + database-scoped VIEWER + field `readable_by_role=EDITOR` | REDACT (database VIEWER < EDITOR) | database scope overrides workspace ADMIN; `_effective_role` picks database assignment |
| 7 | workspace COMMENTER + no database assignment + field `readable_by_role=COMMENTER` | ALLOW (COMMENTER ≥ COMMENTER) | workspace-scoped fallback in `_effective_role`; threshold met → defer |
| 8 | workspace COMMENTER + database-scoped VIEWER + field `readable_by_role=COMMENTER` | REDACT (VIEWER < COMMENTER); database scope wins | database assignment VIEWER < COMMENTER threshold |
| 9 | no role assignment (workspace MEMBER only, no RBAC) + field `readable_by_role=VIEWER` | defer (field visible) — `_hidden_field_ids` returns empty for `role is None` | `_effective_role` returns None; `_hidden_field_ids` L254–257: `if role is None: continue` |
| 10 | anonymous user (public share) + field `editable_by_role=ADMIN` (no `readable_by_role`) | ALLOW read (no read rule → visible); write path irrelevant (anon has no write) | `_hidden_field_ids` anon path only checks `readable_by_role` rules |

---

## Notes on Deferred Cells

- **interface-only role** (15 cells): Requires Story 6.3 (interface-only collaborator) to be
  implemented. Until then, these cells cannot be asserted. Test file
  `backend/tests/baserow/security/test_interface_only_scope.py` is scaffolded with
  `@pytest.mark.skip` markers.

- **view_type=personal** and **view_type=locked**: Field permission enforcement is
  identical to regular views — the same `get_hidden_field_ids` call applies. View type
  only affects UI interactions (who sees the view, whether filters can be added), not
  which field values are included in row responses. All 3 view-type columns produce the
  same access outcome for a given role × field-perm combination.
