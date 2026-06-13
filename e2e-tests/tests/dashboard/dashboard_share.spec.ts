import { expect, test } from "../baserowTest";
import { getClient } from "../../client";

// Story 4.6: Dashboard Public Share with Least-Privilege Principal
// AC #1: Public link with share principal enforcement — owner enables sharing, anonymous reads.
// AC #2: Immediate server-side revocation via public=False.
// AC #3: Slug rotation invalidates old link.
// AC #4: Public dispatch endpoint accessible without auth (AnonymousUser principal).
// AC #5: Public response includes widgets array (read-only surface).
// AC #6: Share management requires workspace update permission.
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

async function enableSharing(user: any, dashboardId: number): Promise<any> {
  const response: any = await getClient(user).post(
    `dashboard/${dashboardId}/share/enable/`,
    {}
  );
  return response.data;
}

async function disableSharing(user: any, dashboardId: number): Promise<any> {
  const response: any = await getClient(user).post(
    `dashboard/${dashboardId}/share/disable/`,
    {}
  );
  return response.data;
}

async function rotateSlug(user: any, dashboardId: number): Promise<any> {
  const response: any = await getClient(user).post(
    `dashboard/${dashboardId}/share/rotate-slug/`,
    {}
  );
  return response.data;
}

async function getPublicDashboard(slug: string): Promise<any> {
  const response: any = await getClient().get(`dashboard/public/${slug}/`);
  return response.data;
}

test.describe("Dashboard Public Share (Story 4.6)", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("AC #1: Enable sharing returns public=true and slug; anonymous GET returns dashboard info", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const dashboard = await createDashboard(user, workspace, "Share Test Board");

    const shareData = await enableSharing(user, dashboard.id);

    expect(shareData.public).toBe(true);
    expect(typeof shareData.slug).toBe("string");
    expect(shareData.slug.length).toBeGreaterThan(0);

    const publicData = await getPublicDashboard(shareData.slug);

    expect(publicData.id).toBe(dashboard.id);
    expect(publicData.name).toBe("Share Test Board");
  });

  test("AC #2: Disable sharing causes public GET to return 401 (immediate revocation)", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const dashboard = await createDashboard(user, workspace, "Revocation Test");

    const shareData = await enableSharing(user, dashboard.id);
    const slug = shareData.slug;

    // Confirm access works before disabling
    await getPublicDashboard(slug);

    await disableSharing(user, dashboard.id);

    let caughtStatus: number | null = null;
    try {
      await getPublicDashboard(slug);
    } catch (e: any) {
      caughtStatus = e.response?.status ?? null;
    }

    expect(caughtStatus).toBe(401);
  });

  test("AC #3: Rotate slug invalidates old link; new link returns 200", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const dashboard = await createDashboard(user, workspace, "Slug Rotation Test");

    const shareData = await enableSharing(user, dashboard.id);
    const oldSlug = shareData.slug;

    const rotateData = await rotateSlug(user, dashboard.id);
    const newSlug = rotateData.slug;

    expect(newSlug).not.toBe(oldSlug);

    // Old slug is now dead
    let oldSlugStatus: number | null = null;
    try {
      await getPublicDashboard(oldSlug);
    } catch (e: any) {
      oldSlugStatus = e.response?.status ?? null;
    }
    expect(oldSlugStatus).toBe(401);

    // New slug is live
    const newData = await getPublicDashboard(newSlug);
    expect(newData.id).toBe(dashboard.id);
  });

  test("AC #1+#5: Public dashboard response includes widgets and data_sources arrays", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const dashboard = await createDashboard(user, workspace, "Widget Surface Test");

    await createSummaryWidget(user, dashboard.id, "Total Revenue");

    const shareData = await enableSharing(user, dashboard.id);
    const publicData = await getPublicDashboard(shareData.slug);

    expect(Array.isArray(publicData.widgets)).toBe(true);
    expect(Array.isArray(publicData.data_sources)).toBe(true);
    expect(publicData.widgets.length).toBe(1);
    expect(publicData.widgets[0].type).toBe("summary");
  });

  test("AC #4: Public dispatch endpoint reachable without auth on a public dashboard", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const dashboard = await createDashboard(user, workspace, "Dispatch Test");
    const widget = await createSummaryWidget(user, dashboard.id, "Metric");

    const shareData = await enableSharing(user, dashboard.id);
    const dataSourceId = widget.data_source_id;

    // Dispatch without auth — unconfigured data source returns 400, not 401.
    // The absence of 401 proves AnonymousUser principal is accepted.
    let responseStatus: number | null = null;
    try {
      await getClient().get(
        `dashboard/public/${shareData.slug}/dispatch/${dataSourceId}/`
      );
      responseStatus = 200;
    } catch (e: any) {
      responseStatus = e.response?.status ?? null;
    }

    // 200 or 400 are both acceptable — 401 is not
    expect(responseStatus).not.toBe(401);
    expect(responseStatus).not.toBeNull();
  });

  test("AC #4: Public dispatch on non-public dashboard returns 401 (no existence oracle)", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const dashboard = await createDashboard(user, workspace, "Non-Public Dispatch Test");
    const widget = await createSummaryWidget(user, dashboard.id, "Metric");

    // Dashboard is NOT public (default)
    const dashboardData: any = await getClient(user).get(
      `applications/${dashboard.id}/`
    );
    const slug = dashboardData.data.slug;

    let caughtStatus: number | null = null;
    try {
      await getClient().get(
        `dashboard/public/${slug}/dispatch/${widget.data_source_id}/`
      );
    } catch (e: any) {
      caughtStatus = e.response?.status ?? null;
    }

    expect(caughtStatus).toBe(401);
  });

  test("AC #6: Enable sharing requires authentication — unauthenticated POST returns 401", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const dashboard = await createDashboard(user, workspace, "Permission Test");

    let caughtStatus: number | null = null;
    try {
      await getClient().post(`dashboard/${dashboard.id}/share/enable/`, {});
    } catch (e: any) {
      caughtStatus = e.response?.status ?? null;
    }

    expect(caughtStatus).toBe(401);
  });

  test("Public GET on non-existent slug returns 401 (no existence oracle)", async ({
    workspacePage,
  }) => {
    let caughtStatus: number | null = null;
    try {
      await getPublicDashboard("definitely-not-a-real-slug-xyzzy-404");
    } catch (e: any) {
      caughtStatus = e.response?.status ?? null;
    }

    expect(caughtStatus).toBe(401);
  });
});
