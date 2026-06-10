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
  createView,
  createViewFilter,
  updateView,
} from "../../fixtures/database/view";

// NOTE (clean-room / Bucket A): the free Kanban view lives in core and is only
// the registered "kanban" view type in an OSS-only build. In an open-core build
// that also ships the premium plugin, premium's Kanban view registers later and
// overrides this one (last registration wins). This spec therefore asserts the
// core DOM (`.kanban-view__column`) and MUST run against the OSS-only e2e stack
// (BASEROW_OSS_ONLY=true). It is authored but is NOT run locally — it is wired
// to run in the dedicated OSS-only CI lane.

/**
 * Builds a Tasks table with a single-select "Status" field (two options) and a
 * Kanban view already grouped by that field. Returns everything a test needs to
 * navigate to the board and seed rows.
 */
async function setupKanban(workspacePage: any) {
  const database = await createDatabase(
    workspacePage.user,
    "kanbanViewTestDb",
    workspacePage.workspace,
  );
  const table = await createTable(workspacePage.user, "Tasks", database);
  await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);

  // A single-select field with two options is the grouping field.
  const statusField = await createField(
    workspacePage.user,
    "Status",
    "single_select",
    {
      select_options: [
        { value: "To do", color: "blue" },
        { value: "Done", color: "green" },
      ],
    },
    table,
  );
  const [toDoOption, doneOption] = statusField.fieldSettings.select_options;

  // Create the Kanban view already grouped by the single-select field.
  const view = await createView(
    workspacePage.user,
    "Board",
    "kanban",
    { single_select_field: statusField.id },
    table,
  );

  return { database, table, statusField, toDoOption, doneOption, view };
}

test.describe("Kanban view", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("groups cards into one column per single-select option plus Uncategorized, and persists", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, view } = await setupKanban(workspacePage);

    // Navigate straight to the Kanban view.
    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // One column per option ("To do", "Done") plus a trailing "Uncategorized"
    // column for rows whose grouping value is null.
    const columns = page.locator(".kanban-view__column");
    await expect(columns).toHaveCount(3);
    await expect(page.locator(".kanban-view__column-label")).toContainText([
      "To do",
      "Done",
      "Uncategorized",
    ]);

    // Reload the page — the grouping configuration persists server-side, so the
    // same three columns render again.
    await tablePage.goto();
    await expect(page.locator(".kanban-view__column")).toHaveCount(3);

    // Re-pointing the view at no grouping field clears the columns and shows the
    // empty state prompting the user to pick a single-select field.
    await updateView(workspacePage.user, view, { single_select_field: null });
    await tablePage.goto();
    await expect(page.locator(".kanban-view__column")).toHaveCount(0);
    await expect(page.locator(".kanban-view__empty")).toBeVisible();
  });

  test("places each row in the column matching its single-select value, with null rows in Uncategorized (AC #1)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, statusField, toDoOption, doneOption, view } =
      await setupKanban(workspacePage);

    // Seed three rows: one per option and one with no grouping value. The
    // single-select cell is set by option id (user_field_names=true).
    await createRow(workspacePage.user, table, { Status: toDoOption.id });
    await createRow(workspacePage.user, table, { Status: doneOption.id });
    await createRow(workspacePage.user, table, { Status: null });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // Columns render in option order, then Uncategorized last.
    const columns = page.locator(".kanban-view__column");
    await expect(columns).toHaveCount(3);

    // Each option column holds exactly its one matching card; the null row lands
    // in the trailing Uncategorized column — it is NOT dropped (AC #1 explicit).
    await expect(columns.nth(0).locator(".kanban-view__card")).toHaveCount(1);
    await expect(columns.nth(1).locator(".kanban-view__card")).toHaveCount(1);
    await expect(columns.nth(2).locator(".kanban-view__card")).toHaveCount(1);

    // The per-column counter in the header reflects the same distribution.
    await expect(
      columns.nth(2).locator(".kanban-view__column-label"),
    ).toHaveText("Uncategorized");
    await expect(
      columns.nth(2).locator(".kanban-view__column-count"),
    ).toHaveText("1");

    // statusField is referenced to keep its option ids in scope for clarity.
    expect(statusField.id).toBeTruthy();
  });

  test("applies existing view filters to the rows shown on the board (AC #2)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, toDoOption, doneOption, view } =
      await setupKanban(workspacePage);

    // Seed two "To do" rows and one "Done" row.
    await createRow(workspacePage.user, table, { Status: toDoOption.id });
    await createRow(workspacePage.user, table, { Status: toDoOption.id });
    await createRow(workspacePage.user, table, { Status: doneOption.id });

    // Filter the view to only show rows whose Status is "Done". The board must
    // route through the standard view row pipeline, so the filter applies.
    const fields = await getFieldsForTable(workspacePage.user, table);
    const statusFieldFull = fields.find((f) => f.name === "Status");
    await createViewFilter(
      workspacePage.user,
      view,
      statusFieldFull.id,
      "single_select_equal",
      String(doneOption.id),
    );

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    const columns = page.locator(".kanban-view__column");
    await expect(columns).toHaveCount(3);

    // Only the single "Done" card survives the filter — the two "To do" rows are
    // filtered out, so that column is empty.
    await expect(columns.nth(0).locator(".kanban-view__card")).toHaveCount(0);
    await expect(columns.nth(1).locator(".kanban-view__card")).toHaveCount(1);
    await expect(page.locator(".kanban-view__card")).toHaveCount(1);
  });
});
