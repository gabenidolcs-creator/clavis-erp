---
baseline_commit: c0e6215518b8044b3e7b10755d0b2a88d849a035
---

# Story 1.8: Password-protected share links with least-privilege principal

Status: done

## Story

As a member,
I want to add a password to a public share link that resolves under a least-privilege principal,
so that I can share read-only Data safely without exposing my full permissions.

**Bucket:** B — existing Baserow upstream code can be read/used. No clean-room provenance docs required (clean-room mandate is for Bucket A only).

## Acceptance Criteria

1. **Given** a password-protected share link,
   **When** a visitor enters the correct password,
   **Then** read access is granted under a deny-by-default least-privilege **share principal** (FR-17), never the sharer's permissions,
   **And** fields with any `readable_by_role` restriction (Story 1.5) are hidden from the share principal — never the sharer's field-level permissions.

2. **Given** the password store,
   **When** a password is set and later verified,
   **Then** it is hashed with **Argon2id** (Django `Argon2PasswordHasher`) and compared in constant time,
   **And** the share token (view `slug`) is generated with `secrets.token_urlsafe()` (already in place — must not regress).

3. **Given** repeated wrong-password attempts from the same IP against the same link,
   **When** they exceed **5 attempts per minute**,
   **Then** a 429 response is returned with a uniform error,
   **And** the error message does not reveal whether the link exists (same response body for wrong-password and non-existent link).

4. **Given** the password is removed (`public_view_password` set to `""`),
   **When** the link is accessed,
   **Then** it reverts to open/closed as configured (no token required for open links, 401 for non-public — existing behavior must not regress).

## Tasks / Subtasks

- [x] Task 1: Argon2id KDF (AC: #2)
  - [x] 1a: Add `argon2-cffi>=23.1.0` to `backend/pyproject.toml` dependencies
  - [x] 1b: Add `PASSWORD_HASHERS` to `backend/src/baserow/config/settings/base.py` with `Argon2PasswordHasher` as the first entry
  - [x] 1c: Create migration `0215_view_password_max_length.py` — `AlterField` on `database_view.public_view_password`, max_length 128 → 256 (safety margin for Argon2id encoded output)
  - [x] 1d: Update `max_length=256` on `View.public_view_password` field in `models.py` to match migration

- [x] Task 2: Rate-limiting on `PublicViewAuthView.post` (AC: #3)
  - [x] 2a: Add `ERROR_PUBLIC_VIEW_AUTH_RATE_LIMIT` constant to `backend/src/baserow/contrib/database/api/views/errors.py` (HTTP 429)
  - [x] 2b: In `PublicViewAuthView.post`, wrap the password-check logic in a `rate_limit(rate=RateLimit.from_string("5/m"), key=f"public_view_auth:{ip}:{slug}")` call, keyed per-IP-per-slug
  - [x] 2c: Add `RateLimitExceededException: ERROR_PUBLIC_VIEW_AUTH_RATE_LIMIT` to the `@map_exceptions` dict and `429` to the OpenAPI schema

- [x] Task 3: Uniform error — no link-existence oracle (AC: #3)
  - [x] 3a: In `PublicViewAuthView.post`, catch `ViewDoesNotExist` and raise `AuthenticationFailed()` instead of propagating a 404 — remove `ViewDoesNotExist: ERROR_VIEW_DOES_NOT_EXIST` from that endpoint's `@map_exceptions`

- [x] Task 4: Share principal — least-privilege field enforcement (AC: #1)
  - [x] 4a: In `FieldPermissionManagerType._hidden_field_ids` (`backend/src/baserow/core/field_permissions/permission_manager.py`), when `actor_id is None` (AnonymousUser / share principal), return **all** field IDs that carry any `readable_by_role` restriction — i.e., `return {field_id for field_id, _, _ in rows}` instead of `return set()`
  - [x] 4b: Ensure `get_hidden_field_ids_for_view_user` and `get_redacted_field_ids_for_user` in `api/views/utils.py` already propagate `request.user` (AnonymousUser) to `FieldPermissionHandler.get_hidden_field_ids` for all public row endpoints — verify with grep, no code change needed if already wired

- [x] Task 5: Frontend — handle 429 rate-limit response (AC: #3)
  - [x] 5a: In `publicViewLogin.vue`, add a `else if (statusCode === 429)` branch that shows a rate-limit error message (i18n key `publicViewAuthLogin.error.rateLimitTitle` / `publicViewAuthLogin.error.rateLimitText`)
  - [x] 5b: Add those two i18n keys to `web-frontend/modules/database/locales/en.json`

- [x] Task 6: Tests
  - [x] 6a: Backend API tests in `test_view_views.py` — cover: Argon2id hash prefix in stored value, rate limit returns 429 after N attempts, uniform 401 on non-existent slug, share principal hides restricted fields
  - [x] 6b: Backend handler tests in `test_view_handler.py` — cover: `_hidden_field_ids` returns restricted fields for AnonymousUser
  - [x] 6c: Frontend unit test for `publicViewLogin.vue` 429 branch

## Dev Notes

### Critical: What Already Exists (Do NOT reinvent)

Baserow upstream already ships a **complete** password-protected share link feature. The story adds **four narrowly-scoped improvements** on top of existing code. Before writing any code, read the files listed in the Key File Map to understand the existing state.

**Existing and working:**
- `View.public_view_password` CharField on `database_view` table — added by migration `0068_view_public_view_password.py`
- `View.set_password()` / `View.check_public_view_password()` / `View.public_view_has_password` property — `views/models.py:194–223`
- JWT token system: `encode_public_view_token` / `decode_public_view_token` / `is_public_view_token_valid` / `_get_public_view_jwt_secret` — `views/handler.py:3832–3881`
- `PublicViewAuthView` API endpoint (`POST /database/views/{slug}/public/auth/`) — `api/views/views.py:2125–2184`
- `get_public_view_by_slug()` — checks token, raises `NoAuthorizationToPubliclySharedView` if password-protected and no valid token — `views/handler.py:3590–3664`
- Frontend visitor password entry page — `web-frontend/modules/database/pages/publicViewLogin.vue`
- Frontend share-link manager with enable/disable password modals — `ShareViewLink.vue`, `EnablePasswordModal.vue`, `DisablePasswordModal.vue` (all already complete)
- `View.slug = secrets.token_urlsafe()` — high-entropy token already in place

**The four gaps this story closes:**
1. KDF is PBKDF2 (Django default) → upgrade to **Argon2id**
2. No rate-limiting on the auth endpoint → add **5/min per-IP-per-slug**
3. Wrong slug returns 404 (leaks link existence) → return **401 (same as wrong password)**
4. `AnonymousUser` accessing public rows sees all fields, bypassing Story 1.5 field permissions → enforce **deny-by-default for fields with any `readable_by_role` restriction**

### Task 1: Argon2id — Technical Details

**Dependency:** add `"argon2-cffi>=23.1.0"` to `dependencies = [...]` in `backend/pyproject.toml` (line ~17). Django 5.2's `Argon2PasswordHasher` requires this package.

**Django settings:** add to `base.py` (near top of file, before `AUTH_PASSWORD_VALIDATORS`):
```python
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]
```
Keeping PBKDF2 entries means existing user account passwords still verify (Django tries the stored algorithm). Existing `public_view_password` PBKDF2 hashes also still verify — they are NOT auto-upgraded (no `setter` is passed to `check_password()`). New passwords set after deployment use Argon2id.

**max_length:** Django 5.2 `Argon2PasswordHasher` default params (m=102400, t=2, p=8) produce a hash string of ~106 chars. Current `max_length=128` technically fits, but increase to `256` for safety margin with any work-factor tuning.

Migration 0215 is a simple `AlterField`. No data migration needed.

### Task 2: Rate Limiting — Pattern Reference

Exact pattern from `baserow/api/two_factor_auth/views.py:212–223`:
```python
from baserow.core.utils import get_user_remote_ip_address_from_request
from baserow.throttling.exceptions import RateLimitExceededException
from baserow.throttling.handler import rate_limit
from baserow.throttling.types import RateLimit

# Inside post():
ip = get_user_remote_ip_address_from_request(request)
def _check():
    # all existing password check logic here
    ...
rate_limit(
    rate=RateLimit.from_string("5/m"),
    key=f"public_view_auth:{ip}:{slug}",
    raise_exception=True,
)(_check)()
```

Add to `@map_exceptions`:
```python
RateLimitExceededException: ERROR_PUBLIC_VIEW_AUTH_RATE_LIMIT,
```

Add `ERROR_PUBLIC_VIEW_AUTH_RATE_LIMIT` to `api/views/errors.py`:
```python
from rest_framework.status import HTTP_429_TOO_MANY_REQUESTS
ERROR_PUBLIC_VIEW_AUTH_RATE_LIMIT = (
    "ERROR_PUBLIC_VIEW_AUTH_RATE_LIMIT",
    HTTP_429_TOO_MANY_REQUESTS,
    "Too many password attempts. Please try again later.",
)
```

OpenAPI schema, add to the endpoint's `responses`:
```python
429: get_error_schema(["ERROR_PUBLIC_VIEW_AUTH_RATE_LIMIT"]),
```

### Task 3: Uniform Error — Exact Change

> **⚠️ Existing test breakage:** There are existing tests in `test_view_views.py` for `PublicViewAuthView` that assert a non-existent slug returns **HTTP 404** (`ERROR_VIEW_DOES_NOT_EXIST`). After this change, those tests will fail because the endpoint now returns **HTTP 401** for non-existent slugs. Find and update all such tests to assert 401 instead of 404.

Current `PublicViewAuthView.post`:
```python
@map_exceptions({ViewDoesNotExist: ERROR_VIEW_DOES_NOT_EXIST})
def post(self, request, slug, data):
    view = handler.get_public_view_by_slug(request.user, slug, raise_authorization_error=False)
    if not view.check_public_view_password(data["password"]):
        raise AuthenticationFailed()
    ...
```

After change (remove `ViewDoesNotExist` from `@map_exceptions` for this method, catch it inline):
```python
@map_exceptions({RateLimitExceededException: ERROR_PUBLIC_VIEW_AUTH_RATE_LIMIT})
def post(self, request, slug, data):
    ip = get_user_remote_ip_address_from_request(request)
    
    def _check():
        try:
            view = handler.get_public_view_by_slug(request.user, slug, raise_authorization_error=False)
        except ViewDoesNotExist:
            raise AuthenticationFailed()
        if not view.check_public_view_password(data["password"]):
            raise AuthenticationFailed()
        return view
    
    view = rate_limit(
        rate=RateLimit.from_string("5/m"),
        key=f"public_view_auth:{ip}:{slug}",
        raise_exception=True,
    )(_check)()
    
    access_token = handler.encode_public_view_token(view)
    serializer = PublicViewAuthResponseSerializer({"access_token": access_token})
    return Response(serializer.data)
```

**Rationale:** Rate limiting wraps the entire lookup+check, so failed lookups also consume rate-limit budget. This prevents timing-based slug enumeration by consuming the same rate limit tokens regardless of whether the slug exists.

Also update the OpenAPI `responses` block to **remove** the `404` entry and add `401` and `429`.

### Task 4: Share Principal — Exact Change

File: `backend/src/baserow/core/field_permissions/permission_manager.py`

In `FieldPermissionManagerType._hidden_field_ids` (the private method), the early-return for anonymous actors is currently:
```python
actor_id = getattr(actor, "id", None)
if workspace is None or actor_id is None:
    return set()  # ← Change this
```

Change to:
```python
actor_id = getattr(actor, "id", None)
if workspace is None:
    return set()
if actor_id is None:
    # Share principal: deny-by-default. Any field carrying a readable_by_role restriction
    # is hidden from anonymous/public access (architecture D12, FR-17/33).
    from baserow.contrib.database.fields.models import FieldPermission
    restricted_rows = (
        FieldPermission.objects.filter(field__table__database__workspace=workspace)
        .exclude(readable_by_role__isnull=True)
        .values_list("field_id", flat=True)
    )
    return set(restricted_rows)
```

**Why this works:** `rows` in the existing method only contains fields with a non-null `readable_by_role`. For an anonymous principal (no role), any restriction threshold is too high. The query is already filtered to `workspace`, so it only hides fields in the workspace being accessed. This mirrors the existing deny-by-default architecture.

**What it does NOT change:** authenticated users with any role still go through the existing `role is None → continue` (defer) path — their behavior is unchanged.

**Existing plumbing (verified working):**
- `get_redacted_field_ids_for_user(request.user, table, view)` is called in `api/views/grid/views.py:252` and `api/views/gallery/views.py:223` for both authenticated and public row read endpoints
- `FieldPermissionHandler.get_hidden_field_ids(user, table)` is called from `get_redacted_field_ids_for_user` at `api/views/utils.py:95`
- `FieldPermissionManagerType.filter_queryset(actor, READ_FIELD_OPERATION, queryset, workspace)` calls `_hidden_field_ids`
- For anonymous public view access, `request.user` is Django's `AnonymousUser` — the chain is already wired

### Task 5: Frontend

`publicViewLogin.vue` already handles `401` correctly (lines ~107–113). Add `else if (statusCode === 429)` immediately after:
```javascript
} else if (statusCode === 429) {
  showError(
    $i18n.t('publicViewAuthLogin.error.rateLimitTitle'),
    $i18n.t('publicViewAuthLogin.error.rateLimitText')
  )
```

`en.json` keys (add under `publicViewAuthLogin`):
```json
"error": {
  "incorrectPasswordTitle": "...",  // already exists
  "incorrectPasswordText": "...",   // already exists
  "rateLimitTitle": "Too many attempts",
  "rateLimitText": "Too many password attempts have been made. Please wait a minute before trying again."
}
```

### Tests

**Backend API (test_view_views.py) — new test cases:**
- `test_public_view_auth_argon2_hash_stored` — set password, verify DB value starts with `argon2$argon2id`
- `test_public_view_auth_rate_limit_returns_429` — make 6 requests in 1 second; assert 5th is 200 (or 401), 6th is 429
- `test_public_view_auth_nonexistent_slug_returns_401` — POST to `/database/views/does-not-exist/public/auth/` with any password → assert 401 (not 404)
- `test_public_view_auth_share_principal_hides_restricted_fields` — set `readable_by_role = "ADMIN"` on a field; access public view rows anonymously; assert field absent from response

**Backend handler (test_view_handler.py) — new test cases:**
- `test_hidden_field_ids_anonymous_hides_restricted` — call `FieldPermissionManagerType._hidden_field_ids(AnonymousUser(), workspace)` with a table having a restricted field; assert field_id in result
- `test_hidden_field_ids_anonymous_no_restriction_returns_empty` — no FieldPermission rows → returns `set()`

**Frontend (publicViewLogin spec):**
- `test_publicViewLogin_shows_rate_limit_error_on_429` — mock API returning 429; assert rate-limit error message visible

### Test Environment

Same as previous stories:
```
TEST_ENV_FILE=.env.testing-oss BASEROW_OSS_ONLY=true
```
(NOT `.env.testing-cleanroom` — that's only for Bucket A clean-room tests)

### Migration Numbering

Last migration: `0214_view_locked.py` (Story 1.7)
Story 1.8 migration: `0215_view_password_max_length.py`

### Key File Map

| Action | File | Notes |
|--------|------|-------|
| MODIFY — add dep | `backend/pyproject.toml` | Add `"argon2-cffi>=23.1.0"` in `dependencies` list |
| MODIFY — add hasher | `backend/src/baserow/config/settings/base.py` | Add `PASSWORD_HASHERS` list with Argon2PasswordHasher first |
| NEW migration | `backend/src/baserow/contrib/database/migrations/0215_view_password_max_length.py` | AlterField max_length 128→256 |
| MODIFY — max_length | `backend/src/baserow/contrib/database/views/models.py` | `public_view_password` max_length 128→256 (L111) |
| MODIFY — add error | `backend/src/baserow/contrib/database/api/views/errors.py` | `ERROR_PUBLIC_VIEW_AUTH_RATE_LIMIT` (HTTP 429) |
| MODIFY — rate-limit + uniform error | `backend/src/baserow/contrib/database/api/views/views.py` | `PublicViewAuthView.post` — rate_limit wrapper, catch ViewDoesNotExist→AuthenticationFailed |
| MODIFY — share principal | `backend/src/baserow/core/field_permissions/permission_manager.py` | `_hidden_field_ids`: when `actor_id is None`, return all restricted field IDs |
| MODIFY — 429 handling | `web-frontend/modules/database/pages/publicViewLogin.vue` | Add 429 branch in catch block |
| MODIFY — i18n | `web-frontend/modules/database/locales/en.json` | Add `publicViewAuthLogin.error.rateLimitTitle/Text` |
| UPDATE | `backend/tests/baserow/contrib/database/api/views/test_view_views.py` | 4 new tests |
| UPDATE | `backend/tests/baserow/contrib/database/view/test_view_handler.py` | 2 new tests |
| NEW | `web-frontend/test/unit/database/publicViewLoginRateLimit.spec.js` | Frontend 429 test |

### Previous Story Learnings (Story 1.7 — Locked Views)

- **`create_user_workspace` defaults to `permissions="ADMIN"`** — always pass `permissions="MEMBER"` explicitly for non-admin test users (critical: caused 3 test failures in 1.7)
- **`except PermissionException` not `except PermissionDenied`** — base class for all permission errors in Baserow is `PermissionException` (`baserow.core.exceptions`). Catching the narrower `PermissionDenied` misses variants like `UserInvalidWorkspacePermissionsError`
- **OperationType registration in `apps.py`** — any new `OperationType` must be registered in `DatabaseConfig.ready()` in `backend/src/baserow/contrib/database/apps.py`, else `OperationTypeDoesNotExist` is raised at runtime
- **Test env**: `TEST_ENV_FILE=.env.testing-oss BASEROW_OSS_ONLY=true` — use this, not the cleanroom test env
- **`allowed_fields` in `update_view()`** — adding a field name to this list (handler.py) plus the UpdateViewSerializer is the correct pattern for making a new boolean/char field writable via PATCH
- **`core/permission_manager.py` string literals** — keep new ADMIN_ONLY_OPERATIONS entries as string literals, not OperationType class imports (existing codebase convention)

### Project Structure Notes

- Backend tests mirror src: `backend/src/baserow/contrib/database/views/` → `backend/tests/baserow/contrib/database/view/` (note singular `view` in tests, plural `views` in src)
- Field permission manager lives in `backend/src/baserow/core/field_permissions/` (not in `database` app) — changes there affect all workspaces globally
- Migration order: `0214` → `0215` — do not skip

### References

- Architecture D12 (password KDF + share principal): `_bmad-output/planning-artifacts/architecture.md` line ~128
- Architecture D14 (personal/locked view model): `_bmad-output/planning-artifacts/architecture.md` line ~121
- Epics FR-17, FR-33: `_bmad-output/planning-artifacts/epics.md` lines 48, 71
- `View.public_view_password` field: `backend/src/baserow/contrib/database/views/models.py:111`
- `View.check_public_view_password`: `backend/src/baserow/contrib/database/views/models.py:213`
- `View.set_password`: `backend/src/baserow/contrib/database/views/models.py:204`
- `PublicViewAuthView.post`: `backend/src/baserow/contrib/database/api/views/views.py:2125`
- `get_public_view_by_slug`: `backend/src/baserow/contrib/database/views/handler.py:3590`
- `FieldPermissionManagerType._hidden_field_ids`: `backend/src/baserow/core/field_permissions/permission_manager.py` (search `_hidden_field_ids`)
- `get_redacted_field_ids_for_user`: `backend/src/baserow/contrib/database/api/views/utils.py:68`
- Rate-limit pattern example: `backend/src/baserow/api/two_factor_auth/views.py:212`
- `get_user_remote_ip_address_from_request`: `backend/src/baserow/core/utils.py:78`
- `publicViewLogin.vue` — 401 error handling: `web-frontend/modules/database/pages/publicViewLogin.vue:107`
- Previous story (1.7): `_bmad-output/implementation-artifacts/1-7-locked-views.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

None — all implementation was pre-applied by the story creation session; this session verified, tested, and closed out the story.

### Completion Notes List

- All Tasks 1a–1d (Argon2id): pre-implemented by story-create session. argon2-cffi already in pyproject.toml, PASSWORD_HASHERS set in base.py, migration 0215 created, models.py max_length=256.
- Tasks 2a–2c (Rate limiting): pre-implemented. ERROR_PUBLIC_VIEW_AUTH_RATE_LIMIT added to errors.py, rate_limit wrapper in PublicViewAuthView.post, map_exceptions updated, OpenAPI 429 added.
- Task 3a (Uniform error): pre-implemented. ViewDoesNotExist caught inline → AuthenticationFailed; 404 removed from OpenAPI schema.
- Task 4a (Share principal): pre-implemented. _hidden_field_ids splits workspace/actor_id checks; actor_id=None path returns all restricted field IDs.
- Task 4b (Wiring verified): get_redacted_field_ids_for_user at api/views/utils.py:95 already passes request.user (AnonymousUser) to FieldPermissionHandler.get_hidden_field_ids. No code change needed.
- Tasks 5a–5b (Frontend 429): pre-implemented. publicViewLogin.vue has 429 branch; en.json has rateLimitTitle/Text keys.
- Task 6a–6c (Tests): pre-implemented. 4 backend API tests, 2 handler tests, 4 frontend tests — all passing.
- Pre-existing test failure (test_patch_default_values_with_interesting_table + test_default_values_stored_in_request_format): unrelated to Story 1.8; fails on baseline commit too (missing field type in interesting kwargs dict).

### File List

- `backend/pyproject.toml` — argon2-cffi>=23.1.0 added
- `backend/src/baserow/config/settings/base.py` — PASSWORD_HASHERS with Argon2PasswordHasher first
- `backend/src/baserow/contrib/database/migrations/0215_view_password_max_length.py` — NEW: AlterField max_length 128→256
- `backend/src/baserow/contrib/database/views/models.py` — public_view_password max_length=256
- `backend/src/baserow/contrib/database/api/views/errors.py` — ERROR_PUBLIC_VIEW_AUTH_RATE_LIMIT (HTTP 429), HTTP_429_TOO_MANY_REQUESTS import
- `backend/src/baserow/contrib/database/api/views/views.py` — PublicViewAuthView.post: rate_limit wrapper, ViewDoesNotExist→AuthenticationFailed, new imports
- `backend/src/baserow/core/field_permissions/permission_manager.py` — _hidden_field_ids: actor_id=None returns all restricted field IDs
- `web-frontend/modules/database/pages/publicViewLogin.vue` — 429 error branch in authorizeView catch
- `web-frontend/modules/database/locales/en.json` — rateLimitTitle/rateLimitText i18n keys
- `backend/uv.lock` — lockfile updated (argon2-cffi dependency resolution)
- `backend/tests/baserow/contrib/database/api/views/test_view_views.py` — 7 new Story 1.8 tests (argon2 hash, nonexistent slug 401, rate limit 429, share principal field hiding, password removal, uniform error body, per-slug isolation)
- `backend/tests/baserow/contrib/database/view/test_view_handler.py` — 2 new _hidden_field_ids AnonymousUser tests
- `web-frontend/test/unit/database/publicViewLoginRateLimit.spec.js` — NEW: 4 frontend 429 branch tests
- `_bmad-output/implementation-artifacts/tests/story-1-8-test-summary.md` — NEW: test coverage summary (13 tests across 3 layers)

## Senior Developer Review (AI)

**Date:** 2026-06-07
**Outcome:** Approve

### Summary

All 4 ACs implemented and verified against code. No CRITICAL or HIGH issues found.

### Findings

| Severity | Finding | Status |
|----------|---------|--------|
| Medium | `backend/uv.lock` changed but absent from story File List | Fixed (added to File List) |
| Medium | File List claimed "4 new Story 1.8 tests" — actual count is 7 | Fixed (updated to 7 with descriptions) |
| Low | Frontend test is logic-extraction, not Vue component mount — future refactors may not be caught | Noted (acceptable for this story) |
| Low | Rate limit test: `cache.clear()` at end not in `finally` block — cache not cleaned on assertion failure | Noted (low risk: slugs are random) |
| Low | Rate limit cache key prefix `_check:` is opaque for production debugging | Noted |

### Action Items

No action items. All MEDIUM findings were doc-only and fixed inline.

---

### Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-06-06 | Story Context Engine | Story file created |
| 2026-06-06 | claude-sonnet-4-6 | Verified all implementation pre-applied; all tests pass; story closed as review |
| 2026-06-07 | claude-sonnet-4-6 (review) | Code review: Approved. Fixed File List (uv.lock + test count). Status → done |

---

### Review 2 Findings (2026-06-07, independent re-review)

| Severity | Finding | Status |
|----------|---------|--------|
| Medium | `HTTP_429_TOO_MANY_REQUESTS` added to top-level imports but test assertions used literal `429` — dead import (ruff F401) | Fixed: replaced literals with constant |
| Medium | `ViewHandler` imported inside `test_public_view_auth_share_principal_hides_restricted_fields` but never used (ruff F401) | Fixed: removed |
| Low | `HTTP_403_FORBIDDEN` unused in top-level imports (left by Story 1.7), ruff F401 + I001 import sort | Fixed: removed via ruff --fix |

**Outcome:** Approve. No CRITICAL/HIGH issues. 3 lint fixes applied to `test_view_views.py`. Status remains: **done**.

_Reviewer: claude-sonnet-4-6 (review-2) on 2026-06-07_
