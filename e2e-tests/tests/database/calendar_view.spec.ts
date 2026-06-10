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
});
