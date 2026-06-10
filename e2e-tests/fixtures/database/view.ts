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
