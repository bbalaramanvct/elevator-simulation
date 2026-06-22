#!/usr/bin/env python3
"""CLI entry point for the elevator simulation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running without installation when invoked from project root.
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from elevator_simulation.config import BuildingConfig
from elevator_simulation.csv_reader import load_requests
from elevator_simulation.rush_hour import active_rush_window, is_rush_hour
from elevator_simulation.schedulers import (
    NearestCarScheduler,
    RoundRobinScheduler,
    RushHourScheduler,
    ScanScheduler,
)
from elevator_simulation.simulation import run_all_algorithms
from elevator_simulation.stats import format_stats_report
from elevator_simulation.validator import ValidationError, validate_requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate elevator dispatch algorithms on passenger requests."
    )
    parser.add_argument(
        "csv_file",
        type=Path,
        help="CSV file with columns: time, passenger_id, start_floor, destination_floor",
    )
    parser.add_argument(
        "--elevators",
        type=int,
        default=2,
        help="Number of elevator cars (default: 2)",
    )
    parser.add_argument(
        "--min-floor",
        type=int,
        default=0,
        help="Minimum floor of the building (default: 0)",
    )
    parser.add_argument(
        "--max-floor",
        type=int,
        required=True,
        help="Maximum floor of the building",
    )
    parser.add_argument(
        "--capacity",
        type=int,
        default=8,
        help="Maximum passengers per elevator (default: 8)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for CSV logs and summary files (default: output)",
    )
    parser.add_argument(
        "--algorithms",
        nargs="+",
        choices=["nearest_car", "round_robin", "scan", "rush_hour", "all"],
        default=["all"],
        help="Scheduler algorithms to run (default: all)",
    )
    parser.add_argument(
        "--rush-hour-scan",
        action="store_true",
        help=(
            "Enable rush-hour adaptive mode: use SCAN during local peak windows "
            "(08:00-10:00, 12:00-13:00, 16:00-18:00), nearest car otherwise. "
            "Adds a rush_hour run when combined with --algorithms all."
        ),
    )
    parser.add_argument(
        "--rush-hour-fallback",
        choices=["nearest_car", "round_robin"],
        default="nearest_car",
        help="Off-peak algorithm when --rush-hour-scan or rush_hour is used (default: nearest_car)",
    )
    return parser.parse_args()


def build_schedulers(selected: list[str], rush_hour_scan: bool, rush_hour_fallback: str) -> list:
    fallback = (
        NearestCarScheduler()
        if rush_hour_fallback == "nearest_car"
        else RoundRobinScheduler()
    )
    rush_hour = RushHourScheduler(fallback=fallback)

    available = {
        "nearest_car": NearestCarScheduler(),
        "round_robin": RoundRobinScheduler(),
        "scan": ScanScheduler(),
        "rush_hour": rush_hour,
    }
    if "all" in selected:
        schedulers = [
            available["nearest_car"],
            available["round_robin"],
            available["scan"],
        ]
        if rush_hour_scan:
            schedulers.append(rush_hour)
        return schedulers
    return [available[name] for name in selected]


def main() -> int:
    args = parse_args()

    config = BuildingConfig(
        num_elevators=args.elevators,
        min_floor=args.min_floor,
        max_floor=args.max_floor,
        max_passengers_per_elevator=args.capacity,
    )

    try:
        config.validate()
        requests = load_requests(args.csv_file)
        validate_requests(requests, config)
    except (ValueError, ValidationError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 1

    schedulers = build_schedulers(args.algorithms, args.rush_hour_scan, args.rush_hour_fallback)
    results = run_all_algorithms(
        config=config,
        requests=requests,
        schedulers=schedulers,
        output_dir=args.output_dir,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "simulation_summary.txt"

    summary_lines = [
        "Elevator Simulation Summary",
        f"Input file: {args.csv_file}",
        f"Building floors: {config.min_floor} to {config.max_floor}",
        f"Elevators: {config.num_elevators}, capacity: {config.max_passengers_per_elevator}",
    ]

    if args.rush_hour_scan or "rush_hour" in args.algorithms:
        rush_status = "active (SCAN)" if is_rush_hour() else f"inactive ({args.rush_hour_fallback})"
        window = active_rush_window()
        summary_lines.append(
            f"Rush-hour mode: {rush_status}"
            + (f", window {window}" if window else "")
        )

    summary_lines.append("")

    for result in results:
        summary_lines.append(format_stats_report(result.stats))
        scheduler = next((s for s in schedulers if s.name == result.algorithm), None)
        if scheduler is not None and hasattr(scheduler, "uses_scan"):
            mode = "SCAN (rush hour)" if scheduler.uses_scan else scheduler.active_algorithm
            summary_lines.append(f"  Dispatch mode selected: {mode}")
        summary_lines.append(f"  Position log: {result.position_log_path}")
        summary_lines.append(f"  Simulation ended at time: {result.final_time}")
        summary_lines.append("")

    report = "\n".join(summary_lines)
    summary_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"Summary written to: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
