# Test Automation Summary — Story 3.6 (Timeline View)

Workflow: `bmad-qa-generate-e2e-tests` · OSS-only lane (`.env.oss-test`) · 2026-06-10

## Generated / Verified Tests

### Backend API tests — `tests/.../api/views/timeline/test_timeline_view_views.py` (9)
- [x] list rows (404 missing / 400 not-in-group / 200 ordered)
- [x] list applies sorts + filters (AC #1)
- [x] list includes field_options
- [x] PATCH start/end date fields persist (AC #1)
- [x] PATCH timescale persists (AC #3)
- [x] PATCH rejects invalid timescale (AC #3)
- [x] PATCH rejects non-date field → `ERROR_INCOMPATIBLE_FIELD`
- [x] PATCH field_options `hidden` persists (AC #5)
- [x] PATCH field_options `order` persists (AC #5)

### Backend view-type tests — `tests/.../view/test_timeline_view_type.py` (13)
- [x] registration, create, set start/end fields, timescale round-trip
- [x] reject non-date start / non-date end / cross-table field
- [x] start/end nulled on soft-delete + on incompatible type change
- [x] get_hidden_fields keeps date fields visible (AC #5)
- [x] export/import round-trip; first-three-fields visible

### Frontend unit tests — `web-frontend/test/.../timeline/timelineView.spec.js` (41)
- [x] pure bar geometry: `timelineUnit`/`parseTimelineValue`/`partitionTimelineRows`/`computeAxisRange`/`computeTicks`/`barGeometry` (AC #2/#3/#4)
- [x] scheduled-vs-tray partition by BOTH start+end (AC #2/#4)
- [x] header dispatch: start/end/timescale via `view/update`; field-option guards (AC #1/#3/#5)

### E2E spec — `e2e-tests/tests/database/timeline_view.spec.ts` (author-only, OSS-only CI lane)
- [x] bars for both-dated rows, rest to tray, config persists on reload (AC #1/#2/#4)
- [x] zoom day↔month switch + persist across reload (AC #3)
- [x] longer span renders a wider bar (AC #2)
- [x] view filters applied to timeline rows (AC #1)
- [x] **GAP APPLIED → AC #5**: card-face field visibility honored (hidden `Name`/`Start` absent from bar card) while a hidden **start-date** field still drives the bar (data-dependency guard keeps the date value serialized → bar still renders)

## Coverage vs Acceptance Criteria
| AC | API | view-type | unit | E2E |
|----|-----|-----------|------|-----|
| #1 persistence/filters/sorts | ✅ | ✅ | ✅ | ✅ |
| #2 bar per dated row | — | — | ✅ | ✅ |
| #3 zoom persists | ✅ | ✅ | ✅ | ✅ |
| #4 missing→tray | — | — | ✅ | ✅ |
| #5 field perms + date-field guard | ✅ | ✅ | ✅ | ✅ (gap applied) |

## Gap Discovered & Applied
- **AC #5 had no E2E coverage.** Added a scenario hiding a non-date card field (visibility honored → absent from bar) and the start-date card field (bar still renders → `get_hidden_fields` data-dependency guard exercised end-to-end). All other ACs were already E2E-covered; backend/unit coverage was already complete.

## Verification
- Frontend: `yarn vitest run .../timeline/timelineView.spec.js` → **41 passed**.
- Backend (OSS-only): `TEST_ENV_FILE=.env.oss-test PYTHONPATH=src:../premium/backend/src:../enterprise/backend/src DATABASE_URL=postgres://baserow:baserow@localhost:5431/baserow-test-db uv run pytest test_timeline_view_type.py test_timeline_view_views.py` → **22 passed**.
- E2E: author-only (Docker/OSS-only CI lane); prettier-clean. Not run locally per story Task 8.

## Next Steps
- Run the E2E spec in the OSS-only CI lane.
- Story 3.7 (drag/resize) will add drag-path E2E on the same bar DOM seams.
