"""Simulation statistics and reporting."""

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Optional

from elevator_simulation.models.passenger import Passenger


@dataclass
class PassengerStats:
    passenger_id: str
    elevator_id: int
    wait_time: int
    travel_time: int
    total_time: int


@dataclass
class AlgorithmStats:
    algorithm: str
    passenger_stats: list[PassengerStats]
    min_wait_time: int
    max_wait_time: int
    avg_wait_time: float
    wait_spread: int
    wait_std_dev: float
    min_total_time: int
    max_total_time: int
    avg_total_time: float
    total_spread: int
    final_time: int = 0

def compute_stats(
    algorithm: str,
    passengers: list[Passenger],
    final_time: int = 0,
) -> AlgorithmStats:
    """Compute wait and total time statistics for completed passengers."""
    incomplete = [p.passenger_id for p in passengers if not p.is_complete]
    if incomplete:
        raise RuntimeError(
            f"Simulation ended before all passengers were served: {', '.join(incomplete)}"
        )

    passenger_stats = sorted(
        (
            PassengerStats(
                passenger_id=p.passenger_id,
                elevator_id=p.assigned_elevator_id if p.assigned_elevator_id is not None else -1,
                wait_time=p.wait_time or 0,
                travel_time=p.travel_time or 0,
                total_time=p.total_time or 0,
            )
            for p in passengers
        ),
        key=lambda s: s.passenger_id,
    )

    wait_times = [s.wait_time for s in passenger_stats]
    total_times = [s.total_time for s in passenger_stats]
    wait_std = pstdev(wait_times) if len(wait_times) > 1 else 0.0

    return AlgorithmStats(
        algorithm=algorithm,
        passenger_stats=passenger_stats,
        min_wait_time=min(wait_times),
        max_wait_time=max(wait_times),
        avg_wait_time=mean(wait_times),
        wait_spread=max(wait_times) - min(wait_times),
        wait_std_dev=wait_std,
        min_total_time=min(total_times),
        max_total_time=max(total_times),
        avg_total_time=mean(total_times),
        total_spread=max(total_times) - min(total_times),
        final_time=final_time,
    )


def format_stats_report(stats: AlgorithmStats) -> str:
    """Format statistics as human-readable text."""
    lines = [
        f"Algorithm: {stats.algorithm}",
        f"  Wait time  - min: {stats.min_wait_time}, max: {stats.max_wait_time}, "
        f"avg: {stats.avg_wait_time:.2f}, spread: {stats.wait_spread}",
        f"  Total time - min: {stats.min_total_time}, max: {stats.max_total_time}, "
        f"avg: {stats.avg_total_time:.2f}, spread: {stats.total_spread}",
        "  Per passenger (elevator, wait, travel, total):",
    ]
    for p in stats.passenger_stats:
        lines.append(
            f"    {p.passenger_id}: elevator={p.elevator_id}, "
            f"wait={p.wait_time}, travel={p.travel_time}, total={p.total_time}"
        )
    return "\n".join(lines)
