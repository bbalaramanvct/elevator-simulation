#!/usr/bin/env python3
"""Run benchmark scenarios and print algorithm comparison statistics."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from elevator_simulation.benchmark import (
    BENCHMARK_SCENARIOS,
    format_comparison_report,
    run_all_scenarios,
    write_comparison_csv,
)
from elevator_simulation.visualize import generate_benchmark_dashboard, open_in_browser


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate elevator algorithms across benchmark scenarios."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/benchmarks"),
        help="Directory for benchmark reports (default: output/benchmarks)",
    )
    parser.add_argument(
        "--scenario",
        nargs="+",
        choices=[s.name for s in BENCHMARK_SCENARIOS],
        help="Run only selected scenarios (default: all)",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate HTML benchmark dashboard after the run",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the benchmark dashboard in the default browser (implies --visualize)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scenarios = BENCHMARK_SCENARIOS
    if args.scenario:
        selected = set(args.scenario)
        scenarios = tuple(s for s in BENCHMARK_SCENARIOS if s.name in selected)

    results = run_all_scenarios(scenarios=scenarios, output_dir=args.output_dir)
    report = format_comparison_report(results)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    txt_path = args.output_dir / "benchmark_comparison.txt"
    csv_path = args.output_dir / "benchmark_comparison.csv"

    txt_path.write_text(report, encoding="utf-8")
    write_comparison_csv(results, csv_path)

    print(report)
    print(f"Report written to: {txt_path}")
    print(f"CSV written to:    {csv_path}")

    if args.visualize or args.open:
        dashboard = generate_benchmark_dashboard(csv_path, args.output_dir / "benchmark_dashboard.html")
        print(f"Dashboard written to: {dashboard}")
        if args.open:
            open_in_browser(dashboard)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
