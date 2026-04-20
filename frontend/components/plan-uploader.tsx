"use client";

import { useRouter } from "next/navigation";
import { useCallback, useRef, useState } from "react";
import { triggerTakeoff, uploadPlan } from "@/lib/api";
import { cn } from "@/lib/utils";

const MAX_BYTES = 100 * 1024 * 1024;

export function PlanUploader() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      if (!file.name.toLowerCase().endsWith(".pdf") && file.type !== "application/pdf") {
        setError("Only PDF files are accepted.");
        return;
      }
      if (file.size > MAX_BYTES) {
        setError("File exceeds the 100 MB limit.");
        return;
      }
      try {
        setBusy(true);
        setProgress("Uploading…");
        const created = await uploadPlan(file);
        setProgress("Triggering takeoff…");
        await triggerTakeoff(created.plan_id);
        router.push(`/plans/${created.plan_id}`);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setBusy(false);
        setProgress(null);
      }
    },
    [router],
  );

  const onDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setDragOver(false);
      const file = event.dataTransfer.files?.[0];
      if (file) void handleFile(file);
    },
    [handleFile],
  );

  return (
    <section className="space-y-4">
      <div
        className={cn(
          "flex h-56 cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed text-center transition",
          dragOver
            ? "border-primary bg-primary/5"
            : "border-border bg-muted/40 hover:bg-muted/60",
        )}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        role="button"
        tabIndex={0}
        aria-busy={busy}
      >
        <p className="text-base font-medium">Drop a PDF here or click to upload</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Vector plans only · max 100 MB
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleFile(file);
          }}
        />
      </div>
      {progress && (
        <p className="text-sm text-muted-foreground" role="status">
          {progress}
        </p>
      )}
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
