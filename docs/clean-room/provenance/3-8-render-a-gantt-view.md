# Provenance record — Story 3.8 Render a Gantt View

- **PR / branch:** feat(story-3.8) render a gantt view (branch: develop)
- **Story:** 3.8 Render a Gantt View
- **Bucket:** B (free-core derivation + vendored MIT third-party renderer)
- **Implementer:** AI dev-agent
- **Date:** 2026-06-10

## Sources Consulted

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | The Story 3.6 free-core Timeline view — the proven net-new free-core `ViewType` spine this story derives from (backend `TimelineViewType` + `TimelineView` model + `TimelineViewFieldOptions` + migration + `api/views/timeline/*`; frontend `TimelineViewType` in `viewTypes.js` + `TimelineView.vue` + `TimelineViewHeader.vue` + `store/view/timeline.js` + `services/view/timeline.js` + `plugin.js`). Gantt swaps Timeline's plain-DOM `{left,width}` bar geometry for a vendored SVG Gantt renderer, and — unlike Timeline's OSS-only override — registers unconditionally under standard names (`database_ganttview`, type `"gantt"`) because Baserow ships no premium Gantt twin. | this repo (core, MIT free-core, authored in 3.6) | `backend/src/baserow/contrib/database/views/view_types.py` (TimelineViewType), `backend/src/baserow/contrib/database/views/models.py` (TimelineView, TimelineViewFieldOptions), `backend/src/baserow/contrib/database/api/views/timeline/*`, `web-frontend/modules/database/components/view/timeline/*`, `web-frontend/modules/database/store/view/timeline.js`, `web-frontend/modules/database/services/view/timeline.js` |
| 2 | Frappe Gantt 1.2.2 — MIT-licensed standalone SVG Gantt renderer, lazy-loaded via a cached-promise dynamic `import()` (mirrors the `excel.js` lazy-load pattern) so it stays out of the initial bundle. Drives bar rendering, the day/week/month `view_mode`, and click-to-open via the `popup` hook. | third-party MIT dependency | https://github.com/frappe/gantt (v1.2.2, MIT); `web-frontend/package.json` |
| 3 | Core MIT shared view helpers reused unchanged — `partitionTimelineRows` and `rowDateRange` (scheduled-vs-tray partition: a row is a bar only when both start + end date fields carry a value), plus `RowCard.vue`, `ViewFieldsContext.vue`, `bufferedRows`/`fieldOptions` store factories for the unscheduled tray, card face, and row listing. | MIT free-core | `web-frontend/modules/database/components/view/timeline/TimelineView.vue` (partitionTimelineRows, rowDateRange), `web-frontend/modules/database/components/card/RowCard.vue`, `web-frontend/modules/database/components/view/ViewFieldsContext.vue`, `web-frontend/modules/database/store/view/bufferedRows.js` |
| 4 | Field-type capability `can_represent_date` (backend) / `canRepresentDate` (frontend) — registry capability used to validate the start / end date fields. | MIT free-core | `backend/src/baserow/contrib/database/fields/registries.py`, `web-frontend/modules/database/fieldTypes.js` |
| 5 | Two shared persistence paths reused unchanged: view config (`start_date_field`, `end_date_field`, `timescale`) via the generic `PATCH /api/database/views/{id}/`; card face (`hidden`/`order`) via `PATCH /api/database/views/{id}/field_options/`. | MIT free-core | `backend/src/baserow/contrib/database/api/views/views.py` |
| 6 | Free-core Timeline view-type + API tests — reference shape for the Gantt backend test suites. | MIT free-core | `backend/tests/baserow/contrib/database/view/test_timeline_view_type.py`, `backend/tests/baserow/contrib/database/api/views/timeline/*` |
| 7 | Playwright locator/assertion API for the authored E2E gantt scenario (Frappe Gantt DOM class names `.gantt`, `.bar-wrapper`, `button--active` zoom state). | general public knowledge | https://playwright.dev , Frappe Gantt 1.2.2 rendered markup |

## Implementer Attestation

- [x] This is a **Bucket B** derivation: it builds on the free-core 3.6 Timeline spine
      (MIT, this repo) and a vendored MIT third-party renderer (Frappe Gantt 1.2.2). I did
      **not** read, copy, adapt, or rely on memory of any `premium/` or `enterprise/`
      (PE/EE) source for this feature. Every source I used is listed above.

**Implementer signature / handle:** AI dev-agent   **Date:** 2026-06-10

## Reviewer confirmation (filled at review)

- [x] Reviewer verified all sources above are free-core MIT, this-repo, vendored MIT, or public.
- [x] Reviewer verified no `premium/` or `enterprise/` source was consulted.

## Notes

- **Free-core derivation, not a clean-room reimplement (Bucket B).** Baserow ships **no**
  premium or enterprise Gantt view, so there is no PE/EE twin to wall off and no
  last-registration-wins override to dodge. The Gantt view-type therefore registers
  **unconditionally** in `apps.py` under standard table names (`database_ganttview`,
  `database_ganttviewfieldoptions`) and the plain type string `"gantt"` — the two
  structural deltas from 3.6 Timeline, which used `core_`-prefixed names and an OSS-only
  guard precisely because premium *does* ship a Timeline.
- **Vendored MIT renderer, lazy-loaded.** Frappe Gantt 1.2.2 (MIT) replaces Timeline's
  pure-DOM `{left,width}` bar math with a standalone SVG Gantt. Both the JS and its CSS are
  pulled through a cached-promise dynamic `import()` (`loadGantt` / `loadGanttCss`),
  mirroring the existing `excel.js` lazy-load, so the initial bundle budget is unchanged
  (verified: no static Frappe Gantt import anywhere in the tree).
- **Render-only in 3.8; bars are read-only.** The Gantt is constructed with
  `readonly: true` and `popup_on: 'click'`; the `popup` hook is repurposed to open the
  standard row modal (`openTaskRow`) and returns `false` to suppress Frappe's own popup.
  No drag-to-reschedule / drag-to-resize write path is wired — that is Story 3.10.
- **Dependency-layer seam (AC #3).** `dependenciesForRow()` returns `''` unconditionally;
  Gantt dependency lines are the Story 3.9 seam and were deliberately not implemented.
- **Scheduled-vs-tray partition (AC #2).** Reuses core `partitionTimelineRows` /
  `rowDateRange` unchanged: a row is a Gantt task only when **both** its `start_date_field`
  and `end_date_field` carry a value; rows missing either land in the unscheduled tray.
- **Known third-party limitation documented (Story 3.10 follow-up).** Frappe Gantt 1.2.2
  registers an anonymous `document` `mouseup` listener at construction and exposes no
  `destroy()`, so `destroyGantt()` cannot remove it (the listener is render-only and
  harmless here). The `ensureGantt` async-loader race is guarded by an explicit
  `isUnmounting` flag set in `beforeUnmount`. Both are documented inline; Story 3.10 should
  pin a lib version with a teardown hook or patch it.
- **No premium/enterprise contamination.** Every source consulted is the free-core 3.6
  Timeline, the MIT shared card/field-options/partition helpers, the vendored MIT Frappe
  Gantt, or public docs. No `premium/` or `enterprise/` source was opened, grepped, or
  recalled.
- **Test execution.** Backend tests run in the **default** profile (no `.env.oss-test`,
  since there is no premium override): 22 passed (13 view-type + 9 API). Frontend unit
  tests run method/computed-level: 30 passed. The E2E scenario in
  `e2e-tests/tests/database/gantt_view.spec.ts` is authored for the CI lane and not run
  locally.
