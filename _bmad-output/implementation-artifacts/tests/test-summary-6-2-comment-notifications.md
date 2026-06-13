# Test Automation Summary — Story 6.2: Comment Notifications

## Generated Tests

### Backend Unit Tests (pytest)
- [x] `backend/tests/baserow/contrib/database/row_comments/test_row_comment_handler.py`
  - 10 Story 6.2 tests: subscribe, unsubscribe, is_subscribed, auto-subscribe on comment, auto-subscribe on @mention, notify_subscribers excludes sender, access-denied recipients skipped, no-duplicate notification when @mentioned
- [x] `backend/tests/baserow/contrib/database/row_comments/test_row_comment_api.py`
  - 7 Story 6.2 tests: GET status (not subscribed), POST subscribe 200, round-trip, idempotent POST, DELETE 204, DELETE no-op, unauthenticated 401

### Frontend Unit Tests (Vitest)
- [x] `web-frontend/test/unit/database/components/row/RowCommentsPanel.spec.js` — 10 tests (5 Story 6.2): fetchSubscriptionStatus on mount, subscribe/unsubscribe button visibility, button click dispatches correct action — **10/10 PASS**
- [x] `web-frontend/test/unit/database/notificationTypes.spec.js` — 6 tests: RowCommentMentionNotificationType and RowCommentCreatedNotificationType type strings and component getters — **6/6 PASS**

### E2E Tests (Playwright API-level, Docker e2e stack)
- [x] `e2e-tests/tests/database/row_comments.spec.ts` — 11 total tests (4 Story 6.2)
  - POST comment auto-subscribes the commenter (AC3)
  - Manual subscribe/unsubscribe cycle works correctly (AC5, AC6)
  - **[NEW]** AC4: @mentioned user is auto-subscribed to the comment thread
  - **[NEW]** AC1: subscribed user receives row_comment_created notification when another user comments (also asserts sender exclusion)

## Gaps Applied

| Gap | AC | Fix |
|-----|-----|-----|
| E2E: @mention auto-subscribe | AC4 | Added multi-user test with invitation flow |
| E2E: subscriber receives row_comment_created | AC1 | Added multi-user test checking `/notifications/{workspace_id}/` |
| E2E: wrong arg order in createDatabase/createTable | All | Fixed all 9 occurrences — swapped to correct `(user, "name", parent)` order |

## Coverage

| Layer | Tests | ACs Covered |
|-------|-------|-------------|
| Backend handler | 10 | AC1, AC2, AC3, AC4, AC9 |
| Backend API | 7 | AC5, AC6 |
| Frontend unit | 16 | AC5, AC6, AC7 |
| E2E | 11 | AC1, AC3, AC4, AC5, AC6 |

AC2 (access guard skips permission-denied recipients) and AC9 (cascade delete) covered in backend handler tests. AC7 (notification click routing) and AC8 (email deferred) are frontend/infra concerns validated via unit tests and code review.

## Next Steps
- Run E2E tests against Docker stack: `cd e2e-tests && yarn playwright test tests/database/row_comments.spec.ts`
- Run backend tests against Docker stack (pre-existing `database_rowcomment` table conflict prevents local run)
