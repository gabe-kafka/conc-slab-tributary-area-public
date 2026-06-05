import { NextResponse } from "next/server";
import { getOptionalSession } from "@/auth";
import { query } from "@/lib/db";
import type { LayerMapping, ProcessResult, ViewMode } from "@/lib/types";

export const runtime = "nodejs";

interface ProjectRow {
  id: string;
  name: string;
  dxf_filename: string;
  dxf_size_bytes: string | number | null;
  updated_at: Date;
  created_at: Date;
}

export async function GET() {
  const session = await getOptionalSession();
  const userId = session?.user && (session.user as { id?: string }).id;
  if (!userId) return new NextResponse("Unauthorized", { status: 401 });

  const rows = await query<ProjectRow>(
    `SELECT id, name, dxf_filename, dxf_size_bytes, updated_at, created_at
       FROM projects
      WHERE user_id = $1
      ORDER BY updated_at DESC`,
    [userId],
  );

  return NextResponse.json({
    projects: rows.map((r) => ({
      id: r.id,
      name: r.name,
      dxf_filename: r.dxf_filename,
      dxf_size_bytes: r.dxf_size_bytes == null ? null : Number(r.dxf_size_bytes),
      updated_at:
        r.updated_at instanceof Date
          ? r.updated_at.toISOString()
          : String(r.updated_at),
    })),
  });
}

interface CreateBody {
  name: string;
  dxf_blob_url: string;
  dxf_filename: string;
  dxf_size_bytes?: number | null;
  source_units: string;
  layer_mapping: LayerMapping;
  result: ProcessResult;
  view_mode?: ViewMode;
}

export async function POST(request: Request) {
  const session = await getOptionalSession();
  const userId = session?.user && (session.user as { id?: string }).id;
  if (!userId) return new NextResponse("Unauthorized", { status: 401 });

  const body = (await request.json()) as CreateBody;
  if (
    !body?.name ||
    !body.dxf_blob_url ||
    !body.dxf_filename ||
    !body.source_units ||
    !body.layer_mapping ||
    !body.result
  ) {
    return new NextResponse("Missing required fields", { status: 400 });
  }

  const rows = await query<{ id: string }>(
    `INSERT INTO projects
       (user_id, name, dxf_blob_url, dxf_filename, dxf_size_bytes,
        source_units, layer_mapping, result, view_mode)
     VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
     RETURNING id`,
    [
      userId,
      body.name,
      body.dxf_blob_url,
      body.dxf_filename,
      body.dxf_size_bytes ?? null,
      body.source_units,
      JSON.stringify(body.layer_mapping),
      JSON.stringify(body.result),
      body.view_mode ?? "plan",
    ],
  );

  return NextResponse.json({ id: rows[0]!.id });
}
