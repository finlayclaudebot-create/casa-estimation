"use client";

import { cn } from "@/lib/utils";

const STEPS = [
  { id: "classify_pdf", label: "Classifying PDF" },
  { id: "classify_pages", label: "Identifying pages" },
  { id: "extract_schedules", label: "Extracting schedule" },
];

export interface ProcessingStep {
  name: string;
  status: string;
}

interface ProcessingStatusProps {
  status: string;
  steps?: ProcessingStep[];
  errorMessage?: string | null;
}

export function ProcessingStatus({ status, steps = [], errorMessage }: ProcessingStatusProps) {
  const stepStatusByName = new Map(steps.map((s) => [s.name, s.status]));

  return (
    <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-4">
      <p className="text-sm font-medium">Status: {status}</p>
      <ol className="space-y-2">
        {STEPS.map((step) => {
          const state = stepStatusByName.get(step.id);
          return (
            <li key={step.id} className="flex items-center gap-3">
              <span
                className={cn(
                  "h-2.5 w-2.5 rounded-full",
                  state === "succeeded"
                    ? "bg-green-500"
                    : state === "failed"
                      ? "bg-destructive"
                      : state === "running"
                        ? "bg-amber-500"
                        : "bg-muted-foreground/40",
                )}
              />
              <span className="text-sm">{step.label}</span>
              {state && (
                <span className="ml-auto text-xs uppercase text-muted-foreground">
                  {state}
                </span>
              )}
            </li>
          );
        })}
      </ol>
      {errorMessage && (
        <p className="text-sm text-destructive" role="alert">
          {errorMessage}
        </p>
      )}
    </div>
  );
}
