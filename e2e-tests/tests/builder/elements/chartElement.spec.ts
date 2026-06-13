import { createBuilderElement } from "../../../fixtures/builder/builderElement";
import { getClient } from "../../../client";
import { expect, test } from "../../baserowTest";

test.describe("Builder chart element (Story 5.1 — FR-22)", () => {
  test.describe("API-level", () => {
    test("Creates chart element with default bar chart_type", async ({
      builderPagePage,
    }) => {
      const { user } = builderPagePage.builder.workspace;
      const response: any = await getClient(user).post(
        `builder/page/${builderPagePage.builderPage.id}/elements/`,
        { page_id: builderPagePage.builderPage.id, type: "chart" }
      );
      expect(response.data.type).toBe("chart");
      expect(response.data.chart_type).toBe("bar");
      expect(response.data.data_source_id).toBeNull();
    });

    for (const chartType of ["line", "pie", "doughnut", "scatter"]) {
      test(`Creates chart element with chart_type=${chartType}`, async ({
        builderPagePage,
      }) => {
        const { user } = builderPagePage.builder.workspace;
        const response: any = await getClient(user).post(
          `builder/page/${builderPagePage.builderPage.id}/elements/`,
          {
            page_id: builderPagePage.builderPage.id,
            type: "chart",
            chart_type: chartType,
          }
        );
        expect(response.data.type).toBe("chart");
        expect(response.data.chart_type).toBe(chartType);
      });
    }

    test("Updates chart_type via PATCH", async ({ builderPagePage }) => {
      const { user } = builderPagePage.builder.workspace;
      const created: any = await getClient(user).post(
        `builder/page/${builderPagePage.builderPage.id}/elements/`,
        {
          page_id: builderPagePage.builderPage.id,
          type: "chart",
          chart_type: "bar",
        }
      );
      const updated: any = await getClient(user).patch(
        `builder/elements/${created.data.id}/`,
        { chart_type: "pie" }
      );
      expect(updated.data.chart_type).toBe("pie");
    });

    test("Returns 400 for invalid chart_type", async ({ builderPagePage }) => {
      const { user } = builderPagePage.builder.workspace;
      let caughtError: any;
      try {
        await getClient(user).post(
          `builder/page/${builderPagePage.builderPage.id}/elements/`,
          {
            page_id: builderPagePage.builderPage.id,
            type: "chart",
            chart_type: "radar",
          }
        );
      } catch (e: any) {
        caughtError = e;
      }
      expect(caughtError).toBeDefined();
      expect(caughtError.response?.status).toBe(400);
    });
  });

  test.describe("UI", () => {
    test.beforeEach(async ({ builderPagePage }) => {
      await createBuilderElement(builderPagePage.builderPage, "chart", {});
      await builderPagePage.goto();
    });

    test("Can add chart element from modal", async ({
      page,
      builderPagePage,
    }) => {
      const modal = await builderPagePage.openAddElementModal();
      await modal.addElementByName("Chart");

      await expect(page.locator(".chart-element")).toBeVisible();
    });

    test("Shows empty-data placeholder when no data source configured", async ({
      page,
    }) => {
      await expect(
        page.locator(".chart-element .chart-element__empty")
      ).toBeVisible();
    });
  });
});
