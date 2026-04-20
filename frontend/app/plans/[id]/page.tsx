"use client";

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ElementsTable } from "@/components/elements-table";
import { ExportButton } from "@/components/export-button";
import { ProcessingStatus } from "@/components/processing-status";
import { getLatestTakeoff, TERMINAL_STATUSES } from "@/lib/api";

export default function PlanDetailPage() {
  const params = useParams<{ id: string }>();
  const planId = params.id;

  const query = useQuery({
    queryKey: ["takeoff", planId],
    queryFn: () => getLatestTakeoff(planId),
    refetchInterval: (q) => {
      const data = q.state.data;
      if (!data) return 2_000;
      return TERMINAL_STATUSES.has(data.status) ? false : 2_000;
    },
    enabled: Boolean(planId),
  });

  if (query.isLoading) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-12">
        <p className="text-sm text-muted-foreground">Loading takeoff…</p>
      </main>
    );
  }

  if (query.isError) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-12">
        <p className="text-sm text-destructive">{(query.error as Error).message}</p>
        <Link href="/" className="mt-4 inline-block text-sm underline">
          Back to upload
        </Link>
      </main>
    );
  }

  const takeoff = query.data;
  if (!takeoff) return null;

  const doors = takeoff.elements.filter((e) => e.element_type === "door");
  const windows = takeoff.elements.filter((e) => e.element_type === "window");
  const isTerminal = TERMINAL_STATUSES.has(takeoff.status);

  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-6 px-6 py-12">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Plan takeoff</h1>
          <p className="text-sm text-muted-foreground">Plan {takeoff.plan_id}</p>
        </div>
        {isTerminal && takeoff.elements.length > 0 && (
          <ExportButton
            filename={`takeoff-${takeoff.plan_id}.csv`}
            elements={takeoff.elements}
          />
        )}
      </header>

      <ProcessingStatus
        status={takeoff.status}
        steps={takeoff.processing_log?.steps ?? []}
        errorMessage={takeoff.error_message}
      />

      {isTerminal && (
        <>
          <ElementsTable title="Doors" elements={doors} />
          <ElementsTable title="Windows" elements={windows} />
        </>
      )}

      <Link href="/" className="text-sm underline">
        Upload another plan
      </Link>
    </main>
  );
}
