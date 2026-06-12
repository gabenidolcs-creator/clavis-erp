import { expect, test } from "../baserowTest";
import { getClient } from "../../client";

// Story 4.3: Chart Widgets — bar and pie/doughnut (clean-room)
// AC #1: bar/pie/doughnut widgets created via API; auto-create a grouped-aggregate data source.
// AC #3: chart widget coexists with summary widget on the same dashboard.
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

async function listWidgets(user: any, dashboardId: number): Promise<any[]> {
  const response: any = await getClient(user).get(
    `dashboard/${dashboardId}/widgets/`
  );
  return response.data;
}

async function getDataSource(user: any, dataSourceId: number): Promise<any> {
  const response: any = await getClient(user).get(
    `dashboard/data-sources/${dataSourceId}/`
  );
  return response.data;
}

test.describe("Chart Widget (Story 4.3)", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("Bar chart widget is created with auto-provisioned grouped-aggregate data source", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const dashboard = await createDashboard(user, workspace, "Bar Chart Test");

    const widget = await createChartWidget(user, dashboard.id, "bar", "Sales Chart");

    expect(widget.type).toBe("chart");
    expect(widget.chart_type).toBe("bar");
    expect(widget.title).toBe("Sales Chart");
    expect(widget.data_source_id).toBeTruthy();

    const dataSource = await getDataSource(user, widget.data_source_id);
    expect(dataSource.type).toBe("local_baserow_grouped_aggregate_rows");
  });

  test("Pie chart widget persists chart_type as 'pie'", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const dashboard = await createDashboard(user, workspace, "Pie Chart Test");

    const widget = await createChartWidget(user, dashboard.id, "pie", "Revenue Pie");

    expect(widget.type).toBe("chart");
    expect(widget.chart_type).toBe("pie");
    expect(widget.data_source_id).toBeTruthy();
  });

  test("Doughnut chart widget persists chart_type as 'doughnut'", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const dashboard = await createDashboard(user, workspace, "Doughnut Chart Test");

    const widget = await createChartWidget(
      user,
      dashboard.id,
      "doughnut",
      "Cost Doughnut"
    );

    expect(widget.type).toBe("chart");
    expect(widget.chart_type).toBe("doughnut");
    expect(widget.data_source_id).toBeTruthy();
  });

  test("Chart widget and summary widget coexist on the same dashboard (AC #3)", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const dashboard = await createDashboard(user, workspace, "Coexistence Test");

    const summaryWidget = await createSummaryWidget(user, dashboard.id, "Total Count");
    const chartWidget = await createChartWidget(
      user,
      dashboard.id,
      "bar",
      "Category Chart"
    );

    const widgets = await listWidgets(user, dashboard.id);
    const widgetIds = widgets.map((w: any) => w.id);

    expect(widgetIds).toContain(summaryWidget.id);
    expect(widgetIds).toContain(chartWidget.id);
    expect(widgets.some((w: any) => w.type === "summary")).toBe(true);
    expect(widgets.some((w: any) => w.type === "chart")).toBe(true);
  });

  test("Creating a chart widget with an invalid chart_type returns a 400 error", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const dashboard = await createDashboard(user, workspace, "Validation Test");

    let caughtError: any;
    try {
      await getClient(user).post(`dashboard/${dashboard.id}/widgets/`, {
        type: "chart",
        chart_type: "scatter",
        title: "Invalid Chart",
      });
    } catch (e: any) {
      caughtError = e;
    }

    expect(caughtError).toBeDefined();
    expect(caughtError.response?.status).toBe(400);
  });
});
