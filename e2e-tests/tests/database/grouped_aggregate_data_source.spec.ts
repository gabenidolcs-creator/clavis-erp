import { expect, test } from "../baserowTest";
import { createDatabase } from "../../fixtures/database/database";
import { createTable } from "../../fixtures/database/table";
import {
  createField,
  deleteAllNonPrimaryFieldsFromTable,
} from "../../fixtures/database/field";
import { createRow } from "../../fixtures/database/rows";
import { getClient } from "../../client";

// NOTE (Story 4.2 / Bucket B greenfield): The grouped-aggregate data source is a
// net-new service type `local_baserow_grouped_aggregate_rows` that returns
// (category, value[, series]) tuples for chart rendering (FR-15, D9).
// Chart widget wiring is deferred to Story 4.3 — this spec tests the API-level
// service type registration and dispatch only.
// Per the e2e-tests convention this spec is AUTHORED here but requires the
// Docker e2e stack to execute (`e2e-tests/` has no local Nuxt server).

/**
 * Create a dashboard application via the applications API.
 */
async function createDashboard(
  user: any,
  workspace: any,
  name: string = "Test Dashboard"
): Promise<any> {
  const response: any = await getClient(user).post(
    `applications/workspace/${workspace.id}/`,
    { name, type: "dashboard" }
  );
  return response.data;
}

/**
 * Create a local_baserow integration on a dashboard.
 */
async function createLocalBaserowIntegration(
  user: any,
  dashboardId: number
): Promise<any> {
  const response: any = await getClient(user).post(
    `application/${dashboardId}/integrations/`,
    { type: "local_baserow", name: "Local Baserow Integration" }
  );
  return response.data;
}

/**
 * Create a grouped-aggregate data source on a dashboard.
 */
async function createGroupedAggregateDataSource(
  user: any,
  dashboardId: number,
  integrationId: number,
  tableId: number,
  groupByFieldId: number,
  aggregationType: string = "count",
  valueFieldId: number | null = null
): Promise<any> {
  const body: any = {
    type: "local_baserow_grouped_aggregate_rows",
    name: "Grouped Aggregate Source",
    integration_id: integrationId,
    table_id: tableId,
    group_by_field_id: groupByFieldId,
    aggregation_type: aggregationType,
  };
  if (valueFieldId !== null) {
    body.value_field_id = valueFieldId;
  }
  const response: any = await getClient(user).post(
    `dashboard/${dashboardId}/data-sources/`,
    body
  );
  return response.data;
}

/**
 * Dispatch a dashboard data source and return the result.
 */
async function dispatchDataSource(
  user: any,
  dataSourceId: number
): Promise<any> {
  const response: any = await getClient(user).post(
    `dashboard/data-sources/${dataSourceId}/dispatch/`,
    {}
  );
  return response.data;
}

test.describe("Grouped Aggregate Data Source (Story 4.2)", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("Service type is registered — data source can be created via API", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;

    const database = await createDatabase(user, "AggTestDb", workspace);
    const table = await createTable(user, "Products", database);
    await deleteAllNonPrimaryFieldsFromTable(user, table);
    const categoryField = await createField(user, "Category", "text", {}, table);

    const dashboard = await createDashboard(user, workspace);
    const integration = await createLocalBaserowIntegration(user, dashboard.id);

    const dataSource = await createGroupedAggregateDataSource(
      user,
      dashboard.id,
      integration.id,
      table.id,
      categoryField.id
    );

    expect(dataSource.type).toBe("local_baserow_grouped_aggregate_rows");
    expect(dataSource.aggregation_type).toBe("count");
    expect(dataSource.group_by_field_id).toBe(categoryField.id);
  });

  test("Dispatch returns (category, value) tuples for count aggregation", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;

    const database = await createDatabase(user, "AggDispatchTestDb", workspace);
    const table = await createTable(user, "Items", database);
    await deleteAllNonPrimaryFieldsFromTable(user, table);
    const categoryField = await createField(user, "Category", "text", {}, table);

    // Seed rows: A×2, B×1
    await createRow(user, table, { Category: "A" });
    await createRow(user, table, { Category: "A" });
    await createRow(user, table, { Category: "B" });

    const dashboard = await createDashboard(user, workspace, "Dispatch Test");
    const integration = await createLocalBaserowIntegration(user, dashboard.id);
    const dataSource = await createGroupedAggregateDataSource(
      user,
      dashboard.id,
      integration.id,
      table.id,
      categoryField.id
    );

    const result = await dispatchDataSource(user, dataSource.id);

    expect(result).toHaveProperty("results");
    const results: any[] = result.results;
    expect(results.length).toBe(2);

    const byCategory: Record<string, number> = {};
    for (const row of results) {
      expect(typeof row.category).toBe("string");
      expect(typeof row.value).toBe("number");
      byCategory[row.category] = row.value;
    }
    expect(byCategory["A"]).toBe(2);
    expect(byCategory["B"]).toBe(1);
  });

  test("Dispatch with series_field returns (category, series, value) tuples", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;

    const database = await createDatabase(user, "AggSeriesTestDb", workspace);
    const table = await createTable(user, "Sales", database);
    await deleteAllNonPrimaryFieldsFromTable(user, table);
    const catField = await createField(user, "Category", "text", {}, table);
    const seriesField = await createField(user, "Region", "text", {}, table);

    await createRow(user, table, { Category: "A", Region: "North" });
    await createRow(user, table, { Category: "A", Region: "South" });
    await createRow(user, table, { Category: "B", Region: "North" });

    const dashboard = await createDashboard(user, workspace, "Series Test");
    const integration = await createLocalBaserowIntegration(user, dashboard.id);

    const body: any = {
      type: "local_baserow_grouped_aggregate_rows",
      name: "Series Source",
      integration_id: integration.id,
      table_id: table.id,
      group_by_field_id: catField.id,
      aggregation_type: "count",
      series_field_id: seriesField.id,
    };
    const createResp: any = await getClient(user).post(
      `dashboard/${dashboard.id}/data-sources/`,
      body
    );
    const dataSource = createResp.data;

    const result = await dispatchDataSource(user, dataSource.id);

    expect(result).toHaveProperty("results");
    const results: any[] = result.results;
    expect(results.length).toBe(3);
    for (const row of results) {
      expect(row).toHaveProperty("category");
      expect(row).toHaveProperty("series");
      expect(row).toHaveProperty("value");
    }
  });

  test("NULL category value is returned as empty string", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;

    const database = await createDatabase(user, "AggNullCatDb", workspace);
    const table = await createTable(user, "NullItems", database);
    await deleteAllNonPrimaryFieldsFromTable(user, table);
    const categoryField = await createField(user, "Category", "text", {}, table);

    await createRow(user, table, {});           // NULL category
    await createRow(user, table, { Category: "X" });

    const dashboard = await createDashboard(user, workspace, "Null Cat Test");
    const integration = await createLocalBaserowIntegration(user, dashboard.id);
    const dataSource = await createGroupedAggregateDataSource(
      user,
      dashboard.id,
      integration.id,
      table.id,
      categoryField.id
    );

    const result = await dispatchDataSource(user, dataSource.id);

    const categories = result.results.map((r: any) => r.category);
    expect(categories).toContain("");
    expect(categories).toContain("X");
    expect(categories.every((c: any) => typeof c === "string")).toBe(true);
  });
});
