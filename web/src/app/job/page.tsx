"use client";

import { useRouter } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { processJob } from "@/lib/api";
import type { ProcessResult } from "@/lib/types";
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
  const [result, setResult] = useState<ProcessResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(true);
  const called = useRef(false);

  const run = useCallback(async () => {
    const raw = sessionStorage.getItem("processParams");
    if (!raw) {
      router.replace("/");
      return;
    }

    try {
      const params = JSON.parse(raw);
      const res = await processJob(
        params.blob_url,
        params.source_units,
        params.layer_mapping,
      );
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Processing failed.");
    } finally {
      setProcessing(false);
      sessionStorage.removeItem("processParams");
    }
  }, [router]);

  useEffect(() => {
    if (called.current) return;
    called.current = true;
    run();
  }, [run]);

  // Show results view once geometry is available
  if (result?.status === "completed" && result.geometry) {
    return <ResultsView result={result} geometry={result.geometry} />;
  }

  // Processing / error view
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 gap-6">
      <div className="w-full max-w-lg space-y-4">
        <div className="flex items-center justify-between">
          <h1 className="text-sm font-semibold text-text-primary">
            {processing
              ? "Computing..."
              : result?.status === "failed"
                ? "Job Failed"
                : result?.status === "needs_review"
                  ? "Needs Review"
                  : "Complete"}
          </h1>
          {result && <StatusChip status={result.status} />}
        </div>

        {/* Progress bar */}
        <div className="w-full h-1 bg-bg-surface overflow-hidden">
          {processing ? (
            <div className="h-full bg-accent animate-pulse w-full" />
          ) : (
            <div
              className={`h-full w-full ${
                result?.status === "failed"
                  ? "bg-error"
                  : "bg-success"
              }`}
            />
          )}
        </div>

        {processing && (
          <p className="text-text-muted text-[11px]">
            Computing tributary areas... this may take a moment.
          </p>
        )}

        {/* Error display */}
        {error && (
          <div className="text-error bg-error/10 border border-error/20 px-4 py-3 text-[12px] max-w-md">
            {error}
          </div>
        )}

        {/* Engine error message */}
        {result?.error_message && (
          <div className="text-error text-[12px] bg-error/10 border border-error/20 px-3 py-2">
            {result.error_message.slice(-500)}
          </div>
        )}

        {/* Warnings */}
        {result && result.warnings.length > 0 && (
          <div className="bg-warning/5 border border-warning/20 p-3">
            <div className="text-warning text-[11px] font-medium mb-1">
              Warnings
            </div>
            {result.warnings.map((w, i) => (
              <div key={i} className="text-text-muted text-[11px]">
                {w}
              </div>
            ))}
          </div>
        )}

        {/* Logs (collapsed by default after completion) */}
        {result && result.logs.length > 0 && !processing && (
          <details className="text-[11px]">
            <summary className="text-text-muted cursor-pointer hover:text-text-secondary">
              Show processing logs ({result.logs.length} lines)
            </summary>
            <div className="bg-bg-surface border border-border-panel p-3 max-h-64 overflow-auto mt-2">
              <pre className="text-[11px] text-text-muted leading-relaxed whitespace-pre-wrap">
                {result.logs.slice(-30).join("\n")}
              </pre>
            </div>
          </details>
        )}

        {/* Download buttons (fallback if geometry failed to load) */}
        {result?.status === "completed" && !result.geometry && (
          <div className="flex gap-3">
            {result.artifacts.dxf_url && (
              <a
                href={`/api/download?url=${encodeURIComponent(result.artifacts.dxf_url)}`}
                className="px-4 py-1.5 text-[12px] bg-accent text-white hover:bg-accent-hover transition-colors"
              >
                Download DXF
              </a>
            )}
            {result.artifacts.xlsx_url && (
              <a
                href={`/api/download?url=${encodeURIComponent(result.artifacts.xlsx_url)}`}
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
    completed: "text-success border-success/30",
    failed: "text-error border-error/30",
    needs_review: "text-warning border-warning/30",
  };
  return (
    <span
      className={`text-[10px] uppercase tracking-wider border px-2 py-0.5 ${colors[status] || "text-text-muted border-border-panel"}`}
    >
      {status}
    </span>
  );
}
