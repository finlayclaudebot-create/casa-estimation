"""Phase 1 accuracy evaluation harness.

Runs the full extraction pipeline (classify_pdf → classify_page_types →
extract_schedules) against every PDF in ``data/sample_plans/``. Each PDF is paired
with a ``<name>.truth.json`` file describing the ground-truth doors and windows.

Usage:
    python scripts/evaluate.py [--data-dir path/to/sample_plans]

Outputs JSON to ``eval_results/<ISO_timestamp>.json`` and a human-readable summary
to stdout. Per the spec, this script measures only — it never tries to fix
accuracy issues at runtime.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.pdf.classifier import classify_pdf
from app.services.pdf.page_classifier import classify_page_types
from app.services.pdf.schedule_parser import extract_schedules


@dataclass
class CountReport:
    truth: int
    detected: int
    correct_ids: int
    missing_ids: list[str] = field(default_factory=list)
    extra_ids: list[str] = field(default_factory=list)


@dataclass
class PlanReport:
    plan: str
    doors: CountReport
    windows: CountReport
    passed: bool
    notes: str = ""
    error: str | None = None


def _evaluate_kind(
    truth_entries: list[dict[str, Any]], detected_ids: list[str]
) -> CountReport:
    truth_ids = {(e.get("id") or "").strip() for e in truth_entries if e.get("id")}
    detected = {x.strip() for x in detected_ids if x and x.strip()}
    missing = sorted(truth_ids - detected)
    extra = sorted(detected - truth_ids)
    return CountReport(
        truth=len(truth_entries),
        detected=len(detected),
        correct_ids=len(truth_ids & detected),
        missing_ids=missing,
        extra_ids=extra,
    )


def _evaluate_plan(pdf_path: Path, truth: dict[str, Any]) -> PlanReport:
    try:
        classification = classify_pdf(pdf_path)
        if classification.overall_type == "raster":
            return PlanReport(
                plan=pdf_path.name,
                doors=CountReport(0, 0, 0),
                windows=CountReport(0, 0, 0),
                passed=False,
                notes="raster PDF (out of Phase 1 scope)",
            )
        page_classifications = classify_page_types(pdf_path)
        schedule_pages = [
            p.page_number for p in page_classifications if p.page_type == "schedule"
        ]
        result = extract_schedules(pdf_path, schedule_pages)
    except Exception as exc:
        return PlanReport(
            plan=pdf_path.name,
            doors=CountReport(0, 0, 0),
            windows=CountReport(0, 0, 0),
            passed=False,
            error=f"{type(exc).__name__}: {exc}",
        )

    door_truth = (truth.get("doors") or {}).get("entries") or []
    window_truth = (truth.get("windows") or {}).get("entries") or []
    door_report = _evaluate_kind(door_truth, [d.schedule_id for d in result.doors])
    window_report = _evaluate_kind(window_truth, [w.schedule_id for w in result.windows])

    accuracies: list[float] = []
    if door_truth:
        accuracies.append(door_report.correct_ids / door_report.truth)
    if window_truth:
        accuracies.append(window_report.correct_ids / window_report.truth)
    accuracy = sum(accuracies) / len(accuracies) if accuracies else 0.0
    passed = bool(accuracies) and accuracy >= 0.95
    return PlanReport(
        plan=pdf_path.name,
        doors=door_report,
        windows=window_report,
        passed=passed,
        notes=f"avg id accuracy={accuracy:.2%}; warnings={len(result.warnings)}",
    )


def evaluate(data_dir: Path) -> dict[str, Any]:
    pdfs = sorted(data_dir.glob("*.pdf"))
    plan_reports: list[PlanReport] = []
    total_truth = 0
    total_correct = 0
    for pdf in pdfs:
        truth_path = pdf.with_suffix(".truth.json")
        if not truth_path.exists():
            plan_reports.append(
                PlanReport(
                    plan=pdf.name,
                    doors=CountReport(0, 0, 0),
                    windows=CountReport(0, 0, 0),
                    passed=False,
                    notes="missing truth file",
                )
            )
            continue
        truth = json.loads(truth_path.read_text())
        report = _evaluate_plan(pdf, truth)
        plan_reports.append(report)
        total_truth += report.doors.truth + report.windows.truth
        total_correct += report.doors.correct_ids + report.windows.correct_ids

    passed = sum(1 for r in plan_reports if r.passed)
    return {
        "run_at": datetime.now(UTC).isoformat(),
        "data_dir": str(data_dir),
        "total_plans": len(plan_reports),
        "passed": passed,
        "failed": len(plan_reports) - passed,
        "overall_element_accuracy": (
            total_correct / total_truth if total_truth else 0.0
        ),
        "per_plan": [
            {
                "plan": r.plan,
                "doors": asdict(r.doors),
                "windows": asdict(r.windows),
                "passed": r.passed,
                "notes": r.notes,
                "error": r.error,
            }
            for r in plan_reports
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/sample_plans"),
        help="Directory containing *.pdf and matching *.truth.json files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("eval_results"),
        help="Where to write the run report JSON",
    )
    args = parser.parse_args()

    if not args.data_dir.exists():
        print(
            f"[evaluate] data dir {args.data_dir} not found; nothing to evaluate.",
            file=sys.stderr,
        )
        print(
            "[evaluate] Add Australian sample plans + .truth.json files to that "
            "directory to measure accuracy.",
            file=sys.stderr,
        )
        return 0

    report = evaluate(args.data_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{report['run_at'].replace(':', '-')}.json"
    out_path.write_text(json.dumps(report, indent=2))

    print(f"\n=== Phase 1 evaluation ({report['total_plans']} plans) ===")
    print(f"Passed:   {report['passed']}")
    print(f"Failed:   {report['failed']}")
    print(f"Overall element accuracy: {report['overall_element_accuracy']:.2%}")
    print(f"Report written to {out_path}")
    print()
    for plan in report["per_plan"]:
        flag = "PASS" if plan["passed"] else "FAIL"
        print(
            f"  [{flag}] {plan['plan']}  "
            f"doors {plan['doors']['correct_ids']}/{plan['doors']['truth']}  "
            f"windows {plan['windows']['correct_ids']}/{plan['windows']['truth']}  "
            f"{plan['notes']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
