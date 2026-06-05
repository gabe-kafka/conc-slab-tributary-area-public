import { NextResponse } from "next/server";
import { getOptionalSession } from "@/auth";
import { query } from "@/lib/db";
import type { LayerMapping, ProcessResult, ViewMode } from "@/lib/types";

export const runtime = "nodejs";

interface FullProjectRow {
  id: string;
  name: string;
  dxf_blob_url: string;
  dxf_filename: string;
  dxf_size_bytes: string | number | null;
  source_units: string;
  layer_mapping: LayerMapping;
  result: ProcessResult;
  view_mode: ViewMode;
  updated_at: Date;
  created_at: Date;
}

async function requireUserId() {
  const session = await getOptionalSession();
  const userId = session?.user && (session.user as { id?: string }).id;
  return userId ?? null;
}

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const userId = await requireUserId();
  if (!userId) return new NextResponse("Unauthorized", { status: 401 });

  const { id } = await context.params;
  const rows = await query<FullProjectRow>(
    `SELECT id, name, dxf_blob_url, dxf_filename, dxf_size_bytes,
            source_units, layer_mapping, result, view_mode,
            updated_at, created_at
       FROM projects
      WHERE id = $1 AND user_id = $2`,
    [id, userId],
  );

  const row = rows[0];
  if (!row) return new NextResponse("Not found", { status: 404 });

  return NextResponse.json({
    id: row.id,
    name: row.name,
    dxf_blob_url: row.dxf_blob_url,
    dxf_filename: row.dxf_filename,
    dxf_size_bytes: row.dxf_size_bytes == null ? null : Number(row.dxf_size_bytes),
    source_units: row.source_units,
    layer_mapping: row.layer_mapping,
    result: row.result,
    view_mode: row.view_mode,
    updated_at:
      row.updated_at instanceof Date
        ? row.updated_at.toISOString()
        : String(row.updated_at),
  });
}

export async function DELETE(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const userId = await requireUserId();
  if (!userId) return new NextResponse("Unauthorized", { status: 401 });

  const { id } = await context.params;
  const rows = await query<{ id: string }>(
    `DELETE FROM projects WHERE id = $1 AND user_id = $2 RETURNING id`,
    [id, userId],
  );
  if (rows.length === 0) return new NextResponse("Not found", { status: 404 });
  return new NextResponse(null, { status: 204 });
}
