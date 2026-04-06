import type { DraftData, GeometryPayload, JobData, LayerMapping } from "./types";

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
  return request<DraftData>("/api/upload/demo", { method: "POST" });
}

export async function createJob(
  draftId: string,
  sourceUnits: string,
  layerMapping: LayerMapping,
): Promise<{ job_id: string; status: string }> {
  return request("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      draft_id: draftId,
      source_units: sourceUnits,
      layer_mapping: layerMapping,
    }),
  });
}

export async function fetchJob(jobId: string): Promise<JobData> {
  return request<JobData>(`/api/jobs/${jobId}`);
}

export async function fetchGeometry(jobId: string): Promise<GeometryPayload> {
  return request<GeometryPayload>(`/api/jobs/${jobId}/geometry`);
}

export function artifactUrl(jobId: string, name: string): string {
  return `/api/jobs/${jobId}/artifacts/${name}`;
}
