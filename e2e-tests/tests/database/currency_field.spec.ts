import { expect, test } from "../baserowTest";
import { TablePage } from "../../pages/database/tablePage";
import { createDatabase } from "../../fixtures/database/database";
import { createTable } from "../../fixtures/database/table";
import {
  createField,
  deleteAllNonPrimaryFieldsFromTable,
} from "../../fixtures/database/field";

test.describe("Currency field tests", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("Currency field column appears in table after creation", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "currencyFieldTestDb",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Budgets", database);
    await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);
    await createField(
      workspacePage.user,
      "Budget",
      "currency",
      { currency_symbol: "€", number_decimal_places: 2 },
      table
    );

    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);

    await expect(tablePage.fields().filter({ hasText: "Budget" })).toBeVisible();
  });

  test("Currency cell renders numeric value with configured symbol", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "currencyDisplayTestDb",
      workspacePage.workspace
    );
    const table = await createTable(
      workspacePage.user,
      "Transactions",
      database
    );
    await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);
    await createField(
      workspacePage.user,
      "Amount",
      "currency",
      { currency_symbol: "$", number_decimal_places: 0 },
      table
    );

    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);
    await tablePage.inFirstNonPrimaryCellInput("100");

    await expect(
      tablePage.firstNonPrimaryCellWrappingColumnDiv
    ).toContainText("$");
  });
});
