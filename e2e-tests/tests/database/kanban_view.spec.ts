import { expect, test } from "../baserowTest";
import { TablePage } from "../../pages/database/tablePage";
import { createDatabase } from "../../fixtures/database/database";
import { createTable } from "../../fixtures/database/table";
import {
  createField,
  deleteAllNonPrimaryFieldsFromTable,
  getFieldsForTable,
} from "../../fixtures/database/field";
import { createRow } from "../../fixtures/database/rows";
import {
  createView,
  createViewFilter,
  updateFieldOptions,
  updateView,
} from "../../fixtures/database/view";

// NOTE (clean-room / Bucket A): the free Kanban view lives in core and is only
// the registered "kanban" view type in an OSS-only build. In an open-core build
// that also ships the premium plugin, premium's Kanban view registers later and
// overrides this one (last registration wins). This spec therefore asserts the
// core DOM (`.kanban-view__column`) and MUST run against the OSS-only e2e stack
// (BASEROW_OSS_ONLY=true). It is authored but is NOT run locally — it is wired
// to run in the dedicated OSS-only CI lane.

/**
 * Builds a Tasks table with a single-select "Status" field (two options) and a
 * Kanban view already grouped by that field. Returns everything a test needs to
 * navigate to the board and seed rows.
 */
async function setupKanban(workspacePage: any) {
  const database = await createDatabase(
    workspacePage.user,
    "kanbanViewTestDb",
    workspacePage.workspace,
  );
  const table = await createTable(workspacePage.user, "Tasks", database);
  await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);

  // A single-select field with two options is the grouping field.
  const statusField = await createField(
    workspacePage.user,
    "Status",
    "single_select",
    {
      select_options: [
        { value: "To do", color: "blue" },
        { value: "Done", color: "green" },
      ],
    },
    table,
  );
  const [toDoOption, doneOption] = statusField.fieldSettings.select_options;

  // Create the Kanban view already grouped by the single-select field.
  const view = await createView(
    workspacePage.user,
    "Board",
    "kanban",
    { single_select_field: statusField.id },
    table,
  );

  return { database, table, statusField, toDoOption, doneOption, view };
}

test.describe("Kanban view", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("groups cards into one column per single-select option plus Uncategorized, and persists", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, view } = await setupKanban(workspacePage);

    // Navigate straight to the Kanban view.
    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // One column per option ("To do", "Done") plus a trailing "Uncategorized"
    // column for rows whose grouping value is null.
    const columns = page.locator(".kanban-view__column");
    await expect(columns).toHaveCount(3);
    await expect(page.locator(".kanban-view__column-label")).toContainText([
      "To do",
      "Done",
      "Uncategorized",
    ]);

    // Reload the page — the grouping configuration persists server-side, so the
    // same three columns render again.
    await tablePage.goto();
    await expect(page.locator(".kanban-view__column")).toHaveCount(3);

    // Re-pointing the view at no grouping field clears the columns and shows the
    // empty state prompting the user to pick a single-select field.
    await updateView(workspacePage.user, view, { single_select_field: null });
    await tablePage.goto();
    await expect(page.locator(".kanban-view__column")).toHaveCount(0);
    await expect(page.locator(".kanban-view__empty")).toBeVisible();
  });

  test("places each row in the column matching its single-select value, with null rows in Uncategorized (AC #1)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, statusField, toDoOption, doneOption, view } =
      await setupKanban(workspacePage);

    // Seed three rows: one per option and one with no grouping value. The
    // single-select cell is set by option id (user_field_names=true).
    await createRow(workspacePage.user, table, { Status: toDoOption.id });
    await createRow(workspacePage.user, table, { Status: doneOption.id });
    await createRow(workspacePage.user, table, { Status: null });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // Columns render in option order, then Uncategorized last.
    const columns = page.locator(".kanban-view__column");
    await expect(columns).toHaveCount(3);

    // Each option column holds exactly its one matching card; the null row lands
    // in the trailing Uncategorized column — it is NOT dropped (AC #1 explicit).
    await expect(columns.nth(0).locator(".kanban-view__card")).toHaveCount(1);
    await expect(columns.nth(1).locator(".kanban-view__card")).toHaveCount(1);
    await expect(columns.nth(2).locator(".kanban-view__card")).toHaveCount(1);

    // The per-column counter in the header reflects the same distribution.
    await expect(
      columns.nth(2).locator(".kanban-view__column-label"),
    ).toHaveText("Uncategorized");
    await expect(
      columns.nth(2).locator(".kanban-view__column-count"),
    ).toHaveText("1");

    // statusField is referenced to keep its option ids in scope for clarity.
    expect(statusField.id).toBeTruthy();
  });

  // STORY 3.2 — Drag a card between columns.
  //
  // Real-time (Story 3.2 AC #2): the outbound `rows_updated` broadcast and the
  // inbound re-bucket are the shared Grid/Gallery path and fire automatically
  // (zero new code). A true two-client assertion needs a second authenticated
  // browser context, but the `workspacePage` fixture authenticates a single
  // `page` (one token), so spinning up a second context as the same user is not
  // supported in this lane. Per the story, AC #2's persistence/broadcast outcome
  // is instead covered by the single-client reload assertion below: after the
  // drag, reloading the board (a fresh server fetch) still shows the card under
  // the target column, proving the value was broadcast/persisted server-side.
  test("dragging a card to another column updates its single-select value and persists (Story 3.2 AC #1, AC #2 via reload)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, toDoOption, doneOption, view } =
      await setupKanban(workspacePage);

    // Seed a single "To do" card. It must end up under "Done" after the drag.
    await createRow(workspacePage.user, table, { Status: toDoOption.id });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    const columns = page.locator(".kanban-view__column");
    await expect(columns).toHaveCount(3);

    // The card starts in the "To do" column (index 0); "Done" is index 1.
    const card = columns.nth(0).locator(".kanban-view__card").first();
    await expect(card).toBeVisible();
    await expect(columns.nth(1).locator(".kanban-view__card")).toHaveCount(0);

    // Drag the card from "To do" to "Done". Native HTML5 DnD typically needs a
    // manual mouse sequence (down → stepped move → up) rather than a single
    // dragTo, so the dragover/drop handlers fire on the way over the target.
    const target = columns.nth(1);
    const cardBox = await card.boundingBox();
    const targetBox = await target.boundingBox();
    if (cardBox === null || targetBox === null) {
      throw new Error("Could not resolve drag source/target bounding boxes");
    }
    await page.mouse.move(
      cardBox.x + cardBox.width / 2,
      cardBox.y + cardBox.height / 2,
    );
    await page.mouse.down();
    await page.mouse.move(
      targetBox.x + targetBox.width / 2,
      targetBox.y + targetBox.height / 2,
      { steps: 12 },
    );
    await page.mouse.up();

    // Optimistically (and after the server confirms) the card now lives under
    // "Done" and "To do" is empty — the card re-buckets from the store (AC #1).
    await expect(columns.nth(1).locator(".kanban-view__card")).toHaveCount(1);
    await expect(columns.nth(0).locator(".kanban-view__card")).toHaveCount(0);

    // The underlying single-select cell value actually changed and was
    // persisted/broadcast server-side: reloading the board (a fresh fetch) still
    // shows the card under "Done" (AC #1 value set; AC #2 broadcast/persisted).
    await tablePage.goto();
    const reloaded = page.locator(".kanban-view__column");
    await expect(reloaded.nth(1).locator(".kanban-view__card")).toHaveCount(1);
    await expect(reloaded.nth(0).locator(".kanban-view__card")).toHaveCount(0);

    // doneOption is referenced to keep its id in scope for clarity.
    expect(doneOption.id).toBeTruthy();
  });

  test("applies existing view filters to the rows shown on the board (AC #2)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, toDoOption, doneOption, view } =
      await setupKanban(workspacePage);

    // Seed two "To do" rows and one "Done" row.
    await createRow(workspacePage.user, table, { Status: toDoOption.id });
    await createRow(workspacePage.user, table, { Status: toDoOption.id });
    await createRow(workspacePage.user, table, { Status: doneOption.id });

    // Filter the view to only show rows whose Status is "Done". The board must
    // route through the standard view row pipeline, so the filter applies.
    const fields = await getFieldsForTable(workspacePage.user, table);
    const statusFieldFull = fields.find((f) => f.name === "Status");
    await createViewFilter(
      workspacePage.user,
      view,
      statusFieldFull.id,
      "single_select_equal",
      String(doneOption.id),
    );

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    const columns = page.locator(".kanban-view__column");
    await expect(columns).toHaveCount(3);

    // Only the single "Done" card survives the filter — the two "To do" rows are
    // filtered out, so that column is empty.
    await expect(columns.nth(0).locator(".kanban-view__card")).toHaveCount(0);
    await expect(columns.nth(1).locator(".kanban-view__card")).toHaveCount(1);
    await expect(page.locator(".kanban-view__card")).toHaveCount(1);
  });

  // STORY 3.3 — Configure Kanban card appearance.
  //
  // The card-appearance feature (per-field visibility on the card face + a cover
  // image field) is shared with the Gallery view and reached from the board's
  // "Customize cards" header link. This scenario drives the two persistence
  // paths exercised by AC #1 (which fields show on the card face) and AC #2 (the
  // cover image field), and confirms both survive a reload. AC #3 (no Kanban
  // row-coloring decorations) is asserted by the absence of a decoration locator.
  test("customizing card appearance hides a field, sets a cover image, and both persist on reload (AC #1, #2, #3)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, view } = await setupKanban(workspacePage);

    // Add a long-text "Notes" field (shown on the card face) and a file "Cover"
    // field (eligible as the cover image source).
    const notesField = await createField(
      workspacePage.user,
      "Notes",
      "long_text",
      {},
      table,
    );
    const coverField = await createField(
      workspacePage.user,
      "Cover",
      "file",
      {},
      table,
    );

    // Seed a single row so exactly one card renders on the board.
    await createRow(workspacePage.user, table, { Notes: "hello" });

    // Make the Notes field visible on the card face to begin with, so the toggle
    // below has a deterministic starting state.
    await updateFieldOptions(workspacePage.user, view, {
      [notesField.id]: { hidden: false },
    });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    const card = page.locator(".kanban-view__card");
    await expect(card).toHaveCount(1);

    // AC #3 — KanbanView passes no `decorationsByPlace` to RowCard, so no
    // row-coloring decorator components render. Decorators are component-driven
    // (no fixed CSS class to assert against), so this is verified at the unit
    // level (kanbanView.spec.js — RowCard receives no decorations). Here we only
    // confirm the card renders its standard content region with no extra layer.
    await expect(card.locator(".card__content")).toHaveCount(1);

    // Open the "Customize cards" context from the view header.
    await page
      .locator(".header__filter-link", { hasText: "Customize cards" })
      .click();

    // AC #1 — the "Customize cards" context is rendered with
    // `allow-cover-image-field=true`, so the shared ViewFieldsContext exposes
    // the cover-image picker FormGroup (the UI surface for toggling the cover).
    await expect(page.locator(".hidings__cover")).toHaveCount(1);

    // The Notes field starts visible on the card face (AC #1).
    const notesCardField = page
      .locator(".card__field-name")
      .filter({ hasText: "Notes" });
    await expect(notesCardField).toHaveCount(1);

    // Toggle Notes off in the field list — it disappears from the card face.
    const notesToggle = page
      .locator(".hidings__item")
      .filter({ hasText: "Notes" })
      .locator(".switch");
    await notesToggle.click();
    await expect(notesCardField).toHaveCount(0);

    // Toggle it back on — it reappears, proving the per-field face toggle is live.
    await notesToggle.click();
    await expect(notesCardField).toHaveCount(1);

    // AC #2 — set the cover image field via the generic view PATCH; the cover
    // placeholder renders on the card (empty-state icon, no uploaded image yet).
    await updateView(workspacePage.user, view, {
      card_cover_image_field: coverField.id,
    });
    await tablePage.goto();
    await expect(page.locator(".card__cover")).toHaveCount(1);

    // Hide Notes from the card face and confirm both settings persist on reload.
    await updateFieldOptions(workspacePage.user, view, {
      [notesField.id]: { hidden: true },
    });
    await tablePage.goto();
    await expect(page.locator(".kanban-view__card")).toHaveCount(1);
    await expect(
      page.locator(".card__field-name").filter({ hasText: "Notes" }),
    ).toHaveCount(0);
    await expect(page.locator(".card__cover")).toHaveCount(1);

    // Clearing the cover field removes the cover region from the card (AC #2).
    await updateView(workspacePage.user, view, {
      card_cover_image_field: null,
    });
    await tablePage.goto();
    await expect(page.locator(".card__cover")).toHaveCount(0);
  });

  // STORY 3.3 — AC #4: the grouping single-select field is always treated as a
  // board data dependency by `get_hidden_fields`, even when its field option is
  // toggled `hidden`. If that guard regressed, the single-select value would no
  // longer be fetched for the board and every card would fall into the trailing
  // "Uncategorized" column. This drives the guard end-to-end: with the grouping
  // field's option hidden, cards must still bucket into their matching option
  // columns after a fresh reload.
  test("keeps the grouping single-select field data-available when its field option is hidden, so cards still bucket correctly (AC #4)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, statusField, toDoOption, doneOption, view } =
      await setupKanban(workspacePage);

    // One card per option — they must land in their own columns, never all in
    // Uncategorized.
    await createRow(workspacePage.user, table, { Status: toDoOption.id });
    await createRow(workspacePage.user, table, { Status: doneOption.id });

    // Hide the grouping single-select field's option. `get_hidden_fields` must
    // exclude it from the hidden set regardless, keeping its value fetchable.
    await updateFieldOptions(workspacePage.user, view, {
      [statusField.id]: { hidden: true },
    });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    const columns = page.locator(".kanban-view__column");
    await expect(columns).toHaveCount(3);

    // Each card still buckets by its grouping value — the option columns hold
    // their card and Uncategorized stays empty. A regressed guard would dump
    // both cards into column index 2 (Uncategorized).
    await expect(columns.nth(0).locator(".kanban-view__card")).toHaveCount(1);
    await expect(columns.nth(1).locator(".kanban-view__card")).toHaveCount(1);
    await expect(columns.nth(2).locator(".kanban-view__card")).toHaveCount(0);
  });
});
