"""Benchmark scenarios and algorithm comparison runner."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from elevator_simulation.config import BuildingConfig
from elevator_simulation.csv_reader import load_requests
from elevator_simulation.schedulers import (
    NearestCarScheduler,
    RoundRobinScheduler,
    RushHourScheduler,
    ScanScheduler,
)
from elevator_simulation.schedulers.base import Scheduler
from elevator_simulation.simulation import ElevatorSimulation
from elevator_simulation.stats import AlgorithmStats
from elevator_simulation.validator import validate_requests

SCENARIOS_DIR = Path(__file__).resolve().parents[2] / "data" / "scenarios"

PEAK_MOMENT = datetime(2026, 6, 20, 9, 0)
OFF_PEAK_MOMENT = datetime(2026, 6, 20, 15, 0)


@dataclass(frozen=True)
class BenchmarkScenario:
    """Input configuration for one evaluation scenario."""

    name: str
    description: str
    csv_file: str
    min_floor: int
    max_floor: int
    num_elevators: int
    capacity: int

    @property
    def csv_path(self) -> Path:
        return SCENARIOS_DIR / self.csv_file


@dataclass
class ScenarioResult:
    scenario: BenchmarkScenario
    stats_by_algorithm: dict[str, AlgorithmStats]


BENCHMARK_SCENARIOS: tuple[BenchmarkScenario, ...] = (
    BenchmarkScenario(
        name="morning_rush",
        description="10 passengers request ground-to-upper floors at t=0-1 (peak up-traffic).",
        csv_file="morning_rush.csv",
        min_floor=0,
        max_floor=15,
        num_elevators=2,
        capacity=8,
    ),
    BenchmarkScenario(
        name="evening_rush",
        description="10 passengers request upper-to-ground floors at t=0-1 (peak down-traffic).",
        csv_file="evening_rush.csv",
        min_floor=0,
        max_floor=15,
        num_elevators=2,
        capacity=8,
    ),
    BenchmarkScenario(
        name="sparse_traffic",
        description="Requests evenly spaced every 5 ticks; low concurrent load.",
        csv_file="sparse_traffic.csv",
        min_floor=0,
        max_floor=10,
        num_elevators=2,
        capacity=8,
    ),
    BenchmarkScenario(
        name="bursty_traffic",
        description="Three bursts of 3-4 requests at t=0, 10, and 20.",
        csv_file="bursty_traffic.csv",
        min_floor=0,
        max_floor=15,
        num_elevators=2,
        capacity=8,
    ),
    BenchmarkScenario(
        name="fairness_outlier",
        description="Six bulk up-requests plus one outlier to floor 25 at t=0.",
        csv_file="fairness_outlier.csv",
        min_floor=0,
        max_floor=25,
        num_elevators=2,
        capacity=8,
    ),
    BenchmarkScenario(
        name="bidirectional",
        description="Mixed up and down requests arriving together.",
        csv_file="bidirectional.csv",
        min_floor=0,
        max_floor=12,
        num_elevators=2,
        capacity=8,
    ),
    BenchmarkScenario(
        name="high_rise",
        description="Six passengers in a 50-floor building with long travel distances.",
        csv_file="high_rise.csv",
        min_floor=0,
        max_floor=50,
        num_elevators=2,
        capacity=8,
    ),
    BenchmarkScenario(
        name="capacity_stress",
        description="12 simultaneous requests with 2 elevators and capacity 4.",
        csv_file="capacity_stress.csv",
        min_floor=0,
        max_floor=10,
        num_elevators=2,
        capacity=4,
    ),
)


def default_schedulers(include_rush_hour: bool = True) -> list[Scheduler]:
    schedulers: list[Scheduler] = [
        NearestCarScheduler(),
        RoundRobinScheduler(),
        ScanScheduler(),
    ]
    if include_rush_hour:
        schedulers.extend(
            [
                RushHourScheduler(fallback=NearestCarScheduler(), moment=PEAK_MOMENT),
                RushHourScheduler(fallback=NearestCarScheduler(), moment=OFF_PEAK_MOMENT),
            ]
        )
    return schedulers


def run_scenario(
    scenario: BenchmarkScenario,
    schedulers: list[Scheduler] | None = None,
    output_dir: Path | None = None,
    write_position_logs: bool = False,
) -> ScenarioResult:
    """Run all schedulers against one scenario."""
    schedulers = schedulers or default_schedulers()
    config = BuildingConfig(
        num_elevators=scenario.num_elevators,
        min_floor=scenario.min_floor,
        max_floor=scenario.max_floor,
        max_passengers_per_elevator=scenario.capacity,
    )
    config.validate()
    requests = load_requests(scenario.csv_path)
    validate_requests(requests, config)

    log_dir = output_dir or Path("output/benchmarks") / scenario.name
    if not write_position_logs:
        log_dir.mkdir(parents=True, exist_ok=True)

    stats_by_algorithm: dict[str, AlgorithmStats] = {}
    for scheduler in schedulers:
        simulation = ElevatorSimulation(
            config=config,
            requests=requests,
            scheduler=scheduler,
            output_dir=log_dir,
            write_position_log=write_position_logs,
        )
        result = simulation.run()
        stats_by_algorithm[scheduler.name] = result.stats

    return ScenarioResult(scenario=scenario, stats_by_algorithm=stats_by_algorithm)


def run_all_scenarios(
    scenarios: tuple[BenchmarkScenario, ...] = BENCHMARK_SCENARIOS,
    schedulers: list[Scheduler] | None = None,
    output_dir: Path | None = None,
) -> list[ScenarioResult]:
    results: list[ScenarioResult] = []
    for scenario in scenarios:
        results.append(run_scenario(scenario, schedulers=schedulers, output_dir=output_dir))
    return results


def _best_algorithm(stats_map: dict[str, AlgorithmStats], key: str) -> str:
    if key == "avg_wait_time":
        return min(stats_map, key=lambda a: stats_map[a].avg_wait_time)
    if key == "max_wait_time":
        return min(stats_map, key=lambda a: stats_map[a].max_wait_time)
    if key == "avg_total_time":
        return min(stats_map, key=lambda a: stats_map[a].avg_total_time)
    if key == "final_time":
        return min(stats_map, key=lambda a: stats_map[a].final_time)
    raise ValueError(f"Unknown metric: {key}")


def format_comparison_report(results: list[ScenarioResult]) -> str:
    lines = [
        "Algorithm Benchmark Comparison",
        "=" * 72,
        "",
    ]
    for result in results:
        scenario = result.scenario
        lines.append(f"Scenario: {scenario.name}")
        lines.append(f"  {scenario.description}")
        lines.append(
            f"  Config: floors {scenario.min_floor}-{scenario.max_floor}, "
            f"{scenario.num_elevators} elevators, capacity {scenario.capacity}"
        )
        lines.append("")
        lines.append(
            f"  {'Algorithm':<28} {'AvgWait':>8} {'MaxWait':>8} {'WaitSpr':>8} "
            f"{'AvgTotal':>9} {'EndTime':>8}"
        )
        lines.append(f"  {'-' * 28} {'-' * 8} {'-' * 8} {'-' * 8} {'-' * 9} {'-' * 8}")
        for name in sorted(result.stats_by_algorithm):
            s = result.stats_by_algorithm[name]
            lines.append(
                f"  {name:<28} {s.avg_wait_time:8.2f} {s.max_wait_time:8d} "
                f"{s.wait_spread:8d} {s.avg_total_time:9.2f} {s.final_time:8d}"
            )
        best_avg_wait = _best_algorithm(result.stats_by_algorithm, "avg_wait_time")
        best_max_wait = _best_algorithm(result.stats_by_algorithm, "max_wait_time")
        best_avg_total = _best_algorithm(result.stats_by_algorithm, "avg_total_time")
        lines.append("")
        lines.append(f"  Best avg wait:   {best_avg_wait}")
        lines.append(f"  Best max wait:   {best_max_wait}  (fairness)")
        lines.append(f"  Best avg total:  {best_avg_total}  (efficiency)")
        lines.append("")
    return "\n".join(lines)


def write_comparison_csv(results: list[ScenarioResult], path: Path) -> None:
    fieldnames = [
        "scenario",
        "description",
        "algorithm",
        "avg_wait",
        "max_wait",
        "min_wait",
        "wait_spread",
        "wait_std_dev",
        "avg_total",
        "max_total",
        "min_total",
        "total_spread",
        "final_time",
        "num_passengers",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            for name, stats in sorted(result.stats_by_algorithm.items()):
                writer.writerow(
                    {
                        "scenario": result.scenario.name,
                        "description": result.scenario.description,
                        "algorithm": name,
                        "avg_wait": f"{stats.avg_wait_time:.2f}",
                        "max_wait": stats.max_wait_time,
                        "min_wait": stats.min_wait_time,
                        "wait_spread": stats.wait_spread,
                        "wait_std_dev": f"{stats.wait_std_dev:.2f}",
                        "avg_total": f"{stats.avg_total_time:.2f}",
                        "max_total": stats.max_total_time,
                        "min_total": stats.min_total_time,
                        "total_spread": stats.total_spread,
                        "final_time": stats.final_time,
                        "num_passengers": len(stats.passenger_stats),
                    }
                )
