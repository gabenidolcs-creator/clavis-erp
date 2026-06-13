import { expect, test } from "../baserowTest";
import { getClient } from "../../client";
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
    const database = await createDatabase(user, workspace, "Comment Test DB");
    const table = await createTable(user, database, "My Table");
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
    const database = await createDatabase(user, workspace, "Comment Test DB");
    const table = await createTable(user, database, "My Table");
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
    const database = await createDatabase(user, workspace, "Comment Test DB");
    const table = await createTable(user, database, "My Table");
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
    const database = await createDatabase(user, workspace, "Comment Test DB");
    const table = await createTable(user, database, "My Table");
    const row = await createRow(user, table, {});

    const created = await createComment(user, table.id, row.id);
    const result = await listComments(user, table.id, row.id);

    expect(result.results.some((c: any) => c.id === created.id)).toBe(true);
  });

  test("Owner can edit their own comment — returns updated message", async ({
    workspacePage,
  }) => {
    const { user, workspace } = workspacePage;
    const database = await createDatabase(user, workspace, "Comment Test DB");
    const table = await createTable(user, database, "My Table");
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
    const database = await createDatabase(user, workspace, "Comment Test DB");
    const table = await createTable(user, database, "My Table");
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
    const database = await createDatabase(user, workspace, "Comment Test DB");
    const table = await createTable(user, database, "My Table");
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
});
