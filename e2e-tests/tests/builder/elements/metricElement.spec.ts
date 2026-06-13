// E2E tests require a running dev stack (`just dev up`).
import { createBuilderElement } from "../../../fixtures/builder/builderElement";
import { getClient } from "../../../client";
import { expect, test } from "../../baserowTest";

test.describe("Builder metric element (Story 5.2 — FR-23)", () => {
  test.describe("API-level", () => {
    test("Creates metric element with null data_source_id by default", async ({
      builderPagePage,
    }) => {
      const { user } = builderPagePage.builder.workspace;
      const response: any = await getClient(user).post(
        `builder/page/${builderPagePage.builderPage.id}/elements/`,
        { page_id: builderPagePage.builderPage.id, type: "metric" }
      );
      expect(response.data.type).toBe("metric");
      expect(response.data.data_source_id).toBeNull();
      expect(response.data.chart_type).toBeUndefined();
    });

    test("Serialized metric element has no chart_type field (AC 7)", async ({
      builderPagePage,
    }) => {
      const { user } = builderPagePage.builder.workspace;
      const response: any = await getClient(user).post(
        `builder/page/${builderPagePage.builderPage.id}/elements/`,
        { page_id: builderPagePage.builderPage.id, type: "metric" }
      );
      expect("chart_type" in response.data).toBe(false);
    });

    test("Can PATCH data_source_id on metric element (AC 7)", async ({
      builderPagePage,
    }) => {
      const { user } = builderPagePage.builder.workspace;
      const created: any = await getClient(user).post(
        `builder/page/${builderPagePage.builderPage.id}/elements/`,
        { page_id: builderPagePage.builderPage.id, type: "metric" }
      );
      expect(created.data.data_source_id).toBeNull();

      const updated: any = await getClient(user).patch(
        `builder/elements/${created.data.id}/`,
        { data_source_id: null }
      );
      expect(updated.data.type).toBe("metric");
      expect("chart_type" in updated.data).toBe(false);
    });
  });

  test.describe("UI", () => {
    test("Can add metric element from modal (AC 4)", async ({
      page,
      builderPagePage,
    }) => {
      await createBuilderElement(builderPagePage.builderPage, "metric", {});
      await builderPagePage.goto();

      const modal = await builderPagePage.openAddElementModal();
      await expect(
        page.locator(".add-element-modal .iconoir-sigma-function")
      ).toBeVisible();
      await modal.addElementByName("Metric");

      await expect(page.locator(".metric-element")).toBeVisible();
    });

    test("Shows empty-data placeholder when no data source configured (AC 3)", async ({
      page,
      builderPagePage,
    }) => {
      await createBuilderElement(builderPagePage.builderPage, "metric", {});
      await builderPagePage.goto();

      await expect(
        page.locator(".metric-element .metric-element__empty")
      ).toBeVisible();
    });

    test("Renders formatted scalar when configured with data source (AC 1)", async ({
      page,
      builderPagePage,
    }) => {
      const dataSourceResponse = await builderPagePage.builder.workspace.dataSourceFixture.create(
        "local_baserow_aggregate_rows",
        { result: 42 }
      );

      await createBuilderElement(builderPagePage.builderPage, "metric", {
        data_source_id: dataSourceResponse.data.id,
      });
      await builderPagePage.goto();

      const value = page.locator(".metric-element .metric-element__value");
      await expect(value).toBeVisible();
      await expect(value).toContainText(/\d+/);
    });
  });
});
