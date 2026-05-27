"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useRef, useState } from "react";
import { type DemoId, uploadDemo, uploadDxf } from "@/lib/api";
import type { DraftData } from "@/lib/types";

const DEMO_OPTIONS: { id: DemoId; label: string; filename: string }[] = [
  { id: "default", label: "Load 358 Demo 1 (archived)", filename: "358 Flatbush - input.dxf" },
  { id: "geom_clean_1", label: "Load 1025 Demo 2 (archived)", filename: "1025 Atlantic - input.dxf" },
  { id: "fulton_356", label: "Load 356 Demo 3 (best reference)", filename: "356 Fulton - input.dxf" },
];

function UploadPageInner() {
  const router = useRouter();
  const params = useSearchParams();
  const expired = params.get("expired") === "1";
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(
    expired ? "Session expired \u2014 please re-upload your DXF." : null,
  );
  const [filename, setFilename] = useState<string | null>(null);

  const handleDraft = useCallback(
    (draft: DraftData) => {
      sessionStorage.setItem("draft", JSON.stringify(draft));
      router.push("/review");
    },
    [router],
  );

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith(".dxf")) {
        setError("Upload a .dxf file.");
        return;
      }
      setError(null);
      setFilename(file.name);
      setLoading(true);
      try {
        const draft = await uploadDxf(file);
        handleDraft(draft);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed.");
        setLoading(false);
      }
    },
    [handleDraft],
  );

  const handleDemo = useCallback(async (demo: (typeof DEMO_OPTIONS)[number]) => {
    setError(null);
    setFilename(demo.filename);
    setLoading(true);
    try {
      const draft = await uploadDemo(demo.id);
      handleDraft(draft);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Demo failed.");
      setLoading(false);
    }
  }, [handleDraft]);

  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="w-full max-w-lg space-y-6">
        <div className="space-y-1">
          <h1 className="text-lg font-semibold text-text-primary">
            Upload DXF
          </h1>
          <p className="text-text-secondary text-[12px]">
            Upload a two-way slab plan to compute tributary areas.
          </p>
        </div>

        {/* Drop zone */}
        <div
          className={`border-2 border-dashed p-8 text-center cursor-pointer transition-colors ${
            dragging
              ? "border-accent bg-accent/5"
              : "border-border-panel hover:border-text-muted"
          }`}
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const file = e.dataTransfer.files[0];
            if (file) handleFile(file);
          }}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".dxf"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
          {loading ? (
            <div className="space-y-2">
              <div className="text-accent animate-pulse">Processing...</div>
              <div className="text-text-muted text-[11px]">{filename}</div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="text-text-secondary">
                Drop .dxf file here or click to browse
              </div>
              {filename && (
                <div className="text-text-muted text-[11px]">{filename}</div>
              )}
            </div>
          )}
        </div>

        {error && (
          <div className="text-error text-[12px] bg-error/10 border border-error/20 px-3 py-2">
            {error}
          </div>
        )}

        <div className="flex items-center gap-3">
          <div className="flex-1 border-t border-border-panel" />
          <span className="text-text-muted text-[11px]">or</span>
          <div className="flex-1 border-t border-border-panel" />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {DEMO_OPTIONS.map((demo) => (
            <button
              key={demo.id}
              onClick={() => handleDemo(demo)}
              disabled={loading}
              className="w-full py-2 px-4 border border-border-panel text-text-secondary hover:text-text-primary hover:border-text-muted transition-colors disabled:opacity-40 text-[12px]"
            >
              {demo.label}
            </button>
          ))}
        </div>

        <a
          href="/template.dxf"
          download="reference.dxf"
          className="block w-full py-2 px-4 border border-border-panel text-text-secondary hover:text-text-primary hover:border-text-muted transition-colors text-center text-[12px]"
        >
          Download Reference DXF
        </a>
      </div>
    </div>
  );
}

export default function UploadPage() {
  return (
    <Suspense>
      <UploadPageInner />
    </Suspense>
  );
}
