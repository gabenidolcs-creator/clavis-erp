// E2E tests require a running dev stack (`just dev up`).
import { createBuilderElement } from "../../../fixtures/builder/builderElement";
import { getClient } from "../../../client";
import { expect, test } from "../../baserowTest";

test.describe("Builder view embed element (Story 5.3 — FR-24)", () => {
  test.describe("API-level", () => {
    test("Creates view embed element with null view_id by default", async ({
      builderPagePage,
    }) => {
      const { user } = builderPagePage.builder.workspace;
      const response: any = await getClient(user).post(
        `builder/page/${builderPagePage.builderPage.id}/elements/`,
        { page_id: builderPagePage.builderPage.id, type: "view_embed" }
      );
      expect(response.data.type).toBe("view_embed");
      expect(response.data.view_id).toBeNull();
    });

    test("Serialized view embed element returns view_id and type=view_embed (AC 7)", async ({
      builderPagePage,
    }) => {
      const { user } = builderPagePage.builder.workspace;
      const response: any = await getClient(user).post(
        `builder/page/${builderPagePage.builderPage.id}/elements/`,
        { page_id: builderPagePage.builderPage.id, type: "view_embed" }
      );
      expect(response.data.type).toBe("view_embed");
      expect("view_id" in response.data).toBe(true);
      expect("chart_type" in response.data).toBe(false);
    });

    test("Can PATCH view_id on view embed element (AC 7)", async ({
      builderPagePage,
    }) => {
      const { user } = builderPagePage.builder.workspace;
      const created: any = await getClient(user).post(
        `builder/page/${builderPagePage.builderPage.id}/elements/`,
        { page_id: builderPagePage.builderPage.id, type: "view_embed" }
      );
      expect(created.data.view_id).toBeNull();

      const updated: any = await getClient(user).patch(
        `builder/elements/${created.data.id}/`,
        { view_id: null }
      );
      expect(updated.data.type).toBe("view_embed");
      expect("view_id" in updated.data).toBe(true);
    });
  });

  test.describe("UI", () => {
    test("Can add view embed element from modal (AC 1) — iconoir-kanban icon visible", async ({
      page,
      builderPagePage,
    }) => {
      await createBuilderElement(builderPagePage.builderPage, "view_embed", {});
      await builderPagePage.goto();

      const modal = await builderPagePage.openAddElementModal();
      await expect(
        page.locator(".add-element-modal .iconoir-kanban")
      ).toBeVisible();
      await modal.addElementByName("View Embed");

      await expect(page.locator(".view-embed-element")).toBeVisible();
    });

    test("Shows misconfigured placeholder when no view configured (AC 3)", async ({
      page,
      builderPagePage,
    }) => {
      await createBuilderElement(builderPagePage.builderPage, "view_embed", {});
      await builderPagePage.goto();

      await expect(
        page.locator(".view-embed-element .view-embed-element__misconfigured")
      ).toBeVisible();
    });
  });
});
