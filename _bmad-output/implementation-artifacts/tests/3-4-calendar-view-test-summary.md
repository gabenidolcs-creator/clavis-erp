# Test Automation Summary — Story 3.4: Create and configure a Calendar View

**Workflow:** bmad-qa-generate-e2e-tests
**Date:** 2026-06-10
**Engineer:** QA automation (Tinsu)
**Baseline commit:** 51c419ddd7586fcfc7d930519c0867ed6526b0c3
**Build profile for all runs:** OSS-only (`BASEROW_OSS_ONLY=true`, `TEST_ENV_FILE=.env.oss-test`) — core Calendar must register as the `"calendar"` view type, else premium overrides it (last-registration-wins).

## Scope

QA test-generation pass over the already-implemented core Calendar view (Bucket A clean-room). Goal: verify existing API/unit coverage runs green and close the E2E gap. No production code touched. No `premium/`/`enterprise/` sources read.

## Coverage at entry (pre-existing tests)

| Layer | File | Tests | Status |
|---|---|---|---|
| Backend view type | `backend/tests/.../view/test_calendar_view_type.py` | 13 | ✅ pass |
| Backend API | `backend/tests/.../api/views/calendar/test_calendar_view_views.py` | 8 | ✅ pass |
| Frontend unit | `web-frontend/test/unit/database/components/view/calendar/calendarView.spec.js` | 34 | ✅ pass |

Backend covers AC #1 (config persist, filters/sorts/visibility), AC #2 (date partition), AC #4 (date validation/round-trip), AC #5 (`get_hidden_fields` data-dependency guard, soft-delete null). Frontend unit covers `rowDateKey` / `buildCalendarDays` (month+week) / `groupRowsByDate` (multi-day span, out-of-grid, null), field-resolution computeds, and header dispatch with readOnly/permission guards.

## Gap discovered & applied

**Gap:** No E2E spec existed (Task 8 unfulfilled). The `createCalendarView` fixture was already present in `e2e-tests/fixtures/database/view.ts`, but no spec consumed it.

**Applied — new file:** `e2e-tests/tests/database/calendar_view.spec.ts` (mirrors `kanban_view.spec.ts`; asserts core `.calendar-view__*` DOM; OSS-only CI lane; authored, NOT run locally per Task 8 — no Docker stack / no `e2e-tests` node_modules).

### E2E scenarios

| Scenario | ACs | Key assertions |
|---|---|---|
| Dated rows on grid, null rows in unscheduled tray, config persists on reload | #1, #2 | card on `.calendar-view__day-cards`; `.calendar-view__unscheduled-count` = 1; survives reload; clearing `date_field` → `.calendar-view__empty` |
| Month ↔ week toggle from header | #3 | `.calendar-view__grid--month` (>7 day cells) ↔ `.calendar-view__grid--week` (exactly 7) |
| Multi-day span with end-date field | #4 | one row, `Date=today`/`End=today+2` → 3 card instances across 3 day cells |
| View filter honored on calendar | #1 | primary `equal "keep"` filter → only 1 of 2 dated rows shown |

Determinism: rows seeded relative to today (`dayKey` helper) so they always fall inside the visible grid (`referenceDate` defaults to today).

## Verification run

- Frontend: `yarn vitest run web-frontend/test/unit/database/components/view/calendar/` → **34 passed**.
- Backend (OSS-only): `TEST_ENV_FILE=.env.oss-test DATABASE_URL=postgres://baserow:baserow@localhost:5431/baserow-test-db PYTHONPATH=src:../premium/backend/src:../enterprise/backend/src uv run pytest <calendar tests>` → **21 passed**.
- E2E: authored only; prettier-clean (`web-frontend/node_modules/.bin/prettier --check` → pass). Runs in OSS-only CI lane, not locally.

## Coverage metrics

- AC #1 (persist config, filters/sorts/visibility): backend ✅ + E2E ✅
- AC #2 (date cell vs unscheduled tray): frontend unit ✅ + E2E ✅
- AC #3 (month/week toggle): frontend unit ✅ + E2E ✅
- AC #4 (multi-day span): frontend unit ✅ + E2E ✅
- AC #5 (field permissions / data-dependency guard): backend ✅ (enforced server-side; no extra E2E needed)

All 5 ACs covered. Backend 21 + frontend 34 green locally; E2E 4 scenarios authored for CI.

## Risks / out of QA scope

- ⚠️ **Provenance missing:** `docs/clean-room/provenance/3-4-create-and-configure-a-calendar-view.md` (Task 9, MANDATORY merge gate) does not exist. This is a dev-story deliverable, not a QA test artifact — **flagging for the dev/review pass; the Bucket A PR cannot merge without it.**
- E2E cannot be executed locally (no Docker e2e stack / no `e2e-tests` node_modules); relies on the OSS-only CI lane. Same constraint as Kanban (3.1–3.3).

## Next steps

- Add the clean-room provenance record (Task 9) before opening the PR.
- Run `calendar_view.spec.ts` in the OSS-only e2e CI lane.
- Lint sweep (Task 10) on the full branch diff before PR.
