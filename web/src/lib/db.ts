import { Pool } from "@neondatabase/serverless";

const databaseUrl = process.env.DATABASE_URL;

export const hasDatabase = Boolean(databaseUrl);

export const pool = databaseUrl
  ? new Pool({ connectionString: databaseUrl })
  : undefined;

export async function query<T = Record<string, unknown>>(
  text: string,
  params: unknown[] = [],
): Promise<T[]> {
  if (!pool) throw new Error("DATABASE_URL is not configured");
  const result = await pool.query(text, params);
  return result.rows as T[];
}
