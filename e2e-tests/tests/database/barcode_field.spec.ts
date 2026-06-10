import { expect, test } from "../baserowTest";
import { TablePage } from "../../pages/database/tablePage";
import { createDatabase } from "../../fixtures/database/database";
import { createTable } from "../../fixtures/database/table";
import {
  createField,
  deleteAllNonPrimaryFieldsFromTable,
} from "../../fixtures/database/field";

test.describe("Barcode field tests", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("Barcode field column appears in table after creation", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "barcodeFieldTestDb",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Items", database);
    await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);
    await createField(
      workspacePage.user,
      "Barcode",
      "barcode",
      { barcode_type: "qr" },
      table
    );

    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);

    await expect(
      tablePage.fields().filter({ hasText: "Barcode" })
    ).toBeVisible();
  });

  test("Barcode QR cell renders SVG after text value entered", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "barcodeQrRenderDb",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Products", database);
    await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);
    await createField(
      workspacePage.user,
      "QR Code",
      "barcode",
      { barcode_type: "qr" },
      table
    );

    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);
    await tablePage.inFirstNonPrimaryCellInput("PROD-001");

    await expect(
      tablePage.firstNonPrimaryCellWrappingColumnDiv.locator(
        ".grid-field-barcode svg"
      )
    ).toBeVisible();
  });

  test("Barcode Code128 cell renders SVG for valid input", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const database = await createDatabase(
      workspacePage.user,
      "barcodeCode128Db",
      workspacePage.workspace
    );
    const table = await createTable(workspacePage.user, "Inventory", database);
    await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);
    await createField(
      workspacePage.user,
      "Barcode",
      "barcode",
      { barcode_type: "code128" },
      table
    );

    const tablePage = new TablePage({ page, goto });
    await tablePage.goToTable(table);
    await tablePage.inFirstNonPrimaryCellInput("ABC-123");

    await expect(
      tablePage.firstNonPrimaryCellWrappingColumnDiv.locator(
        ".grid-field-barcode__code128"
      )
    ).toBeVisible();
  });
});
