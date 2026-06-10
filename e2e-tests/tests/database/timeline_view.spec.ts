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
  createTimelineView,
  createViewFilter,
  updateFieldOptions,
  updateView,
} from "../../fixtures/database/view";

// NOTE (clean-room / Bucket A): the free Timeline view lives in core and is only
// the registered "timeline" view type in an OSS-only build. In an open-core
// build that also ships the premium plugin, premium's Timeline view registers
// later and overrides this one (last registration wins). This spec therefore
// asserts the core DOM (`.timeline-view__*`) and MUST run against the OSS-only
// e2e stack (BASEROW_OSS_ONLY=true). It is authored but is NOT run locally — it
// is wired to run in the dedicated OSS-only CI lane (same lane as the Calendar
// spec). [Source: story 3.6 Task 8; calendar_view.spec.ts header note]

/**
 * Day key in the user's local day, formatted `YYYY-MM-DD`, offset by `days`.
 * The timeline axis centres on the scheduled rows (and falls back to a window
 * around today when none are scheduled), so seeding rows relative to today
 * keeps the bars inside the visible axis deterministically.
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
 * Builds an Events table with a "Start" and "End" date field plus a Timeline
 * view already positioned by both. Returns everything the timeline spec needs to
 * navigate and seed.
 */
async function setupTimeline(
  workspacePage: any,
  timescale: string | null = null,
) {
  const database = await createDatabase(
    workspacePage.user,
    "timelineViewTestDb",
    workspacePage.workspace,
  );
  const table = await createTable(workspacePage.user, "Events", database);
  await deleteAllNonPrimaryFieldsFromTable(workspacePage.user, table);

  // The date fields that position the left/right edge of each bar.
  const startField = await createField(
    workspacePage.user,
    "Start",
    "date",
    {},
    table,
  );
  const endField = await createField(
    workspacePage.user,
    "End",
    "date",
    {},
    table,
  );

  const view = await createTimelineView(
    workspacePage.user,
    "Timeline",
    startField.id,
    endField.id,
    table,
    timescale,
  );

  return { database, table, startField, endField, view };
}

test.describe("Timeline view", () => {
  test.beforeEach(async ({ workspacePage }) => {
    await workspacePage.goto();
  });

  test("renders a bar only for rows with BOTH dates, sends the rest to the tray, and persists the config on reload (AC #1, #2)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, view } = await setupTimeline(workspacePage);

    // A fully-scheduled row (both dates) renders as a bar; a row missing the end
    // date and a row missing both dates land in the unscheduled tray (AC #2).
    await createRow(workspacePage.user, table, {
      Start: dayKey(0),
      End: dayKey(2),
    });
    await createRow(workspacePage.user, table, {
      Start: dayKey(0),
      End: null,
    });
    await createRow(workspacePage.user, table, { Start: null, End: null });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // The axis renders (both date fields are configured, so no empty state).
    await expect(page.locator(".timeline-view__axis")).toHaveCount(1);

    // Exactly one row is scheduled → exactly one bar.
    await expect(page.locator(".timeline-view__bar")).toHaveCount(1);

    // The two rows missing a date sit in the unscheduled tray; the counter
    // reflects exactly two unscheduled rows.
    await expect(page.locator(".timeline-view__unscheduled")).toBeVisible();
    await expect(page.locator(".timeline-view__unscheduled-count")).toHaveText(
      "2",
    );

    // Reload — the date-field configuration persists server-side, so the same
    // partition (one bar, two tray cards) renders again (AC #1).
    await tablePage.goto();
    await expect(page.locator(".timeline-view__bar")).toHaveCount(1);
    await expect(page.locator(".timeline-view__unscheduled-count")).toHaveText(
      "2",
    );

    // Clearing the start date field drops the view back to the empty state
    // prompting the user to pick the positioning fields (AC #1 config round-trip).
    await updateView(workspacePage.user, view, { start_date_field: null });
    await tablePage.goto();
    await expect(page.locator(".timeline-view__empty")).toBeVisible();
    await expect(page.locator(".timeline-view__axis")).toHaveCount(0);
  });

  test("switches the zoom level from the header and persists it on reload (AC #3)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, view } = await setupTimeline(workspacePage);

    // A row spanning a few days so the axis has meaningful ticks at any zoom.
    await createRow(workspacePage.user, table, {
      Start: dayKey(0),
      End: dayKey(3),
    });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // The default zoom is month: a multi-day span fits inside a single month
    // tick, so the axis carries exactly one tick.
    await expect(page.locator(".timeline-view__tick")).toHaveCount(1);

    // Switch to the day zoom via the header RadioGroup button labelled "Day".
    await page
      .locator(".radio-group__radio-button", { hasText: "Day" })
      .click();

    // The day zoom expands the axis to one tick per day across the span
    // (start..end inclusive → 4 day ticks).
    await expect(page.locator(".timeline-view__tick")).toHaveCount(4);

    // Reload — the persisted `timescale` column means the day zoom survives the
    // round-trip (AC #3): the axis still renders the 4 day ticks.
    await tablePage.goto();
    await expect(page.locator(".timeline-view__tick")).toHaveCount(4);

    // view is referenced to keep its id in scope for clarity.
    expect(view.id).toBeTruthy();
  });

  test("positions a longer span as a wider bar than a single-unit span (AC #2)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, view } = await setupTimeline(workspacePage, "day");

    // A 1-day span and a 4-day span; under the day zoom the 4-day bar is
    // visibly wider than the 1-day bar.
    await createRow(workspacePage.user, table, {
      Start: dayKey(0),
      End: dayKey(0),
    });
    await createRow(workspacePage.user, table, {
      Start: dayKey(0),
      End: dayKey(3),
    });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    await expect(page.locator(".timeline-view__bar")).toHaveCount(2);

    const widths = await page
      .locator(".timeline-view__bar")
      .evaluateAll((els) =>
        els.map((el) => (el as HTMLElement).getBoundingClientRect().width),
      );
    const [w1, w2] = widths.sort((a, b) => a - b);
    // The wider (4-day) bar spans more than the narrow (1-day) bar.
    expect(w2).toBeGreaterThan(w1);

    expect(view.id).toBeTruthy();
  });

  test("applies existing view filters to the rows shown on the timeline (AC #1 honors filters)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, startField, view } =
      await setupTimeline(workspacePage);

    // Two fully-scheduled rows; one is given a distinct primary value so a
    // filter can single it out. The timeline routes through the standard view
    // row pipeline, so the view filter applies to what it shows.
    await createRow(workspacePage.user, table, {
      Name: "keep",
      Start: dayKey(0),
      End: dayKey(1),
    });
    await createRow(workspacePage.user, table, {
      Name: "drop",
      Start: dayKey(0),
      End: dayKey(1),
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

    // Only the single "keep" row survives the filter — one bar on the axis, the
    // "drop" row is filtered out before it reaches the timeline.
    await expect(page.locator(".timeline-view__bar")).toHaveCount(1);

    // startField is referenced to keep its id in scope for clarity.
    expect(startField.id).toBeTruthy();
  });

  test("honors card-face field visibility yet keeps a hidden start-date field driving the bar (AC #5)", async ({
    page,
    goto,
    workspacePage,
  }) => {
    const { database, table, startField, view } =
      await setupTimeline(workspacePage);

    // The primary "Name" field is a plain card-face field; the "Start" field
    // both shows on the card AND positions the bar. Hide BOTH card faces.
    // - Name (non-date): its value must disappear from the bar card.
    // - Start (date): its card face must disappear too, but — per the AC #5
    //   data-dependency guard (get_hidden_fields keeps the date fields' values
    //   serialized even when their option is hidden) — the bar must still
    //   render because the start date keeps driving the layout. "End" stays
    //   visible as the control that proves the card still renders its fields.
    const fields = await getFieldsForTable(workspacePage.user, table);
    const nameField = fields.find((f) => f.primary);
    await updateFieldOptions(workspacePage.user, view, {
      [nameField.id]: { hidden: true },
      [startField.id]: { hidden: true },
    });

    // A fully-dated row so there is exactly one bar to inspect.
    await createRow(workspacePage.user, table, {
      Name: "hidden-name",
      Start: dayKey(0),
      End: dayKey(2),
    });

    const tablePage = new TablePage({ page, goto });
    tablePage.pageUrl = `database/${database.id}/table/${table.id}/${view.id}`;
    await tablePage.goto();

    // The bar still renders even though the start-date card face is hidden —
    // the date value is still serialized to the client and positions the bar
    // (AC #5 data-dependency guard).
    await expect(page.locator(".timeline-view__bar")).toHaveCount(1);

    const barCard = page.locator(".timeline-view__bar .card__field-name");

    // The hidden "Name" and "Start" card faces are absent from the bar card
    // (field visibility honored), while the still-visible "End" field remains.
    await expect(barCard.filter({ hasText: "End" })).toHaveCount(1);
    await expect(barCard.filter({ hasText: "Name" })).toHaveCount(0);
    await expect(barCard.filter({ hasText: "Start" })).toHaveCount(0);
  });
});
