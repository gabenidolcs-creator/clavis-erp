import { expect, test } from "../baserowTest";
import { TablePage } from "../../pages/database/tablePage";
import { createDatabase } from "../../fixtures/database/database";
import { createTable } from "../../fixtures/database/table";
import {
  createField,
  deleteAllNonPrimaryFieldsFromTable,
  getFieldsForTable,
} from "../../fixtures/database/field";
import { createRow } from "../../fixtures/database/rows";
import {
  createGanttView,
  createViewFilter,
  updateFieldOptions,
  updateView,
} from "../../fixtures/database/view";

// NOTE (Bucket B / clean-room): the Gantt view is a NET-NEW core view type with
// NO premium twin (`grep -rn gantt premium/ enterprise/` finds nothing relevant),
// so it registers UNCONDITIONALLY and is the only "gantt" view type in any build.
// Unlike the Timeline spec it does NOT require the OSS-only stack — it runs in the
// standard e2e lane. The bars/connectors are drawn by the lazy-loaded third-party
// Frappe Gantt 1.2.2 (MIT) SVG renderer, so this spec asserts the lib's emitted
// DOM (`.bar-wrapper` per scheduled task) inside the core host (`.gantt-view__*`).
// Per story 3.8 Task 8 this spec is AUTHORED but NOT run locally (it needs the
// Docker e2e stack; `e2e-tests/` has no local tsconfig/node_modules).

/**
 * Day key in the user's local day, formatted `YYYY-MM-DD`, offset by `days`.
 * Frappe Gantt centres its axis on the scheduled tasks, so seeding rows relative
 * to today keeps the bars deterministically inside the rendered viewport.
 */
function dayKey(offsetDays = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/**
 * Builds an Events table with a "Start" and "End" date field plus a Gantt view
 * already positioned by both. Returns everything the gantt spec needs to
 * navigate and seed.
 */
async function setupGantt(workspacePage: any, timescale: string | null = null) {
  const database = await createDatabase(
    workspacePage.user,
    "ganttViewTestDb",
    workspacePage.workspace,
  );
  const table = await createTable(workspacePage.user, "Events", database);
  await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);

  // The date fields that position the left/right edge of each Frappe Gantt bar.
  const startField = await createField(
    workspacePage.user,
    "Start",
    "date",
    {},
    table,
  );
  const endField = await createField(
    workspacePage.user,
    "End",
    "date",
    {},
    table,
  );

  const view = await createGanttView(
    workspacePage.user,
    "Gantt",
    startField.id,
    endField.id,
    table,
    timescale,
  );

  return { database, table, startField, endField, view };
}

test.describe("Gantt view", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("draws a Frappe Gantt bar only for rows with BOTH dates, sends the rest to the tray, and persists the config on reload (AC #1, #2)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, view } = await setupGantt(workspacePage);

    // A fully-scheduled row (both dates) becomes a Gantt bar; a row missing the
    // end date and a row missing both dates land in the unscheduled tray (AC #2),
    // never as malformed/zero-width bars.
    await createRow(workspacePage.user, table, {
      Start: dayKey(0),
      End: dayKey(2),
    });
    await createRow(workspacePage.user, table, {
      Start: dayKey(0),
      End: null,
    });
    await createRow(workspacePage.user, table, { Start: null, End: null });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // Both date fields are configured, so the Frappe Gantt host renders (no
    // empty state) and the lazy-loaded lib draws exactly one bar for the single
    // fully-dated row (`.bar-wrapper` is the per-task group the lib emits).
    await expect(page.locator(".gantt-view__empty")).toHaveCount(0);
    await expect(page.locator(".gantt-view__host .bar-wrapper")).toHaveCount(1);

    // The two rows missing a date sit in the unscheduled tray; the counter
    // reflects exactly two unscheduled rows (AC #2 tray rule).
    await expect(page.locator(".gantt-view__unscheduled")).toBeVisible();
    await expect(page.locator(".gantt-view__unscheduled-count")).toHaveText(
      "2",
    );

    // Reload — the date-field configuration persists server-side, so the same
    // partition (one bar, two tray cards) renders again (AC #1).
    await tablePage.goto();
    await expect(page.locator(".gantt-view__host .bar-wrapper")).toHaveCount(1);
    await expect(page.locator(".gantt-view__unscheduled-count")).toHaveText(
      "2",
    );

    // Clearing the start date field drops the view back to the empty state
    // prompting the user to map the positioning fields (AC #1 config round-trip);
    // with no positioning fields the Frappe Gantt host is not mounted.
    await updateView(workspacePage.user, view, { start_date_field: null });
    await tablePage.goto();
    await expect(page.locator(".gantt-view__empty")).toBeVisible();
    await expect(page.locator(".gantt-view__host")).toHaveCount(0);
  });

  test("switches the zoom level from the header and persists it on reload (AC #4)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    // Start at the default (month) zoom so the switch to "Day" is observable.
    const { database, table, view } = await setupGantt(workspacePage);

    // A row spanning a few days so the Gantt axis has meaningful content at any
    // zoom level.
    await createRow(workspacePage.user, table, {
      Start: dayKey(0),
      End: dayKey(3),
    });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // The bar renders at the default zoom.
    await expect(page.locator(".gantt-view__host .bar-wrapper")).toHaveCount(1);

    // The default month zoom is the active RadioGroup button.
    await expect(
      page.locator(".radio-group__radio-button.button--active", {
        hasText: "Month",
      }),
    ).toHaveCount(1);

    // Switch to the day zoom via the header RadioGroup button labelled "Day".
    await page
      .locator(".radio-group__radio-button", { hasText: "Day" })
      .click();

    // The Day button becomes the active zoom — the persisted `timescale` is
    // written through the generic view/update and maps to Frappe Gantt's
    // `view_mode='Day'`.
    await expect(
      page.locator(".radio-group__radio-button.button--active", {
        hasText: "Day",
      }),
    ).toHaveCount(1);

    // Reload — the persisted `timescale` column means the day zoom survives the
    // round-trip (AC #4): the Day button is still the active zoom.
    await tablePage.goto();
    await expect(
      page.locator(".radio-group__radio-button.button--active", {
        hasText: "Day",
      }),
    ).toHaveCount(1);
    await expect(page.locator(".gantt-view__host .bar-wrapper")).toHaveCount(1);

    // view is referenced to keep its id in scope for clarity.
    expect(view.id).toBeTruthy();
  });

  test("draws one bar per fully-dated row across multiple tasks (AC #2)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, view } = await setupGantt(workspacePage, "day");

    // Three fully-dated rows → three Frappe Gantt bars; the lib draws one
    // `.bar-wrapper` group per task fed to it.
    await createRow(workspacePage.user, table, {
      Start: dayKey(0),
      End: dayKey(1),
    });
    await createRow(workspacePage.user, table, {
      Start: dayKey(1),
      End: dayKey(4),
    });
    await createRow(workspacePage.user, table, {
      Start: dayKey(2),
      End: dayKey(2),
    });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    await expect(page.locator(".gantt-view__host .bar-wrapper")).toHaveCount(3);

    // No row is missing a date, so the unscheduled tray is absent.
    await expect(page.locator(".gantt-view__unscheduled")).toHaveCount(0);

    expect(view.id).toBeTruthy();
  });

  test("applies existing view filters to the rows drawn on the gantt (AC #1 honors filters)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, startField, view } =
      await setupGantt(workspacePage);

    // Two fully-scheduled rows; one is given a distinct primary value so a
    // filter can single it out. The gantt routes through the standard view row
    // pipeline, so the view filter applies to what it draws.
    await createRow(workspacePage.user, table, {
      Name: "keep",
      Start: dayKey(0),
      End: dayKey(1),
    });
    await createRow(workspacePage.user, table, {
      Name: "drop",
      Start: dayKey(0),
      End: dayKey(1),
    });

    // Filter the view to only rows whose primary "Name" equals "keep".
    const fields = await getFieldsForTable(workspacePage.user, table);
    const nameField = fields.find((f) => f.primary);
    await createViewFilter(
      workspacePage.user,
      view,
      nameField.id,
      "equal",
      "keep",
    );

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // Only the single "keep" row survives the filter — one bar on the axis, the
    // "drop" row is filtered out before it reaches the gantt renderer.
    await expect(page.locator(".gantt-view__host .bar-wrapper")).toHaveCount(1);

    // startField is referenced to keep its id in scope for clarity.
    expect(startField.id).toBeTruthy();
  });

  test("honors card-face field visibility on the tray yet keeps hidden date fields driving the bars (AC #5)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, startField, view } =
      await setupGantt(workspacePage);

    // Hide the primary "Name" card face AND the "Start" date field's card face.
    // Per the AC #5 data-dependency guard (get_hidden_fields keeps the date
    // fields serialized even when their option is hidden) the bar must still
    // render because the start date keeps driving the layout, while the tray
    // card respects the hidden card faces.
    const fields = await getFieldsForTable(workspacePage.user, table);
    const nameField = fields.find((f) => f.primary);
    await updateFieldOptions(workspacePage.user, view, {
      [nameField.id]: { hidden: true },
      [startField.id]: { hidden: true },
    });

    // A fully-dated row (drawn as a bar) and a tray row missing its end date so
    // there is a tray card to inspect for field visibility.
    await createRow(workspacePage.user, table, {
      Name: "scheduled",
      Start: dayKey(0),
      End: dayKey(2),
    });
    await createRow(workspacePage.user, table, {
      Name: "trayed",
      Start: dayKey(0),
      End: null,
    });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // The bar still renders even though the start-date card face is hidden — the
    // date value is still serialized to the client and positions the bar (AC #5
    // data-dependency guard).
    await expect(page.locator(".gantt-view__host .bar-wrapper")).toHaveCount(1);

    // The hidden "Name" and "Start" card faces are absent from the tray card,
    // while the still-visible "End" field remains.
    const trayCard = page.locator(".gantt-view__unscheduled .card__field-name");
    await expect(trayCard.filter({ hasText: "End" })).toHaveCount(1);
    await expect(trayCard.filter({ hasText: "Name" })).toHaveCount(0);
    await expect(trayCard.filter({ hasText: "Start" })).toHaveCount(0);
  });

  // Story 3.9 — Task Dependencies with cycle prevention. The Gantt instance is
  // `readonly: true` (Frappe Gantt exposes no draw handle when read-only), so
  // the v1 draw affordance is the explicit "Predecessors" picker that appears
  // for the open task row (`.gantt-view__dependencies`). Clicking a bar opens
  // that row (popup side-effect → row modal + picker), and the picker's
  // `.gantt-view__dependencies-add` Dropdown creates a `predecessor → open row`
  // edge. The lib then draws the connector as a `<path data-from data-to>` in
  // its `.arrow` SVG layer from the comma-separated predecessor string the live
  // 3.9 seam (`dependenciesForRow`) now returns. Per story 3.9 Task 10 these
  // are AUTHORED but NOT run locally (they need the Docker e2e stack).

  test("draws a dependency connector between two task bars via the predecessor picker and persists it on reload (AC #1)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, view } = await setupGantt(workspacePage, "day");

    // Three fully-dated rows → three bars, each addressable by the row id the
    // lib stamps on its `.bar-wrapper[data-id]` group.
    const rowA = await createRow(workspacePage.user, table, {
      Name: "Task A",
      Start: dayKey(0),
      End: dayKey(1),
    });
    const rowB = await createRow(workspacePage.user, table, {
      Name: "Task B",
      Start: dayKey(2),
      End: dayKey(3),
    });
    const rowC = await createRow(workspacePage.user, table, {
      Name: "Task C",
      Start: dayKey(4),
      End: dayKey(5),
    });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // All three bars render; no dependency arrows exist yet.
    await expect(page.locator(".gantt-view__host .bar-wrapper")).toHaveCount(3);
    await expect(page.locator(".gantt-view__host .arrow path")).toHaveCount(0);

    // Open task B by clicking its bar — the `popup_on: 'click'` side-effect
    // opens the row and reveals the predecessor picker for the open row.
    await page
      .locator(`.gantt-view__host .bar-wrapper[data-id="${rowB.id}"]`)
      .click();
    await expect(page.locator(".gantt-view__dependencies")).toBeVisible();

    // Draw A → B: select "Task A" as a predecessor of the open row B through the
    // picker Dropdown (open it, then pick the candidate by its primary name).
    await page
      .locator(".gantt-view__dependencies-add .dropdown__selected")
      .click();
    await page
      .locator(
        '.gantt-view__dependencies-add .select__item-name-text[title="Task A"]',
      )
      .click();

    // The connector arrow renders from A's bar to B's bar — the lib draws a
    // `<path data-from data-to>` in its `.arrow` layer from the predecessor
    // string the live seam now returns for B (AC #1 connector render).
    await expect(
      page.locator(
        `.gantt-view__host .arrow path[data-from="${rowA.id}"][data-to="${rowB.id}"]`,
      ),
    ).toHaveCount(1);

    // Reload — the edge is persisted server-side and re-fetched on init, so the
    // same connector renders again without re-opening the row (AC #1 reload).
    await tablePage.goto();
    await expect(
      page.locator(
        `.gantt-view__host .arrow path[data-from="${rowA.id}"][data-to="${rowB.id}"]`,
      ),
    ).toHaveCount(1);

    // rowC is referenced to keep its id in scope for clarity (third bar).
    expect(rowC.id).toBeTruthy();
  });

  test("rejects a dependency that would close a cycle with a clear error and adds no connector (AC #2)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, view } = await setupGantt(workspacePage, "day");

    const rowA = await createRow(workspacePage.user, table, {
      Name: "Task A",
      Start: dayKey(0),
      End: dayKey(1),
    });
    const rowB = await createRow(workspacePage.user, table, {
      Name: "Task B",
      Start: dayKey(2),
      End: dayKey(3),
    });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    await expect(page.locator(".gantt-view__host .bar-wrapper")).toHaveCount(2);

    // Precondition: draw A → B through the picker so the graph holds one edge.
    await page
      .locator(`.gantt-view__host .bar-wrapper[data-id="${rowB.id}"]`)
      .click();
    await expect(page.locator(".gantt-view__dependencies")).toBeVisible();
    await page
      .locator(".gantt-view__dependencies-add .dropdown__selected")
      .click();
    await page
      .locator(
        '.gantt-view__dependencies-add .select__item-name-text[title="Task A"]',
      )
      .click();
    await expect(
      page.locator(
        `.gantt-view__host .arrow path[data-from="${rowA.id}"][data-to="${rowB.id}"]`,
      ),
    ).toHaveCount(1);

    // Now open task A and attempt to add B as A's predecessor — that edge B → A
    // closes the cycle A → B → A and the backend must reject it.
    await page
      .locator(`.gantt-view__host .bar-wrapper[data-id="${rowA.id}"]`)
      .click();
    await expect(page.locator(".gantt-view__dependencies")).toBeVisible();
    await page
      .locator(".gantt-view__dependencies-add .dropdown__selected")
      .click();
    await page
      .locator(
        '.gantt-view__dependencies-add .select__item-name-text[title="Task B"]',
      )
      .click();

    // A clear cycle error toast surfaces (the create action maps
    // ERROR_TASK_DEPENDENCY_CYCLE to the `ganttView.cycleRejectedTitle` toast)
    // and the optimistic edge is rolled back (AC #2 clear error).
    await expect(
      page.locator(".toast__title", {
        hasText: "Dependency would create a cycle",
      }),
    ).toBeVisible();

    // No reverse connector was added — only the original A → B arrow remains.
    await expect(
      page.locator(
        `.gantt-view__host .arrow path[data-from="${rowB.id}"][data-to="${rowA.id}"]`,
      ),
    ).toHaveCount(0);
    await expect(page.locator(".gantt-view__host .arrow path")).toHaveCount(1);
  });

  // Story 3.10 — prompt-first reschedule on dependency. Dragging a predecessor
  // bar forward so it would push a dependent fires the lib's `on_date_change`,
  // which opens the confirm prompt (`ganttView.rescheduleTitle`). The author
  // either cascades the whole chain or moves the predecessor alone, leaving the
  // now-invalid FS connector styled `.gantt-view__arrow--violated`. Per story
  // 3.10 Task 9 these are AUTHORED but NOT run locally (Docker e2e stack only).

  /**
   * Drags a Frappe Gantt bar group horizontally by `dxDays` whole columns. The
   * lib snaps a drag to the column step, so moving by one `column_width` shifts
   * the bar exactly one unit at the active zoom; the drag releases over the
   * target so `on_date_change` fires once with the new dates.
   */
  async function dragBarByDays(page: any, rowId: number, dxDays: number) {
    const bar = page.locator(
      `.gantt-view__host .bar-wrapper[data-id="${rowId}"] .bar`,
    );
    const box = await bar.boundingBox();
    if (box === null) {
      throw new Error(`bar for row ${rowId} has no bounding box`);
    }
    // One Frappe Gantt column at the "day" zoom; the drag step is the column.
    const columnWidth = await page.evaluate(() => {
      const col = document.querySelector(".gantt-view__host .grid-row");
      return col ? col.getBoundingClientRect().height : 38;
    });
    const startX = box.x + box.width / 2;
    const startY = box.y + box.height / 2;
    await page.mouse.move(startX, startY);
    await page.mouse.down();
    await page.mouse.move(startX + columnWidth * dxDays, startY, { steps: 8 });
    await page.mouse.up();
  }

  test("prompts before cascading and reschedules the whole chain on confirm (AC #1, #2)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, view } = await setupGantt(workspacePage, "day");

    // A → B with B starting right after A. Pushing A forward over B's start
    // makes B violate the FS constraint, so the prompt must appear.
    const rowA = await createRow(workspacePage.user, table, {
      Name: "Task A",
      Start: dayKey(0),
      End: dayKey(1),
    });
    const rowB = await createRow(workspacePage.user, table, {
      Name: "Task B",
      Start: dayKey(2),
      End: dayKey(3),
    });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // Draw A → B through the picker (the 3.9 affordance).
    await page
      .locator(`.gantt-view__host .bar-wrapper[data-id="${rowB.id}"]`)
      .click();
    await page
      .locator(".gantt-view__dependencies-add .dropdown__selected")
      .click();
    await page
      .locator(
        '.gantt-view__dependencies-add .select__item-name-text[title="Task A"]',
      )
      .click();
    await expect(
      page.locator(
        `.gantt-view__host .arrow path[data-from="${rowA.id}"][data-to="${rowB.id}"]`,
      ),
    ).toHaveCount(1);
    await page.keyboard.press("Escape");

    // Drag A forward by 3 days so its new finish lands past B's start — the
    // prompt opens and NOTHING is written yet (AC #1: preview only).
    await dragBarByDays(page, rowA.id, 3);
    await expect(
      page.locator(".modal", { hasText: "Reschedule dependent tasks?" }),
    ).toBeVisible();

    // Confirm — the backend shifts A and the transitive dependent B atomically
    // and the bars reposition. B's start is pushed to A's new finish (AC #2).
    await page.locator(".button", { hasText: "Reschedule dependents" }).click();
    await expect(
      page.locator(".modal", { hasText: "Reschedule dependent tasks?" }),
    ).toHaveCount(0);

    // The connector survives and is NOT styled violated — the chain is valid.
    await expect(
      page.locator(
        `.gantt-view__host .arrow.gantt-view__arrow--violated[data-from="${rowA.id}"][data-to="${rowB.id}"]`,
      ),
    ).toHaveCount(0);

    // Reload — both shifts persisted server-side as one undoable batch (AC #2).
    await tablePage.goto();
    await expect(page.locator(".gantt-view__host .bar-wrapper")).toHaveCount(2);
    await expect(
      page.locator(
        `.gantt-view__host .arrow path[data-from="${rowA.id}"][data-to="${rowB.id}"]`,
      ),
    ).toHaveCount(1);
  });

  test("moves only the predecessor on decline and flags the broken connector (AC #4)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, view } = await setupGantt(workspacePage, "day");

    const rowA = await createRow(workspacePage.user, table, {
      Name: "Task A",
      Start: dayKey(0),
      End: dayKey(1),
    });
    const rowB = await createRow(workspacePage.user, table, {
      Name: "Task B",
      Start: dayKey(2),
      End: dayKey(3),
    });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    await page
      .locator(`.gantt-view__host .bar-wrapper[data-id="${rowB.id}"]`)
      .click();
    await page
      .locator(".gantt-view__dependencies-add .dropdown__selected")
      .click();
    await page
      .locator(
        '.gantt-view__dependencies-add .select__item-name-text[title="Task A"]',
      )
      .click();
    await expect(
      page.locator(
        `.gantt-view__host .arrow path[data-from="${rowA.id}"][data-to="${rowB.id}"]`,
      ),
    ).toHaveCount(1);
    await page.keyboard.press("Escape");

    // Drag A forward past B's start → prompt; decline keeps B in place, leaving
    // the FS edge violated. The backend re-derives the `violated` flag on the
    // dependency re-fetch and the connector is repainted as broken (AC #4).
    await dragBarByDays(page, rowA.id, 3);
    await expect(
      page.locator(".modal", { hasText: "Reschedule dependent tasks?" }),
    ).toBeVisible();
    await page.locator(".button", { hasText: "Move this task only" }).click();

    await expect(
      page.locator(
        `.gantt-view__host .arrow.gantt-view__arrow--violated[data-from="${rowA.id}"][data-to="${rowB.id}"]`,
      ),
    ).toHaveCount(1);

    // Reload — the predecessor-only move and the derived violation persist.
    await tablePage.goto();
    await expect(
      page.locator(
        `.gantt-view__host .arrow.gantt-view__arrow--violated[data-from="${rowA.id}"][data-to="${rowB.id}"]`,
      ),
    ).toHaveCount(1);
  });
});

// Story 3.11 / FR-11: Milestones and Critical Path (CPM)
// NOTE: authored only — not run locally (Docker e2e stack required).
describe("Story 3.11 — Milestones and Critical Path", () => {
  test("zero-duration task renders with gantt-view__milestone class (AC #1)", async ({
    page,
  }) => {
    const { database } = await createDatabase(page);
    const { table } = await createTable(page, database.id);
    const fields = await getFieldsForTable(page, database.id, table.id);
    await deleteAllNonPrimaryFieldsFromTable(page, database.id, table.id);
    const startField = await createField(page, table.id, {
      name: "Start",
      type: "date",
    });
    const endField = await createField(page, table.id, {
      name: "End",
      type: "date",
    });
    const today = dayKey(0);
    // Milestone: start == end (zero-duration).
    const milestone = await createRow(page, database.id, table.id, {
      [`field_${fields[0].id}`]: "Milestone",
      [`field_${startField.id}`]: today,
      [`field_${endField.id}`]: today,
    });
    const view = await createGanttView(page, table.id, {
      start_date_field: startField.id,
      end_date_field: endField.id,
    });
    const tablePage = new TablePage(page);
    await tablePage.goto(database.id, table.id, view.id);
    await expect(
      page.locator(
        `.gantt-view__host .bar-wrapper.gantt-view__milestone[data-id="${milestone.id}"]`,
      ),
    ).toHaveCount(1);
  });

  test(
    "aligned A→B chain gets gantt-view__critical class on both bars (AC #2)",
    async ({ page }) => {
      const { database } = await createDatabase(page);
      const { table } = await createTable(page, database.id);
      const fields = await getFieldsForTable(page, database.id, table.id);
      await deleteAllNonPrimaryFieldsFromTable(page, database.id, table.id);
      const startField = await createField(page, table.id, {
        name: "Start",
        type: "date",
      });
      const endField = await createField(page, table.id, {
        name: "End",
        type: "date",
      });
      // A ends day 5, B starts day 5 → perfectly aligned, zero float.
      const rowA = await createRow(page, database.id, table.id, {
        [`field_${fields[0].id}`]: "Task A",
        [`field_${startField.id}`]: dayKey(0),
        [`field_${endField.id}`]: dayKey(5),
      });
      const rowB = await createRow(page, database.id, table.id, {
        [`field_${fields[0].id}`]: "Task B",
        [`field_${startField.id}`]: dayKey(5),
        [`field_${endField.id}`]: dayKey(10),
      });
      const view = await createGanttView(page, table.id, {
        start_date_field: startField.id,
        end_date_field: endField.id,
      });
      const tablePage = new TablePage(page);
      await tablePage.goto(database.id, table.id, view.id);
      // Create A→B dependency.
      await page
        .locator(`.gantt-view__host .bar-wrapper[data-id="${rowB.id}"]`)
        .click();
      await page
        .locator(".gantt-view__dependencies-add .dropdown__selected")
        .click();
      await page
        .locator(
          '.gantt-view__dependencies-add .select__item-name-text[title="Task A"]',
        )
        .click();
      await page.keyboard.press("Escape");
      await expect(
        page.locator(
          `.gantt-view__host .bar-wrapper.gantt-view__critical[data-id="${rowA.id}"]`,
        ),
      ).toHaveCount(1);
      await expect(
        page.locator(
          `.gantt-view__host .bar-wrapper.gantt-view__critical[data-id="${rowB.id}"]`,
        ),
      ).toHaveCount(1);
    },
  );

  test(
    "B starts before A ends → gantt-view__conflict class on B (AC #3)",
    async ({ page }) => {
      const { database } = await createDatabase(page);
      const { table } = await createTable(page, database.id);
      const fields = await getFieldsForTable(page, database.id, table.id);
      await deleteAllNonPrimaryFieldsFromTable(page, database.id, table.id);
      const startField = await createField(page, table.id, {
        name: "Start",
        type: "date",
      });
      const endField = await createField(page, table.id, {
        name: "End",
        type: "date",
      });
      // A ends day 5, B starts day 3 → conflict.
      const rowA = await createRow(page, database.id, table.id, {
        [`field_${fields[0].id}`]: "Task A",
        [`field_${startField.id}`]: dayKey(0),
        [`field_${endField.id}`]: dayKey(5),
      });
      const rowB = await createRow(page, database.id, table.id, {
        [`field_${fields[0].id}`]: "Task B",
        [`field_${startField.id}`]: dayKey(3),
        [`field_${endField.id}`]: dayKey(8),
      });
      const view = await createGanttView(page, table.id, {
        start_date_field: startField.id,
        end_date_field: endField.id,
      });
      const tablePage = new TablePage(page);
      await tablePage.goto(database.id, table.id, view.id);
      // Create A→B dependency (B starts before A ends — conflict).
      await page
        .locator(`.gantt-view__host .bar-wrapper[data-id="${rowB.id}"]`)
        .click();
      await page
        .locator(".gantt-view__dependencies-add .dropdown__selected")
        .click();
      await page
        .locator(
          '.gantt-view__dependencies-add .select__item-name-text[title="Task A"]',
        )
        .click();
      await page.keyboard.press("Escape");
      await expect(
        page.locator(
          `.gantt-view__host .bar-wrapper.gantt-view__conflict[data-id="${rowB.id}"]`,
        ),
      ).toHaveCount(1);
    },
  );
});
