import { expect, test } from "../baserowTest";
import { TablePage } from "../../pages/database/tablePage";
import { createDatabase } from "../../fixtures/database/database";
import { createTable } from "../../fixtures/database/table";
import {
  createField,
  deleteAllNonPrimaryFieldsFromTable,
} from "../../fixtures/database/field";
import {
  createRow,
  deleteRow,
  listRows,
} from "../../fixtures/database/rows";

test.describe("Running Count field tests", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("Running Count field column appears in table after creation", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "runningCountFieldTestDb",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Items", database);
    await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);
    await createField(workspacePage.user, "Total", "running_count", {}, table);

    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);

    await expect(
      tablePage.fields().filter({ hasText: "Total" })
    ).toBeVisible();
  });

  test("Running Count cell is read-only — no input appears on click", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "runningCountReadOnlyTestDb",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Records", database);
    await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);
    await createField(workspacePage.user, "Total", "running_count", {}, table);

    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);

    // Running Count cells render via .grid-field-number — no input or contenteditable
    await expect(
      tablePage.firstNonPrimaryCellWrappingColumnDiv.locator(
        ".grid-field-number"
      )
    ).toBeVisible();

    // Click the cell and assert no edit input appears (field is read-only)
    await tablePage.firstNonPrimaryCellWrappingColumnDiv.click();
    await expect(
      page.locator(".grid-view__cell.active input")
    ).toHaveCount(0);
  });

  test("Running Count cell displays the whole-table row count", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "runningCountValueDisplayDb",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Items", database);
    await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);
    await createField(workspacePage.user, "Total", "running_count", {}, table);

    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);

    // createTable seeds 2 example rows; whole-table count is 2 for every row.
    await expect(
      tablePage.firstNonPrimaryCellWrappingColumnDiv.locator(
        ".grid-field-number"
      )
    ).toHaveText("2");
  });

  test("Running Count increments for all rows when a row is created", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "runningCountOnCreateDb",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Items", database);
    await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);
    await createField(workspacePage.user, "Total", "running_count", {}, table);

    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);

    // createTable seeds 2 example rows; whole-table count starts at 2.
    await expect(
      tablePage.firstNonPrimaryCellWrappingColumnDiv.locator(
        ".grid-field-number"
      )
    ).toHaveText("2");

    // Create a third row via API — the after_rows_created hook recomputes.
    await createRow(workspacePage.user, table, {});

    // Reload the table so the grid re-fetches the recomputed counts.
    await tablePage.goToTable(table);

    // Every row (including the new one) now shows 3.
    await expect(
      tablePage.firstNonPrimaryCellWrappingColumnDiv.locator(
        ".grid-field-number"
      )
    ).toHaveText("3");
    await expect(tablePage.rows()).toHaveCount(3);
  });

  test("Running Count decrements for all rows when a row is deleted", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "runningCountOnDeleteDb",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Items", database);
    await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);
    await createField(workspacePage.user, "Total", "running_count", {}, table);

    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);

    // createTable seeds 2 example rows; whole-table count starts at 2.
    await expect(
      tablePage.firstNonPrimaryCellWrappingColumnDiv.locator(
        ".grid-field-number"
      )
    ).toHaveText("2");

    // Delete one of the seeded rows via API — the rows_deleted signal recomputes.
    const rows = await listRows(workspacePage.user, table);
    await deleteRow(workspacePage.user, table, rows[0].id);

    // Reload the table so the grid re-fetches the recomputed counts.
    await tablePage.goToTable(table);

    // The single remaining row shows the decremented count of 1.
    await expect(
      tablePage.firstNonPrimaryCellWrappingColumnDiv.locator(
        ".grid-field-number"
      )
    ).toHaveText("1");
    await expect(tablePage.rows()).toHaveCount(1);
  });
});
