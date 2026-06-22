"""Discrete-time elevator simulation engine."""

from __future__ import annotations

import csv
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from elevator_simulation.config import BuildingConfig
from elevator_simulation.models.elevator import Direction, Elevator
from elevator_simulation.models.passenger import Passenger, PassengerRequest
from elevator_simulation.schedulers.base import Scheduler
from elevator_simulation.stats import AlgorithmStats, compute_stats


@dataclass
class SimulationResult:
    algorithm: str
    stats: AlgorithmStats
    position_log_path: Path
    final_time: int


class ElevatorSimulation:
    """Runs a discrete-time simulation for one scheduler algorithm."""

    def __init__(
        self,
        config: BuildingConfig,
        requests: list[PassengerRequest],
        scheduler: Scheduler,
        output_dir: Path,
        write_position_log: bool = True,
    ) -> None:
        self.config = config
        self.requests = requests
        self.scheduler = scheduler
        self.output_dir = output_dir
        self.write_position_log = write_position_log
        self.time = 0
        self.elevators = self._create_elevators()
        self.waiting_passengers: list[Passenger] = []
        self.active_passengers: list[Passenger] = []
        self.completed_passengers: list[Passenger] = []
        self._requests_by_time = self._group_requests_by_time(requests)
        self._position_rows: list[dict[str, int | str]] = []

    def _create_elevators(self) -> list[Elevator]:
        start_floor = self.config.min_floor
        return [
            Elevator(
                elevator_id=i,
                current_floor=start_floor,
                max_capacity=self.config.max_passengers_per_elevator,
            )
            for i in range(self.config.num_elevators)
        ]

    @staticmethod
    def _group_requests_by_time(
        requests: list[PassengerRequest],
    ) -> dict[int, list[PassengerRequest]]:
        grouped: dict[int, list[PassengerRequest]] = {}
        for request in requests:
            grouped.setdefault(request.time, []).append(request)
        return grouped

    def run(self) -> SimulationResult:
        """Execute the simulation until all passengers are served."""
        self.scheduler.reset()
        max_time = self._estimate_max_time()
        safety_limit = max_time + 10_000

        while not self._all_passengers_complete() and self.time <= safety_limit:
            self._log_positions()
            self._process_arrivals()
            self._service_current_floors()
            self._move_elevators()
            self.time += 1

        if not self._all_passengers_complete():
            raise RuntimeError(
                f"Simulation exceeded safety limit at time {self.time} "
                f"for algorithm {self.scheduler.name}"
            )

        log_path = (
            self._write_position_log()
            if self.write_position_log
            else self.output_dir / f"elevator_positions_{self.scheduler.name}.csv"
        )
        stats = compute_stats(self.scheduler.name, self.completed_passengers, self.time - 1)
        return SimulationResult(
            algorithm=self.scheduler.name,
            stats=stats,
            position_log_path=log_path,
            final_time=self.time - 1,
        )

    def _estimate_max_time(self) -> int:
        latest_request = max((r.time for r in self.requests), default=0)
        max_travel = self.config.max_floor - self.config.min_floor
        return latest_request + len(self.requests) * max_travel * 2 + 100

    def _all_passengers_complete(self) -> bool:
        pending_requests = sum(
            len(items) for t, items in self._requests_by_time.items() if t >= self.time
        )
        on_elevator = any(p.is_on_elevator for p in self.active_passengers)
        return pending_requests == 0 and not self.waiting_passengers and not on_elevator

    def _process_arrivals(self) -> None:
        for request in self._requests_by_time.get(self.time, []):
            passenger = Passenger(
                passenger_id=request.passenger_id,
                start_floor=request.start_floor,
                destination_floor=request.destination_floor,
                request_time=request.time,
            )
            self.scheduler.assign_elevator(passenger, self.elevators)
            self.waiting_passengers.append(passenger)
        self._sync_elevator_stops()

    def _move_elevators(self) -> None:
        for elevator in self.elevators:
            if not elevator.has_stops():
                elevator.direction = Direction.IDLE
                continue

            elevator.direction = elevator.choose_direction()
            if elevator.direction == Direction.IDLE:
                continue

            elevator.move_one_floor()

    def _service_current_floors(self) -> None:
        for elevator in self.elevators:
            if elevator.current_floor in elevator.stops:
                self._service_floor(elevator)

    def _service_floor(self, elevator: Elevator) -> None:
        floor = elevator.current_floor
        if floor not in elevator.stops:
            return

        self._drop_off_passengers(elevator, floor)
        self._pick_up_passengers(elevator, floor)

        still_waiting_here = any(
            p.assigned_elevator_id == elevator.elevator_id and p.start_floor == floor
            for p in self.waiting_passengers
        )
        still_dropping_here = any(
            p.destination_floor == floor for p in elevator.passengers
        )
        reserved_for_waiting_dest = any(
            p.assigned_elevator_id == elevator.elevator_id
            and p.destination_floor == floor
            for p in self.waiting_passengers
        )
        if not still_waiting_here and not still_dropping_here and not reserved_for_waiting_dest:
            elevator.remove_stop(floor)

        if not elevator.has_stops():
            elevator.direction = Direction.IDLE

        self._sync_elevator_stops()

    def _sync_elevator_stops(self) -> None:
        """Ensure stop lists reflect all pending pickups and onboard destinations."""
        for elevator in self.elevators:
            for passenger in elevator.passengers:
                elevator.add_stop(passenger.destination_floor)
            for passenger in self.waiting_passengers:
                if passenger.assigned_elevator_id == elevator.elevator_id:
                    elevator.add_stop(passenger.start_floor)
                    elevator.add_stop(passenger.destination_floor)

    def _drop_off_passengers(self, elevator: Elevator, floor: int) -> None:
        remaining: list[Passenger] = []
        for passenger in elevator.passengers:
            if passenger.destination_floor == floor:
                passenger.dropoff_time = self.time
                self.completed_passengers.append(passenger)
            else:
                remaining.append(passenger)
        elevator.passengers = remaining
        self.active_passengers = [p for p in self.active_passengers if p.is_on_elevator]

    def _pick_up_passengers(self, elevator: Elevator, floor: int) -> None:
        if elevator.is_full:
            return

        still_waiting: list[Passenger] = []
        for passenger in self.waiting_passengers:
            if (
                passenger.assigned_elevator_id == elevator.elevator_id
                and passenger.start_floor == floor
                and not elevator.is_full
            ):
                passenger.pickup_time = self.time
                elevator.passengers.append(passenger)
                self.active_passengers.append(passenger)
            else:
                still_waiting.append(passenger)
        self.waiting_passengers = still_waiting

        self.active_passengers = [
            p for p in self.active_passengers if p.is_on_elevator
        ]

    def _log_positions(self) -> None:
        row: dict[str, int | str] = {"time": self.time}
        for elevator in self.elevators:
            row[f"elevator_{elevator.elevator_id}_floor"] = elevator.current_floor
            row[f"elevator_{elevator.elevator_id}_direction"] = elevator.direction.value
            row[f"elevator_{elevator.elevator_id}_passengers"] = elevator.passenger_count
        self._position_rows.append(row)

    def _write_position_log(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"elevator_positions_{self.scheduler.name}.csv"

        fieldnames = list(self._position_rows[0].keys()) if self._position_rows else ["time"]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self._position_rows)
        return path


def run_all_algorithms(
    config: BuildingConfig,
    requests: list[PassengerRequest],
    schedulers: Iterable[Scheduler],
    output_dir: Path,
) -> list[SimulationResult]:
    """Run the simulation once per scheduler algorithm."""
    results: list[SimulationResult] = []
    for scheduler in schedulers:
        simulation = ElevatorSimulation(
            config=config,
            requests=deepcopy(requests),
            scheduler=scheduler,
            output_dir=output_dir,
        )
        results.append(simulation.run())
    return results
