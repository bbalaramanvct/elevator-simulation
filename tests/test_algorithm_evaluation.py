"""Algorithm evaluation tests across benchmark scenarios."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from elevator_simulation.benchmark import (
    BENCHMARK_SCENARIOS,
    BenchmarkScenario,
    default_schedulers,
    run_scenario,
)
from elevator_simulation.schedulers import (
    NearestCarScheduler,
    RoundRobinScheduler,
    ScanScheduler,
)


@pytest.fixture(scope="module")
def core_schedulers():
    return [
        NearestCarScheduler(),
        RoundRobinScheduler(),
        ScanScheduler(),
    ]


@pytest.mark.parametrize("scenario", BENCHMARK_SCENARIOS, ids=lambda s: s.name)
def test_scenario_completes_for_all_algorithms(scenario: BenchmarkScenario, core_schedulers):
    result = run_scenario(scenario, schedulers=core_schedulers)
    csv_count = len(list(scenario.csv_path.read_text().strip().splitlines())) - 1
    for algorithm, stats in result.stats_by_algorithm.items():
        assert len(stats.passenger_stats) == csv_count, (
            f"{scenario.name}/{algorithm}: expected {csv_count} passengers, "
            f"got {len(stats.passenger_stats)}"
        )
        assert stats.max_wait_time >= stats.min_wait_time >= 0
        assert stats.max_total_time >= stats.min_total_time >= 0
        assert stats.final_time > 0


@pytest.mark.parametrize("scenario", BENCHMARK_SCENARIOS, ids=lambda s: s.name)
def test_all_passengers_assigned_an_elevator(scenario: BenchmarkScenario, core_schedulers):
    result = run_scenario(scenario, schedulers=core_schedulers)
    for algorithm, stats in result.stats_by_algorithm.items():
        for passenger in stats.passenger_stats:
            assert passenger.elevator_id >= 0, (
                f"{scenario.name}/{algorithm}/{passenger.passenger_id}: no elevator assigned"
            )


def test_fairness_outlier_nearest_car_beats_round_robin_on_max_wait():
    scenario = next(s for s in BENCHMARK_SCENARIOS if s.name == "fairness_outlier")
    result = run_scenario(
        scenario,
        schedulers=[NearestCarScheduler(), RoundRobinScheduler()],
    )
    nearest = result.stats_by_algorithm["nearest_car"]
    robin = result.stats_by_algorithm["round_robin"]
    assert nearest.max_wait_time <= robin.max_wait_time


def test_morning_rush_scan_matches_or_beats_round_robin_avg_total():
    scenario = next(s for s in BENCHMARK_SCENARIOS if s.name == "morning_rush")
    result = run_scenario(
        scenario,
        schedulers=[ScanScheduler(), RoundRobinScheduler()],
    )
    scan = result.stats_by_algorithm["scan"]
    robin = result.stats_by_algorithm["round_robin"]
    assert scan.avg_total_time <= robin.avg_total_time


def test_default_scheduler_list_includes_rush_hour_variants():
    schedulers = default_schedulers()
    names = {s.name for s in schedulers}
    assert "nearest_car" in names
    assert "scan" in names
    assert any(name.startswith("rush_hour_scan") for name in names)
    assert any(name.startswith("rush_hour_nearest_car") for name in names)
