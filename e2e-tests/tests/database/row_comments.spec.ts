import { expect, test } from "../baserowTest";
import { getClient } from "../../client";
import { createUser } from "../../fixtures/user";
import { createDatabase } from "../../fixtures/database/database";
import { createTable } from "../../fixtures/database/table";
import { createRow } from "../../fixtures/database/rows";

// Story 6.1: Row Comments with @mentions (clean-room, Bucket A)
// API-level E2E tests covering CRUD, RBAC enforcement, and field-value leak prevention.
// Requires the Docker e2e stack; no local Nuxt server needed.

const SIMPLE_MESSAGE = {
  type: "doc",
  content: [{ type: "paragraph", content: [{ type: "text", text: "hello" }] }],
};

const UPDATED_MESSAGE = {
  type: "doc",
  content: [
    { type: "paragraph", content: [{ type: "text", text: "updated text" }] },
  ],
};

async function listComments(user: any, tableId: number, rowId: number) {
  const response: any = await getClient(user).get(
    `database/rows/table/${tableId}/${rowId}/comments/`
  );
  return response.data;
}

async function createComment(
  user: any,
  tableId: number,
  rowId: number,
  message: object = SIMPLE_MESSAGE
) {
  const response: any = await getClient(user).post(
    `database/rows/table/${tableId}/${rowId}/comments/`,
    { message }
  );
  return response.data;
}

async function updateComment(
  user: any,
  tableId: number,
  rowId: number,
  commentId: number,
  message: object
) {
  const response: any = await getClient(user).patch(
    `database/rows/table/${tableId}/${rowId}/comments/${commentId}/`,
    { message }
  );
  return response.data;
}

async function deleteComment(
  user: any,
  tableId: number,
  rowId: number,
  commentId: number
) {
  await getClient(user).delete(
    `database/rows/table/${tableId}/${rowId}/comments/${commentId}/`
  );
}

test.describe("Row Comments (Story 6.1)", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("Authenticated member can list comments for a row (returns paginated results)", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const database = await createDatabase(user, "Comment Test DB", workspace);
    const table = await createTable(user, "My Table", database);
    const row = await createRow(user, table, {});

    const result = await listComments(user, table.id, row.id);

    expect(result).toHaveProperty("results");
    expect(Array.isArray(result.results)).toBe(true);
    expect(result.results.length).toBe(0);
  });

  test("Authenticated member can create a comment — returns 201 with correct payload", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const database = await createDatabase(user, "Comment Test DB", workspace);
    const table = await createTable(user, "My Table", database);
    const row = await createRow(user, table, {});

    const comment = await createComment(user, table.id, row.id);

    expect(comment.id).toBeTruthy();
    expect(comment.message).toEqual(SIMPLE_MESSAGE);
    expect(comment.author).toBeTruthy();
  });

  test("Comment payload contains no row field values (field-permission leak prevention)", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const database = await createDatabase(user, "Comment Test DB", workspace);
    const table = await createTable(user, "My Table", database);
    const row = await createRow(user, table, {});

    const comment = await createComment(user, table.id, row.id);

    const allowedKeys = new Set(["id", "author", "message", "created_on", "updated_on"]);
    const commentKeys = Object.keys(comment);
    const unexpectedKeys = commentKeys.filter((k) => !allowedKeys.has(k));

    expect(unexpectedKeys).toHaveLength(0);
    expect(comment).not.toHaveProperty("fields");
    expect(comment).not.toHaveProperty("row_data");
  });

  test("Comment is visible in subsequent list request", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const database = await createDatabase(user, "Comment Test DB", workspace);
    const table = await createTable(user, "My Table", database);
    const row = await createRow(user, table, {});

    const created = await createComment(user, table.id, row.id);
    const result = await listComments(user, table.id, row.id);

    expect(result.results.some((c: any) => c.id === created.id)).toBe(true);
  });

  test("Owner can edit their own comment — returns updated message", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const database = await createDatabase(user, "Comment Test DB", workspace);
    const table = await createTable(user, "My Table", database);
    const row = await createRow(user, table, {});

    const created = await createComment(user, table.id, row.id);
    const updated = await updateComment(
      user,
      table.id,
      row.id,
      created.id,
      UPDATED_MESSAGE
    );

    expect(updated.message).toEqual(UPDATED_MESSAGE);
    expect(updated.id).toBe(created.id);
  });

  test("Owner can delete their own comment — comment no longer in list", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const database = await createDatabase(user, "Comment Test DB", workspace);
    const table = await createTable(user, "My Table", database);
    const row = await createRow(user, table, {});

    const created = await createComment(user, table.id, row.id);
    await deleteComment(user, table.id, row.id, created.id);

    const result = await listComments(user, table.id, row.id);
    expect(result.results.some((c: any) => c.id === created.id)).toBe(false);
  });

  test("Unauthenticated request to create comment returns 401", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const database = await createDatabase(user, "Comment Test DB", workspace);
    const table = await createTable(user, "My Table", database);
    const row = await createRow(user, table, {});

    let caughtError: any;
    try {
      await getClient(undefined).post(
        `database/rows/table/${table.id}/${row.id}/comments/`,
        { message: SIMPLE_MESSAGE }
      );
    } catch (e: any) {
      caughtError = e;
    }

    expect(caughtError).toBeDefined();
    expect(caughtError.response?.status).toBe(401);
  });

  // ─── Story 6.2: Multi-user helpers ─────────────────────────────────────────

  async function getUserId(user: any): Promise<number> {
    const response: any = await getClient(user).get("user/");
    return response.data.id;
  }

  async function addUserToWorkspace(
    owner: any,
    workspaceId: number,
    inviteeEmail: string,
    inviteeUser: any
  ): Promise<void> {
    const inviteResp: any = await getClient(owner).post(
      `workspaces/invitations/workspace/${workspaceId}/`,
      {
        email: inviteeEmail,
        permissions: "MEMBER",
        base_url: "http://localhost",
      }
    );
    const inviteId = inviteResp.data.id;
    await getClient(inviteeUser).post(
      `workspaces/invitations/${inviteId}/accept/`
    );
  }

  // Story 6.2: Comment Notifications — subscription API tests
  test("POST comment auto-subscribes the commenter", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const database = await createDatabase(user, "Subscription Test DB", workspace);
    const table = await createTable(user, "My Table", database);
    const row = await createRow(user, table, {});

    // Before comment — not subscribed
    const beforeResp: any = await getClient(user).get(
      `database/rows/table/${table.id}/${row.id}/comments/subscriptions/`
    );
    expect(beforeResp.data.subscribed).toBe(false);

    // Create a comment
    await createComment(user, table.id, row.id);

    // After comment — auto-subscribed
    const afterResp: any = await getClient(user).get(
      `database/rows/table/${table.id}/${row.id}/comments/subscriptions/`
    );
    expect(afterResp.data.subscribed).toBe(true);
  });

  test("Manual subscribe/unsubscribe cycle works correctly", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const database = await createDatabase(user, "Subscribe Test DB", workspace);
    const table = await createTable(user, "My Table", database);
    const row = await createRow(user, table, {});

    const subUrl = `database/rows/table/${table.id}/${row.id}/comments/subscriptions/`;

    // Subscribe
    const subscribeResp: any = await getClient(user).post(subUrl);
    expect(subscribeResp.status).toBe(200);
    expect(subscribeResp.data.subscribed).toBe(true);

    // Verify subscribed
    const statusResp: any = await getClient(user).get(subUrl);
    expect(statusResp.data.subscribed).toBe(true);

    // Unsubscribe
    const unsubscribeResp: any = await getClient(user).delete(subUrl);
    expect(unsubscribeResp.status).toBe(204);

    // Verify unsubscribed
    const finalResp: any = await getClient(user).get(subUrl);
    expect(finalResp.data.subscribed).toBe(false);
  });

  test("AC4: @mentioned user is auto-subscribed to the comment thread", async ({
    workspacePage,
  }) => {
    const { user: owner, workspace } = workspacePage;
    const database = await createDatabase(owner, "Mention Subscribe DB", workspace);
    const table = await createTable(owner, "My Table", database);
    const row = await createRow(owner, table, {});

    const mentionee = await createUser();
    await addUserToWorkspace(owner, workspace.id, mentionee.email, mentionee);

    const mentioneeId = await getUserId(mentionee);

    const mentionMsg = {
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [{ type: "mention", attrs: { id: mentioneeId } }],
        },
      ],
    };

    const subUrl = `database/rows/table/${table.id}/${row.id}/comments/subscriptions/`;

    // Mentionee not yet subscribed
    const beforeResp: any = await getClient(mentionee).get(subUrl);
    expect(beforeResp.data.subscribed).toBe(false);

    await createComment(owner, table.id, row.id, mentionMsg);

    // Mentionee auto-subscribed via @mention
    const afterResp: any = await getClient(mentionee).get(subUrl);
    expect(afterResp.data.subscribed).toBe(true);
  });

  test("AC1: subscribed user receives row_comment_created notification when another user comments", async ({
    workspacePage,
  }) => {
    const { user: owner, workspace } = workspacePage;
    const database = await createDatabase(owner, "Notification Test DB", workspace);
    const table = await createTable(owner, "My Table", database);
    const row = await createRow(owner, table, {});

    const subscriber = await createUser();
    await addUserToWorkspace(owner, workspace.id, subscriber.email, subscriber);

    // Subscriber manually subscribes before the comment is posted
    await getClient(subscriber).post(
      `database/rows/table/${table.id}/${row.id}/comments/subscriptions/`
    );

    // Owner posts a comment
    await createComment(owner, table.id, row.id);

    // Subscriber should have a row_comment_created notification in their workspace
    const notifResp: any = await getClient(subscriber).get(
      `notifications/${workspace.id}/`
    );
    const notifications = notifResp.data.results ?? notifResp.data;
    const hasCreatedNotif = notifications.some(
      (n: any) => n.type === "row_comment_created"
    );
    expect(hasCreatedNotif).toBe(true);

    // Owner (sender) should NOT receive row_comment_created for their own comment
    const ownerNotifResp: any = await getClient(owner).get(
      `notifications/${workspace.id}/`
    );
    const ownerNotifs = ownerNotifResp.data.results ?? ownerNotifResp.data;
    const ownerHasCreated = ownerNotifs.some(
      (n: any) => n.type === "row_comment_created"
    );
    expect(ownerHasCreated).toBe(false);
  });
});
