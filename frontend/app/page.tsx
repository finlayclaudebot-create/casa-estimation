import { PlanUploader } from "@/components/plan-uploader";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col items-stretch gap-8 px-6 py-16">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Casa Estimation</h1>
        <p className="text-muted-foreground">
          Upload an Australian architectural PDF. We&apos;ll extract the door and
          window schedules and return a structured takeoff you can review and export.
        </p>
      </header>
      <PlanUploader />
      <footer className="text-sm text-muted-foreground">
        Phase 1 supports vector PDFs only. Raster scans are not yet supported.
      </footer>
    </main>
  );
}
