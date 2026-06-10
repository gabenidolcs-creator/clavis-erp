import { getClient } from "../../client";
import { faker } from "@faker-js/faker";
import { Database } from "./database";
import { User } from "../user";

export class Table {
  constructor(
    public id: number,
    public name: string,
    public database: Database
  ) {}
}

export async function updateRows(
  user: User,
  table: Table,
  rowValues: any
): Promise<void> {
  await getClient(user).patch(
    `database/rows/table/${table.id}/batch/?user_field_names=true`,
    { items: rowValues }
  );
}

export async function createRow(
  user: User,
  table: Table,
  rowValues: any = {}
): Promise<any> {
  const response: any = await getClient(user).post(
    `database/rows/table/${table.id}/?user_field_names=true`,
    rowValues
  );
  return response.data;
}

export async function listRows(user: User, table: Table): Promise<any[]> {
  const response: any = await getClient(user).get(
    `database/rows/table/${table.id}/?user_field_names=true`
  );
  return response.data.results;
}

export async function deleteRow(
  user: User,
  table: Table,
  rowId: number
): Promise<void> {
  await getClient(user).delete(`database/rows/table/${table.id}/${rowId}/`);
}
