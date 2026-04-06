"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { fetchGeometry, fetchJob, artifactUrl } from "@/lib/api";
import type { GeometryPayload, JobData } from "@/lib/types";
import dynamic from "next/dynamic";

const ResultsView = dynamic(() => import("@/components/ResultsView"), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center text-text-muted">
      Loading canvas...
    </div>
  ),
});

function JobPageInner() {
  const router = useRouter();
  const params = useSearchParams();
  const jobId = params.get("id");
  const [job, setJob] = useState<JobData | null>(null);
  const [geometry, setGeometry] = useState<GeometryPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const poll = useCallback(async () => {
    if (!jobId) return;
    try {
      const j = await fetchJob(jobId);
      setJob(j);
      if (j.status === "completed" || j.status === "failed" || j.status === "needs_review") {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        if (j.status === "completed") {
          try {
            const geo = await fetchGeometry(jobId);
            setGeometry(geo);
          } catch {
            // geometry may not be available
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch job.");
    }
  }, [jobId]);

  useEffect(() => {
    if (!jobId) {
      router.replace("/");
      return;
    }
    poll();
    intervalRef.current = setInterval(poll, 1500);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobId, poll, router]);

  if (!jobId) return null;

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-error bg-error/10 border border-error/20 px-4 py-3 text-[12px] max-w-md">
          {error}
        </div>
      </div>
    );
  }

  // Show results view once geometry is loaded
  if (geometry && job) {
    return <ResultsView job={job} geometry={geometry} />;
  }

  // Job processing view
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 gap-6">
      <div className="w-full max-w-lg space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-sm font-semibold text-text-primary">
            {job?.status === "failed"
              ? "Job Failed"
              : job?.status === "needs_review"
                ? "Needs Review"
                : "Computing..."}
          </h1>
          {job && (
            <StatusChip status={job.status} />
          )}
        </div>

        {/* Progress bar */}
        <div className="w-full h-1 bg-bg-surface overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              job?.status === "failed"
                ? "bg-error"
                : job?.status === "completed"
                  ? "bg-success"
                  : "bg-accent"
            }`}
            style={{ width: `${deriveProgress(job)}%` }}
          />
        </div>

        {/* Log viewer */}
        {job && job.logs.length > 0 && (
          <div className="bg-bg-surface border border-border-panel p-3 max-h-64 overflow-auto">
            <pre className="text-[11px] text-text-muted leading-relaxed whitespace-pre-wrap">
              {job.logs.slice(-30).join("\n")}
            </pre>
          </div>
        )}

        {/* Warnings */}
        {job && job.warnings.length > 0 && (
          <div className="bg-warning/5 border border-warning/20 p-3">
            <div className="text-warning text-[11px] font-medium mb-1">
              Warnings
            </div>
            {job.warnings.map((w, i) => (
              <div key={i} className="text-text-muted text-[11px]">
                {w}
              </div>
            ))}
          </div>
        )}

        {/* Error message */}
        {job?.status === "failed" && job.error_message && (
          <div className="text-error text-[12px] bg-error/10 border border-error/20 px-3 py-2">
            {job.error_message.slice(-500)}
          </div>
        )}

        {/* Download buttons for completed without geometry */}
        {job?.status === "completed" && !geometry && (
          <div className="flex gap-3">
            {job.artifacts["tributary_output.dxf"] && (
              <a
                href={artifactUrl(jobId, "tributary_output.dxf")}
                className="px-4 py-1.5 text-[12px] bg-accent text-white hover:bg-accent-hover transition-colors"
              >
                Download DXF
              </a>
            )}
            {job.artifacts["column_load_takedown.xlsx"] && (
              <a
                href={artifactUrl(jobId, "column_load_takedown.xlsx")}
                className="px-4 py-1.5 text-[12px] border border-border-panel text-text-secondary hover:text-text-primary transition-colors"
              >
                Download XLSX
              </a>
            )}
          </div>
        )}

        <button
          onClick={() => router.push("/")}
          className="text-text-muted text-[11px] hover:text-text-secondary transition-colors"
        >
          Start over
        </button>
      </div>
    </div>
  );
}

export default function JobPage() {
  return (
    <Suspense
      fallback={
        <div className="flex-1 flex items-center justify-center text-text-muted">
          Loading...
        </div>
      }
    >
      <JobPageInner />
    </Suspense>
  );
}

function StatusChip({ status }: { status: string }) {
  const colors: Record<string, string> = {
    queued: "text-text-muted border-border-panel",
    running: "text-accent border-accent/30",
    completed: "text-success border-success/30",
    failed: "text-error border-error/30",
    needs_review: "text-warning border-warning/30",
  };
  return (
    <span
      className={`text-[10px] uppercase tracking-wider border px-2 py-0.5 ${colors[status] || ""}`}
    >
      {status}
    </span>
  );
}

const PROGRESS_PATTERNS: [RegExp, number][] = [
  [/starting extract_dxf_data/i, 5],
  [/starting tributary/i, 15],
  [/Floor Number Association/i, 25],
  [/Consolidating Floor Plans/i, 35],
  [/Column Association/i, 45],
  [/Tributary Area Calculation/i, 55],
  [/Facade Attribution/i, 70],
  [/DXF output file created/i, 80],
  [/Excel export/i, 90],
  [/Geometry JSON export/i, 95],
  [/LAYER COLOR LEGEND/i, 100],
];

function deriveProgress(job: JobData | null): number {
  if (!job) return 0;
  if (job.status === "completed") return 100;
  if (job.status === "failed") return 100;
  if (job.status === "queued") return 2;

  let progress = 5;
  const combined = job.logs.join("\n");
  for (const [pattern, pct] of PROGRESS_PATTERNS) {
    if (pattern.test(combined)) {
      progress = Math.max(progress, pct);
    }
  }
  return progress;
}
