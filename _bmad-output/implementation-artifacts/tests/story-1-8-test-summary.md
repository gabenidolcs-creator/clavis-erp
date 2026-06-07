# Story 1.8 — Test Summary: Password-Protected Share Links

Generated: 2026-06-06

## Coverage

| Layer | File | Tests | Status |
|-------|------|-------|--------|
| Backend API | `test_view_views.py` | 7 | ✅ All pass |
| Backend handler | `test_view_handler.py` | 2 | ✅ All pass |
| Frontend unit | `publicViewLoginRateLimit.spec.js` | 4 | ✅ All pass |
| **Total** | | **13** | ✅ |

## Backend API Tests (`test_view_views.py`)

| Test | AC | Coverage |
|------|----|----------|
| `test_public_view_auth_argon2_hash_stored` | #2 | Stored hash starts with `argon2$argon2id` |
| `test_public_view_auth_nonexistent_slug_returns_401` | #3 | Non-existent slug returns 401 not 404 |
| `test_public_view_auth_rate_limit_returns_429` | #3 | 5 wrong attempts → 429 on 6th |
| `test_public_view_auth_share_principal_hides_restricted_fields` | #1 | AnonymousUser cannot see `readable_by_role`-restricted fields in public rows |
| `test_public_view_auth_password_removal_reverts_to_open` | #4 | Clearing password (`""`) reverts public view to open access |
| `test_public_view_auth_uniform_error_body` | #3 | Wrong password and non-existent slug return identical 401 JSON body |
| `test_public_view_auth_rate_limit_per_slug_isolation` | #3 | Rate limit counters are scoped per slug — exhausting one does not block another |

## Backend Handler Tests (`test_view_handler.py`)

| Test | Coverage |
|------|----------|
| `test_hidden_field_ids_anonymous_hides_restricted` | `_hidden_field_ids(AnonymousUser, workspace)` returns restricted field IDs |
| `test_hidden_field_ids_anonymous_no_restriction_returns_empty` | No FieldPermission rows → returns `set()` (no false positives) |

## Frontend Unit Tests (`publicViewLoginRateLimit.spec.js`)

| Test | Coverage |
|------|----------|
| `401 shows incorrect password error` | 401 branch in `authorizeView()` error handler |
| `429 shows rate-limit error title and text` | 429 branch shows `rateLimitTitle` / `rateLimitText` i18n keys |
| `other status codes show generic error` | Fallback branch for unexpected status codes |
| `429 does NOT show incorrect-password message` | Negative: 429 branch does not bleed into 401 message |

## Gaps Discovered and Applied

Three gaps were identified and filled with new tests:

1. **AC #4 uncovered** — Added `test_public_view_auth_password_removal_reverts_to_open`: verified that setting `public_view_password = ""` removes the protection and the public view becomes accessible without a JWT token.

2. **Uniform error body unverified** — Added `test_public_view_auth_uniform_error_body`: confirmed that both a wrong-password 401 and a non-existent slug 401 return identical JSON response bodies, closing the link-existence oracle.

3. **Rate limit per-slug isolation** — Added `test_public_view_auth_rate_limit_per_slug_isolation`: confirmed that the `public_view_auth:{ip}:{slug}` key scopes rate limiting per slug; exhausting slug_a does not block slug_b.
