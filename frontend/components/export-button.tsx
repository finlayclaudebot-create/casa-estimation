"use client";

import type { TakeoffElement } from "@/lib/api";

interface ExportButtonProps {
  filename: string;
  elements: TakeoffElement[];
}

const HEADERS = [
  "schedule_id",
  "element_type",
  "category",
  "width_mm",
  "height_mm",
  "material_or_glazing",
  "location",
  "confidence",
];

function escapeCsv(value: string): string {
  if (/[",\n]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

function elementToRow(el: TakeoffElement): string {
  const dims = el.match_key.dimensions as Record<string, number | null | undefined>;
  const attrs = el.match_key.attributes as Record<string, unknown>;
  const props = (el.properties ?? {}) as Record<string, unknown>;
  const matKey = el.element_type === "door" ? "material" : "glazing";

  const cells = [
    el.schedule_id ?? "",
    el.element_type,
    el.match_key.category,
    dims.width_mm == null ? "" : String(dims.width_mm),
    dims.height_mm == null ? "" : String(dims.height_mm),
    attrs[matKey] == null ? "" : String(attrs[matKey]),
    typeof props.location === "string" ? props.location : "",
    String(el.confidence),
  ];
  return cells.map(escapeCsv).join(",");
}

export function ExportButton({ filename, elements }: ExportButtonProps) {
  const onClick = () => {
    const lines = [HEADERS.join(","), ...elements.map(elementToRow)];
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
    >
      Export CSV
    </button>
  );
}
