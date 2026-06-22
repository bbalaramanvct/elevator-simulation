#!/usr/bin/env python3
"""Generate and optionally open visualization dashboards."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from elevator_simulation.visualize import (
    generate_benchmark_dashboard,
    generate_elevator_animation,
    generate_matplotlib_charts,
    open_in_browser,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Visualize elevator simulation output.")
    parser.add_argument(
        "--benchmark-csv",
        type=Path,
        default=Path("output/benchmarks/benchmark_comparison.csv"),
        help="Benchmark comparison CSV (default: output/benchmarks/benchmark_comparison.csv)",
    )
    parser.add_argument(
        "--position-csv",
        type=Path,
        help="Elevator position log CSV for animation (e.g. output/elevator_positions_scan.csv)",
    )
    parser.add_argument(
        "--max-floor",
        type=int,
        default=15,
        help="Building max floor for animation scaling (default: 15)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/visualizations"),
        help="Directory for generated HTML/PNG files",
    )
    parser.add_argument(
        "--png",
        action="store_true",
        help="Also generate matplotlib PNG charts (requires matplotlib)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open generated HTML dashboards in the default browser",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    if args.benchmark_csv.exists():
        dashboard = generate_benchmark_dashboard(
            args.benchmark_csv,
            args.output_dir / "benchmark_dashboard.html",
        )
        generated.append(dashboard)
        print(f"Benchmark dashboard: {dashboard}")
    else:
        print(f"Benchmark CSV not found: {args.benchmark_csv}", file=sys.stderr)
        print("Run: py -3 run_benchmarks.py", file=sys.stderr)

    if args.position_csv:
        if not args.position_csv.exists():
            print(f"Position CSV not found: {args.position_csv}", file=sys.stderr)
            return 1
        animation = generate_elevator_animation(
            args.position_csv,
            args.output_dir / f"{args.position_csv.stem}_animation.html",
            max_floor=args.max_floor,
            title=f"Elevator animation — {args.position_csv.stem}",
        )
        generated.append(animation)
        print(f"Elevator animation:  {animation}")

    if args.png and args.benchmark_csv.exists():
        try:
            pngs = generate_matplotlib_charts(args.benchmark_csv, args.output_dir / "png")
            generated.extend(pngs)
            print(f"PNG charts:          {len(pngs)} files in {args.output_dir / 'png'}")
        except ImportError as exc:
            print(str(exc), file=sys.stderr)
            return 1

    if args.open:
        for path in generated:
            if path.suffix == ".html":
                open_in_browser(path)
                print(f"Opened: {path}")

    return 0 if generated else 1


if __name__ == "__main__":
    raise SystemExit(main())
