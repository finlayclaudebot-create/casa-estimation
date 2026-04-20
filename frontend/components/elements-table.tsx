"use client";

import type { TakeoffElement } from "@/lib/api";

interface ElementsTableProps {
  title: string;
  elements: TakeoffElement[];
}

function dim(element: TakeoffElement, key: "width_mm" | "height_mm"): string {
  const dims = element.match_key.dimensions as Record<string, number | null | undefined>;
  const value = dims[key];
  return value == null ? "–" : String(value);
}

function attribute(element: TakeoffElement, key: string): string {
  const attrs = element.match_key.attributes as Record<string, unknown>;
  const value = attrs[key];
  return value == null ? "–" : String(value);
}

export function ElementsTable({ title, elements }: ElementsTableProps) {
  if (elements.length === 0) {
    return (
      <section className="rounded-lg border border-border bg-muted/20 p-4 text-sm text-muted-foreground">
        No {title.toLowerCase()} extracted.
      </section>
    );
  }

  return (
    <section className="space-y-2">
      <header className="flex items-baseline justify-between">
        <h2 className="text-lg font-semibold">{title}</h2>
        <span className="text-sm text-muted-foreground">{elements.length} items</span>
      </header>
      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full table-auto text-sm">
          <thead className="bg-muted/40 text-left text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">W (mm)</th>
              <th className="px-3 py-2">H (mm)</th>
              <th className="px-3 py-2">Material / Glazing</th>
              <th className="px-3 py-2">Location</th>
            </tr>
          </thead>
          <tbody>
            {elements.map((el) => {
              const props = (el.properties ?? {}) as Record<string, unknown>;
              const location = typeof props.location === "string" ? props.location : "–";
              const matKey = el.element_type === "door" ? "material" : "glazing";
              return (
                <tr key={el.id} className="border-t border-border/50">
                  <td className="px-3 py-2 font-mono">{el.schedule_id ?? "–"}</td>
                  <td className="px-3 py-2">{el.match_key.category}</td>
                  <td className="px-3 py-2">{dim(el, "width_mm")}</td>
                  <td className="px-3 py-2">{dim(el, "height_mm")}</td>
                  <td className="px-3 py-2">{attribute(el, matKey)}</td>
                  <td className="px-3 py-2">{location}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
