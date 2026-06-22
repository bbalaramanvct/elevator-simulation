"""SCAN (elevator algorithm) scheduler."""

from elevator_simulation.models.elevator import Direction, Elevator
from elevator_simulation.models.passenger import Passenger

from .base import Scheduler

# Prefer cars already sweeping toward the passenger; penalize opposite-direction cars.
_OPPOSITE_DIRECTION_PENALTY = 500


class ScanScheduler(Scheduler):
    """Assign requests to the elevator best aligned with SCAN sweep direction."""

    @property
    def name(self) -> str:
        return "scan"

    def assign_elevator(
        self,
        passenger: Passenger,
        elevators: list[Elevator],
    ) -> Elevator:
        best = min(elevators, key=lambda e: self._scan_cost(e, passenger.start_floor))
        self._register_passenger(best, passenger)
        return best

    def _scan_cost(self, elevator: Elevator, start_floor: int) -> int:
        if elevator.direction == Direction.IDLE:
            return elevator.distance_to(start_floor)

        current = elevator.current_floor
        if elevator.direction == Direction.UP:
            if start_floor >= current:
                return start_floor - current
            upward_stops = [f for f in elevator.stops if f >= current] or [current]
            highest = max(upward_stops)
            return (
                (highest - current)
                + (highest - start_floor)
                + _OPPOSITE_DIRECTION_PENALTY
            )

        if start_floor <= current:
            return current - start_floor
        downward_stops = [f for f in elevator.stops if f <= current] or [current]
        lowest = min(downward_stops)
        return (
            (current - lowest)
            + (start_floor - lowest)
            + _OPPOSITE_DIRECTION_PENALTY
        )

    def _register_passenger(self, elevator: Elevator, passenger: Passenger) -> None:
        passenger.assigned_elevator_id = elevator.elevator_id
        elevator.add_stop(passenger.start_floor)
        elevator.add_stop(passenger.destination_floor)
