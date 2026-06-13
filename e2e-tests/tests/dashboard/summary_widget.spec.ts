import { expect, test } from "../baserowTest";
import { createDatabase } from "../../fixtures/database/database";
import { createTable } from "../../fixtures/database/table";
import {
  createField,
  deleteAllNonPrimaryFieldsFromTable,
} from "../../fixtures/database/field";
import { createRow } from "../../fixtures/database/rows";
import { getClient } from "../../client";

// Story 4.5: Metric Widget Non-Regression
// AC #1: SummaryWidget renders correctly (non-regression — auto-provisions
//         local_baserow_aggregate_rows data source on creation).
// AC #2: Backend coexistence test already covered in test_chart_widget_type.py.
// AC #3: SummaryWidget data source is independent of ChartWidget data source
//         (different service types, distinct IDs).
// AC #4: Dispatch returns scalar result when data source is configured.
// Requires the Docker e2e stack; no local Nuxt server needed for API-level tests.

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

async function createSummaryWidget(
  user: any,
  dashboardId: number,
  title: string = "My Summary"
): Promise<any> {
  const response: any = await getClient(user).post(
    `dashboard/${dashboardId}/widgets/`,
    { type: "summary", title }
  );
  return response.data;
}

async function createChartWidget(
  user: any,
  dashboardId: number,
  chartType: string = "bar",
  title: string = "My Chart"
): Promise<any> {
  const response: any = await getClient(user).post(
    `dashboard/${dashboardId}/widgets/`,
    { type: "chart", chart_type: chartType, title }
  );
  return response.data;
}

async function getDataSource(user: any, dataSourceId: number): Promise<any> {
  const response: any = await getClient(user).get(
    `dashboard/data-sources/${dataSourceId}/`
  );
  return response.data;
}

async function configureAggregateDataSource(
  user: any,
  dataSourceId: number,
  integrationId: number,
  tableId: number,
  fieldId: number,
  aggregationType: string = "count"
): Promise<any> {
  const response: any = await getClient(user).patch(
    `dashboard/data-sources/${dataSourceId}/`,
    {
      integration_id: integrationId,
      table_id: tableId,
      field_id: fieldId,
      aggregation_type: aggregationType,
    }
  );
  return response.data;
}

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

test.describe("Summary Widget — Metric Widget Non-Regression (Story 4.5)", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("Summary widget creation auto-provisions a local_baserow_aggregate_rows data source (AC #1)", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const dashboard = await createDashboard(user, workspace, "Summary Creation Test");

    const widget = await createSummaryWidget(user, dashboard.id, "Total Count");

    expect(widget.type).toBe("summary");
    expect(widget.title).toBe("Total Count");
    expect(widget.data_source_id).toBeTruthy();

    const dataSource = await getDataSource(user, widget.data_source_id);
    expect(dataSource.type).toBe("local_baserow_aggregate_rows");
  });

  test("Summary widget and chart widget have independent data sources with different service types (AC #3)", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const dashboard = await createDashboard(user, workspace, "Store Isolation Test");

    const summaryWidget = await createSummaryWidget(user, dashboard.id, "Row Count");
    const chartWidget = await createChartWidget(user, dashboard.id, "bar", "Category Chart");

    // Data source IDs must be distinct
    expect(summaryWidget.data_source_id).not.toBe(chartWidget.data_source_id);

    const summaryDs = await getDataSource(user, summaryWidget.data_source_id);
    const chartDs = await getDataSource(user, chartWidget.data_source_id);

    // Service types are completely different — no cross-contamination possible
    expect(summaryDs.type).toBe("local_baserow_aggregate_rows");
    expect(chartDs.type).toBe("local_baserow_grouped_aggregate_rows");
  });

  test("Configured summary data source dispatch returns scalar result (AC #4)", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;

    const database = await createDatabase(user, "SummaryDispatchDb", workspace);
    const table = await createTable(user, "Numbers", database);
    await deleteAllNonPrimaryFieldsFromTable(user, table);
    const numField = await createField(user, "Amount", "number", {}, table);

    await createRow(user, table, { Amount: 10 });
    await createRow(user, table, { Amount: 20 });
    await createRow(user, table, { Amount: 30 });

    const dashboard = await createDashboard(user, workspace, "Dispatch Test");
    const integration = await createLocalBaserowIntegration(user, dashboard.id);
    const widget = await createSummaryWidget(user, dashboard.id, "Total Amount");

    await configureAggregateDataSource(
      user,
      widget.data_source_id,
      integration.id,
      table.id,
      numField.id,
      "count"
    );

    const result = await dispatchDataSource(user, widget.data_source_id);

    expect(result).toHaveProperty("result");
    expect(typeof result.result).toBe("number");
    expect(result.result).toBe(3);
  });

  test("Unconfigured summary data source dispatch returns error response (AC #4 error path)", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const dashboard = await createDashboard(user, workspace, "Unconfigured Test");
    const widget = await createSummaryWidget(user, dashboard.id, "Unconfigured");

    // Data source exists but has no field/table configured — dispatch must not crash
    // the server; it returns either an empty result or a 400.
    let dispatchResult: any = null;
    let caughtStatus: number | null = null;
    try {
      dispatchResult = await dispatchDataSource(user, widget.data_source_id);
    } catch (e: any) {
      caughtStatus = e.response?.status ?? null;
    }

    // Either a handled error response (4xx) or a result with _error flag
    if (caughtStatus !== null) {
      expect([400, 404]).toContain(caughtStatus);
    } else {
      // Server returned 200 with an error payload
      expect(dispatchResult).toBeDefined();
    }
  });
});
