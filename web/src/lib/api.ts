import type { DraftData, LayerMapping, ProcessResult } from "./types";

const BASE = "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadDxf(file: File): Promise<DraftData> {
  const form = new FormData();
  form.append("upload", file);
  return request<DraftData>("/api/upload", { method: "POST", body: form });
}

export async function uploadDemo(): Promise<DraftData> {
  return request<DraftData>("/api/upload", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ demo: true }),
  });
}

export async function processJob(
  blobUrl: string,
  sourceUnits: string,
  layerMapping: LayerMapping,
): Promise<ProcessResult> {
  return request<ProcessResult>("/api/process", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      blob_url: blobUrl,
      source_units: sourceUnits,
      layer_mapping: layerMapping,
    }),
  });
}
