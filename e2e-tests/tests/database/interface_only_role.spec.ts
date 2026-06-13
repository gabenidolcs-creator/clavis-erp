import { expect, test } from "../baserowTest";
import { getClient } from "../../client";
import { createUser } from "../../fixtures/user";
import { createWorkspace } from "../../fixtures/workspace";
import { createBuilder } from "../../fixtures/builder/builder";
import { createBuilderPage } from "../../fixtures/builder/builderPage";

// Story 6.3: Interface-only Collaborator Role
// API-level E2E tests covering:
// - Assigning INTERFACE_ONLY role to a workspace member
// - Database operation denial for interface-only users
// - Page grant CRUD (grant, list, revoke)
// - Cross-workspace page grant rejection

const ROLE_ASSIGNMENTS_URL = (workspaceId: number) =>
  `rbac/workspaces/${workspaceId}/role-assignments/`;

const PAGE_GRANTS_URL = (workspaceId: number, userId: number) =>
  `rbac/workspaces/${workspaceId}/interface-collaborators/${userId}/page-grants/`;

async function inviteUserToWorkspace(
  adminUser: any,
  inviteeUser: any,
  workspaceId: number
): Promise<void> {
  const inviteResp: any = await getClient(adminUser).post(
    `workspaces/invitations/workspace/${workspaceId}/`,
    {
      email: inviteeUser.email,
      permissions: "MEMBER",
      base_url: "http://localhost",
    }
  );
  const inviteId = inviteResp.data.id;
  await getClient(inviteeUser).post(
    `workspaces/invitations/${inviteId}/accept/`
  );
}

async function assignRole(
  adminUser: any,
  workspaceId: number,
  targetUserId: number,
  role: string
): Promise<void> {
  await getClient(adminUser).post(ROLE_ASSIGNMENTS_URL(workspaceId), {
    user_id: targetUserId,
    role,
  });
}

test.describe("Story 6.3: Interface-only Collaborator Role @rbac", () => {
  test("assign INTERFACE_ONLY role to workspace member", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const member = await createUser();

    await inviteUserToWorkspace(user, member, workspace.id);
    await assignRole(user, workspace.id, member.id, "INTERFACE_ONLY");

    // Confirm role appears in role assignments list
    const resp: any = await getClient(user).get(
      ROLE_ASSIGNMENTS_URL(workspace.id)
    );
    const assignments = resp.data;
    const memberAssignment = assignments.find(
      (a: any) => a.user_id === member.id || a.user?.id === member.id
    );
    expect(memberAssignment).toBeDefined();
  });

  test("INTERFACE_ONLY member is denied database read", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const member = await createUser();

    await inviteUserToWorkspace(user, member, workspace.id);
    await assignRole(user, workspace.id, member.id, "INTERFACE_ONLY");

    // Member should not be able to list applications (database is denied)
    const resp: any = await getClient(member)
      .get(`applications/workspace/${workspace.id}/`)
      .catch((e: any) => e.response);
    expect([403, 400]).toContain(resp.status);
  });

  test("admin can grant page access to INTERFACE_ONLY member", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const member = await createUser();

    await inviteUserToWorkspace(user, member, workspace.id);
    await assignRole(user, workspace.id, member.id, "INTERFACE_ONLY");

    const builder = await createBuilder("Test App", workspace);
    const page = await createBuilderPage("Home", "/home", builder);

    const url = PAGE_GRANTS_URL(workspace.id, member.id);
    const grantResp: any = await getClient(user).post(url, {
      page_id: page.id,
    });
    expect(grantResp.status).toBe(200);
    expect(grantResp.data.page_id).toBe(page.id);
    expect(grantResp.data.user_id).toBe(member.id);
    expect(grantResp.data.workspace_id).toBe(workspace.id);
  });

  test("admin can list page grants for INTERFACE_ONLY member", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const member = await createUser();

    await inviteUserToWorkspace(user, member, workspace.id);
    await assignRole(user, workspace.id, member.id, "INTERFACE_ONLY");

    const builder = await createBuilder("List App", workspace);
    const page = await createBuilderPage("Dashboard", "/dashboard", builder);

    const url = PAGE_GRANTS_URL(workspace.id, member.id);
    // Initially empty
    const emptyResp: any = await getClient(user).get(url);
    expect(emptyResp.data).toHaveLength(0);

    // Grant and re-list
    await getClient(user).post(url, { page_id: page.id });
    const listResp: any = await getClient(user).get(url);
    expect(listResp.data).toHaveLength(1);
    expect(listResp.data[0].page_id).toBe(page.id);
  });

  test("grant is idempotent — duplicate POST creates only one grant", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const member = await createUser();

    await inviteUserToWorkspace(user, member, workspace.id);
    await assignRole(user, workspace.id, member.id, "INTERFACE_ONLY");

    const builder = await createBuilder("Idem App", workspace);
    const page = await createBuilderPage("Index", "/", builder);

    const url = PAGE_GRANTS_URL(workspace.id, member.id);
    await getClient(user).post(url, { page_id: page.id });
    const resp2: any = await getClient(user).post(url, { page_id: page.id });
    expect(resp2.status).toBe(200);

    // List returns exactly one
    const listResp: any = await getClient(user).get(url);
    expect(listResp.data).toHaveLength(1);
  });

  test("admin can revoke page access from INTERFACE_ONLY member", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const member = await createUser();

    await inviteUserToWorkspace(user, member, workspace.id);
    await assignRole(user, workspace.id, member.id, "INTERFACE_ONLY");

    const builder = await createBuilder("Revoke App", workspace);
    const page = await createBuilderPage("Page A", "/a", builder);

    const url = PAGE_GRANTS_URL(workspace.id, member.id);
    await getClient(user).post(url, { page_id: page.id });

    // Revoke
    const delResp: any = await getClient(user).delete(url, {
      data: { page_id: page.id },
    });
    expect(delResp.status).toBe(204);

    // List is empty again
    const listResp: any = await getClient(user).get(url);
    expect(listResp.data).toHaveLength(0);
  });

  test("non-admin member cannot grant page access", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const member = await createUser();

    await inviteUserToWorkspace(user, member, workspace.id);
    await assignRole(user, workspace.id, member.id, "INTERFACE_ONLY");

    const builder = await createBuilder("Deny App", workspace);
    const page = await createBuilderPage("Restricted", "/restricted", builder);

    const url = PAGE_GRANTS_URL(workspace.id, member.id);
    const resp: any = await getClient(member)
      .post(url, { page_id: page.id })
      .catch((e: any) => e.response);
    expect([400, 403]).toContain(resp.status);
  });

  test("granting a page from a different workspace returns 404", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const member = await createUser();

    await inviteUserToWorkspace(user, member, workspace.id);
    await assignRole(user, workspace.id, member.id, "INTERFACE_ONLY");

    // Create another workspace and a page in it
    const otherUser = await createUser();
    const otherWs = await createWorkspace(otherUser);
    const otherBuilder = await createBuilder("Other App", otherWs);
    const otherPage = await createBuilderPage(
      "Other Page",
      "/other",
      otherBuilder
    );

    const url = PAGE_GRANTS_URL(workspace.id, member.id);
    const resp: any = await getClient(user)
      .post(url, { page_id: otherPage.id })
      .catch((e: any) => e.response);
    expect(resp.status).toBe(404);
  });
});
