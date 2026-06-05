"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  deleteProject,
  getProject,
  listProjects,
  uploadDxf,
} from "@/lib/api";
import type { ProjectSummary } from "@/lib/types";

function formatBytes(n: number | null): string {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`;
}

export default function ProjectExplorer() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listProjects()
      .then((rows) => {
        if (!cancelled) setProjects(rows);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load projects.");
          setProjects([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const openProject = useCallback(
    async (id: string) => {
      setBusyId(id);
      setError(null);
      try {
        const project = await getProject(id);
        sessionStorage.removeItem("processParams");
        sessionStorage.removeItem("draft");
        sessionStorage.setItem(
          "openedProject",
          JSON.stringify({
            id: project.id,
            name: project.name,
            result: project.result,
            view_mode: project.view_mode,
            dxf_filename: project.dxf_filename,
          }),
        );
        router.push("/job");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to open project.");
        setBusyId(null);
      }
    },
    [router],
  );

  const removeProject = useCallback(async (id: string) => {
    if (!confirm("Delete this project?")) return;
    setBusyId(id);
    try {
      await deleteProject(id);
      setProjects((prev) => (prev ? prev.filter((p) => p.id !== id) : prev));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete.");
    } finally {
      setBusyId(null);
    }
  }, []);

  const handleUploadFile = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith(".dxf")) {
        setError("Upload a .dxf file.");
        return;
      }
      setError(null);
      setUploading(true);
      try {
        const draft = await uploadDxf(file);
        sessionStorage.removeItem("openedProject");
        sessionStorage.setItem("draft", JSON.stringify(draft));
        router.push("/review");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed.");
        setUploading(false);
      }
    },
    [router],
  );

  const loading = projects === null;
  const empty = projects !== null && projects.length === 0;

  return (
    <div className="flex-1 flex flex-col items-center p-6">
      <div className="w-full max-w-3xl space-y-4">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold text-text-primary">Projects</h1>
          <p className="text-text-secondary text-[12px]">
            Saved tributary jobs. Drop a .dxf below to start a new one.
          </p>
        </div>

        {error && (
          <div className="text-error text-[12px] bg-error/10 border border-error/20 px-3 py-2">
            {error}
          </div>
        )}

        <div
          className={`border ${
            dragging
              ? "border-accent bg-accent/5"
              : "border-border-panel bg-bg-surface"
          } transition-colors`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const file = e.dataTransfer.files[0];
            if (file) void handleUploadFile(file);
          }}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".dxf"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void handleUploadFile(file);
            }}
          />

          {/* Header row */}
          <div className="grid grid-cols-[1fr_160px_90px_28px] gap-3 px-3 py-2 border-b border-border-panel text-[10px] uppercase tracking-wider text-text-muted">
            <span>Name</span>
            <span>Modified</span>
            <span className="text-right">Size</span>
            <span />
          </div>

          {/* + Upload new project row */}
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="w-full grid grid-cols-[1fr_160px_90px_28px] gap-3 px-3 py-2 border-b border-border-panel text-left text-[12px] text-text-secondary hover:bg-bg-panel hover:text-text-primary transition-colors disabled:opacity-50"
          >
            <span>{uploading ? "Uploading…" : "[+] Upload new project"}</span>
            <span />
            <span />
            <span />
          </button>

          {/* Rows / empty state / loading */}
          {loading && (
            <div className="px-3 py-6 text-center text-text-muted text-[11px]">
              Loading…
            </div>
          )}

          {empty && (
            <div className="px-3 py-10 text-center text-text-muted text-[11px]">
              (empty — drop a .dxf here)
            </div>
          )}

          {projects && projects.length > 0 && (
            <ul>
              {projects.map((p) => {
                const isBusy = busyId === p.id;
                return (
                  <li
                    key={p.id}
                    className="grid grid-cols-[1fr_160px_90px_28px] gap-3 px-3 py-2 border-b border-border-panel last:border-b-0 text-[12px] text-text-secondary hover:bg-bg-panel group"
                  >
                    <button
                      type="button"
                      onClick={() => void openProject(p.id)}
                      disabled={isBusy}
                      className="text-left truncate hover:text-text-primary disabled:opacity-50"
                      title={p.dxf_filename}
                    >
                      {p.name}
                    </button>
                    <span className="text-text-muted">
                      {formatDate(p.updated_at)}
                    </span>
                    <span className="text-text-muted text-right">
                      {formatBytes(p.dxf_size_bytes)}
                    </span>
                    <button
                      type="button"
                      onClick={() => void removeProject(p.id)}
                      disabled={isBusy}
                      className="text-text-muted opacity-0 group-hover:opacity-100 hover:text-error transition-opacity"
                      aria-label="Delete project"
                      title="Delete"
                    >
                      ×
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
