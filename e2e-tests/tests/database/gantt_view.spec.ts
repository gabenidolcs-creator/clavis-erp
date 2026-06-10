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
});
