import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ExportButton } from "@/components/export-button";
import type { TakeoffElement } from "@/lib/api";

const sample: TakeoffElement[] = [
  {
    id: "00000000-0000-0000-0000-000000000001",
    element_type: "door",
    element_subtype: "internal.hinged",
    schedule_id: "D01",
    properties: { location: "Bedroom 1" },
    source: "schedule",
    confidence: 0.95,
    status: "detected",
    match_key: {
      category: "door.internal.hinged",
      dimensions: { width_mm: 820, height_mm: 2040 },
      attributes: { material: "solid_core" },
      quantity_unit: "each",
    },
  },
];

describe("ExportButton", () => {
  beforeEach(() => {
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:mock"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
  });

  it("renders an Export CSV button and triggers a download on click", () => {
    const clickSpy = vi.fn();
    const origCreate = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = origCreate(tag);
      if (tag === "a") (el as HTMLAnchorElement).click = clickSpy;
      return el;
    });

    render(<ExportButton filename="takeoff.csv" elements={sample} />);
    fireEvent.click(screen.getByText("Export CSV"));
    expect(clickSpy).toHaveBeenCalled();
  });
});
