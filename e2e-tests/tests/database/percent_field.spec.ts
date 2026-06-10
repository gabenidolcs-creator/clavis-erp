import { expect, test } from "../baserowTest";
import { TablePage } from "../../pages/database/tablePage";
import { createDatabase } from "../../fixtures/database/database";
import { createTable } from "../../fixtures/database/table";
import {
  createField,
  deleteAllNonPrimaryFieldsFromTable,
} from "../../fixtures/database/field";

test.describe("Percent field tests", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("Percent field column appears in table after creation", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "percentFieldTestDb",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Metrics", database);
    await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);
    await createField(
      workspacePage.user,
      "Completion",
      "percent",
      { number_decimal_places: 0 },
      table
    );

    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);

    await expect(
      tablePage.fields().filter({ hasText: "Completion" })
    ).toBeVisible();
  });

  test("Percent cell renders numeric value with locked % suffix", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "percentDisplayTestDb",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Scores", database);
    await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);
    await createField(
      workspacePage.user,
      "Score",
      "percent",
      { number_decimal_places: 0 },
      table
    );

    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);
    await tablePage.inFirstNonPrimaryCellInput("75");

    await expect(
      tablePage.firstNonPrimaryCellWrappingColumnDiv
    ).toContainText("%");
  });

  test("Percent cell renders with decimal places when configured", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "percentDecimalTestDb",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Rates", database);
    await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);
    await createField(
      workspacePage.user,
      "Rate",
      "percent",
      { number_decimal_places: 2 },
      table
    );

    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);
    await tablePage.inFirstNonPrimaryCellInput("75");

    await expect(
      tablePage.firstNonPrimaryCellWrappingColumnDiv
    ).toContainText("75.00%");
  });
});
