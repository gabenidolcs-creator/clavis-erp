import { expect, test } from "../baserowTest";
import { TablePage } from "../../pages/database/tablePage";
import { createDatabase } from "../../fixtures/database/database";
import { createTable } from "../../fixtures/database/table";
import {
  createField,
  deleteAllNonPrimaryFieldsFromTable,
  getFieldsForTable,
} from "../../fixtures/database/field";
import { createRow, listRows } from "../../fixtures/database/rows";
import {
  createCalendarView,
  createViewFilter,
  updateView,
} from "../../fixtures/database/view";

// NOTE (clean-room / Bucket A): the free Calendar view lives in core and is only
// the registered "calendar" view type in an OSS-only build. In an open-core
// build that also ships the premium plugin, premium's Calendar view registers
// later and overrides this one (last registration wins). This spec therefore
// asserts the core DOM (`.calendar-view__*`) and MUST run against the OSS-only
// e2e stack (BASEROW_OSS_ONLY=true). It is authored but is NOT run locally — it
// is wired to run in the dedicated OSS-only CI lane (same lane as the Kanban
// spec). [Source: story 3.4 Task 8; kanban_view.spec.ts header note]

/**
 * Day key in the user's local day, formatted `YYYY-MM-DD`, offset by `days`.
 * The calendar grid centres on "today" (CalendarView.referenceDate defaults to
 * today in the user's timezone), so seeding rows relative to today guarantees
 * they fall inside the visible month/week grid deterministically.
 */
function dayKey(offsetDays = 0): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/**
 * Builds an Events table with a "Date" field (and an optional "End" date field
 * when `withEndDate` is set) plus a Calendar view already positioned by the
 * Date field. Returns everything the calendar spec needs to navigate and seed.
 */
async function setupCalendar(workspacePage: any, withEndDate = false) {
  const database = await createDatabase(
    workspacePage.user,
    "calendarViewTestDb",
    workspacePage.workspace,
  );
  const table = await createTable(workspacePage.user, "Events", database);
  await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);

  // The date field that positions a row on the grid.
  const dateField = await createField(
    workspacePage.user,
    "Date",
    "date",
    {},
    table,
  );

  // Optional end-date field, used by the multi-day-span scenario (AC #4).
  let endDateField = null;
  if (withEndDate) {
    endDateField = await createField(
      workspacePage.user,
      "End",
      "date",
      {},
      table,
    );
  }

  const view = await createCalendarView(
    workspacePage.user,
    "Calendar",
    dateField.id,
    table,
    endDateField ? endDateField.id : null,
  );

  return { database, table, dateField, endDateField, view };
}

test.describe("Calendar view", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("places dated rows on the grid, null rows in the unscheduled tray, and persists the config on reload (AC #1, #2)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, view } = await setupCalendar(workspacePage);

    // One row dated today (lands on the grid) and one with no date (lands in the
    // unscheduled tray — it is NOT dropped, AC #2 explicit).
    await createRow(workspacePage.user, table, { Date: dayKey(0) });
    await createRow(workspacePage.user, table, { Date: null });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // The grid renders (a date field is configured, so no empty state).
    await expect(page.locator(".calendar-view__grid")).toHaveCount(1);

    // The dated row renders as a card on a day cell.
    await expect(
      page.locator(".calendar-view__day-cards .calendar-view__card"),
    ).toHaveCount(1);

    // The null-date row sits in the unscheduled tray, and the tray counter
    // reflects exactly one unscheduled row.
    await expect(page.locator(".calendar-view__unscheduled")).toBeVisible();
    await expect(page.locator(".calendar-view__unscheduled-count")).toHaveText(
      "1",
    );
    await expect(
      page.locator(".calendar-view__unscheduled-cards .calendar-view__card"),
    ).toHaveCount(1);

    // Reload — the date-field configuration persists server-side, so the same
    // partition (one card on the grid, one in the tray) renders again (AC #1).
    await tablePage.goto();
    await expect(
      page.locator(".calendar-view__day-cards .calendar-view__card"),
    ).toHaveCount(1);
    await expect(page.locator(".calendar-view__unscheduled-count")).toHaveText(
      "1",
    );

    // Clearing the positioning date field drops the grid back to the empty
    // state prompting the user to pick a date field (AC #1 config round-trip).
    await updateView(workspacePage.user, view, { date_field: null });
    await tablePage.goto();
    await expect(page.locator(".calendar-view__empty")).toBeVisible();
    await expect(page.locator(".calendar-view__grid")).toHaveCount(0);
  });

  test("switches between month and week display modes from the header (AC #3)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, view } = await setupCalendar(workspacePage);

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // Default display mode is month: the grid carries the month modifier and
    // lays out the full monthly grid (more than one week of day cells).
    await expect(page.locator(".calendar-view__grid--month")).toHaveCount(1);
    const monthDays = await page.locator(".calendar-view__day").count();
    expect(monthDays).toBeGreaterThan(7);

    // Toggle to week mode via the header RadioGroup button labelled "Week".
    await page
      .locator(".radio-group__radio-button", { hasText: "Week" })
      .click();

    // The grid swaps to the week modifier and renders exactly the 7 ISO-week
    // day cells.
    await expect(page.locator(".calendar-view__grid--week")).toHaveCount(1);
    await expect(page.locator(".calendar-view__day")).toHaveCount(7);

    // Toggle back to month restores the full monthly grid.
    await page
      .locator(".radio-group__radio-button", { hasText: "Month" })
      .click();
    await expect(page.locator(".calendar-view__grid--month")).toHaveCount(1);
  });

  test("spans an entry across multiple day cells when an end-date field is configured (AC #4)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, view } = await setupCalendar(workspacePage, true);

    // A single row that starts today and ends two days later occupies three
    // consecutive day cells (start..end inclusive), so its card renders once per
    // day in the span — three card instances on the grid.
    await createRow(workspacePage.user, table, {
      Date: dayKey(0),
      End: dayKey(2),
    });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // The multi-day entry appears on each of its three days (AC #4 continuous
    // span). A single-date entry (no end date) would render exactly once.
    await expect(
      page.locator(".calendar-view__day-cards .calendar-view__card"),
    ).toHaveCount(3);

    // view is referenced to keep its id in scope for clarity.
    expect(view.id).toBeTruthy();
  });

  test("applies existing view filters to the rows shown on the calendar (AC #1 honors filters)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, dateField, view } =
      await setupCalendar(workspacePage);

    // Two rows dated today; one is given a distinct primary value so a filter
    // can single it out. The calendar must route through the standard view row
    // pipeline, so the view filter applies to what the grid shows.
    await createRow(workspacePage.user, table, {
      Name: "keep",
      Date: dayKey(0),
    });
    await createRow(workspacePage.user, table, {
      Name: "drop",
      Date: dayKey(0),
    });

    // Filter the view to only rows whose primary "Name" equals "keep".
    const fields = await getFieldsForTable(workspacePage.user, table);
    const nameField = fields.find((f) => f.primary);
    await createViewFilter(
      workspacePage.user,
      view,
      nameField.id,
      "equal",
      "keep",
    );

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // Only the single "keep" row survives the filter — one card on the grid,
    // the "drop" row is filtered out before it reaches the calendar.
    await expect(
      page.locator(".calendar-view__day-cards .calendar-view__card"),
    ).toHaveCount(1);

    // dateField is referenced to keep its id in scope for clarity.
    expect(dateField.id).toBeTruthy();
  });

  test("dragging a calendar card to another day reschedules its date field and persists (Story 3.5 AC #1, AC #2 via reload)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, dateField, view } =
      await setupCalendar(workspacePage);

    // A single row dated today — it renders as one card on today's day cell.
    await createRow(workspacePage.user, table, { Date: dayKey(0) });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // The card is on today's cell; the grid holds exactly one card.
    await expect(
      page.locator(".calendar-view__day-cards .calendar-view__card"),
    ).toHaveCount(1);

    const card = page
      .locator(".calendar-view__day-cards .calendar-view__card")
      .first();
    await expect(card).toBeVisible();

    // Pick a deterministic drop target: an in-period day cell that is NOT today
    // (so the drop is a real move, never the no-op self-drop). Because the cell
    // is in the current period it shares today's month/year, so its day-number
    // label fully determines the expected `YYYY-MM-DD` value.
    const target = page
      .locator(
        ".calendar-view__day:not(.calendar-view__day--today):not(.calendar-view__day--outside)",
      )
      .first();
    const targetDayNumber = (
      await target.locator(".calendar-view__day-number").innerText()
    ).trim();
    const now = new Date();
    const expectedDate = `${now.getFullYear()}-${String(
      now.getMonth() + 1,
    ).padStart(2, "0")}-${targetDayNumber.padStart(2, "0")}`;

    // Native HTML5 DnD needs a manual mouse sequence (down → stepped move → up)
    // so the dragover/drop handlers fire on the way over the target cell.
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

    // The card re-buckets from the store: still exactly one card on the grid,
    // now under the target day (AC #1).
    await expect(
      page.locator(".calendar-view__day-cards .calendar-view__card"),
    ).toHaveCount(1);
    await expect(target.locator(".calendar-view__card")).toHaveCount(1);

    // The underlying date cell actually changed server-side: a fresh row read
    // returns the target day, not today (AC #1 value set; AC #2 persisted via
    // the reused row-update/broadcast path).
    const rows = await listRows(workspacePage.user, table);
    expect(rows).toHaveLength(1);
    expect(rows[0][`field_${dateField.id}`]).toBe(expectedDate);

    // Reloading the calendar (a fresh server fetch) still shows the single card
    // under the target day, confirming persistence/broadcast (AC #2).
    await tablePage.goto();
    await expect(
      page.locator(".calendar-view__day-cards .calendar-view__card"),
    ).toHaveCount(1);
  });

  test("dragging a scheduled card to the unscheduled tray clears its date field (Story 3.5 AC #5)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, dateField, view } =
      await setupCalendar(workspacePage);

    // Two rows: one dated today (renders on the grid, the drag source) and one
    // already unscheduled (so the unscheduled tray is present as a drop target).
    await createRow(workspacePage.user, table, { Date: dayKey(0) });
    await createRow(workspacePage.user, table, { Date: null });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    await expect(
      page.locator(".calendar-view__day-cards .calendar-view__card"),
    ).toHaveCount(1);
    await expect(page.locator(".calendar-view__unscheduled-count")).toHaveText(
      "1",
    );

    const card = page
      .locator(".calendar-view__day-cards .calendar-view__card")
      .first();
    const tray = page.locator(".calendar-view__unscheduled");

    const cardBox = await card.boundingBox();
    const trayBox = await tray.boundingBox();
    if (cardBox === null || trayBox === null) {
      throw new Error("Could not resolve drag source/target bounding boxes");
    }
    await page.mouse.move(
      cardBox.x + cardBox.width / 2,
      cardBox.y + cardBox.height / 2,
    );
    await page.mouse.down();
    await page.mouse.move(
      trayBox.x + trayBox.width / 2,
      trayBox.y + trayBox.height / 2,
      { steps: 12 },
    );
    await page.mouse.up();

    // The dragged card leaves the grid and joins the tray — now two unscheduled
    // rows, none on the grid (AC #5 clear → tray, reactive re-bucket).
    await expect(
      page.locator(".calendar-view__day-cards .calendar-view__card"),
    ).toHaveCount(0);
    await expect(page.locator(".calendar-view__unscheduled-count")).toHaveText(
      "2",
    );

    // The date cell was cleared to null server-side.
    const rows = await listRows(workspacePage.user, table);
    const cleared = rows.filter((r) => r[`field_${dateField.id}`] === null);
    expect(cleared).toHaveLength(2);

    // view is referenced to keep its id in scope for clarity.
    expect(view.id).toBeTruthy();
  });

  test("dragging an unscheduled card onto a day cell sets its date field (Story 3.5 AC #5 schedule direction)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, dateField, view } =
      await setupCalendar(workspacePage);

    // A single undated row — it starts life in the unscheduled tray, NOT on the
    // grid. Dragging it onto a day cell must schedule it (the mirror of the
    // clear-to-tray case above).
    await createRow(workspacePage.user, table, { Date: null });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // Precondition: the card sits in the tray, the grid is empty.
    await expect(page.locator(".calendar-view__unscheduled-count")).toHaveText(
      "1",
    );
    await expect(
      page.locator(".calendar-view__day-cards .calendar-view__card"),
    ).toHaveCount(0);

    const card = page
      .locator(".calendar-view__unscheduled-cards .calendar-view__card")
      .first();
    await expect(card).toBeVisible();

    // Same deterministic in-period, non-today target as the day→day scenario:
    // its day-number label fully determines the expected `YYYY-MM-DD`.
    const target = page
      .locator(
        ".calendar-view__day:not(.calendar-view__day--today):not(.calendar-view__day--outside)",
      )
      .first();
    const targetDayNumber = (
      await target.locator(".calendar-view__day-number").innerText()
    ).trim();
    const now = new Date();
    const expectedDate = `${now.getFullYear()}-${String(
      now.getMonth() + 1,
    ).padStart(2, "0")}-${targetDayNumber.padStart(2, "0")}`;

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

    // The card leaves the tray and lands under the target day (AC #5 schedule,
    // reactive re-bucket: tray empties, one card on the grid).
    await expect(page.locator(".calendar-view__unscheduled-count")).toHaveText(
      "0",
    );
    await expect(
      page.locator(".calendar-view__day-cards .calendar-view__card"),
    ).toHaveCount(1);
    await expect(target.locator(".calendar-view__card")).toHaveCount(1);

    // The date cell was set to the target day server-side.
    const rows = await listRows(workspacePage.user, table);
    expect(rows).toHaveLength(1);
    expect(rows[0][`field_${dateField.id}`]).toBe(expectedDate);
  });

  test("dropping a card on its own current day is a no-op (Story 3.5 AC #1)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, dateField, view } =
      await setupCalendar(workspacePage);

    // One row dated today — the drag source and the drop target are the same
    // cell, so the move must not fire a request and the value must not change.
    await createRow(workspacePage.user, table, { Date: dayKey(0) });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    const today = page.locator(".calendar-view__day--today").first();
    const card = today.locator(".calendar-view__card").first();
    await expect(card).toBeVisible();

    const cardBox = await card.boundingBox();
    const todayBox = await today.boundingBox();
    if (cardBox === null || todayBox === null) {
      throw new Error("Could not resolve drag source/target bounding boxes");
    }
    // Drag the card and drop it back on its own day cell.
    await page.mouse.move(
      cardBox.x + cardBox.width / 2,
      cardBox.y + cardBox.height / 2,
    );
    await page.mouse.down();
    await page.mouse.move(
      todayBox.x + todayBox.width / 2,
      todayBox.y + todayBox.height / 2,
      { steps: 8 },
    );
    await page.mouse.up();

    // The card stays put and the value is unchanged (no-op guard: no request,
    // no flicker).
    await expect(today.locator(".calendar-view__card")).toHaveCount(1);
    const rows = await listRows(workspacePage.user, table);
    expect(rows).toHaveLength(1);
    expect(rows[0][`field_${dateField.id}`]).toBe(dayKey(0));

    // view referenced to keep its id in scope for clarity.
    expect(view.id).toBeTruthy();
  });
});
