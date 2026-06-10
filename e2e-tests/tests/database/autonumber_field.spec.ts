import { expect, test } from "../baserowTest";
import { TablePage } from "../../pages/database/tablePage";
import { createDatabase } from "../../fixtures/database/database";
import { createTable } from "../../fixtures/database/table";
import {
  createField,
  deleteAllNonPrimaryFieldsFromTable,
} from "../../fixtures/database/field";

test.describe("Autonumber field tests", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("Autonumber field column appears in table after creation", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "autonumberFieldTestDb",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Items", database);
    await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);
    await createField(
      workspacePage.user,
      "Row ID",
      "autonumber",
      {},
      table
    );

    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);

    await expect(tablePage.fields().filter({ hasText: "Row ID" })).toBeVisible();
  });

  test("Autonumber cell is read-only — no input appears on click", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "autonumberReadOnlyTestDb",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Records", database);
    await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);
    await createField(
      workspacePage.user,
      "Row ID",
      "autonumber",
      {},
      table
    );

    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);

    // Autonumber cells render via .grid-field-number — no input or contenteditable
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
});
