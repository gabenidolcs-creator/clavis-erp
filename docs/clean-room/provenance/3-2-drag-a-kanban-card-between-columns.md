# Provenance record — Story 3.2 Drag a Kanban card between columns

- **PR / branch:** feat(story-3.2) drag a kanban card between columns (branch: develop)
- **Story:** 3.2 Drag a Kanban card between columns
- **Bucket:** A (clean-room reimplement)
- **Implementer:** AI dev-agent (walled-off writer population, isolation model (a))
- **Date:** 2026-06-09

## Sources Consulted

| # | Source | Type | Link / location |
|---|--------|------|-----------------|
| 1 | Public Airtable/Baserow "Kanban" UX — dragging a card from one column to another reassigns the card's grouping single-select value | public SaaS UI / public docs | https://baserow.io/docs , https://airtable.com |
| 2 | The Story 3.1 free-core Kanban view this story extends (`KanbanView.vue`, `groupRowsBySingleSelect`, the `updateValue` drop method, `store/view/kanban.js` `populateRow` with the `dragging` flag) | this repo (core, MIT free-core, authored in 3.1) | `web-frontend/modules/database/components/view/kanban/KanbanView.vue`, `web-frontend/modules/database/store/view/kanban.js` |
| 3 | `bufferedRows` Vuex helper — `updateRowValue` / `updatePreparedRowValues` optimistic commit + `RowService.batchUpdate` + rollback-on-failure path reused unchanged | MIT free-core | `web-frontend/modules/database/store/view/bufferedRows.js` |
| 4 | `SingleSelectFieldType.prepareValueForUpdate` — option object → option id conversion for the request | MIT free-core | `web-frontend/modules/database/fieldTypes.js` |
| 5 | `canWriteFieldValues` / `isReadOnlyField` field-writable predicate reused for the drag-enabled guard (AC #4), the same check the grid/row-editing path uses | MIT free-core | `web-frontend/modules/database/fieldTypes.js`, `components/view/grid/GridViewRow.vue` |
| 6 | Inbound realtime re-bucket path (`realtime.js` `rows_updated` → `KanbanViewType.rowUpdated` inherited from `BaseBufferedRowViewTypeMixin`) — verified only, not modified | MIT free-core | `web-frontend/modules/database/realtime.js`, `viewTypes.js` |
| 7 | `GalleryView` decoration unit test + gallery mock-server fixtures — reference shape for the Kanban mount test harness and mock-server helpers | MIT free-core | `web-frontend/test/unit/database/components/view/gallery/galleryViewDecoration.spec.js`, `web-frontend/test/fixtures/gallery.js` |
| 8 | Native HTML5 Drag-and-Drop API (`draggable`, `dragstart`, `dragend`, `dragover.preventDefault`, `drop`, `DataTransfer`) | general public knowledge / MDN | https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API |
| 9 | Playwright manual mouse-sequence drag (`mouse.move`/`down`/`up`) for native DnD in E2E | general public knowledge | https://playwright.dev |

## Implementer Attestation

- [x] I affirm that this Bucket A reimplementation was produced **clean-room**: I did
      **not** read, copy, adapt, or rely on memory of any `premium/` or `enterprise/`
      (PE/EE) source for this feature, and I was not *influenced by* it. Every source I
      used is listed above and is on the allowed-source list.

**Implementer signature / handle:** AI dev-agent (isolation model (a))   **Date:** 2026-06-09

## Reviewer confirmation (filled at review)

- [ ] Reviewer verified implementer eligibility per implementer-isolation.md.
- [ ] Reviewer verified all sources above are on the allowed-source list.

## Notes

- **Pure frontend, zero backend.** Story 3.2 moves a card by changing one
  single-select cell value through the **existing** `view/kanban/updateRowValue`
  action (→ `bufferedRows.updatePreparedRowValues` → `RowService.batchUpdate`).
  That shared handler path already provides the permission check, the WebSocket
  `rows_updated` broadcast, the Redis cache invalidation, and optimistic +
  rollback. No new endpoint, serializer, view, handler, signal, or migration was
  added. No backend file was touched.
- **No premium/enterprise contamination.** Premium ships its own Kanban view with
  its own drag implementation; it was **not** opened, read, grepped, or recalled
  at any point. The drag-and-drop behaviour was derived from the public HTML5 DnD
  API and the free-core Story 3.1 Kanban component only. The free core Kanban
  (and this drag feature) is the registered `kanban` view type only in OSS-only
  builds (`BASEROW_OSS_ONLY=true`); in a full open-core build premium's Kanban
  registers later and overrides it (last-registration-wins).
- **Card movement is store-driven.** The card visually moves because `columns` is
  a computed derived from the store rows via `groupRowsBySingleSelect`; the
  optimistic value change auto re-buckets the card and rollback auto-returns it.
  No per-column array is spliced manually, preserving rollback + realtime.
- **Clean-room test execution.** Frontend unit tests run in the OSS context
  (i18n mocked as in 3.1). The E2E drag scenario in
  `e2e-tests/tests/database/kanban_view.spec.ts` is authored to run in the
  OSS-only CI lane and is not run locally (requires the Docker stack).
