import { getClient } from "../../client";
import { Table } from "./table";
import { User } from "../user";

export class View {
  constructor(
    public id: number,
    public name: string,
    public type: string,
    public table: Table,
  ) {}
}

export async function createView(
  user: User,
  name: string,
  type: string,
  settings: any,
  table: Table,
): Promise<View> {
  const response: any = await getClient(user).post(
    `database/views/table/${table.id}/`,
    {
      name,
      type,
      ...settings,
    },
  );
  return new View(
    response.data.id,
    response.data.name,
    response.data.type,
    table,
  );
}

/**
 * Thin convenience wrapper that creates a core Calendar view already positioned
 * by the given date field (and, optionally, an end date field for multi-day
 * events). Mirrors the generic `createView` call the Kanban e2e helper makes,
 * keeping the calendar spec readable.
 */
export async function createCalendarView(
  user: User,
  name: string,
  dateFieldId: number | null,
  table: Table,
  endDateFieldId: number | null = null,
): Promise<View> {
  return createView(
    user,
    name,
    "calendar",
    { date_field: dateFieldId, end_date_field: endDateFieldId },
    table,
  );
}

export async function updateView(
  user: User,
  view: View,
  settings: any,
): Promise<any> {
  const response: any = await getClient(user).patch(
    `database/views/${view.id}/`,
    settings,
  );
  return response.data;
}

export async function updateFieldOptions(
  user: User,
  view: View,
  fieldOptions: any,
): Promise<any> {
  const response: any = await getClient(user).patch(
    `database/views/${view.id}/field_options/`,
    {
      field_options: fieldOptions,
    },
  );
  return response.data;
}

export async function createViewFilter(
  user: User,
  view: View,
  fieldId: number,
  type: string,
  value: string,
): Promise<any> {
  const response: any = await getClient(user).post(
    `database/views/${view.id}/filters/`,
    {
      field: fieldId,
      type,
      value,
    },
  );
  return response.data;
}
